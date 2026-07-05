import json
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.relationship_service import RelationshipService


class RelationshipServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = RelationshipService()

    def test_loads_relationships(self):
        relationships = self.service.list_relationships()
        self.assertGreaterEqual(len(relationships), 1)

    def test_finds_srag_ubs_relationship(self):
        relationship = self.service.find_direct_relationship("surtos-srag", "atencao-basica")
        self.assertIsNotNone(relationship)
        self.assertEqual(relationship.source_column, "co_mun_not")
        self.assertEqual(relationship.target_column, "ibge")
        self.assertTrue(relationship.requires_preaggregation)

    def test_build_context_returns_relationships(self):
        context = self.service.build_context(["surtos-srag", "atencao-basica"])
        self.assertIn("relationships", context)
        self.assertEqual(len(context["relationships"]), 1)
        self.assertEqual(context["relationships"][0]["id"], "srag_ubs_municipio_notificacao")


if __name__ == "__main__":
    unittest.main()
