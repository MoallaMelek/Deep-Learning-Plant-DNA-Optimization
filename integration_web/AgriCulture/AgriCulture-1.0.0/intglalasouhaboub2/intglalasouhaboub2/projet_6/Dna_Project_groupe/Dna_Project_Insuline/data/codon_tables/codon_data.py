"""
Codon Usage Data Module
=======================
Contains real codon usage tables from Kazusa Codon Usage Database
for the 4 plant species used in Module 5.

Data Format:
- Each table is a dictionary mapping codons to frequencies (per 1000 codons)
- Codons are in DNA format (T instead of U)
- Data collected from: https://www.kazusa.or.jp/codon/

Species:
1. Arabidopsis thaliana (species=3702)
2. Oryza sativa - Rice (species=4530)
3. Zea mays - Maize (species=4577)
4. Phoenix dactylifera - Date palm (species=42345)
"""

# =============================================================================
# CODON TO AMINO ACID MAPPING
# =============================================================================
# Standard genetic code: maps each codon to its amino acid (single letter code)
# Stop codons are marked with '*'

CODON_TO_AA = {
    'TTT': 'F', 'TTC': 'F',  # Phenylalanine
    'TTA': 'L', 'TTG': 'L', 'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',  # Leucine
    'ATT': 'I', 'ATC': 'I', 'ATA': 'I',  # Isoleucine
    'ATG': 'M',  # Methionine (Start codon)
    'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',  # Valine
    'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S', 'AGT': 'S', 'AGC': 'S',  # Serine
    'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',  # Proline
    'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',  # Threonine
    'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',  # Alanine
    'TAT': 'Y', 'TAC': 'Y',  # Tyrosine
    'TAA': '*', 'TAG': '*', 'TGA': '*',  # Stop codons
    'CAT': 'H', 'CAC': 'H',  # Histidine
    'CAA': 'Q', 'CAG': 'Q',  # Glutamine
    'AAT': 'N', 'AAC': 'N',  # Asparagine
    'AAA': 'K', 'AAG': 'K',  # Lysine
    'GAT': 'D', 'GAC': 'D',  # Aspartic acid
    'GAA': 'E', 'GAG': 'E',  # Glutamic acid
    'TGT': 'C', 'TGC': 'C',  # Cysteine
    'TGG': 'W',  # Tryptophan
    'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R', 'AGA': 'R', 'AGG': 'R',  # Arginine
    'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G',  # Glycine
}

# Reverse mapping: amino acid to list of codons
AA_TO_CODONS = {}
for codon, aa in CODON_TO_AA.items():
    if aa not in AA_TO_CODONS:
        AA_TO_CODONS[aa] = []
    AA_TO_CODONS[aa].append(codon)


# =============================================================================
# ARABIDOPSIS THALIANA CODON USAGE TABLE
# =============================================================================
# Source: Kazusa Codon Usage Database (species=3702)
# Values are frequencies per 1000 codons

ARABIDOPSIS_THALIANA = {
    # Phenylalanine (F)
    'TTT': 21.8, 'TTC': 20.7,
    # Leucine (L)
    'TTA': 12.7, 'TTG': 20.9, 'CTT': 24.1, 'CTC': 16.1, 'CTA': 9.9, 'CTG': 9.8,
    # Isoleucine (I)
    'ATT': 21.5, 'ATC': 18.5, 'ATA': 12.6,
    # Methionine (M)
    'ATG': 24.5,
    # Valine (V)
    'GTT': 27.2, 'GTC': 12.8, 'GTA': 9.9, 'GTG': 17.4,
    # Serine (S)
    'TCT': 25.2, 'TCC': 11.2, 'TCA': 18.3, 'TCG': 9.3, 'AGT': 14.0, 'AGC': 11.3,
    # Proline (P)
    'CCT': 18.7, 'CCC': 5.3, 'CCA': 16.1, 'CCG': 8.6,
    # Threonine (T)
    'ACT': 17.5, 'ACC': 10.3, 'ACA': 15.7, 'ACG': 7.7,
    # Alanine (A)
    'GCT': 28.3, 'GCC': 10.3, 'GCA': 17.5, 'GCG': 9.0,
    # Tyrosine (Y)
    'TAT': 14.6, 'TAC': 13.7,
    # Stop codons (*)
    'TAA': 0.9, 'TAG': 0.5, 'TGA': 1.2,
    # Histidine (H)
    'CAT': 13.8, 'CAC': 8.7,
    # Glutamine (Q)
    'CAA': 19.4, 'CAG': 15.2,
    # Asparagine (N)
    'AAT': 22.3, 'AAC': 20.9,
    # Lysine (K)
    'AAA': 30.8, 'AAG': 32.7,
    # Aspartic acid (D)
    'GAT': 36.6, 'GAC': 17.2,
    # Glutamic acid (E)
    'GAA': 34.3, 'GAG': 32.2,
    # Cysteine (C)
    'TGT': 10.5, 'TGC': 7.2,
    # Tryptophan (W)
    'TGG': 12.5,
    # Arginine (R)
    'CGT': 9.0, 'CGC': 3.8, 'CGA': 6.3, 'CGG': 4.9, 'AGA': 19.0, 'AGG': 11.0,
    # Glycine (G)
    'GGT': 22.2, 'GGC': 9.2, 'GGA': 24.2, 'GGG': 10.2,
}


