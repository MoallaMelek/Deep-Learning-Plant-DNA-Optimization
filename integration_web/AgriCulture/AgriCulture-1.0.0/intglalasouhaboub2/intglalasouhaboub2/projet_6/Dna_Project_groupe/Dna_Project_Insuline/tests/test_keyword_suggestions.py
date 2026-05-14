import unittest

from app.internal.keyword_suggestions import get_all_keyword_suggestions, get_keyword_suggestions


class KeywordSuggestionTests(unittest.TestCase):
    def test_filters_by_keyword_prefix(self) -> None:
        suggestions = get_keyword_suggestions("kin")
        keywords = {item["keyword"] for item in suggestions}
        self.assertIn("kinase", keywords)

    def test_filters_by_description(self) -> None:
        suggestions = get_keyword_suggestions("oxygen")
        keywords = {item["keyword"] for item in suggestions}
        self.assertIn("hemoglobin", keywords)

    def test_returns_empty_for_unknown(self) -> None:
        suggestions = get_keyword_suggestions("definitely_not_real")
        self.assertEqual(suggestions, [])

    def test_glu_query_returns_google_like_suggestions(self) -> None:
        suggestions = get_keyword_suggestions("glu")
        keywords = [item["keyword"] for item in suggestions]

        self.assertIn("glucose", keywords)
        self.assertIn("glucagon", keywords)
        self.assertIn("glutathione", keywords)

    def test_re_query_returns_receptor(self) -> None:
        suggestions = get_keyword_suggestions("re")
        keywords = {item["keyword"] for item in suggestions}
        self.assertIn("receptor", keywords)

    def test_required_local_suggestions_are_available(self) -> None:
        required_keywords = {
            "insulin",
            "hemoglobin",
            "albumin",
            "kinase",
            "enzyme",
            "antibody",
            "GFP",
            "amylase",
            "collagen",
            "receptor",
            "transporter",
            "glucose",
            "glucagon",
            "glutathione",
            "growth factor",
            "cytochrome",
            "oxidase",
            "polymerase",
            "protease",
            "lipase",
            "cellulase",
            "keratin",
            "elastin",
            "fibrinogen",
            "casein",
        }
        available_keywords = {item["keyword"] for item in get_all_keyword_suggestions()}

        self.assertTrue(required_keywords.issubset(available_keywords))

    def test_suggestions_include_volume_and_limit_metadata(self) -> None:
        for suggestion in get_all_keyword_suggestions():
            self.assertIn(suggestion["expected_volume"], {"small", "medium", "large"})
            self.assertRegex(suggestion["suggested_limit"], r"^(10-30|30-100|100-300\+)$")


if __name__ == "__main__":
    unittest.main()
