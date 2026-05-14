import React, { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Award,
  BarChart3,
  Beaker,
  CheckCircle2,
  Cpu,
  Database,
  Dna,
  FlaskConical,
  Gauge,
  Info,
  Layers,
  Loader2,
  Microscope,
  Network,
  Search,
  Server,
  Sparkles,
  TrendingUp,
  Zap,
} from 'lucide-react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  RadialLinearScale,
  Tooltip,
  Legend,
} from 'chart.js'
import { Bar, Radar, Scatter } from 'react-chartjs-2'
import * as THREE from 'three'
import {
  PHARMA_API_PREFIX,
  checkPharmaHealth,
  getLatestPharmaResults,
  getPharmaModels,
  getPharmaProteinDetail,
  getPharmaProteinOptions,
  getPharmaSuggestions,
  getPharmaStructureTrace,
  runPharmaPipeline,
  getPharmaDecisionDashboard,
} from '../services/pharmaApi'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  RadialLinearScale,
  Tooltip,
  Legend,
)

const MODEL_OPTIONS = [
  { label: 'Linear Regression', value: 'linear_regression' },
  { label: 'Ridge Regression', value: 'ridge' },
  { label: 'Random Forest', value: 'random_forest' },
  { label: 'XGBoost', value: 'xgboost' },
  { label: 'LightGBM', value: 'lightgbm' },
]

const PRIORITY_OPTIONS = [
  { label: 'Accuracy', value: 'accuracy' },
  { label: 'Speed', value: 'speed' },
  { label: 'Interpretability', value: 'interpretability' },
  { label: 'Balanced', value: 'balanced' },
]

const MODEL_LABELS = Object.fromEntries(MODEL_OPTIONS.map((model) => [model.value, model.label]))

const OVERVIEW_CARDS = [
  {
    title: 'Protein & DNA Pipeline',
    icon: Dna,
    text: 'Retrieves UniProt proteins, builds host-optimized DNA, and engineers codon, sequence, and structure descriptors.',
  },
  {
    title: 'Model Lab',
    icon: BarChart3,
    text: 'Benchmarks regressors with grouped splits, baseline gating, speed scoring, and priority-based recommendations.',
  },
  {
    title: 'Explainable AI',
    icon: Sparkles,
    text: 'Uses feature importance and diagnostics to explain drivers such as CAI, GC3, rare codons, and host identity.',
  },
  {
    title: 'Structure Context',
    icon: Layers,
    text: 'Keeps the original project story around AlphaFold structure, hydrophobicity, stability, and secondary structure.',
  },
]

const PIPELINE_STEPS = ['UniProt', 'Host DNA', 'Features', 'Grouped Split', 'Model Lab', 'Decision']

const FALLBACK_FEATURES = ['CAI', 'GC content', 'rare codon ratio', 'protein length', 'stability score']

const CHART_COLORS = {
  emerald: '#10b981',
  emeraldSoft: 'rgba(16, 185, 129, 0.18)',
  slate: '#0f172a',
  blue: '#2563eb',
  amber: '#f59e0b',
  rose: '#e11d48',
}

const formatNumber = (value, digits = 4) => {
  const number = Number(value)
  if (!Number.isFinite(number)) return 'N/A'
  return number.toFixed(digits)
}

const formatPercent = (value, digits = 1) => {
  const number = Number(value)
  if (!Number.isFinite(number)) return 'N/A'
  return `${number.toFixed(digits)}%`
}

const formatTime = (value) => {
  const number = Number(value)
  if (!Number.isFinite(number)) return 'N/A'
  return `${number.toFixed(number >= 1 ? 3 : 4)}s`
}

