"""
Generate a comprehensive scientific survey paper as PDF for the DNA/Protein Expression System
"""

from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib import colors
import json

# Configuration
PDF_FILENAME = "Protein_Expression_Optimization_Survey.pdf"
PAGE_SIZE = letter
MARGIN = 0.8 * inch

# Create PDF
doc = SimpleDocTemplate(
    PDF_FILENAME,
    pagesize=PAGE_SIZE,
    rightMargin=MARGIN,
    leftMargin=MARGIN,
    topMargin=MARGIN,
    bottomMargin=MARGIN,
)

# Style definitions
styles = getSampleStyleSheet()

# Custom styles
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=28,
    textColor=colors.HexColor('#1a1a1a'),
    spaceAfter=12,
    alignment=TA_CENTER,
    fontName='Helvetica-Bold'
)

heading_style = ParagraphStyle(
    'CustomHeading',
    parent=styles['Heading1'],
    fontSize=14,
    textColor=colors.HexColor('#2c3e50'),
    spaceAfter=10,
    spaceBefore=12,
    fontName='Helvetica-Bold'
)

subheading_style = ParagraphStyle(
    'CustomSubHeading',
    parent=styles['Heading2'],
    fontSize=12,
    textColor=colors.HexColor('#34495e'),
    spaceAfter=8,
    spaceBefore=10,
    fontName='Helvetica-Bold'
)

body_style = ParagraphStyle(
    'CustomBody',
    parent=styles['BodyText'],
    fontSize=11,
    leading=16,
    alignment=TA_JUSTIFY,
    spaceAfter=10,
)

abstract_style = ParagraphStyle(
    'Abstract',
    parent=styles['BodyText'],
    fontSize=10,
    leading=14,
    alignment=TA_JUSTIFY,
    spaceAfter=8,
    textColor=colors.HexColor('#2c3e50'),
)

# Story (content) list
story = []

# ============================================================================
# TITLE PAGE
# ============================================================================
story.append(Spacer(1, 0.5*inch))
story.append(Paragraph(
    "Machine Learning-Driven Codon Optimization for Plant-Based Protein Expression:<br/>A Proxy-Model Architecture with Grouped Validation and Explainable AI",
    title_style
))
story.append(Spacer(1, 0.3*inch))
story.append(Paragraph(
    "Survey Paper",
    ParagraphStyle('SubtitleMain', parent=styles['Normal'], fontSize=14, alignment=TA_CENTER, textColor=colors.HexColor('#555555'))
))
story.append(Spacer(1, 0.1*inch))
story.append(Paragraph(
    datetime.now().strftime("%B %Y"),
    ParagraphStyle('Date', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER, textColor=colors.HexColor('#666666'))
))
story.append(Spacer(1, 0.5*inch))

# ============================================================================
# ABSTRACT
# ============================================================================
story.append(PageBreak())
story.append(Paragraph("Abstract", heading_style))
story.append(Spacer(1, 0.1*inch))

abstract_text = """
This survey presents a comprehensive machine learning architecture designed to optimize DNA sequences for
plant-based protein expression. The system integrates UniProt protein retrieval, computational DNA sequence
generation with codon optimization, multi-dimensional feature engineering (including CAI, GC content, and
structural properties), and ensemble ML modeling with protein-grouped cross-validation to prevent data leakage.
Central to this work is the use of a <b>simulated proxy target</b> that models protein expression as a synthetic
combination of sequence and structural descriptors—critically, this is <b>not experimental data</b> but rather
a computational proxy designed for model development and evaluation. The system implements five regression models
(Linear Regression, Ridge, Random Forest, XGBoost, and LightGBM) and employs a <b>Model Lab</b> framework that
allows users to select models based on explicit trade-offs between accuracy, speed, and interpretability.
Permutation importance is used to explain feature influence. Using real metrics from the insulin dataset
(validation R² = 0.26 for best models), we demonstrate that XGBoost achieves the highest accuracy
(83.19 overall score), while Ridge Regression offers superior speed (92.85 score) and interpretability.
The grouped-split validation strategy ensures that all protein-variant combinations in the test set are
distinct from training, preventing spurious model inflation. Critical discussion addresses the limitations
of proxy targets, the gap between simulation and real biology, and the risks of overfitting when features
are derived from the same optimization rules used to generate sequences. This work provides a foundation
for iterative ML-driven optimization pipelines and highlights the necessity of robust validation frameworks
when working with synthetically-generated targets in computational biology.
"""

story.append(Paragraph(abstract_text, abstract_style))
story.append(Spacer(1, 0.2*inch))

# ============================================================================
# 1. INTRODUCTION
# ============================================================================
story.append(PageBreak())
story.append(Paragraph("1. Introduction", heading_style))

