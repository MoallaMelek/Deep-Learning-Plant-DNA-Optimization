import base64
import io
import re
import numpy as np
import torch

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse

from app.cnn_inference import predict_cnn_from_bytes
from app.explainer import compute_shap_global, explain_crossing, _sanitize_features
from app.genomic import run_odm
from app.graphs import (
    build_correlation_heatmap,
    build_digital_twin_radar,
    build_model_comparison,
    build_montecarlo_chart,
    build_pareto_chart,
    build_shap_summary,
)
from app.models.wheat import PipelineRequest, RecommendRequest, SequenceRequest, VarietyRequest
from app.monte_carlo import simulate_crossing
from app.predictor import (
    classify_parent,
    get_parent_alternatives,
    get_snp_vector,
    predict_one,
    predict_crossing,
    recommend_crossings,
    simulate_montecarlo,
)
from app.schemas import CrossingPredictRequest, ExplainCrossingRequest, FastaGenerateRequest, MonteCarloRequest, ProfilePredictRequest
from app.utils.fasta_builder import build_fasta_content

router = APIRouter()


@router.get('/health')
def health(request: Request):
    return {
        'status': 'ok',
        'models_loaded': bool(getattr(request.app.state, 'models_loaded', False)),
        'cnn_available': bool(getattr(request.app.state, 'cnn_model', None) is not None),
        'cnn_status': getattr(request.app.state, 'cnn_status', 'unknown'),
    }


@router.post('/parent/classify')
def parent_classify(payload: VarietyRequest, request: Request):
    res = classify_parent(payload.variety_name, request.app.state)
    if not res.get('is_good_parent', False):
        return JSONResponse(status_code=400, content=res)
    return res


@router.post('/predict/profile')
def predict_profile(payload: ProfilePredictRequest, request: Request):
    profil = {
        'drought': payload.drought,
        'salt': payload.salt,
        'yield': payload.yield_,
        'disease': payload.disease,
    }
    profil = {k: v for k, v in profil.items() if v is not None}
    recs = recommend_crossings({'mode': 'profile', 'profile': profil, 'top_n': payload.top_n}, request.app.state)
    return {'top_partners': recs, 'recommended_crossing': recs[0] if recs else None}


@router.post('/crossings/recommend')
def crossings_recommend(payload: RecommendRequest, request: Request):
    data = payload.model_dump(by_alias=True)
    if payload.profile:
        data['profile'] = payload.profile.model_dump(by_alias=True)
    return recommend_crossings(data, request.app.state)


@router.post('/predict/features')
def predict_features(payload: dict, request: Request):
    state = request.app.state
    feature_cols = state.feature_cols
    got = set(payload.keys())
    need = set(feature_cols)
    if got != need:
        missing = sorted(list(need - got))
        extra = sorted(list(got - need))
        raise HTTPException(
            status_code=422,
            detail={"error": "payload must contain exactly 160 features", "missing": missing, "extra": extra},
        )
    x = np.array([[float(payload[c]) for c in feature_cols]], dtype=float)
    x_scaled = state.scaler.transform(x)
    with torch.no_grad():
        y = state.mlp(torch.tensor(x_scaled, dtype=torch.float32)).cpu().numpy()[0]
    preds = {"drought": float(y[0]), "salt": float(y[1]), "yield": float(y[2]), "disease": float(y[3])}
    return {k: round(float(preds[k]), 4) for k in ["drought", "salt", "yield", "disease"]}


@router.post('/crossings/predict')
def crossings_predict(payload: CrossingPredictRequest, request: Request):
    state = request.app.state
    if payload.variety_name_a and payload.variety_name_b:
        feat_a = get_snp_vector(payload.variety_name_a, state)
        feat_b = get_snp_vector(payload.variety_name_b, state)
    else:
        sa = payload.snps_a or {}
        sb = payload.snps_b or {}
        vec_a = {k: float(sa.get(k, 0)) for k in state.SNP_COLS}
        vec_b = {k: float(sb.get(k, 0)) for k in state.SNP_COLS}
        vec_a['snp_activity'] = float(sa.get('snp_activity', 0))
        vec_b['snp_activity'] = float(sb.get('snp_activity', 0))
        import pandas as pd

        feat_a = pd.Series(vec_a, index=state.feature_cols).fillna(0)
        feat_b = pd.Series(vec_b, index=state.feature_cols).fillna(0)

    pred = predict_crossing(feat_a, feat_b, state, model_name=payload.model, n_simulations=payload.n_simulations)
    return pred


