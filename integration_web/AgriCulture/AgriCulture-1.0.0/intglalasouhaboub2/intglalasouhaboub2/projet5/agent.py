"""
agent.py
--------
Agentic RAG using LangChain + LangGraph for the IRA DNA Search Platform.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List

from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from search_engine import DNASearchEngine, SearchResult
from rag_engine import RAGEngine


SYSTEM_PROMPT = (
    "You are an expert plant genomics assistant for the IRA "
    "(Institut des Regions Arides) AI platform in Tunisia.\n"
    "You have access to a DNA sequence database of 4,982 "
    "Triticum aestivum (wheat) sequences with 4 trait classes:\n"
    "drought_tolerance, heat_tolerance, salt_tolerance, disease_resistance.\n\n"
    "Use the available tools to search the database and fetch relevant articles.\n"
    "For complex queries, call multiple tools to gather comprehensive information.\n"
    "Always cite specific gene names, accession IDs, and article references.\n"
    "Focus on practical implications for arid region agriculture in Tunisia."
)


class DNAAgent:

    def __init__(
        self,
        engine,
        rag,
        model        = 'llama-3.1-70b-versatile',
        memory_file  = 'agent_memory.json',
        memory_turns = 4,
        verbose      = True,
    ):
        self.engine       = engine
        self.rag          = rag
        self.memory_file  = memory_file
        self.memory_turns = memory_turns
        self.verbose      = verbose

        self.llm = ChatGroq(
            api_key     = rag.groq_key,
            model_name  = model,
            temperature = 0.3,
            max_tokens  = 1000,
        )

        self.memory = self._load_memory()
        self.tools  = self._build_tools()

        self.graph = create_react_agent(
            model  = self.llm,
            tools  = self.tools,
            prompt = SYSTEM_PROMPT,
        )

        print(f'DNA Agent ready (LangChain + LangGraph)')
        print(f'  Model       : {model}')
        print(f'  Tools       : {len(self.tools)} available')
        print(f'  Memory file : {memory_file}')
        print(f'  Memory turns: {len(self.memory)} loaded')
        print()

    def _build_tools(self):
        engine = self.engine
        rag    = self.rag

        @tool
        def search_by_sequence(sequence: str, top_k: int = 10) -> str:
            """Search for similar DNA sequences using hybrid DNABERT + k-mer retrieval.
            Use when user provides a raw DNA sequence (ATCG string)."""
            results = engine.search(sequence, top_k=top_k)
            return _format_results(results)

        @tool
        def search_by_gene(gene_name: str, top_k: int = 10) -> str:
            """Search sequences by gene name (DREB, WRKY, HSP, CBF, etc.)."""
            results = engine.search_by_gene(gene_name, top_k=top_k)
            return _format_results(results)

        @tool
        def search_by_trait(trait: str, top_k: int = 10) -> str:
            """Get sequences for a specific stress tolerance trait.
            Trait must be one of: drought_tolerance, heat_tolerance,
            salt_tolerance, disease_resistance."""
            results = engine.search_by_trait(trait, )
            return _format_results(results)

        @tool
        def search_by_accession(accession: str) -> str:
            """Look up a specific sequence by its GenBank accession ID."""
            result = engine.search_by_accession(accession)
            if result:
                return _format_results([result])
            return f'No sequence found for accession: {accession}'

        @tool
        def fetch_articles(gene_name: str = '', trait: str = '', max_articles: int = 5) -> str:
            """Fetch related scientific articles from Europe PMC."""
            articles = rag.fetch_articles(
                gene_name = gene_name,
                trait     = trait,
                top_k     = max_articles
            )
            return _format_articles(articles)

        return [
            search_by_sequence,
            search_by_gene,
            search_by_trait,
            search_by_accession,
            fetch_articles,
        ]

    def _load_memory(self):
        if Path(self.memory_file).exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f'  Memory loaded: {len(data)} past conversations')
                return data
            except Exception as e:
                print(f'  Memory load error: {e}')
        return []

    def _save_memory(self):
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f'  Memory save error: {e}')

    def _add_to_memory(self, query, answer, tools_used):
        self.memory.append({
            'timestamp' : datetime.now().isoformat(),
            'query'     : query,
            'answer'    : answer,
            'tools_used': tools_used,
        })
        self._save_memory()

    def _get_recent_messages(self):
        messages = []
        for turn in self.memory[-self.memory_turns:]:
            messages.append(HumanMessage(content=turn['query']))
            messages.append(AIMessage(content=turn['answer']))
        return messages

    def clear_memory(self):
        self.memory = []
        if Path(self.memory_file).exists():
            Path(self.memory_file).unlink()
        print('Memory cleared.')

    def show_memory(self):
        if not self.memory:
            print('No conversation history.')
            return
        print(f'\n{"="*60}')
        print(f'  Conversation History ({len(self.memory)} turns)')
        print(f'{"="*60}')
        for i, turn in enumerate(self.memory):
            print(f'\n[{i+1}] {turn["timestamp"][:19]}')
            print(f'  Q: {turn["query"][:80]}')
            print(f'  A: {turn["answer"][:100]}...')
            print(f'  Tools: {turn["tools_used"]}')

    def run(self, query: str) -> str:
        if self.verbose:
            print(f'\nAgent query: {query}')
            print(f'{"="*60}')
            if self.memory:
                print(f'  Memory context: {min(len(self.memory), self.memory_turns)} previous turns injected')

        messages = self._get_recent_messages()
        messages.append(HumanMessage(content=query))

        result       = self.graph.invoke({'messages': messages})
        final_answer = ''
        tools_used   = []

        for msg in result['messages']:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get('name', '') if isinstance(tc, dict) else tc.name
                    tools_used.append(name)
                    if self.verbose:
                        print(f'  [Tool] {name}')

            if (hasattr(msg, 'content') and msg.content
                    and isinstance(msg, AIMessage)
                    and not getattr(msg, 'tool_calls', None)):
                final_answer = msg.content

        if not final_answer:
            final_answer = result['messages'][-1].content

        self._add_to_memory(query, final_answer, tools_used)
        return final_answer

    def display(self, answer: str):
        print(f'\n{"="*70}')
        print(f'  AGENT ANSWER (LangChain + LangGraph)')
        print(f'{"="*70}')
        print(answer)
        print(f'{"="*70}')


def _format_results(results):
    if not results:
        return 'No sequences found.'
    lines = [f'Found {len(results)} sequences:']
    for r in results[:5]:
        lines.append(
            f'- {r.accession} | {r.trait} | gene={r.gene_name or "unknown"} | '
            f'score={r.score:.4f} | {r.description[:80]}'
        )
        if r.publication and r.publication != 'Direct Submission':
            lines.append(f'  Paper: {r.publication[:70]}')
    return '\n'.join(lines)


def _format_articles(articles):
    if not articles:
        return 'No articles found.'
    lines = [f'Found {len(articles)} articles:']
    for i, a in enumerate(articles):
        pmid_url = f'https://pubmed.ncbi.nlm.nih.gov/{a.pmid}' if a.pmid else ''
        lines.append(f'[{i+1}] {a.title} ({a.year})')
        lines.append(f'    Authors: {a.authors}')
        if a.abstract:
            lines.append(f'    Abstract: {a.abstract[:200]}')
        if pmid_url:
            lines.append(f'    Link: {pmid_url}')
    return '\n'.join(lines)