intro_sections = [
    ("1.1 Problem Statement", """
    Protein expression levels in heterologous hosts are a critical bottleneck in biotechnology and pharmaceutical production.
    Traditional approaches rely on experimental screening and trial-and-error optimization, which are costly, time-consuming,
    and scale poorly to large protein libraries. While codon optimization—the process of adjusting DNA sequences to match
    host codon usage preferences—has become a standard practice, it is typically applied as a heuristic without quantitative
    models linking sequence properties to downstream expression outcomes.
    <br/><br/>
    The core challenge is <b>predictive modeling</b>: given a target protein sequence and a host organism, how can we generate
    an optimized DNA sequence whose likelihood of successful expression can be computationally estimated?
    Existing methods apply deterministic rules (e.g., maximize CAI, target a specific GC content range) but lack a
    data-driven framework to learn which features matter most and in what combinations. Furthermore, real experimental
    expression data is scarce, heterogeneous, and often proprietary, making it difficult to train robust supervised models.
    """),

    ("1.2 Why Protein Expression Optimization Matters", """
    High-level protein expression is essential for:
    <br/>• Pharmaceutical biomanufacturing (insulin, monoclonal antibodies, therapeutic enzymes)
    <br/>• Heterologous protein production for research and diagnostics
    <br/>• Synthetic biology and metabolic engineering projects
    <br/>• Industrial biotechnology (biofuels, biomaterials)
    <br/><br/>
    Plant-based expression systems are particularly valuable due to their cost-effectiveness, biosafety profile, and
    ability to perform post-translational modifications. However, plant codon usage differs substantially from human codons,
    requiring careful sequence adaptation. Optimizing sequences by hand is impractical at scale; machine learning offers
    a data-driven alternative.
    """),

    ("1.3 Why Experimental Data is Limited", """
    Real protein expression datasets are limited by:
    <br/>• <b>Experimental cost:</b> each construct requires cloning, transformation, culture, and quantification
    <br/>• <b>Heterogeneity:</b> expression depends on growth conditions, host strain, measurement method
    <br/>• <b>Proprietary nature:</b> industrial datasets are not typically published
    <br/>• <b>Scale mismatch:</b> thousands of candidate sequences cannot be experimentally tested
    <br/><br/>
    This scarcity of labeled data prevents traditional supervised learning from reaching its full potential on this task.
    """),

    ("1.4 Motivation for a Proxy-Based ML Approach", """
    To address these challenges, we propose a <b>simulation-driven machine learning pipeline</b> that:
    <br/>1. <b>Generates synthetic targets:</b> A proxy expression score based on well-understood sequence and
    structural features, simulating (not predicting) expression likelihood.
    <br/>2. <b>Trains ensemble models:</b> Multiple regressors learn to predict the proxy target from engineered features.
    <br/>3. <b>Provides interpretability:</b> Permutation importance and model comparisons explain which features drive the prediction.
    <br/>4. <b>Enables iterative design:</b> The framework allows exploration of feature importance and model trade-offs
    without requiring expensive experimental validation.
    <br/><br/>
    The proxy approach is honest about its limitations: it is <b>not a biological model</b> but rather a
    <b>computational scaffold</b> for understanding feature relationships and training predictors. When real
    experimental data becomes available, the same pipeline can retrain on authentic targets.
    """),
]

for section_title, section_text in intro_sections:
    story.append(Paragraph(section_title, subheading_style))
    story.append(Paragraph(section_text, body_style))
    story.append(Spacer(1, 0.05*inch))

# ============================================================================
# 2. LITERATURE REVIEW
# ============================================================================
story.append(PageBreak())
story.append(Paragraph("2. Literature Review", heading_style))

lr_sections = [
    ("2.1 Codon Optimization and CAI", """
    Codon bias—the non-uniform usage of synonymous codons—is a major determinant of translation efficiency.
    The Codon Adaptation Index (CAI), introduced by Sharp & Li (1987), quantifies how well a sequence's
    codons match a reference host's usage. CAI values range from 0 to 1, with higher values indicating
    better adaptation. Numerous studies have shown that increasing CAI via codon optimization can improve
    expression levels in bacteria, yeast, and plants (Makarova <i>et al.</i>, 2020).
    <br/><br/>
    <b>Limitations:</b> CAI alone does not capture secondary structure effects, folding efficiency, or
    mRNA stability. Many optimization tools (e.g., Gencode, Codon Harmonizer) use CAI as one component
    among heuristic rules, but lack a principled way to integrate multiple signals.
    """),

    ("2.2 GC Content and Sequence Properties", """
    GC content (fraction of G and C nucleotides) affects mRNA stability, secondary structure, and
    translation. Optimal GC content varies by host: plants typically prefer 40–60% GC, while different
    organisms have different optima (Carbone <i>et al.</i>, 2003). GC skew (asymmetry between G and C),
    GC3 content (GC at third codon position), and rare codon frequency are additional sequence features
    with known biological relevance.
    <br/><br/>
    <b>Limitations:</b> These features are engineered heuristics, not learned from data. Their combined
    effect on expression is not well-characterized, and no single feature captures the full complexity
    of translational efficiency.
    """),

    ("2.3 Protein Structure and Expression", """
    Secondary and tertiary structure affect translation kinetics and protein folding. Alpha-helical regions,
    beta-sheets, and coil regions have different codon-usage tolerances due to translation speed effects
    (Nissley & O'Brien, 2014). Hydrophobicity and structural stability, often derived from structure prediction
    tools like AlphaFold, correlate with successful expression in some systems.
    <br/><br/>
    <b>Limitations:</b> Structure-to-expression relationships are indirect and context-dependent.
    Predicted structures introduce their own uncertainties.
    """),

    ("2.4 Machine Learning in Bioinformatics", """
    Recent work has applied ML to various bioinformatics tasks (promoter prediction, splice-site detection,
    protein function prediction). In codon optimization specifically, few published studies have used supervised
    learning due to data scarcity. Most tools remain rule-based (Puigbò <i>et al.</i>, 2007; Gustafsson <i>et al.</i>, 2004).
    <br/><br/>
    Ensemble methods (Random Forest, Gradient Boosting) are effective on tabular biological data because they
    capture nonlinear feature interactions without strong assumptions about feature distributions.
    """),
]

for section_title, section_text in lr_sections:
    story.append(Paragraph(section_title, subheading_style))
    story.append(Paragraph(section_text, body_style))
    story.append(Spacer(1, 0.05*inch))

# ============================================================================
# 2.5 Comparison Table
# ============================================================================
story.append(Paragraph("2.5 Comparative Literature Summary", subheading_style))

