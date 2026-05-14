"""
input_parser.py
---------------
Detects input type and routes to the correct search engine method.

Supported input types:
    1. Raw DNA sequence   — ATCGATCGATCG...
    2. FASTA file         — /path/to/file.fasta
    3. FASTA string       — >header\nATCG...
    4. GenBank accession  — MZ935738.1
    5. Gene name          — TaDREB1, WRKY33
    6. Natural language   — "find drought tolerance genes in wheat"

Usage:
    from search_engine import DNASearchEngine
    from input_parser import InputParser

    engine  = DNASearchEngine()
    parser  = InputParser(engine)

    results = parser.parse_and_search("ATCGATCGATCG...")
    results = parser.parse_and_search("TaDREB1")
    results = parser.parse_and_search("MZ935738.1")
    results = parser.parse_and_search("drought stress genes")
    results = parser.parse_and_search("/path/to/file.fasta")
"""

import re
import os
from typing import List, Tuple
from search_engine import DNASearchEngine, SearchResult


# ─────────────────────────────────────────────────────────────
# Trait synonyms — maps keywords to standard trait names
# ─────────────────────────────────────────────────────────────

TRAIT_SYNONYMS = {
    'drought_tolerance': [
        'drought', 'drought tolerance', 'drought stress',
        'water deficit', 'water stress', 'dehydration',
        'osmotic stress', 'desiccation', 'wilting',
        'drought resistant', 'drought response', 'dreb',
    ],
    'salt_tolerance': [
        'salt', 'salt tolerance', 'salt stress', 'salinity',
        'sodium', 'nacl', 'ionic stress', 'saline',
        'salt resistant', 'halophyte',
    ],
    'heat_tolerance': [
        'heat', 'heat tolerance', 'heat stress', 'thermotolerance',
        'high temperature', 'thermal', 'heat shock',
        'temperature stress', 'heat resistant', 'hsp',
    ],
    'disease_resistance': [
        'disease', 'disease resistance', 'pathogen', 'fungal',
        'bacterial', 'viral', 'rust', 'blight', 'mildew',
        'resistance', 'immune', 'defense', 'pathogenesis',
        'biotic stress', 'infection', 'wrky',
    ],
}

# Build flat keyword → trait lookup
KEYWORD_TO_TRAIT = {}
for trait, keywords in TRAIT_SYNONYMS.items():
    for kw in keywords:
        KEYWORD_TO_TRAIT[kw.lower()] = trait


# ─────────────────────────────────────────────────────────────
# Input type detection
# ─────────────────────────────────────────────────────────────

def detect_input_type(query: str) -> str:
    """
    Returns one of:
        'fasta_file'       — path to a .fasta / .fa file
        'fasta_string'     — raw FASTA text starting with >
        'dna_sequence'     — raw ATCG string
        'accession'        — GenBank accession number
        'gene_name'        — gene symbol like TaDREB1
        'natural_language' — everything else
    """
    q = query.strip()

    # 1. File path
    if os.path.isfile(q) and q.lower().endswith(('.fasta', '.fa', '.fna')):
        return 'fasta_file'

    # 2. FASTA string
    if q.startswith('>'):
        return 'fasta_string'

    # 3. Raw DNA sequence — only ATCGN characters, min 10 bp
    clean = re.sub(r'\s+', '', q.upper())
    if re.match(r'^[ATCGN]+$', clean) and len(clean) >= 10:
        return 'dna_sequence'

    # 4. GenBank accession patterns
    accession_patterns = [
        r'^[A-Z]{1,2}\d{5,8}\.\d+$',    # AY123456.1  BU672196.1
        r'^XM_\d+\.\d+$',               # XM_044575254.1
        r'^XR_\d+\.\d+$',               # XR_123456.1
        r'^NM_\d+\.\d+$',               # NM_123456.1
        r'^[A-Z]{2}\d{6}\.\d+$',        # ES466900.1
        r'^[A-Z]{2}\d{6}$',             # ES466900 (no version)
    ]
    for pat in accession_patterns:
        if re.match(pat, q.strip()):
            return 'accession'

    # 5. Gene name — short alphanumeric symbol
    if re.match(r'^(Ta|Hv|Os|At|Zm)?[A-Z][a-zA-Z0-9\-]{1,20}$', q.strip()):
        return 'gene_name'

    # 6. Default — natural language
    return 'natural_language'