@router.get('/montecarlo')
def montecarlo_get(parent_a: str, parent_b: str, n_simulations: int = 1000, model: str = "rf", request: Request = None):
    state = request.app.state
    feat_a = get_snp_vector(parent_a, state)
    feat_b = get_snp_vector(parent_b, state)
    mc = simulate_montecarlo(feat_a, feat_b, n_simulations, model, seed=42, state=state)
    return {
        "parent_a": parent_a,
        "parent_b": parent_b,
        "n_simulations": n_simulations,
        "mean": {k: round(float(v), 4) for k, v in mc["mean"].items()},
        "std": {k: round(float(v), 4) for k, v in mc["std"].items()},
        "min": {k: round(float(v), 4) for k, v in mc["min"].items()},
        "max": {k: round(float(v), 4) for k, v in mc["max"].items()},
        "p5": {k: round(float(v), 4) for k, v in mc["p5"].items()},
        "p95": {k: round(float(v), 4) for k, v in mc["p95"].items()},
    }


@router.get('/plante-ideale')
def plante_ideale(request: Request):
    state = request.app.state
    cdf = state.crossings_df.copy()
    if "score_fixe" not in cdf.columns:
        cdf["score_fixe"] = 0.4 * cdf["pred_drought"] + 0.3 * cdf["pred_salt"] + 0.2 * cdf["pred_yield"] + 0.1 * cdf["pred_disease"]
    crossing_col = "Croisement" if "Croisement" in cdf.columns else "crossing_name"
    row = cdf.sort_values("score_fixe", ascending=False).iloc[0]
    return {
        "crossing_name": str(row[crossing_col]),
        "drought": round(float(row["pred_drought"]), 4),
        "salt": round(float(row["pred_salt"]), 4),
        "yield": round(float(row["pred_yield"]), 4),
        "disease": round(float(row["pred_disease"]), 4),
        "score_fixe": round(float(row["score_fixe"]), 4),
    }


@router.post('/montecarlo/simulate')
def montecarlo_simulate(payload: MonteCarloRequest, request: Request):
    state = request.app.state
    if payload.crossing_name:
        mc = simulate_crossing(payload.crossing_name, state, payload.n_simulations)
        decision = mc.get("decision", {})
        is_good = decision.get("action") == "accept"
        out = {
            **mc,
            "is_good_crossing": is_good,
            "verdict": "bon" if is_good else "non",
        }
        if decision.get("action") == "trigger_step10":
            out["odm"] = run_odm(state, crossing_name=payload.crossing_name, generate_fasta=True, triggered_by="monte_carlo_decision")
        return out
    elif payload.variety_name_a and payload.variety_name_b:
        feat_a = get_snp_vector(payload.variety_name_a, state)
        feat_b = get_snp_vector(payload.variety_name_b, state)
    else:
        sa = payload.snps_a or {}
        sb = payload.snps_b or {}
        import pandas as pd

        feat_a = pd.Series({k: float(sa.get(k, 0)) for k in state.feature_cols}, index=state.feature_cols).fillna(0)
        feat_b = pd.Series({k: float(sb.get(k, 0)) for k in state.feature_cols}, index=state.feature_cols).fillna(0)

    return simulate_montecarlo(feat_a, feat_b, payload.n_simulations, payload.model, payload.seed, state)


@router.post('/explain/crossing')
def explain_crossing_route(payload: ExplainCrossingRequest, request: Request):
    state = request.app.state
    if payload.variety_name_a and payload.variety_name_b:
        crossing_name = f"{payload.variety_name_a}  x  {payload.variety_name_b}"
    else:
        raise HTTPException(status_code=422, detail='Pour explain/crossing, fournir variety_name_a et variety_name_b')
    return explain_crossing(crossing_name, state, top_n=payload.top_n)