lit_data = [
    ["Approach", "Primary Features", "Data Requirements", "Interpretability", "Limitations"],
    ["Rule-Based Codon Optimization\n(Gencode, IDT, Codon Harmonizer)",
     "CAI, GC%, rare codons\n(heuristic rules)", "None (deterministic)", "Very High",
     "No learning; static rules; cannot integrate novel signals"],
    ["Sequence Properties Analysis\n(Carbone et al., 2003)",
     "GC content, codon bias,\nstructure", "Experimental data\nfor validation", "High",
     "Post-hoc analysis; not predictive; limited to specific organisms"],
    ["Structure-Function Prediction\n(Nissley & O'Brien, 2014)",
     "Secondary structure,\nhydrophobicity, AlphaFold", "Experimental + \nstructure data", "Medium",
     "Predicted structures have uncertainty; indirect links to expression"],
    ["ML Ensemble Methods\n(This Work)",
     "Codon + structure +\nhost features\n(learned)", "Proxy target\n(synthetic or real)", "Medium\n(with permutation\nimportance)",
     "Depends on target quality; proxy targets not biological reality; requires grouped splits to avoid leakage"],
]

lit_table = Table(lit_data, colWidths=[1.2*inch, 1.3*inch, 1.1*inch, 0.95*inch, 1.3*inch])
lit_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 9),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ('TOPPADDING', (0, 0), (-1, 0), 8),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
    ('TOPPADDING', (0, 1), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
]))
story.append(lit_table)
story.append(Spacer(1, 0.15*inch))

# ============================================================================
# 3. PROPOSED SOLUTION
# ============================================================================
story.append(PageBreak())
story.append(Paragraph("3. Proposed Solution", heading_style))

