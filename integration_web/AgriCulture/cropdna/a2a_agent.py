
import json
import time
from pathlib import Path
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from search_engine import DNASearchEngine, SearchResult
from rag_engine import RAGEngine


class A2ASystem:
    def __init__(self, engine, rag, model="llama-3.1-8b-instant",
                 memory_file="a2a_memory.json", verbose=True):
        self.engine = engine
        self.rag = rag
        self.verbose = verbose
        self.memory_file = memory_file
        self.memory = self._load_memory()
        self.store_called = []
        self.store_dna = ""
        self.store_science = ""
        self.llm = ChatGroq(
            api_key=rag.groq_key,
            model_name=model,
            temperature=0.1,
            max_tokens=600,
        )
        engine_ = engine
        rag_ = rag
        self_ = self

        @tool
        def call_dna_agent(gene_name: str = "", trait: str = "") -> str:
            """Search wheat DNA sequences by gene_name OR trait. Call ONCE only."""
            if "DNA" in self_.store_called:
                return self_.store_dna
            if verbose:
                print(f"  [A2A] -> DNA Agent (gene={gene_name}, trait={trait})")
            self_.store_called.append("DNA")
            time.sleep(1)
            if gene_name:
                results = engine_.search_by_gene(gene_name, top_k=5)
            elif trait:
                results = engine_.search_by_trait(trait, top_k=5)
            else:
                results = []
            lines = [f"Found {len(results)} sequences:"]
            for r in results[:3]:
                lines.append(f"- {r.accession} | {r.trait} | gene={r.gene_name or '?'} | {r.description[:60]}")
            self_.store_dna = "\n".join(lines)
            return self_.store_dna

        @tool
        def call_dna_compare(gene1: str, gene2: str) -> str:
            """Compare two genes in the wheat database. Call ONCE only."""
            if "DNA_CMP" in self_.store_called:
                return self_.store_dna
            if verbose:
                print(f"  [A2A] -> DNA Compare ({gene1} vs {gene2})")
            self_.store_called.append("DNA_CMP")
            time.sleep(1)
            r1 = engine_.search_by_gene(gene1, top_k=3)
            time.sleep(1)
            r2 = engine_.search_by_gene(gene2, top_k=3)
            def fmt(results):
                return "\n".join([f"- {r.accession} | {r.trait} | gene={r.gene_name or '?'}" for r in results[:3]])
            answer = f"=== {gene1} ===\n{fmt(r1)}\n\n=== {gene2} ===\n{fmt(r2)}"
            self_.store_dna = answer
            return answer

        @tool
        def call_science_agent(gene_name: str = "", trait: str = "") -> str:
            """Fetch scientific articles from Europe PMC. Call ONCE only."""
            if "SCIENCE" in self_.store_called:
                return self_.store_science
            if verbose:
                print(f"  [A2A] -> Science Agent (gene={gene_name}, trait={trait})")
            self_.store_called.append("SCIENCE")
            time.sleep(1)
            articles = rag_.fetch_articles(gene_name=gene_name, trait=trait, top_k=3)
            lines = []
            for i, a in enumerate(articles[:3]):
                pmid = f"https://pubmed.ncbi.nlm.nih.gov/{a.pmid}" if a.pmid else ""
                lines.append(f"[{i+1}] {a.title} ({a.year})")
                if a.abstract:
                    lines.append(f"    {a.abstract[:150]}")
                if pmid:
                    lines.append(f"    {pmid}")
            self_.store_science = "\n".join(lines)
            return self_.store_science

        @tool
        def call_vision_agent(description: str) -> str:
            """Analyze plant photos. Phase 5 - not yet available."""
            if verbose:
                print(f"  [A2A] -> Vision Agent (Phase 5)")
            self_.store_called.append("VISION")
            return "Vision Agent coming in Phase 5."

        self.coordinator = create_react_agent(
            model=self.llm,
            tools=[call_dna_agent, call_dna_compare, call_science_agent, call_vision_agent],
            prompt=(
                "You are the IRA A2A Coordinator for wheat genomics in Tunisia.\n"
                "Tools (call each MAX ONCE):\n"
                "- call_dna_agent(gene_name, trait) — search sequences\n"
                "- call_dna_compare(gene1, gene2)   — compare two genes\n"
                "- call_science_agent(gene_name, trait) — fetch articles\n"
                "- call_vision_agent(description)   — photo analysis (Phase 5)\n\n"
                "RULES: Gene question -> call_dna_agent + call_science_agent\n"
                "Comparison -> call_dna_compare + call_science_agent\n"
                "Articles only -> call_science_agent\n"
                "NEVER call same tool twice. Max 2 tool calls total."
            ),
        )
        print(f"A2A System ready | Model: {model}")

    def run(self, query: str) -> str:
        self.store_called = []
        self.store_dna = ""
        self.store_science = ""
        if self.verbose:
            print(f"\nA2A query: {query}\n" + "="*60)
        result = self.coordinator.invoke({"messages": [HumanMessage(content=query)]})
        final_answer = ""
        for msg in result["messages"]:
            if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
                final_answer = msg.content
        if not final_answer:
            final_answer = result["messages"][-1].content
        if self.verbose:
            print(f"\n  Agents called: {' -> '.join(self.store_called)}")
        self._save_memory(query, final_answer, self.store_called)
        return final_answer

    def _load_memory(self):
        if Path(self.memory_file).exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return []

    def display(self, answer):
        print(f"\n" + "="*70 + "\n  A2A ANSWER\n" + "="*70)
        print(answer)
        print("="*70)


    def _save_memory(self, query, answer, agents_called):
        import json
        from datetime import datetime
        self.memory.append({
            'timestamp'    : datetime.now().isoformat(),
            'query'        : query,
            'answer'       : answer,
            'agents_called': agents_called,
        })
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f'Memory save error: {e}')

    def show_memory(self):
        print("Memory not implemented in inline version.")

    def clear_memory(self):
        self.store_called = []
