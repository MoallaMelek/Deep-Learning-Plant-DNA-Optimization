"""
cgr_generator.py
----------------
Generates Chaos Game Representation (CGR) of a DNA sequence.
CGR is a fractal visualization where each nucleotide places a point
halfway between the current position and the corner of its base.

Corners:
    C — top left
    G — top right  (we use: A=bottom-left, T=bottom-right, G=top-right, C=top-left)
    A — bottom left
    T — bottom right

Output: standalone HTML file with canvas-based CGR visualization.

Usage:
    from cgr_generator import generate_cgr_html, generate_cgr_svg
    html = generate_cgr_html("ATCGATCGATCG...", title="My Sequence")
"""

import re
from collections import Counter


# ── CGR calculation ───────────────────────────────────────────

def compute_cgr_points(sequence: str, size: int = 500):
    """
    Compute CGR point coordinates for a DNA sequence.
    Returns list of (x, y, base) tuples.
    """
    # Corner positions (normalized 0-1)
    corners = {
        'A': (0.0, 1.0),   # bottom left
        'T': (1.0, 1.0),   # bottom right
        'G': (1.0, 0.0),   # top right
        'C': (0.0, 0.0),   # top left
    }

    sequence = sequence.upper()
    points   = []
    x, y     = 0.5, 0.5   # start at center

    for base in sequence:
        if base not in corners:
            continue
        cx, cy = corners[base]
        x = (x + cx) / 2
        y = (y + cy) / 2
        points.append((x * size, y * size, base))

    return points


def compute_nucleotide_composition(sequence: str) -> dict:
    """Compute A/T/G/C percentages."""
    sequence = sequence.upper()
    total    = sum(1 for b in sequence if b in 'ATGC')
    if total == 0:
        return {'A': 0, 'T': 0, 'G': 0, 'C': 0}
    counts = Counter(b for b in sequence if b in 'ATGC')
    return {
        'A': round(counts.get('A', 0) / total * 100, 1),
        'T': round(counts.get('T', 0) / total * 100, 1),
        'G': round(counts.get('G', 0) / total * 100, 1),
        'C': round(counts.get('C', 0) / total * 100, 1),
    }


# ── Generate standalone CGR HTML ─────────────────────────────