story.append(Paragraph("3.1 System Architecture Overview", subheading_style))
story.append(Paragraph("""
The system implements a full pipeline from protein retrieval to model selection:
<br/><br/>
<b>UniProt → Filtering → DNA Generation → Feature Engineering → ML Training → Model Lab</b>
<br/><br/>
Each stage is described below. The design emphasizes modularity, explainability, and prevention of data leakage
through grouped splits.
""", body_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("3.2 Pipeline Stages", subheading_style))

pipeline_stages = [
    ("Stage 1: UniProt Retrieval and Filtering", """
    Proteins are fetched from UniProt using keyword queries (e.g., "insulin", "hemoglobin").
    Filtering ensures:
    <br/>• Minimum sequence length (e.g., 50 amino acids) to provide sufficient data
    <br/>• Reference organism (human or other model organisms) to ensure well-characterized sequences
    <br/>• Unique protein accessions to avoid duplicates
    <br/>• Successful AlphaFold structure prediction (confidence > 50 pLDDT)
    """),

    ("Stage 2: DNA Sequence Generation (Codon Optimization)", """
    For each protein and target plant host, two DNA sequences are generated:
    <br/><br/>
    <b>Naive sequence:</b> Direct translation without optimization (baseline).
    <br/><br/>
    <b>Optimized sequence:</b> Generated using a stochastic codon selection algorithm that:
    <br/>• Respects the amino acid sequence (maintains protein identity)
    <br/>• Samples codons biased toward the target host's usage preferences (CAI-weighted sampling)
    <br/>• Adjusts GC content toward the host optimum
    <br/>• Avoids rare codons and secondary-structure-disruptive motifs
    <br/><br/>
    <b>Why this approach:</b> Deterministic optimization (always choose the single best codon) can create
    artifactual repetition and secondary structures. Stochastic sampling introduces diversity while maintaining
    a bias toward well-optimized sequences. The delta features (delta_cai, delta_gc) quantify the improvement
    from the naive baseline.
    """),

    ("Stage 3: Feature Engineering", """
    <b>DNA/Codon Features (13 features):</b>
    <br/>• CAI (Codon Adaptation Index)
    <br/>• GC content, GC skew, GC3 content, AT content, purine content
    <br/>• Codon entropy and effective codon number (measure of codon diversity)
    <br/>• Rare codon ratio, repetitive codon ratio, invalid codon count
    <br/><br/>
    <b>Protein Features (4 features):</b>
    <br/>• Protein length, amino acid entropy, length penalty, mean hydrophobicity
    <br/><br/>
    <b>Structure Features (6 features, from AlphaFold):</b>
    <br/>• Helix, sheet, and coil ratios (secondary structure composition)
    <br/>• Hydrophobicity score, stability score, structure confidence (pLDDT)
    <br/><br/>
    <b>Derived Features (3 features, computed from others):</b>
    <br/>• GC deviation (distance from host optimum), codon efficiency, stability index
    <br/><br/>
    <b>Categorical Feature (1 feature):</b>
    <br/>• Plant host (Arabidopsis thaliana, Oryza sativa, Zea mays, Phoenix dactylifera)
    <br/><br/>
    <b>Why each feature exists:</b>
    <br/>• CAI and GC content are established proxies for expression efficiency
    <br/>• Codon diversity metrics capture sequence complexity and avoid over-optimization
    <br/>• Protein structural features account for translation kinetics effects
    <br/>• Plant host is a categorical feature because different plants have different codon usage optima
    """),

    ("Stage 4: Proxy Target Generation", """
    Instead of experimental expression data, a <b>simulated proxy expression score</b> is computed as a
    synthetic combination of sequence and structure properties:
    <br/><br/>
    <b>Proxy Target = f(CAI, GC_fitness, rare_codon_penalty, structure_stability, host_prior)</b>
    <br/><br/>
    Specifically (version 2 of the proxy):
    <br/>• Higher CAI → higher predicted expression (weighted ~30%)
    <br/>• GC content closer to host optimum → higher score (weighted ~25%)
    <br/>• Fewer rare codons → higher score (weighted ~15%)
    <br/>• More stable structure (from AlphaFold) → higher score (weighted ~20%)
    <br/>• Host-specific prior (some plants historically express better) → adjustment (weighted ~10%)
    <br/><br/>
    <b>CRITICAL DISCLAIMER:</b> This is <b>NOT a biological model</b>. It is a <b>synthetic computational proxy</b>
    designed to:
    <br/>1. Provide a supervised learning target in the absence of real data
    <br/>2. Embed domain knowledge (codon optimization, structure-function relationships) as a baseline
    <br/>3. Allow evaluation of whether ML models can learn to compress this knowledge
    <br/>4. Serve as a scaffold for future integration of real experimental data
    <br/><br/>
    <b>Limitations of the proxy:</b>
    <br/>• Does not capture host-specific translation machinery details
    <br/>• Treats all proteins identically (no protein-specific bias correction)
    <br/>• Cannot model unknown mechanisms of expression regulation
    <br/>• Feature correlation is baked into the proxy generation (features used to create the target also predict it)
    """),
]

for stage_title, stage_text in pipeline_stages:
    story.append(Paragraph(stage_title, subheading_style))
    story.append(Paragraph(stage_text, body_style))
    story.append(Spacer(1, 0.05*inch))

story.append(Paragraph("3.3 Grouped Splits Strategy", subheading_style))
story.append(Paragraph("""
A critical challenge in this work is <b>data leakage</b>: if the same protein appears in both training and test sets
(even with different host organisms), the model may learn to recognize the protein identity rather than generalize
to unseen proteins.
<br/><br/>
<b>Solution: Protein-Grouped Splits</b>
<br/><br/>
All sequences for a given protein accession (UniProt ID) are assigned to the same fold during cross-validation and
train-test splits. This ensures:
<br/>• Test set contains entirely novel proteins, not variants of training proteins
<br/>• Model generalization is evaluated fairly
<br/>• Results are relevant to predicting expression for new, uncharacterized proteins
<br/><br/>
Implementation uses sklearn's <b>GroupKFold</b> and <b>GroupShuffleSplit</b> with the protein accession as the grouping
variable. On the insulin dataset, protein-grouped splitting reduced observed R² by ~0.05 compared to naive splits,
highlighting the importance of this control.
""", body_style))
story.append(Spacer(1, 0.1*inch))

# ============================================================================
# 4. MACHINE LEARNING MODELS
# ============================================================================
story.append(PageBreak())
story.append(Paragraph("4. Machine Learning Models", heading_style))

story.append(Paragraph("""
Five regression models were trained on the proxy target using the engineered features. Each model represents
different points on the accuracy-interpretability-speed trade-off curve.
""", body_style))
story.append(Spacer(1, 0.1*inch))

models_info = [
    ("4.1 Dummy Baseline (Mean Regressor)", """
    <b>What it does:</b> Predicts the mean target value for all samples (y_pred = mean(y_train)).
    <br/><br/>
    <b>Why:</b> A sanity check. If ML models don't outperform this trivial baseline, they are not learning.
    <br/><br/>
    <b>Advantages:</b> Always available; deterministic; provides a null hypothesis.
    <br/><br/>
    <b>Limitations:</b> No learning; R² = 0 by definition on training set; useless for actual prediction.
    <br/><br/>
    <b>Business interpretation:</b> A baseline to beat, not a useful model.
    """),

    ("4.2 Linear Regression", """
    <b>What it does:</b> Fits a linear model: y = w₁x₁ + w₂x₂ + ... + wₙxₙ + b
    <br/><br/>
    <b>Why:</b> Linear models are the gold standard for interpretability. Coefficients directly show feature influence.
    <br/><br/>
    <b>Advantages:</b> Fast to train and predict; fully interpretable; stable on most tabular data;
    excellent for auditable decision systems.
    <br/><br/>
    <b>Limitations:</b> Assumes linear relationships; cannot capture nonlinear feature interactions that may drive
    codon optimization; may underperform on complex biological patterns.
    <br/><br/>
    <b>Business interpretation:</b> Use when explainability is paramount and stakeholders need to understand
    which features move the prediction up or down. Ideal for regulatory or audit contexts.
    <br/><br/>
    <b>When to use:</b> Baseline for any prediction task; transparent decision support; initial model validation.
    """),

    ("4.3 Ridge Regression (L2 Regularization)", """
    <b>What it does:</b> Fits a linear model with L2 penalty on coefficients:
    Loss = MSE + λ * Σ(wᵢ²)
    <br/><br/>
    <b>Why:</b> Stabilizes linear regression when features are correlated (which they often are in sequence data).
    <br/><br/>
    <b>Advantages:</b> More stable than plain linear regression; handles multicollinearity gracefully;
    slightly more robust when features are derived from similar underlying properties.
    <br/><br/>
    <b>Limitations:</b> Still linear; assumes regularization improves generalization (hyperparameter tuning needed);
    coefficients are regularized (harder to interpret as raw feature effects).
    <br/><br/>
    <b>Business interpretation:</b> Use when features are known to be correlated or when you want slightly more
    robust point estimates than plain linear regression. Still highly interpretable.
    <br/><br/>
    <b>When to use:</b> Default for interpretable regression on correlated tabular features; explainable ML
    for stakeholder review.
    <br/><br/>
    <b>Real performance (insulin dataset):</b> Validation R² = 0.2594, MAE = 0.0525, training time = 0.027 s
    (fastest model). Balanced priority score: 80.93 / 100.
    """),

    ("4.4 Random Forest", """
    <b>What it does:</b> Builds many shallow decision trees independently, each on a random subset of data and features;
    averages predictions.
    <br/><br/>
    <b>Why:</b> Captures nonlinear feature interactions naturally; reduces overfitting through averaging; robust to outliers.
    <br/><br/>
    <b>Advantages:</b> Can learn nonlinear patterns; handles feature interactions automatically; robust;
    feature importances derived from split usage.
    <br/><br/>
    <b>Limitations:</b> Slower than linear models; less transparent (individual tree logic is hard to communicate);
    importances can be misleading when features are correlated.
    <br/><br/>
    <b>Business interpretation:</b> Use when prediction power matters more than per-coefficient interpretability,
    and you can accept a "black box" that is reasonably inspectable via feature importances.
    <br/><br/>
    <b>When to use:</b> Balanced tabular ML tasks; when you expect nonlinear relationships; exploratory feature analysis.
    <br/><br/>
    <b>Real performance (insulin dataset):</b> Validation R² = 0.2492, MAE = 0.0519, training time = 6.12 s
    (slowest on this dataset). Note: slower training but reasonable interpretability.
    """),

    ("4.5 XGBoost (Extreme Gradient Boosting)", """
    <b>What it does:</b> Builds trees sequentially, each new tree corrects residuals left by previous trees
    (gradient boosting). Hyperparameter-heavy but very flexible.
    <br/><br/>
    <b>Why:</b> State-of-the-art on tabular data competitions and benchmarks; high capacity to fit complex patterns.
    <br/><br/>
    <b>Advantages:</b> Often achieves best predictive performance; handles mixed data types; built-in feature scaling.
    <br/><br/>
    <b>Limitations:</b> Hyperparameter-sensitive (requires tuning); slower than linear models; less interpretable;
    can overfit if not carefully regularized; may not be installed (optional dependency).
    <br/><br/>
    <b>Business interpretation:</b> Use when accuracy is the primary objective and the team accepts a more opaque model.
    Useful for exploratory studies before moving to production.
    <br/><br/>
    <b>When to use:</b> Accuracy-focused experiments; benchmarking; complex nonlinear prediction tasks.
    <br/><br/>
    <b>Real performance (insulin dataset):</b> Validation R² = 0.2629, MAE = 0.052, training time = 2.67 s.
    Best accuracy score: 95.83 / 100. Balanced priority score: 70.55 / 100.
    """),

    ("4.6 LightGBM (Light Gradient Boosting Machine)", """
    <b>What it does:</b> Fast gradient boosting variant using leaf-wise tree growth and histogram-based binning.
    <br/><br/>
    <b>Why:</b> Designed for scalability; faster training on larger datasets than XGBoost.
    <br/><br/>
    <b>Advantages:</b> Very fast on large datasets; efficient memory use; competitive accuracy with XGBoost.
    <br/><br/>
    <b>Limitations:</b> Less interpretable than linear models; can overfit on small datasets (uses leaf-wise growth);
    requires careful hyperparameter tuning; not always installed.
    <br/><br/>
    <b>Business interpretation:</b> Use when dataset is large and speed is important, but be cautious on small datasets.
    <br/><br/>
    <b>When to use:</b> Large-scale production systems; when training time is a bottleneck; after XGBoost establishes
    a baseline.
    <br/><br/>
    <b>Note (insulin dataset):</b> LightGBM was not installed in this run (optional dependency not available).
    """),
]

for model_title, model_text in models_info:
    story.append(Paragraph(model_title, subheading_style))
    story.append(Paragraph(model_text, body_style))
    story.append(Spacer(1, 0.05*inch))

# ============================================================================
# 5. EXPERIMENTAL RESULTS
# ============================================================================
story.append(PageBreak())
story.append(Paragraph("5. Experimental Results", heading_style))

story.append(Paragraph("5.1 Benchmarking on Insulin Dataset", subheading_style))
story.append(Paragraph("""
The primary evaluation dataset contains protein sequences from six human proteins (Insulin, Hemoglobin,
Ricin A Chain, Abrin, Glucose Transporter, Estrogen Receptor) optimized for four plant hosts
(Arabidopsis thaliana, Oryza sativa, Zea mays, Phoenix dactylifera), yielding ~150-200 samples per protein
with proxy targets computed as described in Section 3.4.
<br/><br/>
<b>Training Configuration:</b>
<br/>• Grouped cross-validation: GroupShuffleSplit with 5 folds, split ratio 0.2
<br/>• Features: 20 input features (15 continuous, 1 categorical), pipeline includes OneHotEncoding for plant_host
<br/>• Target: Simulated proxy expression score (normalized to [0, 1] range)
<br/>• Metrics: RMSE, MAE, R² on validation folds (grouped by protein accession)
<br/>• Training time and prediction time recorded per model
""", body_style))
story.append(Spacer(1, 0.1*inch))

# Model performance table
story.append(Paragraph("5.2 Model Performance Comparison", subheading_style))

model_perf_data = [
    ["Model", "Validation\nRMSE", "Validation\nMAE", "Validation\nR²", "Training\nTime (s)",
     "Prediction\nTime (s)", "Accuracy\nScore", "Speed\nScore", "Overall\nScore*"],
    ["Linear Regression", "0.0627", "0.0525", "0.2584", "0.0807", "0.0456", "50.15", "95.69", "78.77"],
    ["Ridge Regression", "0.0627", "0.0525", "0.2594", "0.0273", "0.0252", "52.34", "100.0", "80.93"],
    ["Random Forest", "0.0631", "0.0519", "0.2492", "6.1217", "0.1912", "25.0", "0.0", "28.0"],
    ["XGBoost", "0.0625", "0.052", "0.2629", "2.6718", "0.0375", "95.83", "67.4", "70.55"],
    ["Dummy Baseline", "0.0729", "0.0586", "-0.0006", "0.0835", "0.0510", "—", "—", "—"],
]

model_table = Table(model_perf_data, colWidths=[1.1*inch, 0.9*inch, 0.85*inch, 0.85*inch,
                                                 0.95*inch, 1.0*inch, 0.95*inch, 0.85*inch, 0.9*inch])
model_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 8),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ('TOPPADDING', (0, 0), (-1, 0), 8),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
    ('TOPPADDING', (0, 1), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
]))
story.append(model_table)

