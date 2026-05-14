"""
fiche_generator.py
------------------
Generates a complete IRA genomic report HTML for any DNA sequence.
"""

import re
import os
import json
import requests
import numpy as np
from datetime import date
from collections import Counter
from cgr_generator import compute_cgr_points, compute_nucleotide_composition
from gbif_photo import get_primary_photo


# ── Extract info from RAG ─────────────────────────────────────

def extract_info_from_rag(description: str) -> dict:
    result = {'species': None, 'gene': None, 'accession': None}

    species_patterns = [
        r'\b(Triticum\s+\w+)\b',
        r'\b(Hordeum\s+\w+)\b',
        r'\b(Aegilops\s+\w+)\b',
        r'\b(Zea\s+\w+)\b',
        r'\b(Oryza\s+\w+)\b',
        r'\b([A-Z][a-z]+\s+[a-z]+ium)\b',
        r'\b([A-Z][a-z]+\s+[a-z]+ivum)\b',
        r'\b([A-Z][a-z]+\s+[a-z]+aris)\b',
    ]
    for pat in species_patterns:
        match = re.search(pat, description)
        if match:
            result['species'] = match.group(1)
            break

    gene_patterns = [
        r'\b(Ta[A-Z][a-zA-Z0-9]+)\b',
        r'\b(DREB\d*[A-Z]?)\b',
        r'\b(WRKY\d+)\b',
        r'\b(HSP\d+)\b',
        r'\b(CBF\d*)\b',
        r'\b(LEA\d*)\b',
        r'\b(ERD\d+)\b',
    ]
    for pat in gene_patterns:
        match = re.search(pat, description)
        if match:
            result['gene'] = match.group(1)
            break

    acc_match = re.search(r'\b([A-Z]{1,2}\d{5,8}\.\d+)\b', description)
    if acc_match:
        result['accession'] = acc_match.group(1)

    return result


# ── Trait scores ──────────────────────────────────────────────

def compute_trait_scores(engine, sequence: str) -> dict:
    traits = ['drought_tolerance', 'heat_tolerance', 'salt_tolerance', 'disease_resistance']
    scores = {}
    for trait in traits:
        results = engine.search(sequence, top_k=20, trait_filter=trait)
        if results:
            top5 = [r.dense_dnabert for r in results[:5] if r.dense_dnabert > 0]
            scores[trait] = round(np.mean(top5) * 100, 1) if top5 else 0.0
        else:
            scores[trait] = 0.0
    return scores


# ── RAG description ───────────────────────────────────────────

def generate_description(rag, engine, sequence: str, accession: str) -> tuple:
    """Returns (description_text, articles_list)"""
    results = engine.search(sequence, top_k=10)
    if not results:
        return "Description non disponible.", []

    rag._last_xgb_prediction = engine._last_xgb_prediction
    answer = rag.answer(
        f"Describe the biological function and agricultural significance of sequence {accession} "
        f"for arid region crop improvement in Tunisia. Mention the gene family, stress tolerance "
        f"mechanisms, and practical applications for IRA research.",
        results
    )
    text = answer.answer
    ref_idx = text.find('\nREFERENCES:')
    if ref_idx > 0:
        text = text[:ref_idx].strip()

    articles = getattr(rag, '_last_articles', [])
    return text, articles


# ── CGR ───────────────────────────────────────────────────────

def build_cgr_js(sequence: str, size: int = 400):
    points = compute_cgr_points(sequence, size=size)
    base_colors = {
        'A': '#4CAF8A',
        'T': '#E07B5A',
        'G': '#5A9DE0',
        'C': '#E0C55A',
    }
    js = '[\n'
    for x, y, base in points:
        color = base_colors.get(base, '#888')
        js += '            [' + str(round(x,2)) + ',' + str(round(y,2)) + ',"' + color + '"],\n'
    js += '        ]'
    dot_size = max(0.8, min(2.0, 400 / len(points) * 0.9)) if points else 1.0
    return js, dot_size


# ── Colorize sequence ─────────────────────────────────────────

def colorize_sequence(sequence: str, length: int = 120) -> str:
    colors = {'A': '#4CAF8A', 'T': '#E07B5A', 'G': '#5A9DE0', 'C': '#E0C55A'}
    result = ''
    for base in sequence[:length]:
        color = colors.get(base.upper(), '#888')
        result += '<span style="color:' + color + '">' + base + '</span>'
    return result


