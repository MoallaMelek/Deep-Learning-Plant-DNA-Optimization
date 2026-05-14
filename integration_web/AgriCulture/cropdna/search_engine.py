"""
search_engine.py
----------------
Core search engine for the IRA DNA Search Platform.
THREE signals fused with RRF + Module 1 XGBoost trait prediction.
"""

import sys
import types


# ── Windows triton stub ────────────────────────────────────────────────────
# triton is Linux-only. torch._inductor / DNABERT-2 try to import it at
# module-load time. We use a meta-path finder so that:
#   "import triton"                     → returns stub
#   "import triton.backends.compiler"   → returns another stub
# All stubs have proper list __path__ so inspect/torch never crashes.
# Real inference uses attn_implementation="eager" → zero triton calls.

class _TritonFinder:
    """sys.meta_path hook: satisfies any 'triton.*' import with a stub module."""

    @staticmethod
    def _make_stub(fullname: str) -> types.ModuleType:
        mod = types.ModuleType(fullname)
        mod.__path__ = []            # real list — makes it a package
        mod.__package__ = fullname
        mod.__loader__ = None
        mod.__spec__ = None
        return mod

    def find_module(self, fullname, path=None):          # Python ≤ 3.11 style
        if fullname == "triton" or fullname.startswith("triton."):
            return self

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]
        mod = self._make_stub(fullname)
        sys.modules[fullname] = mod
        return mod

    # Python 3.12+ style (find_spec / exec_module)
    def find_spec(self, fullname, path, target=None):
        if fullname == "triton" or fullname.startswith("triton."):
            import importlib.machinery
            spec = importlib.machinery.ModuleSpec(fullname, self, is_package=True)
            return spec

    def create_module(self, spec):
        return self._make_stub(spec.name)

    def exec_module(self, module):
        pass   # nothing to execute — stub is already populated


if "triton" not in sys.modules:
    _finder = _TritonFinder()
    sys.meta_path.insert(0, _finder)

    # Pre-register top-level + all sub-packages torch/_inductor touches
    for _name in [
        "triton", "triton.language", "triton.runtime",
        "triton.backends", "triton.backends.compiler",
        "triton.backends.cuda", "triton.compiler",
    ]:
        if _name not in sys.modules:
            sys.modules[_name] = _finder._make_stub(_name)

    # Concrete attributes expected by torch._dynamo / transformers
    triton_lang = sys.modules["triton.language"]
    triton_lang.dtype         = type("dtype",        (), {})()
    triton_lang.constexpr     = int
    triton_lang.pointer_type  = type("pointer_type", (), {})()

    triton_backends        = sys.modules["triton.backends"]
    triton_compiler_stub   = sys.modules["triton.backends.compiler"]
    triton_compiler_stub.AttrsDescriptor = type("AttrsDescriptor", (), {})  # class (not instance)
    triton_backends.compiler = triton_compiler_stub   # wire as attribute too

    triton_root = sys.modules["triton"]
    triton_root.language   = triton_lang
    triton_root.backends   = triton_backends
    triton_root.jit        = lambda fn=None, **kw: (fn if fn is not None else lambda f: f)
    triton_root.autotune   = lambda configs=None, key=None, **kw: (lambda f: f)
    triton_root.heuristics = lambda values=None, **kw: (lambda f: f)
    triton_root.cdiv       = lambda a, b: (a + b - 1) // b

    # triton.Config is instantiated (not just decorated) by flash_attn_triton.py
    class _TritonConfig:
        def __init__(self, meta=None, num_warps=4, num_stages=1, pre_hook=None, **kw):
            self.meta       = meta or {}
            self.num_warps  = num_warps
            self.num_stages = num_stages
            self.pre_hook   = pre_hook
        def __repr__(self):
            return f"TritonConfig(stub)"
    triton_root.Config = _TritonConfig


import pandas as pd
import numpy as np
import faiss
import pickle
import re
import time
import torch
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Optional, Tuple
from transformers import AutoTokenizer, AutoModel


