import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from services.result_formatter import (
    build_factual_summary,
    extract_output_columns,
    is_low_information_interpretation,
    should_use_deterministic_interpretation,
)


class ResultFormatterTests(unittest.TestCase):
    SQL = "SELECT uf, total_doses, total_uti_beds FROM resultado ORDER BY total_doses DESC"

    def test_extracts_outer_projection_aliases(self):
        self.assertEqual(["uf", "total_doses", "total_uti_beds"], extract_output_columns(self.SQL))

    def test_reports_independent_leader_for_each_metric(self):
        summary = build_factual_summary(
            self.SQL,
            [("AC", 373854, 105), ("SP", 824, 15676)],
            "Qual estado tem maior número de doses e qual tem maior quantidade de leitos?",
        )
        self.assertIn("doses registradas: AC (373.854)", summary)
        self.assertIn("leitos de UTI: SP (15.676)", summary)
        self.assertNotIn("leitos de UTI: AC", summary)
        self.assertTrue(
            should_use_deterministic_interpretation(
                "Quais estados apresentam maior número de doses e maior quantidade de leitos?",
                summary,
            )
        )

    def test_formats_scalar_count_from_question_context(self):
        summary = build_factual_summary(
            "SELECT COUNT(*) FROM vacinacao WHERE paciente_endereco_uf = 'SP'",
            [(824,)],
            "Quantas vacinas foram aplicadas em SP?",
        )
        self.assertEqual("Total de registros de doses aplicadas: 824.", summary)
        self.assertTrue(should_use_deterministic_interpretation("Quantas vacinas foram aplicadas?", summary))

    def test_listing_reports_rows_instead_of_unrequested_maxima(self):
        summary = build_factual_summary(
            self.SQL,
            [("AC", 373854, 105), ("SP", 824, 15676)],
            "Quais estados possuem registros nas duas bases e quais são os respectivos totais?",
        )
        self.assertTrue(summary.startswith("Foram encontrados 2 resultados:"))
        self.assertIn("AC (número de doses registradas: 373.854", summary)
        self.assertIn("SP (número de doses registradas: 824", summary)

    def test_comparison_uses_deterministic_factual_summary(self):
        summary = build_factual_summary(
            self.SQL,
            [("AC", 373854, 105), ("SP", 824, 15676)],
            "Compare doses registradas com leitos de UTI por estado",
        )
        self.assertTrue(
            should_use_deterministic_interpretation(
                "Compare doses registradas com leitos de UTI por estado",
                summary,
            )
        )

    def test_rejects_generic_llm_interpretation(self):
        summary = "Nos dados retornados, maior número de doses: AC (373.854)."
        self.assertTrue(
            is_low_information_interpretation(
                "Consulta retornou 27 registros. Primeiros dados: ('AC', 373854)",
                summary,
            )
        )

    def test_numeric_ibge_is_treated_as_dimension(self):
        summary = build_factual_summary(
            "SELECT ibge, total_srag, total_ubs FROM resultado",
            [(355030, 120, 45)],
            "Quais municípios possuem SRAG e UBS e quais são os respectivos totais?",
        )
        self.assertTrue(summary.startswith("Foram encontrados 1 resultado:"))
        self.assertIn("355030", summary)
        self.assertIn("município (código IBGE 355030)", summary)
        self.assertTrue(
            should_use_deterministic_interpretation(
                "Quais municípios possuem SRAG e UBS e quais são os respectivos totais?",
                summary,
            )
        )

    def test_summary_reports_applied_result_limit(self):
        rows = [(350000 + index, 1000 - index, 20) for index in range(100)]
        summary = build_factual_summary(
            "SELECT ibge, total_srag, total_ubs FROM resultado LIMIT 100",
            rows,
            "Quais municípios possuem SRAG e UBS?",
        )
        self.assertTrue(summary.startswith("A consulta retornou os primeiros 100 resultados (limite aplicado):"))
        self.assertIn("Os demais 90 resultados retornados estão na tabela.", summary)


if __name__ == "__main__":
    unittest.main()