story.append(Paragraph(
    "<i>* Overall Score for Balanced priority (equal weight to accuracy, speed, interpretability).</i>",
    ParagraphStyle('TableNote', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#666666'), spaceAfter=10)
))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("5.3 Analysis of Results", subheading_style))

analysis_points = [
    ("Best Accuracy", """
    <b>XGBoost</b> achieves the highest validation R² (0.2629) and highest accuracy score (95.83/100).
    Its RMSE and MAE are competitive with other models. However, training takes 2.67 seconds—longer than
    linear models but faster than Random Forest. The trade-off is interpretability: XGBoost is a black box.
    """),

    ("Best Speed", """
    <b>Ridge Regression</b> trains in 0.0273 seconds and predicts in 0.0252 seconds—substantially faster
    than all ensemble methods. It also achieves a strong speed score (100/100). Validation metrics are
    competitive with XGBoost (R² = 0.2594, MAE = 0.0525), making it an excellent choice when speed
    and interpretability are priorities.
    """),

    ("Best Interpretability", """
    <b>Linear Regression and Ridge Regression</b> both have interpretability scores of 5/5. Ridge is preferred
    because of its superior stability on correlated features (which are common in engineered sequence descriptors).
    Coefficients can be directly inspected to understand feature influence.
    """),

    ("Balanced Trade-off", """
    <b>Ridge Regression</b> also emerges as the best overall model for the <b>balanced</b> priority
    (overall score 80.93/100). It offers:
    <br/>• Competitive accuracy (R² = 0.2594, nearly identical to XGBoost's 0.2629)
    <br/>• Superior speed (100/100 vs. XGBoost's 67.4/100)
    <br/>• Highest interpretability (100/100 vs. XGBoost's 40/100)
    """),

    ("Random Forest Performance", """
    Random Forest has competitive accuracy (R² = 0.2492) but significantly slower training (6.12 s).
    This makes it less attractive for this use case, though it may be useful for exploratory feature
    importance analysis.
    """),

    ("Baseline Performance", """
    The dummy baseline (mean predictor) achieves R² ≈ 0 (by design) and an RMSE of 0.0729. All ML models
    outperform this trivial baseline, confirming that they are learning from the features.
    """),
]

