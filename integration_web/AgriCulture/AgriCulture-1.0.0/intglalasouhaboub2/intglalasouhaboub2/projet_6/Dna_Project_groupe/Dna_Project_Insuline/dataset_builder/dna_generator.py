"""DNA generator for plant host-specific codon optimization."""

import hashlib
from dataclasses import dataclass

from src.codon_analysis import optimize_codons


@dataclass(frozen=True)
class DnaOptimizationResult:
    dna_sequence: str
    plant_host: str


class DnaGenerator:
    def __init__(
        self,
        random_seed: int = 42,
        min_relative_frequency: float = 0.62,
        frequency_exponent: float = 1.8,
        exploration_rate: float = 0.05,
    ) -> None:
        self.random_seed = int(random_seed)
        self.min_relative_frequency = float(min_relative_frequency)
        self.frequency_exponent = float(frequency_exponent)
        self.exploration_rate = float(exploration_rate)

    def _seed_for_pair(self, protein_sequence: str, plant_host: str) -> int:
        payload = f"{self.random_seed}|{plant_host}|{protein_sequence.upper()}"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        # Use 64 bits for a stable per-input seed accepted by random.Random.
        return int(digest[:16], 16)

    def generate(self, protein_sequence: str, plant_host: str) -> DnaOptimizationResult:
        sequence_seed = self._seed_for_pair(protein_sequence, plant_host)
        dna_sequence = optimize_codons(
            protein_sequence,
            plant_host,
            random_state=sequence_seed,
            min_relative_frequency=self.min_relative_frequency,
            frequency_exponent=self.frequency_exponent,
            exploration_rate=self.exploration_rate,
        )
        return DnaOptimizationResult(dna_sequence=dna_sequence, plant_host=plant_host)
