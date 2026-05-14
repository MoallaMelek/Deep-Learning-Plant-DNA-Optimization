# Artifact Policy

The repository is prepared for GitHub and excludes large generated or binary ML assets.

Ignored artifact types include:

| Type | Examples |
| --- | --- |
| Model weights | `*.pth`, `*.pt`, `*.h5`, `*.keras`, `*.bin`, `*.safetensors` |
| Classical ML | `*.pkl`, `*.pickle`, `*.joblib` |
| Vector indexes | `*.index`, `*.faiss` |
| Raw genomic data | `*.fna`, `*.fasta`, `*.fastq` |
| Runtime stores | `*.db`, `*.sqlite`, `*.sqlite3` |
| Archives | `*.zip`, `*.tar.gz`, `*.7z` |

Recommended production pattern:

1. Store large artifacts in GitHub Releases, Hugging Face Hub, S3-compatible storage or institutional storage.
2. Download them during setup into `./artifacts` or a path defined by `MODEL_ARTIFACT_DIR`.
3. Keep lightweight source code, adapters, schemas and documentation in Git.