const readable = (value) => {
  if (!value) return 'N/A'
  return MODEL_LABELS[value] || String(value).replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

const safeMetrics = (payload) => payload?.metrics || payload?.model_lab?.metrics || {}

const getModelLab = (payload) => {
  const metrics = safeMetrics(payload)
  return payload?.model_lab && Object.keys(payload.model_lab).length ? payload.model_lab : metrics?.model_lab || {}
}

const getRecommended = (payload, priority) => {
  const modelLab = getModelLab(payload)
  const metrics = safeMetrics(payload)
  const recommendations = modelLab?.priority_recommendations || metrics?.priority_recommendations || {}
  const recommendation = recommendations?.[priority] || {}
  return {
    model: payload?.recommended_model || recommendation.model || metrics?.recommended_model_by_default_priority || metrics?.best_model_name,
    displayName:
      recommendation.display_name ||
      payload?.recommended_model_label ||
      metrics?.recommended_model_label_by_default_priority,
    reason: payload?.recommended_model_reason || recommendation.reason || metrics?.recommended_model_reason_by_default_priority || '',
  }
}

const normalizeArray = (value) => {
  if (Array.isArray(value)) return value
  if (typeof value === 'string') {
    return value
      .split(/[\s,]+/)
      .map((item) => item.trim())
      .filter(Boolean)
  }
  return []
}

const numberArray = (value) => normalizeArray(value).map(Number).filter((item) => Number.isFinite(item))

const extractComparisonRows = (payload) => {
  const modelLab = getModelLab(payload)
  if (Array.isArray(modelLab?.comparison_rows) && modelLab.comparison_rows.length) {
    return modelLab.comparison_rows
  }

  const comparison = payload?.model_comparison || safeMetrics(payload)?.model_comparison || {}
  if (Array.isArray(comparison)) return comparison

  if (comparison && typeof comparison === 'object') {
    return Object.entries(comparison).map(([model, values]) => ({
      model,
      display_name: readable(model),
      ...(values || {}),
    }))
  }

  return []
}

const extractResultSummary = (payload, priority) => {
  if (!payload) return null
  const rows = extractComparisonRows(payload)
  const recommended = getRecommended(payload, priority)
  const metrics = safeMetrics(payload)
  const targetModel = recommended.model
  const selectedRow = rows.find((row) => row.model === targetModel) || rows[0] || metrics

  return {
    recommendedModel: recommended.displayName || readable(targetModel || selectedRow?.model),
    reason: recommended.reason,
    mae: selectedRow?.validation_mae ?? selectedRow?.mae ?? metrics?.validation_mae ?? metrics?.mae,
    rmse: selectedRow?.validation_rmse ?? selectedRow?.rmse ?? metrics?.validation_rmse ?? metrics?.rmse,
    r2: selectedRow?.validation_r2 ?? selectedRow?.r2 ?? metrics?.validation_r2 ?? metrics?.r2,
    trainingTime: selectedRow?.training_time_seconds ?? metrics?.training_time_seconds,
    predictionTime: selectedRow?.prediction_time_seconds ?? metrics?.prediction_time_seconds,
    priority: payload.priority || priority,
    rowsGenerated: payload.rows_generated || payload.manifest?.rows_generated || metrics?.total_samples,
    keyword: payload.keyword || payload.manifest?.keyword || payload.metadata?.keyword,
    cvRmse: selectedRow?.cv_rmse_mean ?? metrics?.cv_rmse_mean,
    cvStd: selectedRow?.cv_rmse_std ?? metrics?.cv_rmse_std,
  }
}

const selectedModelMetrics = (payload, priority) => {
  const metrics = safeMetrics(payload)
  const recommended = getRecommended(payload, priority)
  const modelName = recommended.model || metrics.best_model_name || metrics.best_model
  return metrics?.model_comparison?.[modelName] || metrics
}

const extractFeatureImportance = (payload, priority) => {
  const metrics = safeMetrics(payload)
  const selected = selectedModelMetrics(payload, priority)
  const table =
    selected?.feature_importance_table ||
    metrics.feature_importance_table ||
    metrics.explainability?.feature_importance_table ||
    metrics.explainability?.top_features ||
    metrics.top_features ||
    []

  if (Array.isArray(table) && table.length) {
    return table
      .map((item) => ({
        feature: item.feature || item.name || item.column || 'Feature',
        importance: Number(item.importance ?? item.value ?? item.score ?? 0),
      }))
      .filter((item) => Number.isFinite(item.importance))
      .sort((a, b) => b.importance - a.importance)
      .slice(0, 8)
  }

  const names = normalizeArray(selected?.feature_names || metrics.feature_names)
  const importances = numberArray(selected?.feature_importances || metrics.feature_importances)

  if (names.length && importances.length) {
    return names
      .slice(0, importances.length)
      .map((feature, index) => ({ feature, importance: importances[index] || 0 }))
      .filter((item) => Number.isFinite(item.importance))
      .sort((a, b) => b.importance - a.importance)
      .slice(0, 8)
  }

  return []
}

const extractPredictionPairs = (payload, priority) => {
  const metrics = selectedModelMetrics(payload, priority)
  const actual =
    numberArray(metrics.validation_actual_values).length > 0
      ? numberArray(metrics.validation_actual_values)
      : numberArray(metrics.test_actual_values || metrics.actual_values)
  const predicted =
    numberArray(metrics.validation_predicted_values).length > 0
      ? numberArray(metrics.validation_predicted_values)
      : numberArray(metrics.test_predicted_values || metrics.predicted_values)

  return actual
    .slice(0, Math.min(actual.length, predicted.length, 70))
    .map((value, index) => ({ x: value, y: predicted[index] }))
}

const extractResidualBins = (payload, priority) => {
  const metrics = selectedModelMetrics(payload, priority)
  const residuals =
    numberArray(metrics.validation_residual_values).length > 0
      ? numberArray(metrics.validation_residual_values)
      : numberArray(metrics.test_residual_values || metrics.residual_values)

  if (!residuals.length) return []

  const min = Math.min(...residuals)
  const max = Math.max(...residuals)
  const binCount = 8
  const span = max - min || 1
  const bins = Array.from({ length: binCount }, (_, index) => ({
    label: `${(min + (span * index) / binCount).toFixed(2)}`,
    count: 0,
  }))

  residuals.forEach((value) => {
    const index = Math.min(binCount - 1, Math.floor(((value - min) / span) * binCount))
    bins[index].count += 1
  })

  return bins
}

const extractHostRows = (payload) => {
  const rowsPerHost = payload?.quality?.rows_per_plant_host || payload?.quality?.summary?.rows_per_plant_host || {}
  return Object.entries(rowsPerHost).map(([host, rows]) => ({ host, rows: Number(rows) || 0 }))
}

const extractPriorityScores = (payload, priority) => {
  const rows = extractComparisonRows(payload)
  const recommended = getRecommended(payload, priority)
  const active = rows.find((row) => row.model === recommended.model) || rows[0] || safeMetrics(payload)
  return [
    Number(active?.accuracy_score ?? 0),
    Number(active?.speed_score ?? 0),
    Number(active?.interpretability_score_normalized ?? (Number(active?.interpretability_score) / 5) * 100 ?? 0),
  ].map((value) => (Number.isFinite(value) ? value : 0))
}

const codonChunks = (sequence, maxCodons = 42) => {
  const clean = String(sequence || '').toUpperCase()
  const chunks = []
  for (let index = 0; index < clean.length - (clean.length % 3) && chunks.length < maxCodons; index += 3) {
    chunks.push(clean.slice(index, index + 3))
  }
  return chunks
}

const chartBaseOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        color: '#64748b',
        boxWidth: 10,
        font: { size: 11, weight: 'bold' },
      },
    },
    tooltip: {
      backgroundColor: '#0f172a',
      padding: 14,
      cornerRadius: 12,
      displayColors: true,
    },
  },
}

