"""Example entrypoint for the automated dataset pipeline."""

import argparse
from dataclasses import replace
from typing import Any, Dict, Optional

from dataset_builder import DatasetBuilder, PipelineConfig, TrainingConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automated protein dataset builder (proxy expression pipeline).")
    parser.add_argument("--keyword", default=None, help="UniProt keyword query.")
    parser.add_argument("--protein-limit", type=int, default=None, help="Number of proteins to fetch.")
    parser.add_argument("--output-dir", default=None, help="Directory to save outputs.")
    parser.add_argument("--random-seed", type=int, default=None, help="Seed for deterministic codon optimization.")
    parser.add_argument("--train", dest="train", action="store_true", help="Enable model training.")
    parser.add_argument("--no-train", dest="train", action="store_false", help="Disable model training.")
    parser.add_argument(
        "--structure-fetch",
        dest="structure_fetch",
        action="store_true",
        help="Enable AlphaFold structure lookup.",
    )
    parser.add_argument(
        "--no-structure-fetch",
        dest="structure_fetch",
        action="store_false",
        help="Disable AlphaFold structure lookup and keep deterministic fallback IDs.",
    )
    parser.set_defaults(train=None)
    parser.set_defaults(structure_fetch=None)
    return parser


def run_pipeline(
    keyword: Optional[str] = None,
    protein_limit: Optional[int] = None,
    output_dir: Optional[str] = None,
    random_seed: Optional[int] = None,
    train: Optional[bool] = None,
    structure_fetch: Optional[bool] = None,
) -> Dict[str, Any]:
    """Run the backend pipeline without argparse for programmatic callers."""
    pipeline_config = PipelineConfig()
    training_config = TrainingConfig()

    if output_dir:
        pipeline_config = replace(pipeline_config, output_dir=output_dir)

    if random_seed is not None:
        pipeline_config = replace(pipeline_config, random_seed=int(random_seed))

    if structure_fetch is not None:
        pipeline_config = replace(pipeline_config, alphafold_enabled=structure_fetch)

    if train is not None:
        training_config = replace(training_config, enabled=train)

    builder = DatasetBuilder(pipeline_config=pipeline_config, training_config=training_config)

    final_keyword = (keyword or pipeline_config.default_keyword).strip()
    final_protein_limit = (
        pipeline_config.default_protein_limit
        if protein_limit is None
        else int(protein_limit)
    )
    if final_protein_limit <= 0:
        raise ValueError("protein_limit must be greater than zero")

    return builder.build(keyword=final_keyword, protein_limit=final_protein_limit)


def run() -> None:
    args = build_parser().parse_args()
    result = run_pipeline(
        keyword=args.keyword,
        protein_limit=args.protein_limit,
        output_dir=args.output_dir,
        random_seed=args.random_seed,
        train=args.train,
        structure_fetch=args.structure_fetch,
    )
    print(f"Rows: {result['rows']}")
    print(f"CSV: {result['csv']}")
    print(f"JSON: {result['json']}")
    print(f"Metadata: {result['metadata']}")
    print(f"Quality report: {result['quality']}")
    if result.get("manifest"):
        print(f"Manifest: {result['manifest']}")
    if result.get("metrics"):
        print(f"Metrics: {result['metrics']}")


if __name__ == "__main__":
    run()