# ── Trait bar ─────────────────────────────────────────────────

def trait_bar(label, score, color):
    return (
        '<div class="trait-row">'
        '<span class="trait-label">' + label + '</span>'
        '<div class="trait-bar-bg">'
        '<div class="trait-bar-fill" style="width:' + str(score) + '%;background:' + color + '"></div>'
        '</div>'
        '<span class="trait-pct">' + str(score) + '%</span>'
        '</div>'
    )


# ── Articles HTML ─────────────────────────────────────────────

def build_articles_html(articles) -> str:
    if not articles:
        return ''

    html = '<div class="articles-section">'
    html += '<div class="section-title">Articles scientifiques · Europe PMC</div>'

    for i, a in enumerate(articles[:5]):
        pmid_clean = a.pmid.replace('PMID:', '').strip() if a.pmid else ''
        if pmid_clean:
            link = 'https://pubmed.ncbi.nlm.nih.gov/' + pmid_clean
        elif a.doi:
            link = 'https://doi.org/' + a.doi
        else:
            link = ''

        html += '<div class="article-row">'
        html += '<span class="article-num">[' + str(i+1) + ']</span>'
        html += '<div class="article-content">'
        html += '<div class="article-title">' + (a.title or '') + '</div>'
        meta = (a.authors or '') + (' (' + a.year + ')' if a.year else '')
        if a.journal:
            meta += ' — ' + a.journal
        html += '<div class="article-meta">' + meta + '</div>'
        if link:
            html += '<a class="article-link" href="' + link + '" target="_blank">PubMed →</a>'
        html += '</div></div>'

    html += '</div>'
    return html


# ── Main generator ────────────────────────────────────────────