@router.post('/crossings/recommend/image')
async def recommend_by_image(request: Request, file: UploadFile = File(...), top_n: int = 5):
    state = request.app.state
    img_bytes = await file.read()
    if not state.cnn_loaded or state.cnn_model is None:
        return {
            'error': 'wheat_classifier.h5 absent dans models_weights/',
            'message': 'Déposez wheat_classifier.h5 dans models_weights/ pour activer cette fonctionnalité.',
            'cnn_loaded': False,
        }

    classe, confiance, probs = None, None, None
    pred = predict_cnn_from_bytes(img_bytes, state.cnn_model)
    classe = pred['predicted_class']
    confiance = pred['confidence']
    probs = pred['probabilities']

    cnn_to_traits = {
        'healthy': {'drought': 0.50, 'salt': 0.50, 'yield_val': 0.75, 'disease': 0.50},
        'stress': {'drought': 0.85, 'salt': 0.70, 'yield_val': 0.50, 'disease': 0.40},
        'disease': {'drought': 0.40, 'salt': 0.40, 'yield_val': 0.45, 'disease': 0.90},
    }
    label_fr = {'healthy': 'Saine 🌾', 'stress': 'Stress hydrique / salin 🌵', 'disease': 'Maladie 🦠'}
    profil = cnn_to_traits[classe]

    crossings = state.crossings_df.copy()
    crossing_col = 'Croisement' if 'Croisement' in crossings.columns else 'crossing_name'
    crossings['score_cnn'] = (
        profil['drought'] * crossings['pred_drought']
        + profil['salt'] * crossings['pred_salt']
        + profil['yield_val'] * crossings['pred_yield']
        + profil['disease'] * crossings['pred_disease']
    )
    top = crossings.sort_values('score_cnn', ascending=False).head(top_n)

    return {
        'cnn_loaded': True,
        'cnn_class': classe,
        'cnn_label_fr': label_fr[classe],
        'cnn_confidence_pct': round(confiance * 100, 1),
        'cnn_probabilities': {k: round(v * 100, 1) for k, v in probs.items()},
        'mapped_profile': profil,
        'crossings': top[[crossing_col, 'pred_drought', 'pred_salt', 'pred_yield', 'pred_disease', 'score_cnn']].to_dict(orient='records'),
    }


@router.get('/graphs/digital-twin')
def graph_digital_twin(variety_name: str, model: str = 'rf', format: str = 'png', request: Request = None):
    state = request.app.state
    feat = get_snp_vector(variety_name, state)
    preds = predict_crossing(feat, feat, state, model_name=model)
    traits = {k: preds[k] for k in ['drought', 'salt', 'yield', 'disease']}
    b64 = build_digital_twin_radar(traits, variety_name)
    if format == 'json':
        return {'chart_type': 'radar', 'data': preds, 'image_b64': b64}
    return Response(content=base64.b64decode(b64), media_type='image/png')


@router.get('/graphs/montecarlo')
def graph_montecarlo(variety_name_a: str, variety_name_b: str, n_simulations: int = 500, model: str = 'rf', request: Request = None):
    state = request.app.state
    feat_a = get_snp_vector(variety_name_a, state)
    feat_b = get_snp_vector(variety_name_b, state)
    mc = simulate_montecarlo(feat_a, feat_b, n_simulations, model, seed=42, state=state)
    b64 = build_montecarlo_chart(mc)
    return Response(content=base64.b64decode(b64), media_type='image/png')


@router.get('/graphs/correlations')
def graph_correlations(top_n: int = 20, request: Request = None):
    b64 = build_correlation_heatmap(request.app.state.df_snp.reset_index(drop=False), top_n=top_n)
    return Response(content=base64.b64decode(b64), media_type='image/png')


@router.get('/graphs/model-comparison')
def graph_model_comparison(format: str = 'png'):
    metrics = {
        'rf': {'avg_R2': 0.80, 'avg_MAE': 0.11},
        'xgb': {'avg_R2': 0.82, 'avg_MAE': 0.10},
        'ridge': {'avg_R2': 0.74, 'avg_MAE': 0.13},
        'mlp': {'avg_R2': 0.79, 'avg_MAE': 0.11},
    }
    b64 = build_model_comparison(metrics)
    if format == 'json':
        return {'metrics': metrics, 'image_b64': b64}
    return Response(content=base64.b64decode(b64), media_type='image/png')


@router.get('/graphs/shap-summary')
def graph_shap_summary(model: str = 'rf', top_n: int = 10, request: Request = None):
    state = request.app.state
    try:
        import shap
        # Use a precomputed or smaller set for global SHAP to avoid timeouts
        _model_map = {
            'xgb': getattr(state, 'xgb', None),
            'rf': getattr(state, 'rf', None),
            'lgb': getattr(state, 'lgb', None),
            'ridge': getattr(state, 'ridge', None),
        }
        chosen = _model_map.get(model) or _model_map.get('rf')
        if chosen is None:
            raise ValueError('Model not loaded')

        # Take first 100 samples for faster global summary if too many
        X_all = _sanitize_features(state.pair_features)
        X_sample = X_all[:100] if len(X_all) > 100 else X_all
        
        est = chosen.estimators_[0] if hasattr(chosen, 'estimators_') else chosen
        explainer = shap.TreeExplainer(est)
        shap_vals = explainer.shap_values(X_sample)

        if isinstance(shap_vals, list): shap_vals = shap_vals[0]
        if isinstance(shap_vals, np.ndarray) and shap_vals.ndim == 3:
            shap_vals = shap_vals[:, :, 0]

        b64 = build_shap_summary(shap_vals, state.feature_cols, model=model, top_n=top_n)
        return Response(content=base64.b64decode(b64), media_type='image/png')
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f'SHAP indisponible: {exc}')