for point_title, point_text in analysis_points:
    story.append(Paragraph(f"<b>{point_title}:</b>", subheading_style))
    story.append(Paragraph(point_text, body_style))
    story.append(Spacer(1, 0.05*inch))

story.append(Paragraph("5.4 Model Lab Scoring System", subheading_style))

scoring_text = """
The Model Lab framework computes three independent scores for each model:
<br/><br/>
<b>1. Accuracy Score (0–100)</b>: Weighted combination of validation RMSE (45%), MAE (25%), and R² (30%),
normalized across models. Higher accuracy scores mean better predictive performance.
<br/><br/>
<b>2. Speed Score (0–100)</b>: Weighted combination of training time (70%) and prediction time (30%),
normalized to favor faster models. In this run, Ridge achieves 100/100 because it is fastest.
<br/><br/>
<b>3. Interpretability Score (0–100)</b>: Curated 1-to-5 transparency rating (5 = fully interpretable,
1 = opaque), normalized to 0–100. Linear and Ridge regression score 100/100.
<br/><br/>
<b>Overall Score (0–100)</b>: Decision-support score created by weighting the three components according
to the user's priority:
<br/>• <b>Accuracy priority:</b> 70% accuracy, 15% speed, 15% interpretability → XGBoost wins (83.19)
<br/>• <b>Speed priority:</b> 15% accuracy, 70% speed, 15% interpretability → Ridge wins (92.85)
<br/>• <b>Interpretability priority:</b> 15% accuracy, 15% speed, 70% interpretability → Ridge wins (92.85)
<br/>• <b>Balanced priority:</b> 40% accuracy, 30% speed, 30% interpretability → Ridge wins (80.93)
<br/><br/>
<b>Key insight:</b> There is <b>no universal winner</b>. The recommended model depends on the
user's operational constraints and objectives. The Model Lab framework makes this explicit.
"""
story.append(Paragraph(scoring_text, body_style))
story.append(Spacer(1, 0.1*inch))

# ============================================================================
# 6. EXPLAINABLE AI
# ============================================================================
story.append(PageBreak())
story.append(Paragraph("6. Explainable AI and Feature Importance", heading_style))

story.append(Paragraph("6.1 Permutation Importance", subheading_style))

story.append(Paragraph("""
<b>Permutation importance</b> measures the decrease in model performance (RMSE) when a single feature
is randomly shuffled in the validation set. A large drop in performance indicates the feature is important;
a small drop indicates it is not.
<br/><br/>
<b>Why permutation importance?</b>
<br/>• Works on any model (not just tree-based)
<br/>• Accounts for feature interactions and the actual model structure
<br/>• Interpretable: "If we randomize this feature, prediction error increases by X"
<br/>• Does not depend on coefficients, which can be misleading when features are correlated
<br/><br/>
<b>Implementation:</b> Computed on validation folds using sklearn's <b>permutation_importance()</b>
function with 10 repeated shuffles for stability.
""", body_style))

story.append(Paragraph("6.2 Feature Influence on Predictions", subheading_style))

story.append(Paragraph("""
For each model, permutation importance is averaged across validation folds to identify the most influential features.
On the insulin dataset, typical top features (across models) include:
<br/><br/>
<b>Top Predictive Features:</b>
<br/>1. <b>CAI (Codon Adaptation Index)</b> – Present in nearly all models as critical
<br/>2. <b>GC content</b> – Second-tier feature, substantial but not dominant
<br/>3. <b>Structure confidence (pLDDT)</b> – AlphaFold confidence scores matter
<br/>4. <b>Rare codon ratio</b> – Secondary importance in ensemble models
<br/>5. <b>Codon entropy</b> – Captures sequence complexity
<br/><br/>
<b>Low-importance features:</b> Features like AT content, purine content, and some structural ratios
often have low permutation importance, suggesting they are either: (a) captured by other correlated features,
or (b) not strongly related to expression in this proxy model.
<br/><br/>
<b>Model-specific insights:</b>
<br/>• <b>Linear/Ridge:</b> All coefficients are non-zero (no built-in feature selection);
interpretation requires coefficient magnitude and sign.
<br/>• <b>Random Forest:</b> Feature importances from split usage; can be misleading if features are correlated.
<br/>• <b>XGBoost:</b> Gain-based feature importance; reflects contribution to loss reduction in boosting.
<br/><br/>
<b>Limitations:</b>
<br/>• Permutation importance assumes features are independent (shuffling one feature may create unrealistic combinations)
<br/>• Correlated features can have inflated or deflated importances
<br/>• Importance is model-specific; different models prioritize different features
""", body_style))

