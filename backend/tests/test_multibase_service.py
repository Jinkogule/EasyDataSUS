import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.multibase_service import multibase_service
from services.relationship_service import relationship_service


class MultibaseServiceTests(unittest.TestCase):
    def test_parses_single_dataset_selection(self):
        selection = multibase_service._parse_selection_response(
            '{"datasets": ["surtos-srag"], "cross_dataset": false, "reason": "SRAG only"}',
            ["surtos-srag", "atencao-basica"],
        )
        self.assertIsNotNone(selection)
        self.assertEqual(selection.datasets, ["surtos-srag"])
        self.assertFalse(selection.cross_dataset)

    def test_parses_multi_dataset_selection(self):
        selection = multibase_service._parse_selection_response(
            '{"datasets": ["surtos-srag", "atencao-basica"], "cross_dataset": true, "reason": "cross dataset"}',
            ["surtos-srag", "atencao-basica"],
        )
        self.assertIsNotNone(selection)
        self.assertEqual(selection.datasets, ["surtos-srag", "atencao-basica"])
        self.assertTrue(selection.cross_dataset)

    def test_builds_multibase_context(self):
        context = multibase_service.build_multibase_context(
            ["surtos-srag", "atencao-basica"],
            relationship_service.find_relationships(["surtos-srag", "atencao-basica"]),
        )
        self.assertIn("datasets", context)
        self.assertIn("relationships", context)
        self.assertEqual(context["datasets"], ["surtos-srag", "atencao-basica"])

    def test_accepts_canonical_preaggregated_srag_ubs_sql(self):
        relationships = relationship_service.find_relationships(["surtos-srag", "atencao-basica"])
        sql = multibase_service.build_deterministic_fallback_sql(["surtos-srag", "atencao-basica"], relationships)
        self.assertIsNotNone(sql)
        validation = multibase_service.validate_sql(sql, ["surtos-srag", "atencao-basica"], relationships)
        self.assertTrue(validation.valid)
        self.assertIn("srag", " ".join(validation.tables))

    def test_rejects_wrong_join_key(self):
        relationships = relationship_service.find_relationships(["surtos-srag", "atencao-basica"])
        sql = multibase_service.build_deterministic_fallback_sql(["surtos-srag", "atencao-basica"], relationships)
        self.assertIsNotNone(sql)
        invalid_sql = sql.replace("s.ibge = u.ibge", "s.ibge = u.uf")
        validation = multibase_service.validate_sql(invalid_sql, ["surtos-srag", "atencao-basica"], relationships)
        self.assertFalse(validation.valid)

    def test_rejects_additional_unauthorized_table(self):
        relationships = relationship_service.find_relationships(["surtos-srag", "atencao-basica"])
        sql = "SELECT * FROM srag s INNER JOIN leitos l ON s.co_mun_not = l.uf"
        validation = multibase_service.validate_sql(sql, ["surtos-srag", "atencao-basica"], relationships)
        self.assertFalse(validation.valid)

    def test_does_not_confuse_cte_with_physical_table(self):
        relationships = relationship_service.find_relationships(["surtos-srag", "atencao-basica"])
        sql = multibase_service.build_deterministic_fallback_sql(["surtos-srag", "atencao-basica"], relationships)
        validation = multibase_service.validate_sql(sql, ["surtos-srag", "atencao-basica"], relationships)
        self.assertTrue(validation.valid)
        self.assertNotIn("srag_by_municipality", validation.tables)
        self.assertNotIn("ubs_by_municipality", validation.tables)


if __name__ == "__main__":
    unittest.main()
