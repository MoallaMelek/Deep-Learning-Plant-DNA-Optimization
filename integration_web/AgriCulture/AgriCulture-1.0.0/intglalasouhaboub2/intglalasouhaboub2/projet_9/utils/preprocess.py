"""
Étape 1-3 : Nettoyage ADN + Encodage k-mers
"""
import numpy as np
from pathlib import Path

def clean_dna_sequence(fasta_content):
    """
    Nettoie une séquence ADN brute (FASTA)
    - Enlève les headers (>...)
    - Enlève les espaces et caractères invalides
    - Garde seulement A, T, G, C
    """
    lines = fasta_content.strip().split('\n')
    sequence = ''.join([line for line in lines if not line.startswith('>')])
    sequence = sequence.upper()
    # Garder seulement ATGC
    sequence = ''.join([c for c in sequence if c in 'ATGC'])
    return sequence

def generate_kmers(sequence, k=4):
    """
    Génère tous les k-mers d'une séquence
    Ex: ATGCATGC avec k=4 → ['ATGC', 'TGCA', 'GCAT', 'CATG', 'ATGC']
    """
    kmers = []
    for i in range(len(sequence) - k + 1):
        kmers.append(sequence[i:i+k])
    return kmers

def generate_all_possible_kmers(k=4):
    """
    Génère tous les k-mers possibles (AAAA, AAAT, ..., TTTT)
    Pour k=4 : 4^4 = 256 k-mers
    """
    bases = ['A', 'C', 'G', 'T']
    kmers = []

    def generate(current):
        if len(current) == k:
            kmers.append(current)
            return
        for base in bases:
            generate(current + base)

    generate('')
    return kmers

def encode_sequence_to_kmers(sequence, k=4):
    """
    Encode une séquence ADN en vecteur de fréquences k-mers
    Output: vecteur de 256 valeurs (fréquences de chaque k-mer)
    """
    all_kmers = generate_all_possible_kmers(k)
    kmer_counts = {kmer: 0 for kmer in all_kmers}

    # Compter les k-mers
    seq_kmers = generate_kmers(sequence, k)
    for kmer in seq_kmers:
        if kmer in kmer_counts:
            kmer_counts[kmer] += 1

    # Normaliser (fréquences)
    total = len(seq_kmers)
    if total > 0:
        frequencies = np.array([kmer_counts[kmer] / total for kmer in all_kmers])
    else:
        frequencies = np.zeros(len(all_kmers))

    return frequencies, all_kmers

def process_fasta_file(fasta_file_path):
    """
    Traite un fichier FASTA complet
    Output: liste de séquences encodées + liste de k-mers de référence
    """
    with open(fasta_file_path, 'r') as f:
        content = f.read()

    sequence = clean_dna_sequence(content)

    # Découper en sous-séquences si trop long
    chunk_size = 1000  # 1000 bp par sous-séquence
    sequences = []
    for i in range(0, len(sequence), chunk_size):
        seq_chunk = sequence[i:i+chunk_size]
        if len(seq_chunk) > 100:  # Au moins 100 bp
            sequences.append(seq_chunk)

    # Encoder chaque sous-séquence
    encoded_sequences = []
    all_kmers = generate_all_possible_kmers(4)

    for seq in sequences:
        freq, _ = encode_sequence_to_kmers(seq, k=4)
        encoded_sequences.append(freq)

    return np.array(encoded_sequences), all_kmers