# =============================================================================
# ORYZA SATIVA (RICE) CODON USAGE TABLE
# =============================================================================
# Source: Kazusa Codon Usage Database (species=4530)
# Values are frequencies per 1000 codons

ORYZA_SATIVA = {
    # Phenylalanine (F)
    'TTT': 13.1, 'TTC': 22.4,
    # Leucine (L)
    'TTA': 6.1, 'TTG': 14.7, 'CTT': 15.2, 'CTC': 25.8, 'CTA': 7.7, 'CTG': 21.0,
    # Isoleucine (I)
    'ATT': 14.2, 'ATC': 19.4, 'ATA': 8.8,
    # Methionine (M)
    'ATG': 23.8,
    # Valine (V)
    'GTT': 15.5, 'GTC': 20.1, 'GTA': 6.8, 'GTG': 24.3,
    # Serine (S)
    'TCT': 12.7, 'TCC': 16.3, 'TCA': 12.4, 'TCG': 12.3, 'AGT': 8.8, 'AGC': 16.0,
    # Proline (P)
    'CCT': 13.6, 'CCC': 12.1, 'CCA': 14.2, 'CCG': 18.0,
    # Threonine (T)
    'ACT': 10.6, 'ACC': 14.9, 'ACA': 11.6, 'ACG': 11.4,
    # Alanine (A)
    'GCT': 19.6, 'GCC': 30.8, 'GCA': 17.3, 'GCG': 26.6,
    # Tyrosine (Y)
    'TAT': 10.0, 'TAC': 15.1,
    # Stop codons (*)
    'TAA': 0.7, 'TAG': 0.8, 'TGA': 1.2,
    # Histidine (H)
    'CAT': 11.3, 'CAC': 13.8,
    # Glutamine (Q)
    'CAA': 13.5, 'CAG': 20.8,
    # Asparagine (N)
    'AAT': 15.1, 'AAC': 18.5,
    # Lysine (K)
    'AAA': 16.0, 'AAG': 32.3,
    # Aspartic acid (D)
    'GAT': 25.3, 'GAC': 28.1,
    # Glutamic acid (E)
    'GAA': 21.6, 'GAG': 38.6,
    # Cysteine (C)
    'TGT': 6.2, 'TGC': 12.4,
    # Tryptophan (W)
    'TGG': 13.8,
    # Arginine (R)
    'CGT': 7.2, 'CGC': 16.1, 'CGA': 6.4, 'CGG': 13.4, 'AGA': 10.5, 'AGG': 16.0,
    # Glycine (G)
    'GGT': 14.8, 'GGC': 29.5, 'GGA': 15.9, 'GGG': 17.1,
}


# =============================================================================
# ZEA MAYS (MAIZE) CODON USAGE TABLE
# =============================================================================
# Source: Kazusa Codon Usage Database (species=4577)
# Values are frequencies per 1000 codons

ZEA_MAYS = {
    # Phenylalanine (F)
    'TTT': 12.6, 'TTC': 25.1,
    # Leucine (L)
    'TTA': 5.7, 'TTG': 13.0, 'CTT': 15.7, 'CTC': 25.4, 'CTA': 7.3, 'CTG': 25.8,
    # Isoleucine (I)
    'ATT': 13.8, 'ATC': 22.7, 'ATA': 8.4,
    # Methionine (M)
    'ATG': 24.2,
    # Valine (V)
    'GTT': 15.7, 'GTC': 21.0, 'GTA': 6.4, 'GTG': 25.5,
    # Serine (S)
    'TCT': 12.0, 'TCC': 16.4, 'TCA': 11.0, 'TCG': 10.7, 'AGT': 7.8, 'AGC': 16.4,
    # Proline (P)
    'CCT': 12.6, 'CCC': 13.5, 'CCA': 13.8, 'CCG': 15.8,
    # Threonine (T)
    'ACT': 10.7, 'ACC': 16.6, 'ACA': 10.5, 'ACG': 11.0,
    # Alanine (A)
    'GCT': 21.0, 'GCC': 31.1, 'GCA': 16.7, 'GCG': 23.3,
    # Tyrosine (Y)
    'TAT': 9.5, 'TAC': 19.4,
    # Stop codons (*)
    'TAA': 0.5, 'TAG': 0.7, 'TGA': 1.1,
    # Histidine (H)
    'CAT': 10.1, 'CAC': 14.9,
    # Glutamine (Q)
    'CAA': 13.2, 'CAG': 23.7,
    # Asparagine (N)
    'AAT': 13.5, 'AAC': 22.1,
    # Lysine (K)
    'AAA': 15.1, 'AAG': 39.4,
    # Aspartic acid (D)
    'GAT': 22.9, 'GAC': 32.1,
    # Glutamic acid (E)
    'GAA': 19.9, 'GAG': 40.8,
    # Cysteine (C)
    'TGT': 5.6, 'TGC': 12.2,
    # Tryptophan (W)
    'TGG': 13.0,
    # Arginine (R)
    'CGT': 6.0, 'CGC': 14.3, 'CGA': 4.4, 'CGG': 9.5, 'AGA': 8.8, 'AGG': 14.8,
    # Glycine (G)
    'GGT': 14.1, 'GGC': 30.3, 'GGA': 13.4, 'GGG': 15.4,
}