const Pharmaceutical = () => {
  const [form, setForm] = useState({
    keyword: 'insulin',
    protein_limit: 80,
    model: 'ridge',
    priority: 'balanced',
  })
  const [backendOnline, setBackendOnline] = useState(null)
  const [models, setModels] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [results, setResults] = useState(null)
  const [proteinOptions, setProteinOptions] = useState([])
  const [selectedAccession, setSelectedAccession] = useState('')
  const [selectedHost, setSelectedHost] = useState('')
  const [proteinDetail, setProteinDetail] = useState(null)
  const [structureTrace, setStructureTrace] = useState(null)
  const [loadingStructure, setLoadingStructure] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingLatest, setLoadingLatest] = useState(false)
  const [decisionData, setDecisionData] = useState(null)
  const [loadingDecision, setLoadingDecision] = useState(false)
  const [error, setError] = useState('')

  const summary = useMemo(() => extractResultSummary(results, form.priority), [results, form.priority])
  const comparisonRows = useMemo(() => extractComparisonRows(results), [results])
  const featureImportance = useMemo(() => extractFeatureImportance(results, form.priority), [results, form.priority])
  const predictionPairs = useMemo(() => extractPredictionPairs(results, form.priority), [results, form.priority])
  const residualBins = useMemo(() => extractResidualBins(results, form.priority), [results, form.priority])
  const hostRows = useMemo(() => extractHostRows(results), [results])
  const priorityScores = useMemo(() => extractPriorityScores(results, form.priority), [results, form.priority])

  const loadProteinOptions = async () => {
    try {
      const payload = await getPharmaProteinOptions()
      const proteins = payload.proteins || []
      setProteinOptions(proteins)
      if (proteins.length && !selectedAccession) {
        setSelectedAccession(proteins[0].accession)
        setSelectedHost(proteins[0].hosts?.[0] || '')
      }
    } catch {
      setProteinOptions([])
    }
  }

  const loadDecisionDashboard = async () => {
    setLoadingDecision(true)
    try {
      const data = await getPharmaDecisionDashboard()
      setDecisionData(data.status === 'success' ? data : null)
    } catch {
      setDecisionData(null)
    } finally {
      setLoadingDecision(false)
    }
  }

  useEffect(() => {
    const initialize = async () => {
      try {
        await checkPharmaHealth()
        setBackendOnline(true)
        setError('')
        const [modelPayload, latestPayload] = await Promise.allSettled([
          getPharmaModels(),
          getLatestPharmaResults(),
        ])
        if (modelPayload.status === 'fulfilled') setModels(modelPayload.value.models || [])
        if (latestPayload.status === 'fulfilled' && latestPayload.value.status === 'success') {
          setResults(latestPayload.value)
        }
        await Promise.all([loadProteinOptions(), loadDecisionDashboard()])
      } catch {
        setBackendOnline(false)
        setError('Backend unavailable. Start the shared API with: python -m uvicorn main_combine:app --reload')
      }
    }

    initialize()
  }, [])

  useEffect(() => {
    if (backendOnline !== true || !selectedAccession) return undefined

    let cancelled = false
    const loadProteinContext = async () => {
      setLoadingStructure(true)
      try {
        const detail = await getPharmaProteinDetail({ accession: selectedAccession, host: selectedHost })
        if (cancelled) return
        setProteinDetail(detail.status === 'success' ? detail : null)
        if (detail.status === 'success' && detail.selected_host && detail.selected_host !== selectedHost) {
          setSelectedHost(detail.selected_host)
        }

        const trace = await getPharmaStructureTrace({
          accession: detail.accession || selectedAccession,
          host: detail.selected_host || selectedHost,
        })
        if (!cancelled) setStructureTrace(trace.status === 'success' ? trace : null)
      } catch {
        if (!cancelled) {
          setProteinDetail(null)
          setStructureTrace(null)
        }
      } finally {
        if (!cancelled) setLoadingStructure(false)
      }
    }

    loadProteinContext()
    return () => {
      cancelled = true
    }
  }, [backendOnline, selectedAccession, selectedHost])

  useEffect(() => {
    const query = form.keyword.trim()
    if (!query || backendOnline !== true) {
      setSuggestions([])
      return undefined
    }

    const timer = window.setTimeout(async () => {
      try {
        const payload = await getPharmaSuggestions(query)
        setSuggestions(payload.suggestions || [])
      } catch {
        setSuggestions([])
      }
    }, 350)

    return () => window.clearTimeout(timer)
  }, [form.keyword, backendOnline])

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const handleRun = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const payload = await runPharmaPipeline({
        keyword: form.keyword,
        protein_limit: Number(form.protein_limit),
        model: form.model,
        priority: form.priority,
      })
      setBackendOnline(true)
      setResults(payload)
      await Promise.all([loadProteinOptions(), loadDecisionDashboard()])
      if (payload.status === 'error') setError(payload.message || 'Pipeline returned an error.')
    } catch {
      setBackendOnline(false)
      setError('Backend unavailable. Start the shared API with: python -m uvicorn main_combine:app --reload')
    } finally {
      setLoading(false)
    }
  }

  const handleLoadLatest = async () => {
    setLoadingLatest(true)
    setError('')
    try {
      const payload = await getLatestPharmaResults()
      setBackendOnline(true)
      if (payload.status === 'success') {
        setResults(payload)
        await Promise.all([loadProteinOptions(), loadDecisionDashboard()])
      } else {
        setResults(null)
        setError(payload.message || 'No latest results were found.')
      }
    } catch {
      setBackendOnline(false)
      setError('Backend unavailable. Start the shared API with: python -m uvicorn main_combine:app --reload')
    } finally {
      setLoadingLatest(false)
    }
  }

  return (
    <div className="py-12 container mx-auto px-4">
      <div className="max-w-7xl mx-auto">
        <header className="mb-12">
          <div className="flex items-center space-x-3 mb-4 text-emerald-600 font-bold tracking-widest text-sm uppercase">
            <Microscope className="w-5 h-5" />
            <span>Pharma Model Lab</span>
          </div>
          <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-8 items-center">
            <div>
              <h1 className="text-4xl lg:text-5xl font-bold text-slate-900 mb-4">Plant Protein Expression Intelligence</h1>
              <p className="text-slate-600 text-lg max-w-3xl">
                Machine learning decision-support for codon optimization and plant-based protein expression.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <div className="inline-flex items-center gap-2 bg-amber-50 text-amber-700 border border-amber-100 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-widest w-fit">
                  <AlertTriangle className="w-4 h-4" />
                  Proxy model - not wet-lab validation
                </div>
                <BackendBadge online={backendOnline} />
              </div>
            </div>
            <ProteinStructureScene trace={structureTrace} detail={proteinDetail} loading={loadingStructure} />
          </div>
        </header>

        {error && (
          <div className="bg-amber-50 border border-amber-100 text-amber-800 rounded-2xl p-5 mb-8 flex items-start gap-3">
            <Info className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <p className="text-sm font-semibold">{error}</p>
          </div>
        )}

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          {OVERVIEW_CARDS.map((card) => (
            <FeatureCard key={card.title} {...card} />
          ))}
        </div>

        <ProteinExplorer
          proteins={proteinOptions}
          selectedAccession={selectedAccession}
          selectedHost={selectedHost}
          detail={proteinDetail}
          trace={structureTrace}
          loading={loadingStructure}
          onSelectAccession={(accession) => {
            const protein = proteinOptions.find((item) => item.accession === accession)
            setSelectedAccession(accession)
            setSelectedHost(protein?.hosts?.[0] || '')
          }}
          onSelectHost={setSelectedHost}
        />

        <DnaOptimizationImpact detail={proteinDetail} />

        <div className="grid lg:grid-cols-3 gap-8 mb-12">
          <PipelineForm
            form={form}
            models={models}
            suggestions={suggestions}
            loading={loading}
            loadingLatest={loadingLatest}
            onChange={updateField}
            onRun={handleRun}
            onLoadLatest={handleLoadLatest}
          />

          <section className="lg:col-span-2 bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Run Intelligence</h2>
                <p className="text-slate-500 text-sm">Grouped model results, latest artifacts, and proxy-expression diagnostics.</p>
              </div>
              {summary?.keyword && (
                <span className="bg-slate-50 border border-slate-100 rounded-full px-4 py-2 text-xs font-bold text-slate-500 uppercase tracking-widest w-fit">
                  Keyword: {summary.keyword}
                </span>
              )}
            </div>

            {summary ? (
              <>
                <div className="bg-slate-50 rounded-3xl border border-slate-100 p-6 mb-6">
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div>
                      <div className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-2">
                        Recommended model
                      </div>
                      <h3 className="text-3xl font-black text-slate-900">{summary.recommendedModel}</h3>
                      {summary.reason && <p className="text-sm text-slate-500 mt-2 max-w-2xl">{summary.reason}</p>}
                    </div>
                    <span className="bg-emerald-100 text-emerald-700 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-widest w-fit">
                      {readable(summary.priority)}
                    </span>
                  </div>
                </div>

                <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
                  <MetricCard label="MAE" value={formatNumber(summary.mae)} />
                  <MetricCard label="RMSE" value={formatNumber(summary.rmse)} />
                  <MetricCard label="R2" value={formatNumber(summary.r2)} />
                  <MetricCard label="Training" value={formatTime(summary.trainingTime)} />
                  <MetricCard label="Prediction" value={formatTime(summary.predictionTime)} />
                </div>

                <div className="mt-6 grid sm:grid-cols-3 gap-4">
                  <MetricCard label="Rows generated" value={summary.rowsGenerated || 'N/A'} />
                  <MetricCard label="CV RMSE" value={formatNumber(summary.cvRmse)} />
                  <MetricCard label="CV Std" value={formatNumber(summary.cvStd)} />
                </div>
              </>
            ) : (
              <EmptyState />
            )}
          </section>
        </div>

        <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm mb-12">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
            <div className="flex items-center gap-3">
              <Gauge className="w-6 h-6 text-emerald-600" />
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Model Lab Comparison</h2>
                <p className="text-slate-500 text-sm">Model accuracy, speed, and interpretability in one lab view.</p>
              </div>
            </div>
            <span className="bg-slate-50 border border-slate-100 rounded-full px-4 py-2 text-xs font-bold text-slate-500 uppercase tracking-widest w-fit">
              {comparisonRows.length || 0} models reported
            </span>
          </div>

          {comparisonRows.length ? (
            <div className="grid lg:grid-cols-5 gap-8">
              <div className="lg:col-span-3 h-[360px]">
                <ModelComparisonChart rows={comparisonRows} />
              </div>
              <div className="lg:col-span-2 h-[360px]">
                <PriorityRadarChart scores={priorityScores} />
              </div>
            </div>
          ) : (
            <div className="bg-slate-50 border border-slate-100 rounded-2xl p-8 text-center text-slate-500 font-semibold">
              No results yet. Run the pipeline or load latest results.
            </div>
          )}
        </section>

        <div className="grid lg:grid-cols-2 gap-8 mb-12">
          <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
            <div className="flex items-center gap-3 mb-6">
              <Cpu className="w-6 h-6 text-emerald-600" />
              <div>
              <h2 className="text-2xl font-bold text-slate-900">SHAP-Style Attribution</h2>
              <p className="text-slate-500 text-sm">Global feature drivers from saved model importance artifacts.</p>
              </div>
            </div>
            {featureImportance.length ? (
              <div className="h-[390px]">
                <FeatureImportanceChart features={featureImportance} />
              </div>
            ) : (
              <div className="bg-slate-50 border border-slate-100 rounded-2xl p-6">
                <p className="text-slate-600 font-semibold mb-4">SHAP/global attribution will appear after pipeline execution.</p>
                <div className="flex flex-wrap gap-2">
                  {FALLBACK_FEATURES.map((feature) => (
                    <span key={feature} className="bg-white border border-slate-200 rounded-full px-4 py-2 text-xs font-bold text-slate-500">
                      {feature}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </section>

          <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
            <div className="flex items-center gap-3 mb-6">
              <Activity className="w-6 h-6 text-emerald-600" />
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Prediction Diagnostics</h2>
                <p className="text-slate-500 text-sm">Predicted-vs-proxy and residual distribution from saved metrics.</p>
              </div>
            </div>
            {predictionPairs.length ? (
              <div className="grid sm:grid-cols-2 gap-5">
                <div className="h-[330px]">
                  <PredictionScatterChart pairs={predictionPairs} />
                </div>
                <div className="h-[330px]">
                  <ResidualChart bins={residualBins} />
                </div>
              </div>
            ) : (
              <div className="bg-slate-50 border border-slate-100 rounded-2xl p-8 text-center text-slate-500 font-semibold">
                Diagnostics appear when metrics include predicted and residual vectors.
              </div>
            )}
          </section>
        </div>

        <div className="grid lg:grid-cols-3 gap-8 mb-12">
          <section className="lg:col-span-2 bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
            <div className="flex items-center gap-3 mb-6">
              <Database className="w-6 h-6 text-emerald-600" />
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Dataset Quality</h2>
                <p className="text-slate-500 text-sm">Protein retrieval, structure enrichment, and host expansion from the latest run.</p>
              </div>
            </div>
            <QualityDashboard payload={results} hostRows={hostRows} />
          </section>

          <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
            <div className="flex items-center gap-3 mb-6">
              <Network className="w-6 h-6 text-emerald-600" />
              <h2 className="text-2xl font-bold text-slate-900">Architecture</h2>
            </div>
            <div className="space-y-4">
              {PIPELINE_STEPS.map((step, index) => (
                <div key={step} className="relative bg-slate-50 border border-slate-100 rounded-2xl p-4 flex items-center justify-between">
                  <div>
                    <div className="text-[10px] font-black uppercase tracking-widest text-emerald-600 mb-1">
                      Step {index + 1}
                    </div>
                    <div className="font-bold text-slate-900">{step}</div>
                  </div>
                  {index < PIPELINE_STEPS.length - 1 ? (
                    <ArrowRight className="w-4 h-4 text-slate-300" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  )}
                </div>
              ))}
            </div>
          </section>
        </div>

        <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm mb-12">
          <div className="flex items-center gap-3 mb-6">
            <BarChart3 className="w-6 h-6 text-emerald-600" />
            <h2 className="text-2xl font-bold text-slate-900">Model Comparison Table</h2>
          </div>
          {comparisonRows.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-100">
                  <tr>
                    <th className="py-4 pr-4">Model</th>
                    <th className="py-4 pr-4">MAE</th>
                    <th className="py-4 pr-4">RMSE</th>
                    <th className="py-4 pr-4">R2</th>
                    <th className="py-4 pr-4">Training time</th>
                    <th className="py-4 pr-4">Prediction time</th>
                    <th className="py-4 pr-4">Best use case</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm">
                  {comparisonRows.map((row) => (
                    <tr key={row.model || row.display_name}>
                      <td className="py-4 pr-4 font-bold text-slate-900">{row.display_name || readable(row.model)}</td>
                      <td className="py-4 pr-4 text-slate-600">{formatNumber(row.validation_mae ?? row.mae)}</td>
                      <td className="py-4 pr-4 text-slate-600">{formatNumber(row.validation_rmse ?? row.rmse)}</td>
                      <td className="py-4 pr-4 text-slate-600">{formatNumber(row.validation_r2 ?? row.r2)}</td>
                      <td className="py-4 pr-4 text-slate-600">{formatTime(row.training_time_seconds)}</td>
                      <td className="py-4 pr-4 text-slate-600">{formatTime(row.prediction_time_seconds)}</td>
                      <td className="py-4 pr-4 text-slate-500">{row.recommended_for || row.best_use_case || 'Decision support'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="bg-slate-50 border border-slate-100 rounded-2xl p-8 text-center text-slate-500 font-semibold">
              No results yet. Run the pipeline or load latest results.
            </div>
          )}
        </section>

        <DecisionDashboard data={decisionData} loading={loadingDecision} />

        <div className="grid lg:grid-cols-2 gap-8">
          <div className="bg-blue-50 rounded-2xl p-6 flex items-start space-x-4 border border-blue-100">
            <Info className="w-6 h-6 text-blue-600 flex-shrink-0" />
            <div>
              <h4 className="font-bold text-blue-900">Scientific Limitation</h4>
              <p className="text-blue-800 text-sm">
                This module uses a simulated proxy target. Results support early-stage ranking and decision support, but do not replace biological experiments.
              </p>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <Server className="w-5 h-5 text-emerald-600" />
              <h4 className="font-bold text-slate-900">FastAPI Backend</h4>
            </div>
            <div className="grid sm:grid-cols-2 gap-3">
              {[
                `GET ${PHARMA_API_PREFIX}/health`,
                `GET ${PHARMA_API_PREFIX}/models`,
                `POST ${PHARMA_API_PREFIX}/run-pipeline`,
                `GET ${PHARMA_API_PREFIX}/latest-results`,
              ].map((endpoint) => (
                <span key={endpoint} className="bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 text-xs font-bold text-slate-600">
                  {endpoint}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const PipelineForm = ({ form, models, suggestions, loading, loadingLatest, onChange, onRun, onLoadLatest }) => (
  <section className="lg:col-span-1 bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
    <div className="flex items-center gap-3 mb-6">
      <div className="p-3 bg-emerald-50 rounded-2xl text-emerald-600 border border-emerald-100">
        <Beaker className="w-6 h-6" />
      </div>
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Run Pipeline</h2>
        <p className="text-xs text-slate-400 font-bold uppercase tracking-widest">
          FastAPI decision support
        </p>
      </div>
    </div>

    <form className="space-y-5" onSubmit={onRun}>
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">Protein keyword</label>
        <div className="relative">
          <Search className="w-4 h-4 text-slate-300 absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            list="pharma-keyword-suggestions"
            className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-11 pr-4 py-3 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
            value={form.keyword}
            onChange={(event) => onChange('keyword', event.target.value)}
            placeholder="insulin"
          />
          <datalist id="pharma-keyword-suggestions">
            {suggestions.map((suggestion, index) => (
              <option
                key={`${suggestion.keyword || suggestion.label || index}`}
                value={suggestion.keyword || suggestion.label || suggestion.value || ''}
              />
            ))}
          </datalist>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">Protein limit</label>
        <input
          type="number"
          min="1"
          className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
          value={form.protein_limit}
          onChange={(event) => onChange('protein_limit', event.target.value)}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">Model selection</label>
        <select
          className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
          value={form.model}
          onChange={(event) => onChange('model', event.target.value)}
        >
          {MODEL_OPTIONS.map((model) => {
            const apiModel = models.find((item) => item.name === model.value)
            return (
              <option key={model.value} value={model.value} disabled={apiModel?.available === false}>
                {model.label}{apiModel?.available === false ? ' - unavailable' : ''}
              </option>
            )
          })}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">Decision priority</label>
        <select
          className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
          value={form.priority}
          onChange={(event) => onChange('priority', event.target.value)}
        >
          {PRIORITY_OPTIONS.map((priority) => (
            <option key={priority.value} value={priority.value}>{priority.label}</option>
          ))}
        </select>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-emerald-600 text-white px-6 py-4 rounded-2xl font-bold hover:bg-emerald-700 transition-all shadow-lg shadow-emerald-200 flex items-center justify-center gap-2 disabled:opacity-60"
      >
        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <FlaskConical className="w-5 h-5" />}
        Run Pharma Pipeline
      </button>

      <button
        type="button"
        onClick={onLoadLatest}
        disabled={loadingLatest}
        className="w-full border border-slate-200 bg-white text-slate-700 px-6 py-3 rounded-2xl font-semibold hover:bg-slate-50 transition-all flex items-center justify-center gap-2 disabled:opacity-60"
      >
        {loadingLatest ? <Loader2 className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
        Load Latest Results
      </button>
    </form>
  </section>
)

const ProteinExplorer = ({
  proteins,
  selectedAccession,
  selectedHost,
  detail,
  trace,
  loading,
  onSelectAccession,
  onSelectHost,
}) => {
  const hosts = detail?.hosts?.length
    ? detail.hosts
    : proteins.find((item) => item.accession === selectedAccession)?.hosts || []

  return (
    <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm mb-12">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5 mb-8">
        <div className="flex items-center gap-3">
          <Layers className="w-6 h-6 text-emerald-600" />
          <div>
            <h2 className="text-2xl font-bold text-slate-900">AlphaFold Protein Explorer</h2>
            <p className="text-slate-500 text-sm">
              Select a generated protein and plant host to inspect structure, host-specific DNA, and optimization signals.
            </p>
          </div>
        </div>
        {loading && (
          <span className="inline-flex items-center gap-2 bg-slate-50 text-slate-500 border border-slate-100 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-widest w-fit">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading protein
          </span>
        )}
      </div>

      <div className="grid lg:grid-cols-[1fr_0.8fr] gap-8">
        <div>
          <div className="grid md:grid-cols-2 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Protein</label>
              <select
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
                value={selectedAccession}
                onChange={(event) => onSelectAccession(event.target.value)}
              >
                {proteins.map((protein) => (
                  <option key={protein.accession} value={protein.accession}>
                    {protein.accession} - {protein.protein_name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Plant host</label>
              <select
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
                value={selectedHost}
                onChange={(event) => onSelectHost(event.target.value)}
              >
                {hosts.map((host) => (
                  <option key={host} value={host}>{host}</option>
                ))}
              </select>
            </div>
          </div>

          {detail ? (
            <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
              <MetricCard label="Accession" value={detail.accession} />
              <MetricCard label="Confidence" value={formatNumber(detail.structure?.confidence, 2)} />
              <MetricCard label="Helix ratio" value={formatNumber(detail.structure?.helix_ratio, 3)} />
              <MetricCard label="Atoms rendered" value={trace?.atom_count || 'N/A'} />
            </div>
          ) : (
            <div className="bg-slate-50 border border-slate-100 rounded-2xl p-8 text-center text-slate-500 font-semibold">
              Protein-level artifacts appear after loading latest results.
            </div>
          )}
        </div>

        <div className="bg-slate-50 border border-slate-100 rounded-2xl p-6">
          <div className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">Structure source</div>
          <h3 className="text-xl font-black text-slate-900 mb-2">
            {detail?.structure?.source === 'alphafold' ? 'AlphaFold predicted structure' : 'Deterministic fallback structure'}
          </h3>
          <p className="text-sm text-slate-600 leading-relaxed">
            {detail?.structure?.pdb_id
              ? `${detail.structure.pdb_id} is used for the 3D trace. The same fold is inspected across hosts while the DNA design changes.`
              : 'When AlphaFold content is unavailable, a deterministic fallback keeps the visual and feature pipeline explainable.'}
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            {['Hydrophobicity', 'Secondary structure', 'Host DNA', 'Codon impact'].map((item) => (
              <span key={item} className="bg-white border border-slate-200 rounded-full px-4 py-2 text-xs font-bold text-slate-500">
                {item}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

const DnaOptimizationImpact = ({ detail }) => {
  if (!detail?.dna) {
    return (
      <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm mb-12">
        <div className="flex items-center gap-3 mb-6">
          <Dna className="w-6 h-6 text-emerald-600" />
          <h2 className="text-2xl font-bold text-slate-900">Naive vs Optimized DNA</h2>
        </div>
        <div className="bg-slate-50 border border-slate-100 rounded-2xl p-8 text-center text-slate-500 font-semibold">
          Load latest results to compare naive and host-optimized DNA.
        </div>
      </section>
    )
  }

  const metrics = detail.metrics || {}
  const chartRows = [
    {
      label: 'CAI',
      naive: Number(metrics.naive_cai),
      optimized: Number(metrics.optimized_cai),
    },
    {
      label: 'GC content',
      naive: Number(metrics.naive_gc_content),
      optimized: Number(metrics.optimized_gc_content),
    },
    {
      label: 'Proxy expression',
      naive: Number(metrics.naive_proxy_expression),
      optimized: Number(metrics.optimized_proxy_expression),
    },
  ].filter((row) => Number.isFinite(row.naive) && Number.isFinite(row.optimized))

  return (
    <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm mb-12">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5 mb-8">
        <div className="flex items-center gap-3">
          <Dna className="w-6 h-6 text-emerald-600" />
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Naive vs Optimized DNA</h2>
            <p className="text-slate-500 text-sm">
              Host-specific codon optimization from your original DNA-to-protein impact view.
            </p>
          </div>
        </div>
        <span className="bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-widest w-fit">
          {detail.selected_host}
        </span>
      </div>

      <div className="grid lg:grid-cols-2 gap-8 mb-8">
        <DnaCodonTrack
          title="Naive DNA"
          sequence={detail.dna.naive_sequence}
          diffIndexes={detail.dna.different_codon_indexes || []}
          tone="naive"
        />
        <DnaCodonTrack
          title="Optimized DNA"
          sequence={detail.dna.optimized_sequence}
          diffIndexes={detail.dna.different_codon_indexes || []}
          tone="optimized"
        />
      </div>

      <div className="grid lg:grid-cols-5 gap-8">
        <div className="lg:col-span-2 grid sm:grid-cols-2 gap-4">
          <MetricCard label="Different codons" value={`${detail.dna.different_codons} / ${detail.dna.total_codons}`} />
          <MetricCard label="Difference" value={formatPercent(detail.dna.difference_percent)} />
          <MetricCard label="Delta CAI" value={formatNumber(metrics.delta_cai, 4)} />
          <MetricCard label="Delta proxy" value={formatNumber(metrics.delta_proxy_expression, 4)} />
        </div>
        <div className="lg:col-span-3 h-[320px] bg-slate-50 border border-slate-100 rounded-2xl p-4">
          <Bar
            data={{
              labels: chartRows.map((row) => row.label),
              datasets: [
                {
                  label: 'Naive',
                  data: chartRows.map((row) => row.naive),
                  backgroundColor: 'rgba(244, 63, 94, 0.75)',
                  borderRadius: 8,
                },
                {
                  label: 'Optimized',
                  data: chartRows.map((row) => row.optimized),
                  backgroundColor: CHART_COLORS.emerald,
                  borderRadius: 8,
                },
              ],
            }}
            options={{
              ...chartBaseOptions,
              scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(15,23,42,0.06)' }, ticks: { color: '#64748b' } },
                x: { grid: { display: false }, ticks: { color: '#64748b' } },
              },
            }}
          />
        </div>
      </div>
    </section>
  )
}

const DnaCodonTrack = ({ title, sequence, diffIndexes, tone }) => {
  const diffSet = new Set(diffIndexes)
  const chunks = codonChunks(sequence)
  const baseClass = tone === 'optimized' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-rose-50 text-rose-700 border-rose-100'

  return (
    <div className="bg-slate-50 border border-slate-100 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-bold text-slate-900">{title}</h3>
        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
          first {chunks.length} codons
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5 font-mono text-[11px] leading-none">
        {chunks.map((codon, index) => (
          <span
            key={`${codon}-${index}`}
            className={`border rounded-md px-2 py-1 ${diffSet.has(index) ? baseClass : 'bg-white text-slate-500 border-slate-200'}`}
          >
            {codon}
          </span>
        ))}
      </div>
    </div>
  )
}

const ProteinStructureScene = ({ trace, detail, loading }) => {
  const mountRef = useRef(null)

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return undefined

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100)
    camera.position.set(0, 0.15, 7.8)
    camera.lookAt(0, 0, 0)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x020617, 1)
    mount.appendChild(renderer.domElement)

    const group = new THREE.Group()
    scene.add(group)

    scene.add(new THREE.AmbientLight(0xffffff, 1.4))
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.8)
    keyLight.position.set(3, 4, 5)
    scene.add(keyLight)

    const backboneMaterial = new THREE.MeshStandardMaterial({ color: CHART_COLORS.emerald, roughness: 0.35, metalness: 0.12 })
    const pairMaterial = new THREE.MeshStandardMaterial({ color: CHART_COLORS.blue, roughness: 0.4, metalness: 0.05 })
    const proteinMaterial = new THREE.MeshStandardMaterial({ color: '#f59e0b', roughness: 0.4, metalness: 0.08 })
    const sphereGeometry = new THREE.SphereGeometry(0.065, 18, 18)
    const proteinGeometry = new THREE.SphereGeometry(0.09, 18, 18)
    const rungGeometry = new THREE.CylinderGeometry(0.018, 0.018, 1, 10)

    const makeLine = (points) => {
      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const material = new THREE.LineBasicMaterial({ color: CHART_COLORS.emerald, transparent: true, opacity: 0.45 })
      const line = new THREE.Line(geometry, material)
      group.add(line)
    }

    const traceAtoms = Array.isArray(trace?.atoms) ? trace.atoms : []
    if (traceAtoms.length > 2) {
      const rawPoints = traceAtoms.map((atom) => new THREE.Vector3(Number(atom.x), Number(atom.y), Number(atom.z)))
      const box = new THREE.Box3().setFromPoints(rawPoints)
      const center = new THREE.Vector3()
      const size = new THREE.Vector3()
      box.getCenter(center)
      box.getSize(size)
      const maxAxis = Math.max(size.x, size.y, size.z, 1)
      const scale = 4.2 / maxAxis
      const points = rawPoints.map((point) => point.sub(center).multiplyScalar(scale))

      const traceGeometry = new THREE.BufferGeometry().setFromPoints(points)
      const traceLine = new THREE.Line(
        traceGeometry,
        new THREE.LineBasicMaterial({ color: CHART_COLORS.emerald, transparent: true, opacity: 0.92 }),
      )
      group.add(traceLine)

      points.forEach((point, index) => {
        if (index % 5 !== 0 && index !== points.length - 1) return
        const atom = traceAtoms[index] || {}
        const bfactor = Number(atom.bfactor)
        const color =
          Number.isFinite(bfactor) && bfactor > 70
            ? '#f59e0b'
            : Number.isFinite(bfactor) && bfactor < 35
              ? '#2563eb'
              : '#10b981'
        const bead = new THREE.Mesh(
          new THREE.SphereGeometry(0.045, 14, 14),
          new THREE.MeshStandardMaterial({ color, roughness: 0.38, metalness: 0.08 }),
        )
        bead.position.copy(point)
        group.add(bead)
      })
    } else {
      const pointsA = []
      const pointsB = []
      const turns = 2.35
      const count = 40

      for (let index = 0; index < count; index += 1) {
        const t = (index / (count - 1)) * Math.PI * 2 * turns
        const y = (index / (count - 1) - 0.5) * 3.45
        const radius = 0.92
        const a = new THREE.Vector3(Math.cos(t) * radius, y, Math.sin(t) * radius)
        const b = new THREE.Vector3(Math.cos(t + Math.PI) * radius, y, Math.sin(t + Math.PI) * radius)
        pointsA.push(a)
        pointsB.push(b)

        const sphereA = new THREE.Mesh(sphereGeometry, backboneMaterial)
        sphereA.position.copy(a)
        group.add(sphereA)

        const sphereB = new THREE.Mesh(sphereGeometry, backboneMaterial)
        sphereB.position.copy(b)
        group.add(sphereB)

        if (index % 3 === 0) {
          const midpoint = new THREE.Vector3().addVectors(a, b).multiplyScalar(0.5)
          const direction = new THREE.Vector3().subVectors(b, a)
          const rung = new THREE.Mesh(rungGeometry, pairMaterial)
          rung.position.copy(midpoint)
          rung.scale.set(1, direction.length(), 1)
          rung.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.clone().normalize())
          group.add(rung)
        }
      }

      makeLine(pointsA)
      makeLine(pointsB)

      for (let index = 0; index < 18; index += 1) {
        const angle = index * 0.95
        const protein = new THREE.Mesh(proteinGeometry, proteinMaterial)
        protein.position.set(Math.cos(angle) * 1.65, Math.sin(index * 0.55) * 0.75, Math.sin(angle) * 1.65)
        group.add(protein)
      }
    }

    group.scale.setScalar(0.92)

    const resize = () => {
      const width = mount.clientWidth || 480
      const height = mount.clientHeight || 340
      renderer.setSize(width, height, false)
      camera.aspect = width / height
      camera.updateProjectionMatrix()
    }

    resize()
    const resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(mount)

    let frame = 0
    const animate = () => {
      frame = window.requestAnimationFrame(animate)
      group.rotation.y += 0.007
      group.rotation.x = Math.sin(Date.now() * 0.0008) * 0.08
      renderer.render(scene, camera)
    }
    animate()

    return () => {
      window.cancelAnimationFrame(frame)
      resizeObserver.disconnect()
      renderer.dispose()
      mount.removeChild(renderer.domElement)
    }
  }, [trace])

  const sourceLabel = trace?.source === 'alphafold' || detail?.structure?.source === 'alphafold'
    ? 'AlphaFold structure'
    : '3D sequence context'

  return (
    <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="relative h-[340px] w-full bg-slate-950">
        <div ref={mountRef} className="h-full w-full" />
        {loading && (
          <div className="absolute inset-0 bg-slate-950/60 flex items-center justify-center text-white text-xs font-bold uppercase tracking-widest">
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
            Loading structure
          </div>
        )}
      </div>
      <div className="p-5 border-t border-slate-100 flex items-center justify-between gap-4">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-slate-400">{sourceLabel}</div>
          <div className="font-bold text-slate-900">
            {detail?.protein?.protein_name || 'DNA helix plus protein feature cloud'}
          </div>
        </div>
        <span className="bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-widest">
          {trace?.source === 'alphafold' ? 'AlphaFold' : 'Live 3D'}
        </span>
      </div>
    </div>
  )
}

const ModelComparisonChart = ({ rows }) => (
  <Bar
    data={{
      labels: rows.map((row) => row.display_name || readable(row.model)),
      datasets: [
        {
          label: 'Validation RMSE',
          data: rows.map((row) => Number(row.validation_rmse ?? row.rmse ?? 0)),
          backgroundColor: CHART_COLORS.emerald,
          borderRadius: 10,
        },
        {
          label: 'Validation MAE',
          data: rows.map((row) => Number(row.validation_mae ?? row.mae ?? 0)),
          backgroundColor: CHART_COLORS.blue,
          borderRadius: 10,
        },
      ],
    }}
    options={{
      ...chartBaseOptions,
      scales: {
        y: { beginAtZero: true, grid: { color: 'rgba(15,23,42,0.06)' }, ticks: { color: '#64748b' } },
        x: { grid: { display: false }, ticks: { color: '#64748b' } },
      },
    }}
  />
)

const PriorityRadarChart = ({ scores }) => (
  <Radar
    data={{
      labels: ['Accuracy', 'Speed', 'Interpretability'],
      datasets: [
        {
          label: 'Decision score',
          data: scores,
          backgroundColor: CHART_COLORS.emeraldSoft,
          borderColor: CHART_COLORS.emerald,
          pointBackgroundColor: CHART_COLORS.emerald,
          pointBorderColor: '#ffffff',
          borderWidth: 2,
        },
      ],
    }}
    options={{
      ...chartBaseOptions,
      scales: {
        r: {
          beginAtZero: true,
          max: 100,
          grid: { color: 'rgba(15,23,42,0.08)' },
          angleLines: { color: 'rgba(15,23,42,0.08)' },
          pointLabels: { color: '#475569', font: { size: 12, weight: 'bold' } },
          ticks: { display: false },
        },
      },
    }}
  />
)

const FeatureImportanceChart = ({ features }) => {
  const max = Math.max(...features.map((item) => Math.abs(item.importance)), 1)
  return (
    <Bar
      data={{
        labels: features.map((item) => readable(item.feature)),
        datasets: [
          {
            label: 'Importance',
            data: features.map((item) => Math.abs(item.importance) / max),
            backgroundColor: features.map((_, index) => (index < 3 ? CHART_COLORS.emerald : 'rgba(16, 185, 129, 0.45)')),
            borderRadius: 8,
          },
        ],
      }}
      options={{
        ...chartBaseOptions,
        indexAxis: 'y',
        plugins: { ...chartBaseOptions.plugins, legend: { display: false } },
        scales: {
          x: { beginAtZero: true, grid: { color: 'rgba(15,23,42,0.06)' }, ticks: { color: '#64748b' } },
          y: { grid: { display: false }, ticks: { color: '#64748b' } },
        },
      }}
    />
  )
}

const PredictionScatterChart = ({ pairs }) => (
  <Scatter
    data={{
      datasets: [
        {
          label: 'Predicted vs proxy',
          data: pairs,
          backgroundColor: CHART_COLORS.emerald,
          pointRadius: 4,
          pointHoverRadius: 6,
        },
      ],
    }}
    options={{
      ...chartBaseOptions,
      plugins: { ...chartBaseOptions.plugins, legend: { display: false } },
      scales: {
        x: { title: { display: true, text: 'Proxy target', color: '#64748b' }, grid: { color: 'rgba(15,23,42,0.06)' }, ticks: { color: '#64748b' } },
        y: { title: { display: true, text: 'Prediction', color: '#64748b' }, grid: { color: 'rgba(15,23,42,0.06)' }, ticks: { color: '#64748b' } },
      },
    }}
  />
)

const ResidualChart = ({ bins }) => (
  <Bar
    data={{
      labels: bins.map((bin) => bin.label),
      datasets: [
        {
          label: 'Residual count',
          data: bins.map((bin) => bin.count),
          backgroundColor: CHART_COLORS.amber,
          borderRadius: 8,
        },
      ],
    }}
    options={{
      ...chartBaseOptions,
      plugins: { ...chartBaseOptions.plugins, legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: 'rgba(15,23,42,0.06)' }, ticks: { color: '#64748b' } },
        x: { grid: { display: false }, ticks: { color: '#64748b' } },
      },
    }}
  />
)

const HostRowsChart = ({ rows }) => (
  <Bar
    data={{
      labels: rows.map((row) => row.host.replace(' ', '\n')),
      datasets: [
        {
          label: 'Rows',
          data: rows.map((row) => row.rows),
          backgroundColor: CHART_COLORS.emerald,
          borderRadius: 8,
        },
      ],
    }}
    options={{
      ...chartBaseOptions,
      plugins: { ...chartBaseOptions.plugins, legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: 'rgba(15,23,42,0.06)' }, ticks: { color: '#64748b' } },
        x: { grid: { display: false }, ticks: { color: '#64748b', font: { size: 10 } } },
      },
    }}
  />
)

const QualityDashboard = ({ payload, hostRows }) => {
  const quality = payload?.quality || {}
  const metadata = payload?.metadata || {}
  const metrics = safeMetrics(payload)

  if (!payload) {
    return (
      <div className="bg-slate-50 border border-slate-100 rounded-2xl p-8 text-center text-slate-500 font-semibold">
        Quality metrics will appear after loading the latest run.
      </div>
    )
  }

  return (
    <div className="grid lg:grid-cols-5 gap-6">
      <div className="lg:col-span-2 grid sm:grid-cols-2 gap-4">
        <MetricCard label="Fetched proteins" value={quality.fetched_proteins ?? metadata.proteins_fetched ?? 'N/A'} />
        <MetricCard label="Rows generated" value={quality.rows_generated ?? metadata.rows_generated ?? 'N/A'} />
        <MetricCard label="AlphaFold rate" value={formatPercent((quality.structure_retrieval_rate ?? 0) * 100)} />
        <MetricCard label="Leakage check" value={metrics?.credibility_checks?.leakage_check_passed === false ? 'Failed' : 'Passed'} />
      </div>
      <div className="lg:col-span-3 h-[300px] bg-slate-50 border border-slate-100 rounded-2xl p-4">
        {hostRows.length ? (
          <HostRowsChart rows={hostRows} />
        ) : (
          <div className="h-full flex items-center justify-center text-slate-500 font-semibold">
            Host expansion chart appears when quality report includes host rows.
          </div>
        )}
      </div>
    </div>
  )
}

const FeatureCard = ({ title, icon: Icon, text }) => (
  <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm h-full">
    <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100 w-fit mb-4">
      <Icon className="w-6 h-6 text-emerald-600" />
    </div>
    <h3 className="text-lg font-bold text-slate-900 mb-2">{title}</h3>
    <p className="text-slate-600 text-sm leading-relaxed">{text}</p>
  </div>
)

const MetricCard = ({ label, value }) => (
  <div className="bg-white p-5 rounded-2xl border border-slate-200 text-center shadow-sm">
    <div className="text-slate-400 text-[10px] font-bold uppercase tracking-widest mb-2">{label}</div>
    <div className="text-xl font-black text-slate-900">{value}</div>
  </div>
)

const EmptyState = () => (
  <div className="bg-slate-50 border border-slate-100 rounded-3xl p-10 text-center">
    <BarChart3 className="w-10 h-10 text-slate-300 mx-auto mb-4" />
    <h3 className="font-bold text-slate-900 mb-2">No results yet</h3>
    <p className="text-slate-500 text-sm">Run the pipeline or load latest results.</p>
  </div>
)

const DecisionScatterChart = ({ rankings }) => (
  <Scatter
    data={{
      datasets: [
        {
          label: 'Host Performance',
          data: rankings.map((r) => ({ x: r.feasibility, y: r.efficiency, label: r.plant_host })),
          backgroundColor: '#10b981',
          pointRadius: 8,
          pointHoverRadius: 10,
        },
      ],
    }}
    options={{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => `${context.raw.label}: Eff ${context.raw.y}%, Feas ${context.raw.x}%`,
          },
        },
      },
      scales: {
        y: { title: { display: true, text: 'Efficiency (%)', font: { size: 10, weight: 'bold' } }, beginAtZero: true, max: 100 },
        x: { title: { display: true, text: 'Feasibility (%)', font: { size: 10, weight: 'bold' } }, beginAtZero: true, max: 100 },
      },
    }}
  />
)

const CostBarChart = ({ rankings }) => (
  <Bar
    data={{
      labels: rankings.map((r) => r.plant_host),
      datasets: [
        {
          label: 'Cost (TND)',
          data: rankings.map((r) => r.cost_tnd),
          backgroundColor: '#f59e0b',
          borderRadius: 8,
        },
      ],
    }}
    options={{
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { beginAtZero: true, grid: { display: false } },
        y: { grid: { display: false }, ticks: { font: { size: 10 } } },
      },
    }}
  />
)

const DecisionDashboard = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="bg-white rounded-3xl border border-slate-200 p-12 shadow-sm mb-12 text-center">
        <Loader2 className="w-10 h-10 text-emerald-600 animate-spin mx-auto mb-4" />
        <p className="text-slate-500 font-bold uppercase tracking-widest text-xs">Analyzing decision support data...</p>
      </div>
    )
  }

  if (!data || !data.rankings || data.rankings.length === 0) {
    return (
      <div className="bg-slate-50 border border-slate-100 rounded-3xl p-10 text-center mb-12">
        <TrendingUp className="w-10 h-10 text-slate-300 mx-auto mb-4" />
        <h3 className="font-bold text-slate-900 mb-2">No decision data available</h3>
        <p className="text-slate-500 text-sm">Run the pipeline to generate ML-powered host rankings.</p>
      </div>
    )
  }

  const bestHost = data.best_host

  return (
    <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm mb-12 overflow-hidden relative">
      <div className="absolute top-0 right-0 p-8 opacity-5">
        <TrendingUp className="w-64 h-64 text-emerald-600" />
      </div>

      <div className="relative z-10">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
          <div className="flex items-center gap-3">
            <Award className="w-6 h-6 text-emerald-600" />
            <div>
              <h2 className="text-2xl font-bold text-slate-900">Production Decision Dashboard</h2>
              <p className="text-slate-500 text-sm">ML-powered host ranking, feasibility trade-offs, and strategic recommendations.</p>
            </div>
          </div>
          <span className="bg-emerald-100 text-emerald-700 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-widest w-fit">
            AI Recommended: {bestHost?.plant_host}
          </span>
        </div>

        <div className="grid lg:grid-cols-3 gap-8 mb-10">
          <div className="lg:col-span-2">
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="text-[10px] font-black uppercase tracking-widest text-slate-400 border-b border-slate-100">
                  <tr>
                    <th className="py-4 pr-4">Plant Host</th>
                    <th className="py-4 pr-4">Efficiency</th>
                    <th className="py-4 pr-4">Feasibility</th>
                    <th className="py-4 pr-4">Cost (TND)</th>
                    <th className="py-4 pr-4">Time (min)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.rankings.map((host, idx) => (
                    <tr key={host.plant_host} className={idx === 0 ? 'bg-emerald-50/30' : ''}>
                      <td className="py-4 pr-4">
                        <div className="flex items-center gap-3">
                          {idx === 0 && <Award className="w-4 h-4 text-amber-500" />}
                          <span className="font-bold text-slate-900">{host.plant_host}</span>
                        </div>
                      </td>
                      <td className="py-4 pr-4">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-black text-slate-700">{host.efficiency}%</span>
                          <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full bg-emerald-500" style={{ width: `${host.efficiency}%` }} />
                          </div>
                        </div>
                      </td>
                      <td className="py-4 pr-4">
                        <span className={`text-xs font-bold px-2 py-1 rounded-full ${host.feasibility > 70 ? 'bg-blue-50 text-blue-700' : 'bg-slate-50 text-slate-600'}`}>
                          {host.feasibility}%
                        </span>
                      </td>
                      <td className="py-4 pr-4 font-mono text-xs text-slate-500 font-bold">{host.cost_tnd}</td>
                      <td className="py-4 pr-4 font-mono text-xs text-slate-500 font-bold">{host.time_minutes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="bg-slate-900 rounded-3xl p-6 text-white h-full shadow-xl shadow-slate-200">
              <div className="flex items-center gap-2 mb-4 text-emerald-400">
                <Zap className="w-4 h-4" />
                <span className="text-[10px] font-black uppercase tracking-widest">AI Strategic Verdict</span>
              </div>
              <p className="text-sm leading-relaxed mb-6 italic">
                "{data.recommendation_text}"
              </p>
              <div className="pt-6 border-t border-slate-800">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-[10px] font-bold text-slate-500 uppercase mb-1">Optimized GC</div>
                    <div className="text-lg font-black text-emerald-400">{bestHost?.avg_gc}</div>
                  </div>
                  <div>
                    <div className="text-[10px] font-bold text-slate-500 uppercase mb-1">Confidence</div>
                    <div className="text-lg font-black text-blue-400">High</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          <div className="bg-slate-50 border border-slate-100 rounded-2xl p-4 h-[280px]">
            <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4 text-center">Efficiency vs Feasibility Map</h4>
            <DecisionScatterChart rankings={data.rankings} />
          </div>
          <div className="bg-slate-50 border border-slate-100 rounded-2xl p-4 h-[280px]">
            <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4 text-center">Synthesis Cost Index (TND)</h4>
            <CostBarChart rankings={data.rankings} />
          </div>
        </div>
      </div>
    </section>
  )
}

const BackendBadge = ({ online }) => {
  if (online === true) {
    return (
      <span className="inline-flex items-center gap-2 bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-widest w-fit">
        <CheckCircle2 className="w-4 h-4" />
        Backend online
      </span>
    )
  }

  if (online === false) {
    return (
      <span className="inline-flex items-center gap-2 bg-amber-50 text-amber-700 border border-amber-100 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-widest w-fit">
        <AlertTriangle className="w-4 h-4" />
        Backend offline
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-2 bg-slate-50 text-slate-500 border border-slate-100 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-widest w-fit">
      <Loader2 className="w-4 h-4 animate-spin" />
      Checking API
    </span>
  )
}

export default Pharmaceutical
