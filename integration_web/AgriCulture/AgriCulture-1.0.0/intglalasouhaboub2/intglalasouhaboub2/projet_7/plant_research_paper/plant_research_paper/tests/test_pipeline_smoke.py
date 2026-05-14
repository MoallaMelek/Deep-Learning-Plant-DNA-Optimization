from __future__ import annotations

from pathlib import Path

from app.pipeline.research_pipeline import ResearchPipeline


def test_pipeline_smoke(tmp_path: Path) -> None:
    pipeline = ResearchPipeline(output_root=tmp_path)
    out = pipeline.run("Drought resistance genes in maize", "ATGCGTACGTAGCTAGCTAGCTAG")
    assert Path(out["pdf_path"]).exists()
    assert Path(out["json_path"]).exists()
    assert Path(out["tex_path"]).exists()

