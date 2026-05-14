# Dependency Audit

## Mobile

The Flutter app depends on Riverpod, GoRouter, Dio/HTTP, image/audio capture, text-to-speech, charts and animation packages. Locked dependency versions are stored in `pubspec.lock`.

## Backend

The unified backend uses FastAPI with a scientific Python stack:

| Category | Libraries |
| --- | --- |
| API | `fastapi`, `uvicorn`, `starlette`, `python-multipart`, `jinja2` |
| Data science | `numpy`, `pandas`, `scikit-learn`, `scipy`, `joblib`, `openpyxl` |
| Deep learning | `tensorflow`, `keras`, `torch`, `torchvision`, `timm`, `librosa` |
| Vision/audio | `Pillow`, `opencv-python`, `soundfile`, `imageio` |
| RAG/LLM | `langchain`, `langchain-groq`, `faiss-cpu`, `chromadb`, `transformers` |
| Simulation | `simpy`, `pcse` |
| Utilities | `python-dotenv`, `PyYAML`, `rich`, `requests`, `httpx`, `aiohttp` |

## Web

The research dashboard uses React 19, Vite, TypeScript, Tailwind CSS, Axios, Chart.js, Framer Motion, Lucide React and Three.js.

## Notes

Large ML files and generated runtime databases are intentionally ignored by Git. Recreate or download them into `MODEL_ARTIFACT_DIR` before running full inference.
