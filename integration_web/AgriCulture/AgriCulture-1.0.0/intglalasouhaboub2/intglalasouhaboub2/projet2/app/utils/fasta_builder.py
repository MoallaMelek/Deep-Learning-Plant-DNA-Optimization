def build_fasta_content(snp_names, traits, df_agront, alleles, resultats_odm) -> str:
    """
    Construit le contenu FASTA pour une liste de SNPs et de traits.

    Chaque SNP × trait produit 2 à 3 entrées :
      - ORIGINAL     : séquence de référence
      - BASE_EDITING : séquence optimisée
      - ODM          : oligo ODM si disponible
    """
    lines = []

    for snp in snp_names:
        for trait in traits:
            row = df_agront[
                (df_agront["SNP"] == snp) & (df_agront["trait"] == trait)
            ]
            if row.empty:
                continue

            seq_orig = str(row["sequence_originale"].values[0])
            seq_opt  = str(row["sequence_optimisee"].values[0])

            # Séquence originale
            allele_ref = row["allele_ref"].values[0]
            header = f">{snp}_{trait.upper()}_ORIGINAL allele={allele_ref}"
            lines.append(header)
            lines += [seq_orig[i: i + 60] for i in range(0, len(seq_orig), 60)]

            # Séquence optimisée (base editing)
            allele_alt = row["allele_alt"].values[0]
            header = f">{snp}_{trait.upper()}_BASE_EDITING allele={allele_alt}"
            lines.append(header)
            lines += [seq_opt[i: i + 60] for i in range(0, len(seq_opt), 60)]

            # Oligo ODM si présent
            odm_rows = resultats_odm[resultats_odm["SNP"] == snp].head(1)
            if not odm_rows.empty:
                seq_odm   = str(odm_rows["Sequence"].values[0])
                score_odm = odm_rows["Score_ODM"].values[0]

                # Robustesse : score_odm peut être une string ou un float
                try:
                    score_val = float(str(score_odm).strip().lstrip("[").rstrip("]"))
                except (ValueError, TypeError):
                    score_val = 0.0

                header = f">{snp}_{trait.upper()}_ODM score={score_val:.3f}"
                lines.append(header)
                lines += [seq_odm[i: i + 60] for i in range(0, len(seq_odm), 60)]

    return "\n".join(lines)