import unittest

from src.codon_analysis import count_rare_codons


class CodonAnalysisTests(unittest.TestCase):
    def test_rare_codon_count_ignores_incomplete_and_invalid_codons(self) -> None:
        result = count_rare_codons("ATGNNNTA", "Arabidopsis thaliana", threshold=10.0)

        self.assertEqual(result["total_codons"], 2)
        self.assertEqual(result["invalid_codon_count"], 1)
        self.assertEqual(result["incomplete_codon_count"], 1)
        self.assertEqual(result["rare_codon_count"], 0)


if __name__ == "__main__":
    unittest.main()
