from __future__ import annotations

from pathlib import Path

import gradio as gr
import requests

from app.pipeline.research_pipeline import ResearchPipeline


class GradioFrontend:
    def __init__(self, api_url: str = "http://127.0.0.1:8000/generate") -> None:
        self.api_url = api_url
        self.local_pipeline = ResearchPipeline()

    def generate(self, topic: str, dna_sequence: str) -> tuple[str, str, str, str]:
        payload = {"topic": topic, "dna_sequence": dna_sequence or None, "max_revision_rounds": 2}
        try:
            response = requests.post(self.api_url, json=payload, timeout=240)
            response.raise_for_status()
            data = response.json()
        except Exception:
            data = self.local_pipeline.run(topic=topic, dna_sequence=dna_sequence or None)

        summary = (
            f"Paper generated for topic: {topic}\n"
            f"PDF: {data['pdf_path']}\n"
            f"JSON: {data['json_path']}\n"
            f"Figures: {', '.join(data['figure_paths']) if data['figure_paths'] else 'None'}"
        )
        first_figure = data["figure_paths"][0] if data.get("figure_paths") else None
        return summary, data["pdf_path"], data["json_path"], first_figure

    def build(self) -> gr.Blocks:
        with gr.Blocks(title="Plant DNA Research Assistant") as demo:
            gr.Markdown("# Plant DNA Research Paper Generator")
            topic = gr.Textbox(label="Research Topic", placeholder="Drought resistance genes in maize")
            dna = gr.Textbox(label="Optional DNA Sequence", lines=4, placeholder="ATGCGTACGTAGCTAGCTAGCTAG")
            run_btn = gr.Button("Generate Paper")
            summary = gr.Textbox(label="Run Summary", lines=6)
            pdf_file = gr.File(label="Download PDF")
            json_file = gr.File(label="Download JSON Report")
            first_figure = gr.Image(label="DNA Figure Preview", type="filepath")

            run_btn.click(
                fn=self.generate,
                inputs=[topic, dna],
                outputs=[summary, pdf_file, json_file, first_figure],
            )
        return demo


def create_demo() -> gr.Blocks:
    return GradioFrontend().build()
