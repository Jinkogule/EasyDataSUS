import importlib.util
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "backend" / "tests" / "benchmark_68_questoes_seidig.py"
SPEC = importlib.util.spec_from_file_location("seidig_benchmark", MODULE_PATH)
benchmark = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(benchmark)


class BenchmarkRubricTests(unittest.TestCase):
    def test_parser_keeps_all_68_questions(self):
        grouped = benchmark.parse_68_questions()
        questions = [question for group in grouped.values() for question in group]
        self.assertEqual(68, len(questions))

    def test_only_curated_relationships_enter_relationship_metrics(self):
        results = [
            {
                "implementation_support": "supported",
                "expected_datasets": ["surtos-srag", "atencao-basica"],
                "datasets": ["surtos-srag", "atencao-basica"],
                "expected_relationships": ["srag_ubs_municipio_notificacao"],
                "relationships": ["srag_ubs_municipio_notificacao"],
            },
            {
                "implementation_support": "unsupported",
                "expected_datasets": ["surtos-srag", "leitos"],
                "datasets": ["surtos-srag"],
                "expected_relationships": [],
                "relationships": [],
            },
        ]

        metrics = benchmark._compute_selection_metrics(results)
        self.assertEqual(2, metrics["dataset_selection"]["evaluated"])
        self.assertEqual(1, metrics["relationship_selection"]["evaluated"])
        self.assertEqual(1.0, metrics["relationship_selection"]["exact_match_rate"])

    def test_interoperability_rubric_separates_data_and_implementation(self):
        self.assertEqual("full", benchmark.INTEROPERABILITY_GOLD[61]["data_answerability"])
        self.assertEqual("supported", benchmark.INTEROPERABILITY_GOLD[61]["implementation_support"])
        self.assertEqual("full", benchmark.INTEROPERABILITY_GOLD[64]["data_answerability"])
        self.assertEqual("supported", benchmark.INTEROPERABILITY_GOLD[64]["implementation_support"])
        self.assertEqual("partial", benchmark.INTEROPERABILITY_GOLD[65]["data_answerability"])
        self.assertEqual("unsupported", benchmark.INTEROPERABILITY_GOLD[65]["implementation_support"])


if __name__ == "__main__":
    unittest.main()