# ─────────────────────────────────────────────────────────────
# FASTA parsing helpers
# ─────────────────────────────────────────────────────────────

def parse_fasta_string(text: str) -> List[Tuple[str, str]]:
    """
    Parse FASTA text into list of (header, sequence) tuples.
    Handles both single and multi-record FASTA.
    """
    records   = []
    header    = None
    seq_parts = []

    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('>'):
            if header is not None:
                seq = ''.join(seq_parts).upper()
                seq = re.sub(r'[^ATCGN]', 'N', seq)
                records.append((header, seq))
            header    = line[1:]
            seq_parts = []
        else:
            seq_parts.append(line)

    if header is not None:
        seq = ''.join(seq_parts).upper()
        seq = re.sub(r'[^ATCGN]', 'N', seq)
        records.append((header, seq))

    return records


def parse_fasta_file(path: str) -> List[Tuple[str, str]]:
    """Read a FASTA file and return (header, sequence) tuples."""
    with open(path, 'r') as f:
        return parse_fasta_string(f.read())


# ─────────────────────────────────────────────────────────────
# Natural language intent extractor
# ─────────────────────────────────────────────────────────────

def extract_intent(query: str) -> dict:
    """
    Parse a natural language query into intent + entities.

    Returns dict with:
        intent  : 'trait_search' | 'gene_search' | 'question'
        trait   : detected trait name or None
        gene    : detected gene symbol or None
        keywords: list of meaningful words
    """
    ql = query.lower()

    # Detect trait
    detected_trait = None
    for kw, trait in KEYWORD_TO_TRAIT.items():
        if kw in ql:
            detected_trait = trait
            break

    # Detect gene symbol
    detected_gene = None
    gene_match = re.search(
        r'\b(Ta[A-Z][a-zA-Z0-9]+|DREB|WRKY|HSP|CBF|LEA|DHN|ERD|MYB|NAC|bZIP)\d*\b',
        query,
        re.IGNORECASE
    )
    if gene_match:
        detected_gene = gene_match.group(0)

    # Determine intent
    if detected_gene:
        intent = 'gene_search'
    elif detected_trait:
        intent = 'trait_search'
    elif query.strip().endswith('?'):
        intent = 'question'
    else:
        intent = 'trait_search'

    # Extract keywords (remove stopwords)
    stopwords = {
        'what', 'which', 'where', 'how', 'why', 'when',
        'is', 'are', 'was', 'the', 'a', 'an', 'in', 'of',
        'for', 'and', 'or', 'to', 'find', 'show', 'get',
        'me', 'genes', 'gene', 'sequence', 'sequences',
        'wheat', 'triticum', 'aestivum', 'related', 'with',
        'associated', 'involved', 'responsible', 'give',
    }
    words    = re.findall(r'\b\w+\b', ql)
    keywords = [w for w in words if w not in stopwords and len(w) > 2]

    return {
        'intent'  : intent,
        'trait'   : detected_trait,
        'gene'    : detected_gene,
        'keywords': keywords,
    }


# ─────────────────────────────────────────────────────────────
# InputParser — main class
# ─────────────────────────────────────────────────────────────