@router.post('/fasta/generate')
def generate_fasta(payload: FastaGenerateRequest, request: Request):
    state = request.app.state
    if payload.crossing_name:
        odm = run_odm(state, crossing_name=payload.crossing_name, generate_fasta=True, triggered_by="direct")
        fasta_str = odm.get("fasta_content", "")
        headers = {'Content-Disposition': 'attachment; filename="sequences_optimisees_ble_dur.fasta"'}
        return StreamingResponse(io.StringIO(fasta_str), media_type='text/plain', headers=headers)

    if not all(hasattr(state, x) for x in ['df_agront', 'alleles', 'resultats_odm']):
        raise HTTPException(status_code=503, detail='Ressources FASTA non chargées dans app.state')
    if not hasattr(state.df_agront, "columns") or "SNP" not in state.df_agront.columns or "trait" not in state.df_agront.columns:
        raise HTTPException(status_code=503, detail="df_agront incomplet: colonnes SNP/trait manquantes")
    if not payload.snp_names or not payload.traits:
        raise HTTPException(status_code=422, detail="Provide crossing_name OR (snp_names + traits)")
    fasta_str = build_fasta_content(payload.snp_names, payload.traits, state.df_agront, state.alleles, state.resultats_odm)
    headers = {'Content-Disposition': 'attachment; filename="sequences_optimisees_ble_dur.fasta"'}
    return StreamingResponse(io.StringIO(fasta_str), media_type='text/plain', headers=headers)


@router.get('/odm/{snp_name}')
def odm_for_snp(snp_name: str, request: Request):
    state = request.app.state
    d = getattr(state, "meilleur_oligo_par_snp", {})
    if snp_name not in d:
        odm = run_odm(state, snp_targets=[snp_name], generate_fasta=False, triggered_by="direct")
        if odm.get("results"):
            r = odm["results"][0]
            d[snp_name] = {
                "Séquence": r["best_oligo"]["sequence"],
                "Score_ODM": round(float(r["best_oligo"]["score_odm"]), 4),
                "Longueur": int(r["best_oligo"]["length_bp"]),
                "GC%": round(float(r["best_oligo"]["gc_pct"]), 4),
                "Tm": round(float(r["best_oligo"]["tm_celsius"]), 4),
            }
            state.meilleur_oligo_par_snp = d
    if snp_name not in d:
        raise HTTPException(status_code=404, detail=f"ODM not found for {snp_name}")
    return d[snp_name]


# Existing endpoints kept for compatibility
@router.get('/varieties')
def varieties(request: Request):
    return sorted(request.app.state.df_snp.reset_index(drop=False)['variety_name'].astype(str).unique().tolist())


@router.get('/varieties/{name}')
def variety_detail(name: str, request: Request):
    df = request.app.state.df_snp.reset_index(drop=False)
    mask = df['variety_name'].str.contains(re.escape(name), case=False, na=False)
    if not mask.any():
        raise HTTPException(status_code=404, detail='Variety not found')
    return df[mask].iloc[0].to_dict()


@router.post('/predict/sequence')
def predict_sequence(payload: SequenceRequest, request: Request):
    seq = ''.join([c for c in payload.fasta_sequence.upper() if c in 'ATCG'])
    if not seq:
        raise HTTPException(status_code=422, detail='Invalid FASTA sequence')
    gc = (seq.count('G') + seq.count('C')) / len(seq)
    tm = 2 * (seq.count('A') + seq.count('T')) + 4 * (seq.count('G') + seq.count('C'))
    return {'gc_pct': gc * 100, 'tm': tm}


@router.post('/pipeline/full')
def full_pipeline(payload: PipelineRequest, request: Request):
    state = request.app.state
    step1 = classify_parent(payload.variety_name, state)
    req = {'mode': payload.recommendation_mode, 'variety_name': payload.variety_name, 'top_n': payload.top_n_crossings}
    step2 = recommend_crossings(req, state)
    return {
        'variety_name': payload.variety_name,
        'step1_parent': step1,
        'step2_crossings': step2,
        'pipeline_complete': True,
    }