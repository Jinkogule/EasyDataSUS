import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config.datasets import DATASETS_CONFIG, get_table_name
from metadata.loader import load_metadata

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Relationship:
    id: str
    description: str
    source_dataset: str
    source_table: str
    source_column: str
    target_dataset: str
    target_table: str
    target_column: str
    join_type: str
    common_dimension: str
    source_granularity: str
    target_granularity: str
    cardinality: str
    requires_preaggregation: bool
    analytical_notes: str = ""
    source_temporal_column: str = ""
    target_temporal_column: str = ""
    use_latest_target_period: bool = False
    limitation_keywords: Tuple[str, ...] = ()
    result_notes: Tuple[str, ...] = ()


class RelationshipService:
    """Carrega e valida relacionamentos estruturados entre datasets."""

    def __init__(self, relationships_path: Optional[Path] = None):
        self.relationships_path = relationships_path or Path(__file__).resolve().parents[1] / "metadata" / "relationships.json"
        self._relationships = self._load_relationships()

    def _load_relationships(self) -> List[Relationship]:
        if not self.relationships_path.exists():
            logger.warning(f"Arquivo de relacionamentos não encontrado: {self.relationships_path}")
            return []

        with open(self.relationships_path, "r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)

        relationships: List[Relationship] = []
        for item in payload.get("relationships", []):
            relationship = Relationship(
                id=item["id"],
                description=item.get("description", ""),
                source_dataset=item["source_dataset"],
                source_table=item["source_table"],
                source_column=item["source_column"],
                target_dataset=item["target_dataset"],
                target_table=item["target_table"],
                target_column=item["target_column"],
                join_type=item.get("join_type", "INNER").upper(),
                common_dimension=item.get("common_dimension", ""),
                source_granularity=item.get("source_granularity", ""),
                target_granularity=item.get("target_granularity", ""),
                cardinality=item.get("cardinality", ""),
                requires_preaggregation=bool(item.get("requires_preaggregation", False)),
                analytical_notes=item.get("analytical_notes", ""),
                source_temporal_column=item.get("source_temporal_column", ""),
                target_temporal_column=item.get("target_temporal_column", ""),
                use_latest_target_period=bool(item.get("use_latest_target_period", False)),
                limitation_keywords=tuple(item.get("limitation_keywords", [])),
                result_notes=tuple(item.get("result_notes", [])),
            )
            self._validate_relationship(relationship)
            relationships.append(relationship)

        return relationships

    def _validate_relationship(self, relationship: Relationship) -> None:
        if relationship.source_dataset not in DATASETS_CONFIG:
            raise ValueError(f"Dataset de origem inválido: {relationship.source_dataset}")
        if relationship.target_dataset not in DATASETS_CONFIG:
            raise ValueError(f"Dataset de destino inválido: {relationship.target_dataset}")

        source_table = get_table_name(relationship.source_dataset)
        target_table = get_table_name(relationship.target_dataset)
        if source_table != relationship.source_table:
            raise ValueError(f"Tabela de origem inconsistente para {relationship.id}: {relationship.source_table}")
        if target_table != relationship.target_table:
            raise ValueError(f"Tabela de destino inconsistente para {relationship.id}: {relationship.target_table}")

        source_metadata = json.loads(load_metadata(relationship.source_dataset))
        target_metadata = json.loads(load_metadata(relationship.target_dataset))
        source_columns = self._schema_columns(source_metadata)
        target_columns = self._schema_columns(target_metadata)
        source_lookup = {column_name.lower() for column_name in source_columns.keys()}
        target_lookup = {column_name.lower() for column_name in target_columns.keys()}

        if relationship.source_column.lower() not in source_lookup:
            raise ValueError(f"Coluna de origem inexistente: {relationship.source_column}")
        if relationship.target_column.lower() not in target_lookup:
            raise ValueError(f"Coluna de destino inexistente: {relationship.target_column}")
        if relationship.source_temporal_column and relationship.source_temporal_column.lower() not in source_lookup:
            raise ValueError(f"Coluna temporal de origem inexistente: {relationship.source_temporal_column}")
        if relationship.target_temporal_column and relationship.target_temporal_column.lower() not in target_lookup:
            raise ValueError(f"Coluna temporal de destino inexistente: {relationship.target_temporal_column}")

    @staticmethod
    def _schema_columns(metadata: dict) -> Dict[str, dict]:
        columns = metadata.get("colunas_principais") or metadata.get("columns") or {}
        return columns if isinstance(columns, dict) else {}

    def list_relationships(self) -> List[Relationship]:
        return list(self._relationships)

    def find_relationships(self, datasets: List[str]) -> List[Relationship]:
        dataset_set = set(datasets)
        return [
            relationship for relationship in self._relationships
            if {relationship.source_dataset, relationship.target_dataset}.issubset(dataset_set)
        ]

    def find_direct_relationship(self, source_dataset: str, target_dataset: str) -> Optional[Relationship]:
        for relationship in self._relationships:
            if relationship.source_dataset == source_dataset and relationship.target_dataset == target_dataset:
                return relationship
            if relationship.source_dataset == target_dataset and relationship.target_dataset == source_dataset:
                return relationship
        return None

    def build_context(self, datasets: List[str]) -> Dict[str, object]:
        relationships = self.find_relationships(datasets)
        return {
            "datasets": datasets,
            "relationships": [relationship.__dict__ for relationship in relationships],
        }


relationship_service = RelationshipService()