@dataclass
class SearchResult:
    rank          : int
    accession     : str
    trait         : str
    score         : float
    score_type    : str
    seq_length    : int
    gc_content    : float
    gene_name     : str
    organism      : str
    description   : str
    publication   : str
    pmid          : str
    sparse_score  : int   = 0
    dense_dnabert : float = 0.0
    dense_kmer    : float = 0.0

    def to_dict(self):
        return self.__dict__


class DNASearchEngine:

    def __init__(
        self,
        master_parquet = 'master_index.parquet',
        faiss_dnabert  = 'faiss_dnabert.index',
        faiss_kmer     = 'faiss_kmer.index',
        kmer_index     = 'kmer_inverted_index.pkl',
        id_map_file    = 'seq_id_to_accession.pkl',
        kmer_csv       = 'wheat_enriched.csv',
        dnabert_model  = 'zhihan1996/DNABERT-2-117M',
        top_k          = 10,
    ):
        print('Loading DNA Search Engine ...')
        t0 = time.time()

        # 1 — Metadata table
        self.df         = pd.read_parquet(master_parquet).fillna('')
        self.df_indexed = self.df.set_index('seq_id')
        print(f'  Metadata       : {len(self.df):,} sequences')

        # 2 — FAISS DNABERT index (768-dim)
        self.index_dnabert = faiss.read_index(faiss_dnabert)
        print(f'  DNABERT index  : {self.index_dnabert.ntotal:,} vectors | dim={self.index_dnabert.d}')

        # 3 — FAISS k-mer index (256-dim)
        self.index_kmer = faiss.read_index(faiss_kmer)
        print(f'  K-mer index    : {self.index_kmer.ntotal:,} vectors | dim={self.index_kmer.d}')

        # 4 — K-mer inverted index
        with open(kmer_index, 'rb') as f:
            self.kmer_inv = pickle.load(f)
        print(f'  Inverted index : {len(self.kmer_inv):,} unique k-mers')

        # 5 — ID map
        with open(id_map_file, 'rb') as f:
            self.id_map = pickle.load(f)

        # 6 — K-mer feature columns
        df_full        = pd.read_csv(kmer_csv)
        self.kmer_cols = [c for c in df_full.columns if c.startswith('k_')]
        print(f'  K-mer cols     : {len(self.kmer_cols)}')

        # 7 — DNABERT-2 model
        print(f'  Loading DNABERT-2 ...')
        self.device    = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.tokenizer = AutoTokenizer.from_pretrained(dnabert_model, trust_remote_code=True)

        # Patch: newer transformers requires pad_token_id in BertConfig,
        # but DNABERT-2's config.json may omit it (version mismatch on Windows).
        from transformers import AutoConfig
        _dna_cfg = AutoConfig.from_pretrained(dnabert_model, trust_remote_code=True)
        if not hasattr(_dna_cfg, 'pad_token_id') or _dna_cfg.pad_token_id is None:
            _dna_cfg.pad_token_id = 3   # BERT standard: [PAD] token id
        self.bert = AutoModel.from_pretrained(
            dnabert_model,
            config=_dna_cfg,
            trust_remote_code=True,
            attn_implementation="eager",
            low_cpu_mem_usage=False,
        )

        # Rebuild alibi tensor properly to replace the empty meta tensor from init
        try:
            for module in self.bert.modules():
                if hasattr(module, 'rebuild_alibi_tensor') and hasattr(module, '_current_alibi_size'):
                    module.rebuild_alibi_tensor(size=module._current_alibi_size, device=self.device)
        except Exception as e:
            print(f"Warning: Failed to rebuild alibi tensor: {e}")
        self.bert.eval()
        self.bert.to(self.device)
        print(f'  DNABERT-2      : loaded | device={self.device}')

        # 8 — Module 1 XGBoost classifier
        print(f'  Loading Module 1 XGBoost ...')
        try:
            import joblib
            self.xgb_model = joblib.load('best_xgboost.pkl')
            self.xgb_le    = joblib.load('label_encoder.pkl')
            print(f'  XGBoost        : loaded | classes={list(self.xgb_le.classes_)}')
        except Exception as e:
            self.xgb_model = None
            self.xgb_le    = None
            print(f'  XGBoost        : not loaded ({e})')

        self.top_k              = top_k
        self.K                  = 4
        self._last_prediction   = None
        self._last_xgb_prediction = None

        print(f'  Ready in {time.time()-t0:.1f}s')
        print()

    # ── Encode: DNABERT 768-dim ───────────────────────────────

    def _encode_dnabert(self, sequence: str) -> Optional[np.ndarray]:
        inputs = self.tokenizer(
            sequence.upper()[:512],
            return_tensors='pt',
            padding=True,
            truncation=True,
            max_length=512
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self.bert(**inputs)
        vec = outputs[0][:, 0, :].cpu().numpy().astype('float32')
        vec = np.ascontiguousarray(vec)
        faiss.normalize_L2(vec)
        return vec

    # ── Encode: k-mer 256-dim ────────────────────────────────

    def _encode_kmer(self, sequence: str) -> Optional[np.ndarray]:
        seq = sequence.upper()
        n   = len(seq) - self.K + 1
        if n <= 0:
            return None
        counts = defaultdict(int)
        for i in range(n):
            kmer = seq[i:i+self.K]
            if re.match(r'^[ATCG]+$', kmer):
                counts[kmer] += 1
        vec = np.array(
            [counts.get(col[2:], 0) / n for col in self.kmer_cols],
            dtype='float32'
        )
        vec = np.ascontiguousarray(vec.reshape(1, -1))
        faiss.normalize_L2(vec)
        return vec

    # ── Encode: raw k-mer array (for XGBoost) ────────────────

    def _encode_kmer_raw(self, sequence: str) -> np.ndarray:
        """
        Encode sequence as 258-dim vector for XGBoost Module 1.
        256 k-mer frequencies + gc content + sequence length.
        """
        seq = sequence.upper()
        n   = len(seq) - self.K + 1
        if n <= 0:
            return np.zeros(len(self.kmer_cols) + 2, dtype='float32')

        counts = defaultdict(int)
        for i in range(n):
            kmer = seq[i:i+self.K]
            if re.match(r'^[ATCG]+$', kmer):
                counts[kmer] += 1

        # 256 k-mer frequencies
        kmer_vec = np.array(
            [counts.get(col[2:], 0) / n for col in self.kmer_cols],
            dtype='float32'
        )

        # + gc content + sequence length = 258 total
        gc = sum(1 for b in seq if b in 'GC') / len(seq)
        return np.append(kmer_vec, [gc, len(seq)])

    # ── Module 1: predict trait ───────────────────────────────

    def predict_trait(self, sequence: str) -> dict:
        """Prédit le trait via Module 1 XGBoost."""
        if self.xgb_model is None:
            return {'trait': 'unknown', 'confidence': 0.0, 'probabilities': {}}
        seq = sequence.upper()
        if len(seq) < self.K:
            return {'trait': 'unknown', 'confidence': 0.0, 'probabilities': {}}
        vec          = self._encode_kmer_raw(seq).reshape(1, -1)
        pred_encoded = self.xgb_model.predict(vec)[0]
        pred_proba   = self.xgb_model.predict_proba(vec)[0]
        pred_trait   = self.xgb_le.inverse_transform([pred_encoded])[0]
        confidence   = float(pred_proba.max())
        proba_dict   = {
            cls: round(float(p), 4)
            for cls, p in zip(self.xgb_le.classes_, pred_proba)
        }
        return {
            'trait'        : pred_trait,
            'confidence'   : round(confidence, 4),
            'probabilities': proba_dict,
        }

    # ── Sparse retrieval ──────────────────────────────────────

    def _sparse(self, sequence: str, top_k: int) -> List[Tuple[int, int]]:
        seq    = sequence.upper()
        kmers  = set(
            seq[i:i+self.K]
            for i in range(len(seq) - self.K + 1)
            if re.match(r'^[ATCG]+$', seq[i:i+self.K])
        )
        scores = defaultdict(int)
        for kmer in kmers:
            for sid in self.kmer_inv.get(kmer, []):
                scores[sid] += 1
        return sorted(scores.items(), key=lambda x: -x[1])[:top_k]

    # ── Dense retrieval (both FAISS) ──────────────────────────

    def _dense(self, sequence: str, top_k: int) -> Tuple[list, list]:
        results_dnabert = []
        results_kmer    = []

        vec_d = self._encode_dnabert(sequence)
        if vec_d is not None:
            scores, indices = self.index_dnabert.search(vec_d, top_k + 1)
            results_dnabert = [
                (int(idx), float(score))
                for idx, score in zip(indices[0], scores[0])
                if idx != -1
            ]

        vec_k = self._encode_kmer(sequence)
        if vec_k is not None:
            scores, indices = self.index_kmer.search(vec_k, top_k + 1)
            results_kmer = [
                (int(idx), float(score))
                for idx, score in zip(indices[0], scores[0])
                if idx != -1
            ]

        return results_dnabert, results_kmer

    # ── RRF Fusion ────────────────────────────────────────────

    def _fuse(self, sparse, dense_dnabert, dense_kmer, exclude_sid=None) -> list:
        RRF_K  = 60
        scores = defaultdict(float)
        for rank, (sid, _) in enumerate(sparse):
            scores[sid] += 1.0 / (RRF_K + rank + 1)
        for rank, (sid, _) in enumerate(dense_dnabert):
            scores[sid] += 1.0 / (RRF_K + rank + 1)
        for rank, (sid, _) in enumerate(dense_kmer):
            scores[sid] += 1.0 / (RRF_K + rank + 1)
        if exclude_sid is not None and exclude_sid in scores:
            del scores[exclude_sid]
        return sorted(scores.items(), key=lambda x: -x[1])

    # ── Build results ─────────────────────────────────────────

    def _build_results(self, ranked, sparse, dense_dnabert, dense_kmer, top_k) -> List[SearchResult]:
        sparse_map  = dict(sparse)
        dnabert_map = dict(dense_dnabert)
        kmer_map    = dict(dense_kmer)
        results     = []
        for rank, (sid, score) in enumerate(ranked[:top_k]):
            if sid not in self.df_indexed.index:
                continue
            row = self.df_indexed.loc[sid]
            results.append(SearchResult(
                rank          = rank + 1,
                accession     = str(row.get('id',          '')),
                trait         = str(row.get('trait',       '')),
                score         = round(score, 4),
                score_type    = 'hybrid',
                seq_length    = int(row['len'])   if str(row.get('len',  '')) != '' else 0,
                gc_content    = float(row['gc'])  if str(row.get('gc',   '')) != '' else 0.0,
                gene_name     = str(row.get('gene_name',   '')),
                organism      = str(row.get('organism',    '')),
                description   = str(row.get('description', ''))[:120],
                publication   = str(row.get('publication', ''))[:120],
                pmid          = str(row.get('pmid',        '')),
                sparse_score  = sparse_map.get(sid,  0),
                dense_dnabert = round(dnabert_map.get(sid, 0.0), 4),
                dense_kmer    = round(kmer_map.get(sid,    0.0), 4),
            ))
        return results

    # ── PUBLIC: search by sequence ────────────────────────────

    def search(self, sequence: str, top_k: int = None, trait_filter: str = None) -> List[SearchResult]:
        top_k = top_k or self.top_k
        seq   = re.sub(r'[^ATCGN]', '', sequence.upper().strip())
        if len(seq) < self.K:
            return []

        # Module 1 — predict trait
        prediction                = self.predict_trait(seq)
        self._last_prediction     = prediction
        self._last_xgb_prediction = prediction

        sparse                    = self._sparse(seq, top_k * 3)
        dense_dnabert, dense_kmer = self._dense(seq, top_k * 3)
        ranked                    = self._fuse(sparse, dense_dnabert, dense_kmer)
        results                   = self._build_results(ranked, sparse, dense_dnabert, dense_kmer, top_k * 2)

        if trait_filter:
            tf      = trait_filter.lower().replace(' ', '_')
            results = [r for r in results if tf in r.trait.lower()]

        for i, r in enumerate(results[:top_k]):
            r.rank = i + 1

        return results[:top_k]

    # ── PUBLIC: search by trait ───────────────────────────────

    def search_by_trait(self, trait: str, top_k: int = None) -> List[SearchResult]:
        top_k  = top_k or self.top_k
        trait  = trait.lower().replace(' ', '_')
        subset = self.df[self.df['trait'].str.lower().str.replace(' ', '_') == trait].head(top_k)
        return self._rows_to_results(subset)

    # ── PUBLIC: search by gene ────────────────────────────────

    def search_by_gene(self, gene: str, top_k: int = None) -> List[SearchResult]:
        top_k  = top_k or self.top_k
        subset = self.df[self.df['gene_name'].str.lower().str.contains(gene.lower(), na=False)].head(top_k)
        return self._rows_to_results(subset)

    # ── PUBLIC: search by accession ───────────────────────────

    def search_by_accession(self, accession: str) -> Optional[SearchResult]:
        subset = self.df[self.df['id'] == accession.strip()]
        if subset.empty:
            return None
        results = self._rows_to_results(subset)
        return results[0] if results else None

    # ── Helper ────────────────────────────────────────────────

    def _rows_to_results(self, subset) -> List[SearchResult]:
        results = []
        for rank, (_, row) in enumerate(subset.iterrows()):
            results.append(SearchResult(
                rank          = rank + 1,
                accession     = str(row.get('id',          '')),
                trait         = str(row.get('trait',       '')),
                score         = 1.0,
                score_type    = 'metadata',
                seq_length    = int(row['len'])   if str(row.get('len',  '')) != '' else 0,
                gc_content    = float(row['gc'])  if str(row.get('gc',   '')) != '' else 0.0,
                gene_name     = str(row.get('gene_name',   '')),
                organism      = str(row.get('organism',    '')),
                description   = str(row.get('description', ''))[:120],
                publication   = str(row.get('publication', ''))[:120],
                pmid          = str(row.get('pmid',        '')),
            ))
        return results

    # ── PUBLIC: display ───────────────────────────────────────

    def display(self, results: List[SearchResult], show_prediction: bool = True):
        if not results:
            print('No results found.')
            return

        # Module 1 prediction block
        if show_prediction and self._last_prediction and self._last_prediction['trait'] != 'unknown':
            pred = self._last_prediction
            print(f'\n{"="*70}')
            print(f'  MODULE 1 — XGBoost Trait Prediction (F1=0.738)')
            print(f'{"="*70}')
            print(f'  Predicted trait : {pred["trait"]}')
            print(f'  Confidence      : {pred["confidence"]:.1%}')
            print(f'  Probabilities   :', end=' ')
            for trait, prob in pred['probabilities'].items():
                short = trait.split("_")[0]
                print(f'{short}={prob:.2f}', end='  ')
            print()

        print(f'\n{"="*70}')
        print(f'  {len(results)} result(s) found')
        print(f'{"="*70}')

        for r in results:
            print(f'\nRank {r.rank} — {r.accession}')
            print(f'  Trait        : {r.trait}')
            print(f'  Score        : {r.score:.4f}  ({r.score_type})')
            print(f'  Gene         : {r.gene_name  or "—"}')
            print(f'  Organism     : {r.organism   or "—"}')
            print(f'  Length / GC  : {r.seq_length} bp | {r.gc_content:.2%}')
            print(f'  Description  : {r.description}')
            if r.publication:
                print(f'  Publication  : {r.publication}')
            if r.pmid:
                pmid = r.pmid.replace('PMID:', '').strip()
                print(f'  PubMed       : https://pubmed.ncbi.nlm.nih.gov/{pmid}')
            if r.score_type == 'hybrid':
                print(f'  Signals      : sparse={r.sparse_score} | '
                      f'dnabert={r.dense_dnabert:.4f} | '
                      f'kmer={r.dense_kmer:.4f}')
            print(f'  {"—"*65}')