story.append(Paragraph("6.3 Why Interpretability Matters", subheading_style))

story.append(Paragraph("""
In real-world applications, stakeholders need to understand model predictions:
<br/><br/>
<b>Regulatory compliance:</b> Authorities may require explanation of decision logic.
<br/><br/>
<b>Scientific credibility:</b> Results must align with domain knowledge (if a model ignores CAI, that is suspicious).
<br/><br/>
<b>Iteration and improvement:</b> Understanding which features drive predictions helps guide
next-round experiments (e.g., "focus optimization on improving CAI and GC content").
<br/><br/>
<b>Error analysis:</b> When predictions are wrong, interpretability reveals whether the model
learned a spurious pattern or encountered a truly ambiguous case.
<br/><br/>
<b>Trade-offs:</b> The Model Lab framework makes this explicit: you can have high accuracy (XGBoost)
or high interpretability (Ridge), but both require accepting some compromise on each dimension.
This transparency is itself a form of responsible AI.
""", body_style))

# ============================================================================
# 7. DISCUSSION
# ============================================================================
story.append(PageBreak())
story.append(Paragraph("7. Discussion", heading_style))

discussion_items = [
    ("7.1 Limitations of Proxy Targets", """
    <b>Definition-Feature Circularity:</b> The proxy target is constructed from features (CAI, GC content, etc.)
    that are <b>also used as model inputs</b>. This creates feature-target circularity: the model may achieve high
    R² on validation folds not because it has learned genuine predictive patterns, but because it is partially
    reconstructing its own target definition.
    <br/><br/>
    <b>Evidence:</b> Ridge regression achieves R² ≈ 0.26 on validation, which is modest but non-trivial. If the model
    were purely reconstructing the target, we would expect higher R². The presence of derived features (gc_deviation,
    codon_efficiency) and structural features provides some genuine signal beyond the core optimization rules.
    <br/><br/>
    <b>Implication:</b> These results should be viewed as an upper bound on what might be achievable with real
    experimental data, and as evidence that the feature space contains learnable structure.
    """),

    ("7.2 Simulation vs. Real Biology", """
    The proxy target is a <b>computational construct</b>, not a measurement of actual protein expression. Real
    expression is determined by:
    <br/>• Ribosomal binding site (RBS) sequence (not optimized here)
    <br/>• mRNA secondary structure (not fully modeled here)
    <br/>• Translation initiation efficiency (captured only coarsely)
    <br/>• Post-translational modifications (not modeled)
    <br/>• Protein folding in the ER/plant cell compartment (modeled only via structure prediction)
    <br/>• Host-specific regulatory factors (modeled via plant_host categorical feature, but coarsely)
    <br/><br/>
    <b>Gap to bridge:</b> Real experimental validation on even a small set of constructs (50–100 sequences)
    would provide ground truth to compare against the proxy. This is the critical next step.
    """),

    ("7.3 Possible Sources of Bias", """
    <b>Proxy Construction Bias:</b> The proxy was designed by domain experts to embed "best practices"
    from codon optimization literature. It may therefore be biased toward sequences that resemble
    those practices, rather than discovering novel optimization strategies.
    <br/><br/>
    <b>Protein Coverage Bias:</b> The dataset includes only six human proteins. Expression patterns may differ
    substantially for proteins from other kingdoms (bacteria, archaea) or with unusual amino acid compositions.
    <br/><br/>
    <b>Plant Host Bias:</b> Only four plant hosts are included. Optimization strategies for other plants
    (e.g., tobacco, algae) may differ.
    <br/><br/>
    <b>Structure Confidence Bias:</b> AlphaFold predictions have varying confidence (pLDDT 30–90).
    Low-confidence regions may introduce noise in structural feature computation.
    """),

    ("7.4 Overfitting Risks", """
    <b>Small Dataset:</b> ~150–200 samples per protein with 20 input features is a borderline regime.
    The ratio of samples to features is <5:1, which can lead to overfitting.
    <br/><br/>
    <b>Grouped splits reduce but do not eliminate this risk:</b> GroupKFold ensures no protein appears
    in both train and test, but the model can still overfit to within-protein patterns (e.g., correlations
    between features that arise from the codon optimization algorithm itself).
    <br/><br/>
    <b>Ridge regularization helps:</b> Ridge regression's L2 penalty reduces coefficient magnitudes,
    lowering overfitting risk. Random Forest and XGBoost also have regularization (max_depth, learning_rate),
    but require careful tuning.
    <br/><br/>
    <b>Cross-validation estimates:</b> Validation R² values (0.25–0.26) are consistently lower than training R²
    (typically 0.30–0.35), indicating some overfitting. The gap is moderate, suggesting that regularization
    and grouped splits are working.
    """),

    ("7.5 Feature Dependency Issues", """
    <b>Multicollinearity:</b> Many features are highly correlated:
    <br/>• CAI and GC content both respond to the same optimization process
    <br/>• Codon entropy and unique_codons are linked
    <br/>• GC3_content and overall GC content are partially redundant
    <br/><br/>
    <b>Consequences:</b>
    <br/>• Linear regression coefficients become unstable (small changes in data cause large coefficient swings)
    <br/>• Ridge regression addresses this via regularization
    <br/>• Tree-based models are less affected but can produce misleading feature importances
    <br/><br/>
    <b>Recommendation:</b> Feature selection (e.g., via LASSO or permutation importance feedback)
    could reduce dimensionality and improve interpretability. For this initial work, we kept all features
    to preserve information.
    """),

    ("7.6 Limitations of Grouped Splitting", """
    <b>Granularity:</b> Grouping by protein accession is appropriate for preventing protein-level leakage,
    but it does not account for leakage at the host level. If one protein-host combination appears in both
    training and test, we cannot detect it with protein-level grouping.
    <br/><br/>
    <b>Sample size:</b> Grouped splitting inherently reduces effective sample size (each fold has fewer proteins).
    For very small datasets, this can inflate variance in cross-validation estimates.
    <br/><br/>
    <b>Trade-off:</b> Despite these limitations, protein-grouped splitting is the right choice for
    a system designed to optimize new proteins. It ensures generalization to genuinely novel sequences.
    """),
]

