from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except Exception:  # noqa: BLE001
    REPORTLAB_AVAILABLE = False

from app.config import settings

logger = logging.getLogger(__name__)


class LatexBuilder:
    @staticmethod
    def _escape_latex(text: str) -> str:
        replacements = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        pattern = re.compile("|".join(re.escape(k) for k in replacements))
        return pattern.sub(lambda m: replacements[m.group(0)], text)

    def _paragraphs(self, text: str) -> str:
        clean = self._escape_latex(text.strip())
        parts = [p.strip() for p in clean.split("\n\n") if p.strip()]
        return "\n\n".join(parts)

    def build_tex(self, report: dict[str, Any], tex_path: Path) -> None:
        refs = "\n".join(f"\\item {self._escape_latex(ref)}" for ref in report.get("references", []))
        keywords = ", ".join(self._escape_latex(k) for k in report.get("keywords", [])) or "plant genetics, bioinformatics"
        summary_rows = report.get("summary_table", [])
        table_rows = "\n".join(
            f"{self._escape_latex(row[0])} & {self._escape_latex(row[1])} \\\\"
            for row in summary_rows[1:]
            if len(row) == 2
        )

        figures = "\n".join(
            f"""
\\begin{{figure}}[h]
\\centering
\\includegraphics[width=0.85\\linewidth]{{{Path(path).as_posix()}}}
\\caption{{DNA analysis figure}}
\\end{{figure}}
""".strip()
            for path in report.get("figure_paths", [])
        )
        methods_subsections = self._latex_subsections(report.get("methods_subsections", []))
        results_subsections = self._latex_subsections(report.get("results_subsections", []))
        discussion_subsections = self._latex_subsections(report.get("discussion_subsections", []))
        short_title = self._escape_latex(report.get("title", "Research Article"))[:70]
        tex = f"""
\\documentclass[12pt]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{graphicx}}
\\usepackage{{booktabs}}
\\usepackage{{setspace}}
\\usepackage{{microtype}}
\\usepackage{{hyperref}}
\\usepackage{{xcolor}}
\\usepackage{{fancyhdr}}
\\usepackage{{lastpage}}
\\usepackage{{titlesec}}
\\hypersetup{{colorlinks=true, linkcolor=black, urlcolor=blue, citecolor=black}}
\\onehalfspacing
\\setcounter{{secnumdepth}}{{2}}
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\lhead{{{short_title}}}
\\rhead{{\\today}}
\\cfoot{{Page \\thepage\\ of \\pageref{{LastPage}}}}
\\titleformat{{\\section}}{{\\large\\bfseries}}{{\\thesection.}}{{0.5em}}{{}}
\\titleformat{{\\subsection}}{{\\normalsize\\bfseries}}{{\\thesubsection}}{{0.5em}}{{}}
\\title{{\\textbf{{{self._escape_latex(report["title"])}}}}}
\\author{{AI Research Assistant}}
\\date{{\\today}}
\\begin{{document}}
\\maketitle
\\begin{{abstract}}
{self._paragraphs(report["abstract"])}
\\end{{abstract}}
\\noindent\\textbf{{Keywords:}} {keywords}

\\section*{{Research Summary}}
\\begin{{table}}[h]
\\centering
\\begin{{tabular}}{{ll}}
\\toprule
Metric & Value \\\\
\\midrule
{table_rows}
\\bottomrule
\\end{{tabular}}
\\end{{table}}

\\section{{Introduction}}
{self._paragraphs(report["introduction"])}
\\section{{Methods}}
{self._paragraphs(report["methods"])}
{methods_subsections}
\\section{{Results}}
{self._paragraphs(report["results"])}
{results_subsections}
{figures}
\\section{{Discussion}}
{self._paragraphs(report["discussion"])}
{discussion_subsections}
\\section{{Conclusion}}
{self._paragraphs(report["conclusion"])}
\\section*{{References}}
\\begin{{enumerate}}
{refs}
\\end{{enumerate}}
\\end{{document}}
""".strip()
        tex_path.write_text(tex, encoding="utf-8")

    def _latex_subsections(self, subsections: list[dict[str, str]]) -> str:
        blocks: list[str] = []
        for item in subsections:
            title = self._escape_latex(str(item.get("title", "")).strip())
            text = self._paragraphs(str(item.get("text", "")).strip())
            if title and text:
                blocks.append(f"\\subsection{{{title}}}\n{text}")
        return "\n".join(blocks)

    def compile_pdf(
        self, tex_path: Path, output_dir: Path, report: dict[str, Any] | None = None
    ) -> tuple[Path, dict[str, Any]]:
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [settings.latex_engine, "-interaction=nonstopmode", "-output-directory", str(output_dir), str(tex_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            return (
                output_dir / f"{tex_path.stem}.pdf",
                {
                    "available": True,
                    "used_fallback": False,
                    "engine": settings.latex_engine,
                    "message": "PDF generated with LaTeX engine.",
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("LaTeX compilation failed, generating fallback PDF: %s", exc)
            fallback = output_dir / f"{tex_path.stem}.pdf"
            self._write_fallback_pdf(tex_path, fallback, report)
            message = (
                "pdflatex is not installed or is unavailable on this machine. "
                "A downloadable PDF was generated with the built-in ReportLab fallback."
            )
            return (
                fallback,
                {
                    "available": False,
                    "used_fallback": True,
                    "engine": settings.latex_engine,
                    "message": message,
                },
            )

    def _write_fallback_pdf(self, tex_path: Path, output_path: Path, report: dict[str, Any] | None = None) -> None:
        if not REPORTLAB_AVAILABLE:
            self._write_minimal_pdf(output_path, report)
            return

        if report is None:
            report = {
                "title": tex_path.stem.replace("_", " ").title(),
                "abstract": tex_path.read_text(encoding="utf-8")[:1500],
                "introduction": "No structured report available.",
                "methods": "No structured report available.",
                "results": "No structured report available.",
                "discussion": "No structured report available.",
                "conclusion": "No structured report available.",
                "references": [],
                "summary_table": [],
                "figure_paths": [],
                "keywords": [],
            }

        doc = SimpleDocTemplate(str(output_path), pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading2"], spaceBefore=8, spaceAfter=6))
        styles.add(ParagraphStyle(name="SubSectionTitle", parent=styles["Heading3"], spaceBefore=6, spaceAfter=4))
        story = []

        story.append(Paragraph(report.get("title", "Research Report"), styles["Title"]))
        story.append(Spacer(1, 0.2 * inch))
        keywords = ", ".join(report.get("keywords", []))
        if keywords:
            story.append(Paragraph(f"<b>Keywords:</b> {keywords}", styles["Normal"]))
            story.append(Spacer(1, 0.15 * inch))

        sections = [
            ("Abstract", report.get("abstract", "")),
            ("Introduction", report.get("introduction", "")),
            ("Methods", report.get("methods", "")),
            ("Results", report.get("results", "")),
            ("Discussion", report.get("discussion", "")),
            ("Conclusion", report.get("conclusion", "")),
        ]
        subsection_map = {
            "Methods": report.get("methods_subsections", []),
            "Results": report.get("results_subsections", []),
            "Discussion": report.get("discussion_subsections", []),
        }

        summary = report.get("summary_table", [])
        if summary and len(summary) > 1:
            story.append(Paragraph("Research Summary", styles["Heading2"]))
            table = Table(summary, colWidths=[2.6 * inch, 2.8 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.2 * inch))

        for heading, body in sections:
            story.append(Paragraph(heading, styles["SectionTitle"]))
            story.append(Paragraph(body or "N/A", styles["BodyText"]))
            story.append(Spacer(1, 0.12 * inch))
            for idx, subsection in enumerate(subsection_map.get(heading, []), start=1):
                subtitle = subsection.get("title", "").strip()
                subtext = subsection.get("text", "").strip() or "N/A"
                if subtitle:
                    story.append(Paragraph(f"{heading}.{idx} {subtitle}", styles["SubSectionTitle"]))
                    story.append(Paragraph(subtext, styles["BodyText"]))
                    story.append(Spacer(1, 0.1 * inch))

        for fig_path in report.get("figure_paths", []):
            fp = Path(fig_path)
            if fp.exists():
                story.append(Paragraph("DNA Analysis Figure", styles["Heading3"]))
                story.append(Image(str(fp), width=5.8 * inch, height=2.4 * inch))
                story.append(Spacer(1, 0.15 * inch))

        refs = report.get("references", [])
        story.append(Paragraph("References", styles["SectionTitle"]))
        if refs:
            for idx, ref in enumerate(refs, start=1):
                story.append(Paragraph(f"{idx}. {ref}", styles["BodyText"]))
        else:
            story.append(Paragraph("No references available.", styles["BodyText"]))

        doc.build(
            story,
            onFirstPage=self._draw_page_decor(report.get("title", "Research Report")),
            onLaterPages=self._draw_page_decor(report.get("title", "Research Report")),
        )

    def _write_minimal_pdf(self, output_path: Path, report: dict[str, Any] | None = None) -> None:
        title = "Research Report"
        if report and report.get("title"):
            title = str(report["title"])
        text = f"Fallback PDF generated.\n\nTitle: {title}\n\nInstall reportlab for rich fallback rendering."
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 760 Td ({escaped}) Tj ET".encode("latin-1", errors="replace")

        objects: list[bytes] = []
        objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
        objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
        objects.append(b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n")
        objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
        objects.append(f"5 0 obj << /Length {len(stream)} >> stream\n".encode("ascii") + stream + b"\nendstream endobj\n")

        header = b"%PDF-1.4\n"
        offsets = [0]
        body = b""
        cursor = len(header)
        for obj in objects:
            offsets.append(cursor)
            body += obj
            cursor += len(obj)
        xref_start = cursor
        xref = [b"xref\n0 6\n", b"0000000000 65535 f \n"]
        for off in offsets[1:]:
            xref.append(f"{off:010d} 00000 n \n".encode("ascii"))
        trailer = b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref_start).encode("ascii") + b"\n%%EOF\n"
        output_path.write_bytes(header + body + b"".join(xref) + trailer)

    def _draw_page_decor(self, title: str):
        short_title = title[:70]

        def _draw(canvas, doc):  # noqa: ANN001
            canvas.saveState()
            canvas.setFont("Helvetica", 9)
            canvas.setFillColor(colors.grey)
            canvas.drawString(doc.leftMargin, letter[1] - 0.55 * inch, short_title)
            canvas.drawRightString(letter[0] - doc.rightMargin, letter[1] - 0.55 * inch, "AI Research Assistant")
            canvas.drawCentredString(letter[0] / 2, 0.5 * inch, f"Page {canvas.getPageNumber()}")
            canvas.restoreState()

        return _draw
