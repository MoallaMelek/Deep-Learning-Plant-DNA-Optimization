"""
rag_engine.py
-------------
RAG layer using LangChain for the IRA DNA Search Platform.
Uses direct LLM call (not LCEL chain) to avoid template variable issues.
"""

import requests
from dataclasses import dataclass, field
from typing import List, Optional

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from search_engine import SearchResult


@dataclass
class Article:
    title    : str
    authors  : str
    journal  : str
    year     : str
    abstract : str
    pmid     : str
    doi      : str
    url      : str

    def citation(self):
        return f'{self.authors} ({self.year}). {self.title}. {self.journal}.'

    def pubmed_url(self):
        if self.pmid:
            return f'https://pubmed.ncbi.nlm.nih.gov/{self.pmid}'
        return self.url or ''


@dataclass
class RAGAnswer:
    query      : str
    answer     : str
    articles   : List[Article]      = field(default_factory=list)
    sequences  : List[SearchResult] = field(default_factory=list)
    trait      : str = ''
    gene       : str = ''
    model_used : str = ''


class RAGEngine:

    EUROPE_PMC_URL = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'

    def __init__(
        self,
        llm_provider  = 'groq',
        groq_key      = None,
        groq_model    = 'llama-3.1-8b-instant',
        max_articles  = 5,
        max_abstract  = 300,
    ):
        self.llm_provider         = llm_provider
        self.groq_key             = groq_key
        self.groq_model           = groq_model
        self.max_articles         = max_articles
        self.max_abstract         = max_abstract
        self._last_articles       = []
        self._last_xgb_prediction = None

        self.llm = ChatGroq(
            api_key    = groq_key,
            model_name = groq_model,
            temperature= 0.3,
            max_tokens = 500,
        )

        self.system_message = SystemMessage(content=(
            "You are a plant genomics expert for the IRA (Institut des Regions Arides) "
            "AI platform in Tunisia. Answer questions about wheat (Triticum aestivum) "
            "genomics using the retrieved sequences and articles provided. "
            "Be specific, concise, and cite articles using [1], [2] notation. "
            "Focus on practical implications for arid region agriculture in Tunisia."
        ))

        print(f'RAG Engine ready (LangChain)')
        print(f'  Provider : {llm_provider}')
        print(f'  Model    : {groq_model}')
        if groq_key:
            print(f'  Key      : {groq_key[:8]}... (masked)')
        print()

    # ── Fetch articles ────────────────────────────────────────

    def fetch_articles(self, gene_name='', trait='', top_k=None) -> List[Article]:
        top_k = top_k or self.max_articles
        terms = []
        if gene_name and gene_name not in ('', '-'):
            terms.append(f'"{gene_name}"')
        if trait:
            terms.append(f'"{trait.replace("_", " ")}"')
        terms.append('"Triticum aestivum"')

        params = {
            'query'     : ' AND '.join(terms),
            'format'    : 'json',
            'pageSize'  : top_k,
            'resultType': 'core',
            'sort'      : 'CITED desc',
        }

        try:
            resp = requests.get(self.EUROPE_PMC_URL, params=params, timeout=10)
            resp.raise_for_status()
            records = resp.json().get('resultList', {}).get('result', [])
        except Exception as e:
            print(f'  Europe PMC error: {e}')
            return []

        articles = []
        for r in records:
            authors = r.get('authorString', '')
            if len(authors) > 60:
                authors = authors[:57] + '...'
            articles.append(Article(
                title    = r.get('title', '').rstrip('.'),
                authors  = authors,
                journal  = r.get('journalTitle', ''),
                year     = str(r.get('pubYear', '')),
                abstract = r.get('abstractText', '')[:self.max_abstract * 2],
                pmid     = r.get('pmid', ''),
                doi      = r.get('doi', ''),
                url      = '',
            ))
        return articles

    # ── Build prompt as plain string ──────────────────────────

    def _build_prompt(self, query, results, articles, xgb_prediction=None) -> str:
        """Build prompt as plain string — avoids LangChain template variable issues."""

        # XGBoost context
        xgb_context = ''
        if xgb_prediction and xgb_prediction.get('trait') != 'unknown':
            proba_str = '  '.join(
                f'{t.split("_")[0]}={p:.2f}'
                for t, p in xgb_prediction.get('probabilities', {}).items()
            )
            xgb_context = (
                f'\nMODULE 1 CLASSIFICATION (XGBoost, F1=0.738):\n'
                f'  Predicted trait : {xgb_prediction["trait"]} '
                f'(confidence: {xgb_prediction["confidence"]:.1%})\n'
                f'  Probabilities   : {proba_str}\n'
            )

        # Sequence context
        seq_lines = ''
        for r in results[:5]:
            seq_lines += f'\n- {r.accession} | {r.trait} | gene={r.gene_name or "unknown"}'
            seq_lines += f'\n  {r.description[:100]}'
            if r.publication and r.publication != 'Direct Submission':
                seq_lines += f'\n  Paper: {r.publication[:80]}'

        # Article context
        art_lines = ''
        for i, a in enumerate(articles[:5]):
            art_lines += f'\n[{i+1}] {a.title} ({a.year})'
            if a.abstract:
                art_lines += f'\n     {a.abstract[:self.max_abstract]}'

        return (
            f"{xgb_context}\n"
            f"QUESTION: {query}\n\n"
            f"RETRIEVED SEQUENCES:\n{seq_lines}\n\n"
            f"RELATED ARTICLES:\n{art_lines}\n\n"
            f"INSTRUCTIONS:\n"
            f"- Answer in 3-5 sentences\n"
            f"- Mention specific gene names and accession IDs\n"
            f"- Cite articles using [1], [2] format\n"
            f"- Focus on Tunisia arid region agriculture\n"
            f"- If Module 1 prediction is available, mention it\n\n"
            f"ANSWER:"
        )

    def _build_references(self, articles) -> str:
        if not articles:
            return ''
        refs = '\nREFERENCES:\n'
        for i, a in enumerate(articles[:5]):
            refs += f'[{i+1}] {a.citation()}'
            if a.pmid:
                refs += f'\n     -> https://pubmed.ncbi.nlm.nih.gov/{a.pmid}'
            elif a.doi:
                refs += f'\n     -> https://doi.org/{a.doi}'
            refs += '\n'
        return refs

    # ── Main answer ───────────────────────────────────────────

    def answer(
        self,
        query          : str,
        results        : List[SearchResult],
        trait          : str  = '',
        gene           : str  = '',
        xgb_prediction : dict = None,
    ) -> RAGAnswer:

        if not gene:
            for r in results:
                if r.gene_name and r.gene_name not in ('', '-'):
                    gene = r.gene_name
                    break
        if not trait:
            for r in results:
                if r.trait:
                    trait = r.trait
                    break

        if xgb_prediction is None:
            xgb_prediction = getattr(self, '_last_xgb_prediction', None)

        print(f'  Fetching articles from Europe PMC ...')
        articles = self.fetch_articles(gene_name=gene, trait=trait)
        print(f'  Found {len(articles)} articles')

        existing = [a.title[:40] for a in articles]
        for r in results[:5]:
            if (r.publication
                    and r.publication != 'Direct Submission'
                    and r.publication[:40] not in existing):
                pmid_clean = r.pmid.replace('PMID:', '').strip() if r.pmid else ''
                articles.append(Article(
                    title    = r.publication,
                    authors  = '',
                    journal  = '',
                    year     = '',
                    abstract = r.description,
                    pmid     = pmid_clean,
                    doi      = '',
                    url      = '',
                ))

        self._last_articles = articles

        # Build prompt as plain string
        prompt = self._build_prompt(query, results, articles, xgb_prediction)

        # Call LLM directly with system + human messages
        print(f'  Calling LangChain LLM ({self.groq_model}) ...')
        response   = self.llm.invoke([
            self.system_message,
            HumanMessage(content=prompt)
        ])
        llm_answer = response.content

        llm_answer += '\n' + self._build_references(articles)

        return RAGAnswer(
            query      = query,
            answer     = llm_answer,
            articles   = articles,
            sequences  = results,
            trait      = trait,
            gene       = gene,
            model_used = self.groq_model,
        )

    def fetch_only(self, gene_name='', trait='') -> List[Article]:
        return self.fetch_articles(gene_name=gene_name, trait=trait)

    def display(self, rag_answer: RAGAnswer):
        print(f'\n{"="*70}')
        print(f'  RAG ANSWER (LangChain)')
        print(f'{"="*70}')
        print(f'\nQuestion : {rag_answer.query}')
        print(f'Trait    : {rag_answer.trait}')
        print(f'Gene     : {rag_answer.gene or "-"}')
        print(f'Model    : {rag_answer.model_used}')
        print(f'Articles : {len(rag_answer.articles)} fetched')
        print()
        print(rag_answer.answer)
        print(f'{"="*70}')

    def display_articles(self, articles: List[Article]):
        if not articles:
            print('No articles found.')
            return
        print(f'\n{"="*70}')
        print(f'  {len(articles)} Related Article(s)')
        print(f'{"="*70}')
        for i, a in enumerate(articles):
            print(f'\n[{i+1}] {a.title}')
            print(f'     {a.authors} ({a.year}) - {a.journal}')
            if a.abstract:
                print(f'     {a.abstract[:200]}...')
            print(f'     {a.pubmed_url()}')