# =============================================================================
# PHOENIX DACTYLIFERA (DATE PALM) CODON USAGE TABLE
# =============================================================================
# Source: Kazusa Codon Usage Database (species=42345)
# Note: This species has limited data (small sample size)
# Values are frequencies per 1000 codons

PHOENIX_DACTYLIFERA = {
    # Phenylalanine (F)
    'TTT': 15.2, 'TTC': 15.2,
    # Leucine (L)
    'TTA': 7.6, 'TTG': 7.6, 'CTT': 22.7, 'CTC': 30.3, 'CTA': 0.0, 'CTG': 0.0,
    # Isoleucine (I)
    'ATT': 0.0, 'ATC': 60.6, 'ATA': 7.6,
    # Methionine (M)
    'ATG': 53.0,
    # Valine (V)
    'GTT': 37.9, 'GTC': 15.2, 'GTA': 7.6, 'GTG': 0.0,
    # Serine (S)
    'TCT': 7.6, 'TCC': 7.6, 'TCA': 15.2, 'TCG': 22.7, 'AGT': 0.0, 'AGC': 15.2,
    # Proline (P)
    'CCT': 15.2, 'CCC': 7.6, 'CCA': 15.2, 'CCG': 7.6,
    # Threonine (T)
    'ACT': 22.7, 'ACC': 22.7, 'ACA': 7.6, 'ACG': 0.0,
    # Alanine (A)
    'GCT': 15.2, 'GCC': 15.2, 'GCA': 7.6, 'GCG': 22.7,
    # Tyrosine (Y)
    'TAT': 15.2, 'TAC': 22.7,
    # Stop codons (*)
    'TAA': 7.6, 'TAG': 0.0, 'TGA': 0.0,
    # Histidine (H)
    'CAT': 15.2, 'CAC': 15.2,
    # Glutamine (Q)
    'CAA': 15.2, 'CAG': 37.9,
    # Asparagine (N)
    'AAT': 22.7, 'AAC': 15.2,
    # Lysine (K)
    'AAA': 7.6, 'AAG': 37.9,
    # Aspartic acid (D)
    'GAT': 22.7, 'GAC': 15.2,
    # Glutamic acid (E)
    'GAA': 30.3, 'GAG': 45.5,
    # Cysteine (C)
    'TGT': 0.0, 'TGC': 15.2,
    # Tryptophan (W)
    'TGG': 15.2,
    # Arginine (R)
    'CGT': 7.6, 'CGC': 0.0, 'CGA': 0.0, 'CGG': 0.0, 'AGA': 0.0, 'AGG': 7.6,
    # Glycine (G)
    'GGT': 15.2, 'GGC': 45.5, 'GGA': 30.3, 'GGG': 30.3,
}


# =============================================================================
# MASTER DICTIONARY FOR EASY ACCESS
# =============================================================================
# Use this to switch between species easily

CODON_TABLES = {
    "Arabidopsis thaliana": ARABIDOPSIS_THALIANA,
    "Oryza sativa": ORYZA_SATIVA,
    "Zea mays": ZEA_MAYS,
    "Phoenix dactylifera": PHOENIX_DACTYLIFERA,
}

# List of all supported species
SUPPORTED_SPECIES = list(CODON_TABLES.keys())


def get_codon_table(species: str) -> dict:
    """
    Get the codon usage table for a specific species.
    
    Args:
        species: Name of the plant species
        
    Returns:
        Dictionary mapping codons to frequencies (per 1000)
        
    Raises:
        ValueError: If species is not supported
    """
    if species not in CODON_TABLES:
        raise ValueError(f"Species '{species}' not found. Supported: {SUPPORTED_SPECIES}")
    return CODON_TABLES[species]


def get_codons_for_aa(aa: str) -> list:
    """
    Get all codons that encode a specific amino acid.
    
    Args:
        aa: Single letter amino acid code (e.g., 'M', 'L', 'K')
        
    Returns:
        List of codons that encode this amino acid
    """
    if aa not in AA_TO_CODONS:
        raise ValueError(f"Unknown amino acid: {aa}")
    return AA_TO_CODONS[aa]


if __name__ == "__main__":
    # Quick test
    print("Codon Usage Data Module")
    print("=" * 50)
    print(f"Supported species: {SUPPORTED_SPECIES}")
    print()
    
    # Show sample data for Arabidopsis
    print("Sample: Arabidopsis thaliana codon frequencies")
    print("-" * 40)
    for codon in ['ATG', 'TGG', 'TAA', 'TAG', 'TGA']:
        freq = ARABIDOPSIS_THALIANA.get(codon, 0)
        aa = CODON_TO_AA.get(codon, '?')
        print(f"  {codon} -> {aa}: {freq} per 1000")
