import sys
import unittest
import os
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from services.sql_service import fallback_sql, generate_sql
from routes.query import AskRequest, _error_response, ask, sanitize_sql


class SqlServiceSemanticTests(unittest.TestCase):
    def test_bed_capacity_list_uses_latest_competence(self):
        sql = fallback_sql("Quais cidades têm UTI neonatal?", "leitos")
        self.assertIn("UTI_NEONATAL_EXIST > 0", sql)
        self.assertIn("COMP = (SELECT MAX(COMP) FROM leitos)", sql)

    def test_simple_count_uses_fast_deterministic_rule(self):
        with patch.dict(os.environ, {"SQL_GENERATION_STRATEGY": "deterministic_first"}):
            with patch("services.sql_service.get_llm") as get_llm_mock:
                sql, mode = generate_sql(
                    "Quantas vacinas foram aplicadas em SP?",
                    "{}",
                    "deepseek-local",
                    "covid-19-vacinacao",
                    return_mode=True,
                )

        get_llm_mock.assert_not_called()
        self.assertEqual("deterministic_rule", mode)
        self.assertIn("COUNT(*) AS total_registros", sql)
        self.assertIn("paciente_endereco_uf = 'SP'", sql)
        self.assertNotIn("LIMIT", sql)

    def test_sanitizer_does_not_add_limit_to_scalar_aggregate(self):
        sql = sanitize_sql("SELECT COUNT(*) AS total_registros FROM vacinacao")
        self.assertNotIn("LIMIT", sql)

    def test_error_response_keeps_standard_contract(self):
        response = _error_response(
            "Pergunta",
            ["surtos-srag"],
            "Erro",
            "Consulta não executada.",
            routing_mode="heuristic_single_dataset",
        )
        for field in (
            "dataset", "datasets", "cross_dataset", "relationships",
            "routing_mode", "sql_generation_mode", "validation", "success",
        ):
            self.assertIn(field, response)
        self.assertFalse(response["success"])

    def test_srag_ubs_question_reaches_multibase_flow(self):
        request = AskRequest(
            question=(
                "Quais municípios possuem registros de SRAG e Unidades Básicas "
                "de Saúde, e quais são os respectivos totais?"
            )
        )
        with patch.dict(os.environ, {"SQL_GENERATION_STRATEGY": "deterministic_first"}):
            with patch("routes.query.run_query", return_value=[(355030, 120, 45)]):
                response = ask(request)

        self.assertTrue(response["success"])
        self.assertTrue(response["cross_dataset"])
        self.assertEqual(["surtos-srag", "atencao-basica"], response["datasets"])
        self.assertEqual(["srag_ubs_municipio_notificacao"], response["relationships"])
        self.assertTrue(response["analytical_limitations"])
        self.assertIn("município de notificação", response["analytical_limitations"][0])
        self.assertIn("co_mun_not", response["sql"])
        self.assertIn("atencao_basica", response["sql"])


if __name__ == "__main__":
    unittest.main()