def generate_fiche(
    engine,
    rag,
    sequence         : str,
    accession        : str  = '',
    species          : str  = 'Triticum aestivum',
    gene             : str  = '',
    trait            : str  = '',
    output_file      : str  = None,
    show_description : bool = True,
) -> str:

    print(f'Generating fiche for {accession or "sequence"} ...')

    # Auto-detect gene and trait from engine
    results  = engine.search(sequence, top_k=5)
    xgb_pred = engine._last_xgb_prediction or {}

    if not trait and results:
        trait = results[0].trait
    if not gene and results:
        for r in results:
            if r.gene_name and r.gene_name not in ('', '-'):
                gene = r.gene_name
                break

    detected_trait      = xgb_pred.get('trait', trait)
    detected_confidence = xgb_pred.get('confidence', 0.0)

    # Composition
    comp    = compute_nucleotide_composition(sequence)
    seq_len = len(sequence)

    print('  Computing trait scores ...')
    trait_scores = compute_trait_scores(engine, sequence)

    print('  Building CGR ...')
    js_points, dot_size = build_cgr_js(sequence, size=400)
    colored_seq         = colorize_sequence(sequence, 120)

    # Generate RAG description first
    description = ''
    articles    = []
    if show_description:
        print('  Generating RAG description ...')
        description, articles = generate_description(rag, engine, sequence, accession)

        # Auto-extract species, gene, accession from RAG
        extracted = extract_info_from_rag(description)

        if extracted['species']:
            print(f'  Species from RAG  : {extracted["species"]}')
            species = extracted['species']

        if extracted['gene'] and not gene:
            print(f'  Gene from RAG     : {extracted["gene"]}')
            gene = extracted['gene']

        if extracted['accession'] and not accession:
            print(f'  Accession from RAG: {extracted["accession"]}')
            accession = extracted['accession']

    # Fetch photo AFTER species detected
    print('  Fetching photo ...')
    photo          = get_primary_photo(species, country='TN', save_path='plant_photo.jpg')
    photo_url      = photo['url']                                     if photo else ''
    photo_credit   = photo.get('photographer', 'iNaturalist / GBIF') if photo else ''
    photo_location = photo.get('location', '')                        if photo else ''

    # Trait labels and colors
    trait_labels = {
        'drought_tolerance'  : 'Tolerance secheresse',
        'heat_tolerance'     : 'Resistance chaleur',
        'salt_tolerance'     : 'Tolerance salinite',
        'disease_resistance' : 'Resistance maladies',
    }
    trait_colors = {
        'drought_tolerance'  : '#4CAF8A',
        'heat_tolerance'     : '#E07B5A',
        'salt_tolerance'     : '#5A9DE0',
        'disease_resistance' : '#E0C55A',
    }

    bars_html     = ''
    for t, score in trait_scores.items():
        bars_html += trait_bar(trait_labels.get(t, t), score, trait_colors.get(t, '#888'))

    articles_html = build_articles_html(articles)
    badge_color   = trait_colors.get(detected_trait, '#888')
    today         = date.today().strftime('%d/%m/%Y')
    json_xgb      = json.dumps(xgb_pred.get('probabilities', {}))
    json_colors   = json.dumps(trait_colors)
    json_labels   = json.dumps(trait_labels)

    # Photo
    local_photo = photo.get('local_path') if photo else None
    if local_photo and os.path.exists(local_photo):
        photo_img = '<img class="photo-main" src="' + local_photo + '" alt="' + species + '" style="object-fit:cover;width:100%;height:280px">'
    elif photo_url:
        photo_img = '<img class="photo-main" src="' + photo_url + '" alt="' + species + '" style="object-fit:cover;width:100%;height:280px">'
    else:
        photo_img = '<div class="photo-main" style="background:#e8e4dc;height:280px"></div>'

    gene_html      = '<div>Gene : <strong>' + gene + '</strong></div>' if gene else ''
    accession_html = '<div>Accession : <strong>' + accession + '</strong></div>' if accession else ''

    html = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fiche IRA — """ + (accession or species) + """</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Georgia', serif; background: #f5f2ec; color: #2a2a2a; }
        .header { background: #f5f2ec; padding: 28px 40px 20px; border-bottom: 1px solid #ddd; }
        .header-top { display: flex; justify-content: space-between; align-items: flex-start; }
        .platform-label { font-family: 'Courier New', monospace; font-size: 0.65rem; letter-spacing: 0.2em; color: #888; text-transform: uppercase; margin-bottom: 10px; }
        .platform-label .dot { color: #4CAF8A; margin-right: 6px; }
        .species-name { font-size: 2.4rem; font-style: italic; color: #1a1a1a; font-weight: normal; line-height: 1.1; }
        .species-sub { font-size: 0.85rem; color: #666; margin-top: 6px; }
        .header-meta { text-align: right; font-family: 'Courier New', monospace; font-size: 0.75rem; color: #888; line-height: 2; }
        .header-meta strong { color: #2a2a2a; }
        .confidence-badge { display: inline-block; margin-top: 10px; padding: 6px 16px; background: """ + badge_color + """; color: white; font-family: 'Courier New', monospace; font-size: 0.8rem; font-weight: bold; border-radius: 3px; }
        .tags { display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
        .tag { padding: 3px 12px; border: 1px solid #ccc; border-radius: 2px; font-size: 0.72rem; font-family: 'Courier New', monospace; color: #555; background: white; }
        .tag.accent { border-color: #c0392b; color: #c0392b; }
        .main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; border-bottom: 1px solid #ddd; }
        .panel { padding: 24px; border-right: 1px solid #ddd; }
        .panel:last-child { border-right: none; }
        .panel-label { font-family: 'Courier New', monospace; font-size: 0.6rem; letter-spacing: 0.2em; color: #999; text-transform: uppercase; margin-bottom: 14px; }
        .photo-main { width: 100%; height: 280px; object-fit: cover; border-radius: 3px; display: block; }
        .photo-credit { font-size: 0.65rem; color: #aaa; margin-top: 6px; font-style: italic; display: flex; justify-content: space-between; }
        #cgr-canvas { border-radius: 3px; display: block; width: 100%; }
        .cgr-comp { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; margin-top: 12px; }
        .comp-box { text-align: center; padding: 8px 4px; background: white; border-radius: 3px; border: 1px solid #eee; }
        .comp-pct { font-size: 1.1rem; font-weight: bold; }
        .comp-base { font-size: 0.6rem; font-family: 'Courier New', monospace; color: #999; margin-top: 2px; }
        .traits-section { padding: 24px 40px; display: grid; grid-template-columns: 1fr 1fr; gap: 30px; border-bottom: 1px solid #ddd; background: white; }
        .trait-row { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
        .trait-label { font-size: 0.78rem; color: #555; min-width: 160px; }
        .trait-bar-bg { flex: 1; height: 6px; background: #eee; border-radius: 3px; overflow: hidden; }
        .trait-bar-fill { height: 100%; border-radius: 3px; }
        .trait-pct { font-family: 'Courier New', monospace; font-size: 0.75rem; color: #555; min-width: 38px; text-align: right; }
        .section-title { font-family: 'Courier New', monospace; font-size: 0.6rem; letter-spacing: 0.2em; color: #999; text-transform: uppercase; margin-bottom: 16px; }
        .description-section { padding: 28px 40px; border-bottom: 1px solid #ddd; background: #f5f2ec; }
        .description-text { font-size: 0.9rem; line-height: 1.8; color: #333; max-width: 800px; }
        .source-tags { display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap; }
        .source-tag { padding: 3px 10px; border: 1px solid #ccc; font-family: 'Courier New', monospace; font-size: 0.65rem; color: #777; border-radius: 2px; background: white; }
        .articles-section { padding: 24px 40px; border-bottom: 1px solid #ddd; background: white; }
        .article-row { display: flex; gap: 12px; padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
        .article-row:last-child { border-bottom: none; }
        .article-num { font-family: 'Courier New', monospace; font-size: 0.75rem; color: #999; min-width: 24px; margin-top: 2px; }
        .article-content { flex: 1; }
        .article-title { font-size: 0.85rem; color: #1a1a1a; margin-bottom: 3px; line-height: 1.4; }
        .article-meta { font-size: 0.72rem; color: #888; font-style: italic; margin-bottom: 4px; }
        .article-link { font-family: 'Courier New', monospace; font-size: 0.68rem; color: #4CAF8A; text-decoration: none; border: 1px solid #4CAF8A; padding: 2px 8px; border-radius: 2px; display: inline-block; margin-top: 3px; }
        .article-link:hover { background: #4CAF8A; color: white; }
        .sequence-section { background: #1a1a1a; padding: 20px 40px; border-bottom: 1px solid #333; }
        .seq-label { font-family: 'Courier New', monospace; font-size: 0.6rem; letter-spacing: 0.2em; color: #555; text-transform: uppercase; margin-bottom: 10px; }
        .seq-text { font-family: 'Courier New', monospace; font-size: 0.8rem; line-height: 1.9; word-break: break-all; }
        .footer { padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; background: #f5f2ec; }
        .footer-text { font-family: 'Courier New', monospace; font-size: 0.65rem; color: #aaa; line-height: 1.8; }
        .footer-badge { font-family: 'Courier New', monospace; font-size: 0.6rem; color: #aaa; text-align: right; border: 1px solid #ddd; padding: 8px 12px; border-radius: 3px; }
    </style>
</head>
<body>

<div class="header">
    <div class="header-top">
        <div>
            <div class="platform-label"><span class="dot">&#9679;</span>IRA Genomics Platform &middot; Module 7 &middot; DNA Search Engine</div>
            <div class="species-name">""" + (species.split()[0] if species else '') + """ <span style="font-style:normal;font-size:1.8rem">""" + (' '.join(species.split()[1:]) if species else '') + """</span></div>
            <div class="species-sub">""" + species + """ &mdash; Zone aride, Tunisie</div>
            <div class="tags">
                <span class="tag">Triticeae</span>
                <span class="tag">Poaceae</span>
                <span class="tag accent">""" + detected_trait.replace('_', ' ').title() + """</span>
                <span class="tag">Zone IRA &middot; Sud Tunisie</span>
            </div>
        </div>
        <div class="header-meta">
            """ + gene_html + """
            """ + accession_html + """
            <div>Longueur : <strong>""" + str(seq_len) + """ bp</strong></div>
            <div>Analyse : <strong>""" + today + """</strong></div>
            <div class="confidence-badge">&#10003; """ + f'{detected_confidence:.1%}' + """ confiance</div>
        </div>
    </div>
</div>

<div class="main-grid">
    <div class="panel">
        <div class="panel-label">Photographie de reference &middot; iNaturalist</div>
        """ + photo_img + """
        <div class="photo-credit">
            <span>&#169; """ + photo_credit + """ &middot; CC BY 4.0</span>
            <span>""" + photo_location + """</span>
        </div>
    </div>
    <div class="panel">
        <div class="panel-label">Empreinte CGR &middot; Chaos Game Representation</div>
        <canvas id="cgr-canvas" width="400" height="300"></canvas>
        <div class="cgr-comp">
            <div class="comp-box"><div class="comp-pct" style="color:#4CAF8A">""" + str(comp['A']) + """%</div><div class="comp-base">A</div></div>
            <div class="comp-box"><div class="comp-pct" style="color:#E07B5A">""" + str(comp['T']) + """%</div><div class="comp-base">T</div></div>
            <div class="comp-box"><div class="comp-pct" style="color:#5A9DE0">""" + str(comp['G']) + """%</div><div class="comp-base">G</div></div>
            <div class="comp-box"><div class="comp-pct" style="color:#E0C55A">""" + str(comp['C']) + """%</div><div class="comp-base">C</div></div>
        </div>
    </div>
</div>

<div class="traits-section">
    <div>
        <div class="section-title">Scores de tolerance aux stress &middot; DNABERT-2 + FAISS</div>
        """ + bars_html + """
    </div>
    <div>
        <div class="section-title">Module 1 &middot; Classification XGBoost (F1=0.738)</div>
        <div id="xgb-bars"></div>
    </div>
</div>

""" + ("""<div class="description-section">
    <div class="section-title">Description generee &middot; RAG + LLaMA 3.1 &middot; Groq</div>
    <div class="description-text">""" + description + """</div>
    <div class="source-tags">
        <span class="source-tag">NCBI GenBank</span>
        <span class="source-tag">Europe PMC</span>
        <span class="source-tag">DNABERT-2</span>
        <span class="source-tag">IRA Medenine</span>
    </div>
</div>""" if description else '') + """

""" + articles_html + """

<div class="sequence-section">
    <div class="seq-label">Sequence &middot; Positions 1-120 / """ + str(seq_len) + """ bp</div>
    <div class="seq-text">""" + colored_seq + """</div>
</div>

<div class="footer">
    <div class="footer-text">
        IRA &middot; Institut des Regions Arides &middot; Medenine, Tunisie<br>
        Plateforme IA Genomique &middot; Module 7 &mdash; DNA Search Engine<br>
        Genere le """ + today + """ &middot; Sequence : """ + (accession or 'N/A') + """ &middot; Analyse : DNABERT-2 + k-mer + FAISS
    </div>
    <div class="footer-badge">Certificat<br>numerique<br>IRA-2026</div>
</div>

<script>
    const canvas  = document.getElementById('cgr-canvas');
    const ctx     = canvas.getContext('2d');
    const points  = """ + js_points + """;
    const dotSize = """ + str(round(dot_size, 2)) + """;

    ctx.fillStyle = '#0a0f0a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.font = 'bold 11px Courier New';
    ctx.fillStyle = '#E0C55A'; ctx.fillText('C', 6, 14);
    ctx.fillStyle = '#5A9DE0'; ctx.fillText('G', canvas.width-14, 14);
    ctx.fillStyle = '#4CAF8A'; ctx.fillText('A', 6, canvas.height-4);
    ctx.fillStyle = '#E07B5A'; ctx.fillText('T', canvas.width-14, canvas.height-4);

    points.forEach(function(p) {
        ctx.beginPath();
        ctx.arc(p[0] * canvas.width / 400, p[1] * canvas.height / 400, dotSize, 0, Math.PI * 2);
        ctx.fillStyle = p[2] + 'bb';
        ctx.fill();
    });

    const xgbProbs  = """ + json_xgb + """;
    const xgbColors = """ + json_colors + """;
    const xgbLabels = """ + json_labels + """;
    const xgbDiv    = document.getElementById('xgb-bars');
    if (xgbDiv && xgbProbs) {
        Object.entries(xgbProbs).forEach(function(entry) {
            var trait = entry[0], prob = entry[1];
            var pct   = (prob * 100).toFixed(0);
            var color = xgbColors[trait] || '#888';
            var label = xgbLabels[trait] || trait;
            xgbDiv.innerHTML += '<div class="trait-row"><span class="trait-label">' + label + '</span><div class="trait-bar-bg"><div class="trait-bar-fill" style="width:' + pct + '%;background:' + color + '"></div></div><span class="trait-pct">' + pct + '%</span></div>';
        });
    }
</script>
</body>
</html>"""

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'  Saved: {output_file}')

    print('  Done')
    return html