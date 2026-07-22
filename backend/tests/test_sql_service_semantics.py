import sys
import unittest
import os
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from services.sql_service import fallback_sql, generate_sql, validate_sql_syntax
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

    def test_supported_single_dataset_intents_generate_semantic_sql(self):
        cases = [
            (
                "Quais estados possuem o maior número de doses registradas contra a COVID-19?",
                "covid-19-vacinacao",
                ("COUNT(*) AS total_doses", "GROUP BY paciente_endereco_uf"),
                ("MAX(paciente_endereco_uf)",),
            ),
            (
                "Qual é a quantidade de leitos de UTI por estado na competência mais recente?",
                "leitos",
                ("SUM(UTI_TOTAL_EXIST) AS total_uti_beds", "MAX(COMP)", "GROUP BY UF"),
                ("COUNT(*)",),
            ),
            (
                "Quais municípios possuem leitos de UTI neonatal?",
                "leitos",
                ("UTI_NEONATAL_EXIST > 0", "MAX(COMP)", "DISTINCT MUNICIPIO"),
                ("COUNT(*) AS total_registros",),
            ),
            (
                "Quantos casos de SRAG foram notificados por estado?",
                "surtos-srag",
                ("COUNT(*) AS total_srag", "GROUP BY SG_UF_NOT", "SG_UF_NOT != ''"),
                (),
            ),
            (
                "Quais municípios possuem o maior número de Unidades Básicas de Saúde?",
                "atencao-basica",
                ("COUNT(DISTINCT CNES) AS total_ubs", "GROUP BY IBGE"),
                ("MAX(IBGE)",),
            ),
        ]

        with patch.dict(os.environ, {"SQL_GENERATION_STRATEGY": "deterministic_first"}):
            with patch("services.sql_service.get_llm") as get_llm_mock:
                for question, dataset, expected, forbidden in cases:
                    with self.subTest(question=question):
                        sql, mode = generate_sql(
                            question,
                            "{}",
                            "deepseek-local",
                            dataset,
                            return_mode=True,
                        )
                        self.assertEqual("deterministic_rule", mode)
                        for fragment in expected:
                            self.assertIn(fragment, sql)
                        for fragment in forbidden:
                            self.assertNotIn(fragment, sql)
        get_llm_mock.assert_not_called()

    def test_semantic_validation_rejects_maximum_of_dimension_code(self):
        self.assertFalse(
            validate_sql_syntax(
                "SELECT MAX(IBGE) AS resultado FROM atencao_basica",
                "atencao-basica",
                "Quais municípios possuem o maior número de Unidades Básicas de Saúde?",
            )
        )

    def test_bed_ratio_fallback_preserves_requested_metric(self):
        question = (
            "Qual é a proporção de leitos SUS em relação ao total de leitos "
            "existentes por região na competência mais recente?"
        )
        sql = fallback_sql(question, "leitos")
        self.assertIn("SUM(LEITOS_SUS) AS leitos_sus", sql)
        self.assertIn("SUM(LEITOS_EXISTENTES) AS leitos_totais", sql)
        self.assertIn("AS percentual_sus", sql)
        self.assertIn("GROUP BY REGIAO", sql)
        self.assertIn("MAX(COMP)", sql)
        self.assertTrue(validate_sql_syntax(sql, "leitos", question))

    def test_bed_ratio_rejects_row_count_substitution(self):
        question = (
            "Qual é a proporção de leitos SUS em relação ao total de leitos "
            "existentes por região na competência mais recente?"
        )
        wrong_sql = "SELECT REGIAO, COUNT(*) AS total FROM leitos GROUP BY REGIAO"
        self.assertFalse(validate_sql_syntax(wrong_sql, "leitos", question))

    def test_llm_failure_uses_semantically_correct_bed_ratio_fallback(self):
        question = (
            "Qual é a proporção de leitos SUS em relação ao total de leitos "
            "existentes por região na competência mais recente?"
        )
        llm = patch("services.sql_service.get_llm").start()
        self.addCleanup(patch.stopall)
        llm.return_value.generate.side_effect = TimeoutError("timeout")
        sql, mode = generate_sql(
            question,
            "{}",
            "deepseek-local",
            "leitos",
            return_mode=True,
        )
        self.assertEqual("deterministic_fallback", mode)
        self.assertIn("AS percentual_sus", sql)
        self.assertNotIn("COUNT(*) AS total", sql)

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
        self.assertEqual(["ibge", "total_srag", "total_ubs"], response["columns"])
        self.assertEqual(1, len(response["highlights"]))
        self.assertEqual(response["analytical_limitations"], response["warnings"])
        self.assertIn("co_mun_not", response["sql"])
        self.assertIn("atencao_basica", response["sql"])

    def test_llm_generated_distribution_uses_deterministic_presentation(self):
        request = AskRequest(question="Qual é a distribuição dos casos de SRAG por sexo?")
        generated_sql = (
            "SELECT cs_sexo, COUNT(*) AS total FROM srag "
            "GROUP BY cs_sexo ORDER BY total DESC"
        )
        rows = [("M", 48074), ("F", 44073), ("I", 9)]
        with patch("routes.query.generate_sql", return_value=(generated_sql, "llm")):
            with patch("routes.query.run_query", return_value=rows):
                with patch("routes.query.interpret_result") as interpret_mock:
                    response = ask(request)

        interpret_mock.assert_not_called()
        self.assertEqual("llm", response["sql_generation_mode"])
        self.assertEqual("deterministic_factual", response["interpretation_mode"])
        self.assertIn("Masculino: 48.074 (52,17%)", response["insight"])
        self.assertEqual("Masculino — casos de SRAG: 48.074", response["highlights"][0])


if __name__ == "__main__":
    unittest.main()