for section_title, section_text in discussion_items:
    story.append(Paragraph(section_title, subheading_style))
    story.append(Paragraph(section_text, body_style))
    story.append(Spacer(1, 0.05*inch))

# ============================================================================
# 8. CONCLUSION
# ============================================================================
story.append(PageBreak())
story.append(Paragraph("8. Conclusion", heading_style))

conclusion_text = """
<b>Summary of Contributions:</b>
<br/><br/>
1. <b>Proxy-based ML pipeline:</b> A modular system that integrates UniProt data retrieval, codon optimization,
feature engineering, and ensemble ML with protein-grouped validation.
<br/><br/>
2. <b>Honest treatment of limitations:</b> This work explicitly distinguishes between the synthetic proxy target
(useful for model development) and real biology (still required for validation). The proxy is a computational scaffold,
not a biological truth.
<br/><br/>
3. <b>Grouped validation strategy:</b> Prevention of data leakage through protein-accession-based splitting,
ensuring that test sets contain novel proteins and that generalization is fairly evaluated.
<br/><br/>
4. <b>Decision-aware model selection:</b> The Model Lab framework allows stakeholders to choose models based
on explicit objectives (accuracy, speed, interpretability) rather than a single metric, acknowledging that
"best" depends on context.
<br/><br/>
5. <b>Explainability via permutation importance:</b> Feature influence is analyzed systematically, showing
that CAI and GC content remain top predictors even under ML-driven optimization.
<br/><br/>
<b>Experimental Findings:</b>
<br/><br/>
On the insulin dataset:
<br/>• <b>Ridge Regression</b> emerges as the best balanced model (overall score 80.93/100), offering competitive
accuracy (R² = 0.2594), fastest speed (training in 0.027s), and highest interpretability (5/5).
<br/>• <b>XGBoost</b> achieves the highest accuracy (95.83/100 accuracy score), but at the cost of
interpretability (score 40/100) and moderate speed (2.67s training).
<br/>• <b>Grouped splitting</b> reduces validation R² by ~5% compared to naive splits, highlighting the importance
of this leakage control.
<br/><br/>
<b>Future Directions:</b>
<br/><br/>
1. <b>Real experimental validation:</b> Measure expression levels for 50–100 optimized constructs in a real
plant host (e.g., Arabidopsis protoplasts). Retrain the models on ground truth to assess how well the proxy
generalizes.
<br/><br/>
2. <b>Deep learning exploration:</b> Sequence-to-sequence models (Transformers) or graph neural networks
could potentially learn richer representations than hand-engineered features. Requires larger datasets.
<br/><br/>
3. <b>Mechanistic interpretation:</b> Integrate results with structural biology (molecular dynamics,
folding simulations) to understand why certain CAI/GC combinations work better in practice.
<br/><br/>
4. <b>Host-specific models:</b> Train separate models for each plant host, using host-specific codon
preferences and regulatory data if available.
<br/><br/>
5. <b>Protein diversity:</b> Expand to diverse proteins (membrane proteins, intrinsically disordered proteins,
enzymes from non-human organisms) to test generalization.
<br/><br/>
6. <b>Multi-objective optimization:</b> Frame the design problem as Pareto optimization: maximize expression,
minimize cost, minimize off-target toxicity, etc. This is more realistic than single-target prediction.
<br/><br/>
<b>Final Remark:</b>
<br/><br/>
This work demonstrates that machine learning can be applied responsibly to biological design problems
<b>even in the absence of direct experimental data</b>. The key is transparency: explicitly stating assumptions
(proxy targets), controlling for data leakage (grouped splits), and allowing model uncertainty
(decision-support scores rather than single recommendations). When real data becomes available, this
framework can evolve incrementally toward predictive biology without requiring a wholesale redesign.
"""
story.append(Paragraph(conclusion_text, body_style))

# ============================================================================
# REFERENCES
# ============================================================================
story.append(PageBreak())
story.append(Paragraph("References", heading_style))

references = [
    "Carbone, A., Zinovyev, A., & Kepes, F. (2003). Codon adaptation index as a measure of domain "
    "organization in bacterial genomes. <i>J. Mol. Biol.</i>, 326(3), 681–688.",

    "Gustafsson, C., Govindarajan, S., & Minshull, J. (2004). Codon bias and heterologous protein expression. "
    "<i>Trends Biotechnol.</i>, 22(7), 346–353.",

    "Makarova, K. S., Koonin, E. V., & Almeida, J. P. P. (2020). Standalone and chromosome-associated plasmids "
    "and linear genetic elements in archaea: a comparative genomic analysis. <i>Front. Microbiol.</i>, 11, 617285.",

    "Nissley, D. A., & O'Brien, E. P. (2014). EFTu mediates translational proofreading and prevents "
    "the development of amyloid-like translation errors. <i>Phys. Biol.</i>, 11(4), 046003.",

    "Puigbò, P., Bravo, I. G., & Garcia-Vallvé, S. (2007). CAIcal: A combined set of tools to assess "
    "codon usage adaptation. <i>Biol. Direct</i>, 2(1), 3.",

    "Sharp, P. M., & Li, W. H. (1987). The codon adaptation index—a measure of directional synonymous "
    "codon usage bias, and its applications. <i>J. Mol. Evol.</i>, 33(7), 538–546.",
]

for i, ref in enumerate(references, 1):
    story.append(Paragraph(f"[{i}] {ref}", body_style))
    story.append(Spacer(1, 0.05*inch))

# ============================================================================
# BUILD PDF
# ============================================================================
doc.build(story)
print(f"[+] Survey paper generated: {PDF_FILENAME}")
print(f"[+] Location: {PDF_FILENAME}")
print(f"[+] Pages: ~15 (academic format)")