class InputParser:

    def __init__(self, engine: DNASearchEngine):
        self.engine = engine

    def parse_and_search(
        self,
        query  : str,
        top_k  : int  = 10,
        verbose: bool = True,
    ) -> List[SearchResult]:
        """
        Accept any input type, detect it, route to correct handler.

        Args:
            query  : any supported input string
            top_k  : number of results to return
            verbose: print detected input type

        Returns:
            List of SearchResult objects
        """
        query      = query.strip()
        input_type = detect_input_type(query)

        if verbose:
            print(f'Input type : {input_type}')

        if input_type == 'dna_sequence':
            return self._handle_sequence(query, top_k)

        elif input_type == 'fasta_string':
            return self._handle_fasta_string(query, top_k)

        elif input_type == 'fasta_file':
            return self._handle_fasta_file(query, top_k)

        elif input_type == 'accession':
            return self._handle_accession(query)

        elif input_type == 'gene_name':
            return self._handle_gene(query, top_k)

        elif input_type == 'natural_language':
            return self._handle_nl(query, top_k, verbose)

        return []

    # ── Handler: raw DNA sequence ─────────────────────────────

    def _handle_sequence(self, sequence: str, top_k: int) -> List[SearchResult]:
        return self.engine.search(sequence, top_k=top_k)

    # ── Handler: FASTA string ─────────────────────────────────

    def _handle_fasta_string(self, fasta: str, top_k: int) -> List[SearchResult]:
        records = parse_fasta_string(fasta)
        if not records:
            print('  Could not parse FASTA string.')
            return []

        # If multiple records, search each and combine
        all_results = []
        for header, seq in records:
            print(f'  Searching record: {header[:60]}')
            results = self.engine.search(seq, top_k=top_k)
            all_results.extend(results)

        # Re-rank combined results by score
        all_results.sort(key=lambda r: -r.score)
        for i, r in enumerate(all_results[:top_k]):
            r.rank = i + 1
        return all_results[:top_k]

    # ── Handler: FASTA file ───────────────────────────────────

    def _handle_fasta_file(self, path: str, top_k: int) -> List[SearchResult]:
        print(f'  Reading FASTA file: {path}')
        records = parse_fasta_file(path)
        print(f'  Records found: {len(records)}')

        all_results = []
        for header, seq in records:
            print(f'  Searching: {header[:60]}')
            results = self.engine.search(seq, top_k=top_k)
            all_results.extend(results)

        all_results.sort(key=lambda r: -r.score)
        for i, r in enumerate(all_results[:top_k]):
            r.rank = i + 1
        return all_results[:top_k]

    # ── Handler: GenBank accession ────────────────────────────

    def _handle_accession(self, accession: str) -> List[SearchResult]:
        result = self.engine.search_by_accession(accession)
        if result is None:
            print(f'  Accession not found in index: {accession}')
            return []
        return [result]

    # ── Handler: gene name ────────────────────────────────────

    def _handle_gene(self, gene: str, top_k: int) -> List[SearchResult]:
        results = self.engine.search_by_gene(gene, top_k=top_k)
        if not results:
            print(f'  No sequences found with gene name: {gene}')
        return results

    # ── Handler: natural language ─────────────────────────────

    def _handle_nl(self, query: str, top_k: int, verbose: bool) -> List[SearchResult]:
        intent = extract_intent(query)

        if verbose:
            print(f'  Intent : {intent["intent"]}')
            print(f'  Trait  : {intent["trait"]  or "—"}')
            print(f'  Gene   : {intent["gene"]   or "—"}')

        if intent['intent'] == 'gene_search' and intent['gene']:
            return self.engine.search_by_gene(intent['gene'], top_k=top_k)

        elif intent['intent'] == 'trait_search' and intent['trait']:
            return self.engine.search_by_trait(intent['trait'], top_k=top_k)

        elif intent['intent'] == 'question':
            # No RAG yet — return top sequences for detected trait
            if intent['trait']:
                print('  [RAG layer not yet connected — returning top sequences]')
                return self.engine.search_by_trait(intent['trait'], top_k=top_k)
            else:
                print('  Could not extract trait or gene from question.')
                return []

        else:
            # Fallback — try each keyword as gene name or trait
            for kw in intent['keywords']:
                results = self.engine.search_by_gene(kw, top_k=top_k)
                if results:
                    return results
            print('  Could not match query to any known trait or gene.')
            return []
