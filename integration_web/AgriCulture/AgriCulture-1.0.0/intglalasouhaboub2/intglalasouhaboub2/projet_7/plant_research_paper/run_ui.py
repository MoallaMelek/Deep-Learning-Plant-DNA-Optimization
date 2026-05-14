from __future__ import annotations

from app.ui.gradio_app import create_demo


if __name__ == "__main__":
    demo = create_demo()
    demo.launch(server_name="127.0.0.1", server_port=7860)

