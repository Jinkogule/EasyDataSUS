import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from services.interpretation_service import _fallback_interpretation, interpret_result


class InterpretationServiceTests(unittest.TestCase):
    def test_empty_llm_response_uses_factual_summary(self):
        llm = MagicMock()
        llm.generate.return_value = ""
        with patch("services.interpretation_service.get_llm", return_value=llm):
            response = interpret_result(
                "Apresente os resultados",
                [("SP", 10)],
                factual_summary="São Paulo possui 10 registros.",
            )
        self.assertEqual("São Paulo possui 10 registros.", response)

    def test_generic_fallback_does_not_expose_python_tuple(self):
        response = _fallback_interpretation(
            [("SP", 10, 20), ("RJ", 8, 15)],
            "Compare os resultados",
        )
        self.assertNotIn("('SP'", response)
        self.assertIn("Consulte a tabela", response)


if __name__ == "__main__":
    unittest.main()