def generate_cgr_html(
    sequence   : str,
    accession  : str = '',
    title      : str = '',
    output_file: str = None,
) -> str:
    """
    Generate a standalone HTML file with CGR visualization.
    Returns HTML string. Optionally saves to file.
    """
    points  = compute_cgr_points(sequence, size=500)
    comp    = compute_nucleotide_composition(sequence)
    seq_len = len(sequence)

    # Colors per base
    base_colors = {
        'A': '#4CAF8A',   # green
        'T': '#E07B5A',   # orange-red
        'G': '#5A9DE0',   # blue
        'C': '#E0C55A',   # yellow
    }

    # Build JavaScript points array
    js_points = '[\n'
    for x, y, base in points:
        color = base_colors.get(base, '#888888')
        js_points += f'        [{x:.2f}, {y:.2f}, "{color}"],\n'
    js_points += '    ]'

    # Colorize sequence preview (first 120 bases)
    seq_preview = sequence[:120]
    colored_seq = ''
    for base in seq_preview:
        color = base_colors.get(base.upper(), '#888')
        colored_seq += f'<span style="color:{color}">{base}</span>'

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CGR — {accession or title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Courier New', monospace;
            background: #0a0f0a;
            color: #c8d8c8;
            padding: 30px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 1.4rem;
            letter-spacing: 0.2em;
            color: #8fb88f;
            text-transform: uppercase;
        }}
        .header .sub {{
            font-size: 0.8rem;
            color: #556655;
            margin-top: 6px;
            letter-spacing: 0.15em;
        }}
        .main-grid {{
            display: grid;
            grid-template-columns: 520px 1fr;
            gap: 30px;
            max-width: 900px;
            margin: 0 auto;
        }}
        .cgr-container {{
            position: relative;
        }}
        canvas {{
            border: 1px solid #1a2a1a;
            border-radius: 4px;
            display: block;
        }}
        .corner-label {{
            position: absolute;
            font-size: 0.75rem;
            font-weight: bold;
            letter-spacing: 0.1em;
        }}
        .corner-C {{ top: 6px;  left: 8px;  color: #E0C55A; }}
        .corner-G {{ top: 6px;  right: 8px; color: #5A9DE0; }}
        .corner-A {{ bottom: 6px; left: 8px;  color: #4CAF8A; }}
        .corner-T {{ bottom: 6px; right: 8px; color: #E07B5A; }}
        .info-panel {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        .info-card {{
            background: #0f1a0f;
            border: 1px solid #1a2a1a;
            border-radius: 6px;
            padding: 16px;
        }}
        .info-card h3 {{
            font-size: 0.65rem;
            letter-spacing: 0.2em;
            color: #556655;
            text-transform: uppercase;
            margin-bottom: 12px;
        }}
        .comp-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}
        .comp-item {{
            text-align: center;
            padding: 10px;
            border-radius: 4px;
            background: #0a0f0a;
        }}
        .comp-pct {{
            font-size: 1.4rem;
            font-weight: bold;
        }}
        .comp-base {{
            font-size: 0.7rem;
            letter-spacing: 0.15em;
            color: #556655;
            margin-top: 3px;
        }}
        .meta-row {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #1a2a1a;
            font-size: 0.8rem;
        }}
        .meta-row:last-child {{ border-bottom: none; }}
        .meta-label {{ color: #556655; }}
        .meta-value {{ color: #8fb88f; }}
        .legend {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 0.72rem;
        }}
        .legend-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }}
        .seq-preview {{
            font-size: 0.72rem;
            line-height: 1.8;
            word-break: break-all;
            background: #0a0f0a;
            padding: 10px;
            border-radius: 4px;
            border: 1px solid #1a2a1a;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            font-size: 0.65rem;
            letter-spacing: 0.15em;
            color: #334433;
        }}
    </style>
</head>
<body>

<div class="header">
    <h1>Empreinte CGR &middot; Chaos Game Representation</h1>
    <div class="sub">IRA Genomics Platform &middot; Module 7 &middot; DNA Search Engine</div>
</div>

<div class="main-grid">

    <div class="cgr-container">
        <canvas id="cgr" width="500" height="500"></canvas>
        <span class="corner-label corner-C">C</span>
        <span class="corner-label corner-G">G</span>
        <span class="corner-label corner-A">A</span>
        <span class="corner-label corner-T">T</span>
    </div>

    <div class="info-panel">

        <div class="info-card">
            <h3>Identifiant</h3>
            <div class="meta-row">
                <span class="meta-label">Accession</span>
                <span class="meta-value">{accession or 'N/A'}</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">Longueur</span>
                <span class="meta-value">{seq_len:,} bp</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">Points CGR</span>
                <span class="meta-value">{len(points):,}</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">GC content</span>
                <span class="meta-value">{comp['G'] + comp['C']:.1f}%</span>
            </div>
        </div>

        <div class="info-card">
            <h3>Composition nucléotidique</h3>
            <div class="comp-grid">
                <div class="comp-item">
                    <div class="comp-pct" style="color:#4CAF8A">{comp['A']}%</div>
                    <div class="comp-base">A — adénine</div>
                </div>
                <div class="comp-item">
                    <div class="comp-pct" style="color:#E07B5A">{comp['T']}%</div>
                    <div class="comp-base">T — thymine</div>
                </div>
                <div class="comp-item">
                    <div class="comp-pct" style="color:#5A9DE0">{comp['G']}%</div>
                    <div class="comp-base">G — guanine</div>
                </div>
                <div class="comp-item">
                    <div class="comp-pct" style="color:#E0C55A">{comp['C']}%</div>
                    <div class="comp-base">C — cytosine</div>
                </div>
            </div>
        </div>

        <div class="info-card">
            <h3>Légende</h3>
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-dot" style="background:#4CAF8A"></div>
                    <span>A — bas gauche</span>
                </div>
                <div class="legend-item">
                    <div class="legend-dot" style="background:#E07B5A"></div>
                    <span>T — bas droit</span>
                </div>
                <div class="legend-item">
                    <div class="legend-dot" style="background:#5A9DE0"></div>
                    <span>G — haut droit</span>
                </div>
                <div class="legend-item">
                    <div class="legend-dot" style="background:#E0C55A"></div>
                    <span>C — haut gauche</span>
                </div>
            </div>
        </div>

        <div class="info-card">
            <h3>Séquence &middot; positions 1–120 / {seq_len} bp</h3>
            <div class="seq-preview">{colored_seq}</div>
        </div>

    </div>
</div>

<div class="footer">
    IRA &middot; Institut des Régions Arides &middot; Medenine, Tunisie &middot;
    Analyse DNABERT-2 + k-mer + FAISS
</div>

<script>
    const canvas  = document.getElementById('cgr');
    const ctx     = canvas.getContext('2d');
    const points  = {js_points};
    const dotSize = {max(0.5, min(1.5, 500/len(points)*0.8)):.2f};

    ctx.fillStyle = '#080d08';
    ctx.fillRect(0, 0, 500, 500);

    points.forEach(([x, y, color]) => {{
        ctx.beginPath();
        ctx.arc(x, y, dotSize, 0, Math.PI * 2);
        ctx.fillStyle = color + 'aa';
        ctx.fill();
    }});
</script>

</body>
</html>"""

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'CGR saved: {output_file}')

    return html


# ── Quick test ────────────────────────────────────────────────

if __name__ == '__main__':
    # Test with MZ935738.1 DREB sequence
    test_seq = (
        "GGATTGCCTTGATGAACAGGAAGAAGAAAGTGCGCAGGAGAAGCACTGGTCCTGATTCGG"
        "TTGCTGAAACCATCAAGAAGTGGAAGGAGGAAAACCAGAAGCTCCAGCAAGAGAATGGAT"
        "CCCGGAAAGCACCGGCCAAGGGTTCCAAGAAAGGGTGCATGGCAGGGAAAGGAGGTCCAG"
        "AGAATTCAAAATCCGTTTACCTCGGTGTGAGGCAGAGGACGTGGGGGAAATGGGTTGCTG"
        "ATATCCGAGAGCCCAACCGTGGCAACCGGCTGTGTCTTGGTTCATTCCCTACCGCAGTCG"
        "AACCTGCACGTGCATATGATGATGCGGCAAGGGCAATGTATGGCGCCAAAGCACGTGTCA"
        "ACTTCTCAGAGCAGTCCCCGGATGCCAACTCTGGTTGCACGCTGGCACCTCCATTGCTGA"
        "TGTCTAATGGGGCAACCGCTGCATCACATCCTTCTGATGGGAAGGAT"
    )

    generate_cgr_html(
        sequence    = test_seq,
        accession   = 'MZ935738.1',
        title       = 'DREB drought tolerance',
        output_file = 'cgr_test.html'
    )

    comp = compute_nucleotide_composition(test_seq)
    print(f'Composition: {comp}')
    print(f'Points: {len(compute_cgr_points(test_seq))}')
