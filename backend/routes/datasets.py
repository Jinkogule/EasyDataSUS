"""
Endpoints para gerenciar datasets disponíveis.
Fornece informações sobre datasets, esquemas e configurações.
"""

from fastapi import APIRouter
from typing import Dict, List
from metadata.loader import get_available_datasets, get_metadata_by_dataset
from config.datasets import DATASETS_CONFIG
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("/")
def list_datasets():
    """
    Lista todos os datasets disponíveis com informações básicas.
    
    **Returns:**
    - `datasets`: Lista de datasets com nome, descrição, tabela ClickHouse, e status
    
    **Exemplo:**
    ```json
    {
      "datasets": [
        {
          "id": "covid-19-vacinacao",
          "name": "Campanha Nacional de Vacinação COVID-19",
          "description": "Vacinação COVID-19 no Brasil",
                    "table_name": "vacinacao",
          "objetivo_estrategico": "OE 3.6.1",
          "dominio": "Imunização",
          "status": "implementado"
        },
        {
          "id": "surtos-srag",
          "name": "Síndrome Respiratória Aguda Grave (SRAG)",
          "description": "Vigilância da Síndrome Respiratória Aguda Grave",
          "table_name": "srag",
          "objetivo_estrategico": "OE 9.1",
          "dominio": "Vigilância Epidemiológica",
          "status": "implementado"
        }
      ]
    }
    ```
    """
    available = get_available_datasets()
    datasets = []
    
    for dataset_id in available:
        if dataset_id in DATASETS_CONFIG:
            config = DATASETS_CONFIG[dataset_id]
            datasets.append({
                "id": dataset_id,
                "name": config.get("name", ""),
                "description": config.get("description", ""),
                "table_name": config.get("table_name", ""),
                "objetivo_estrategico": config.get("objetivo_estrategico", ""),
                "dominio": config.get("dominio", ""),
                "status": config.get("status", "")
            })
    
    logger.info(f"Listados {len(datasets)} datasets disponíveis")
    return {
        "total": len(datasets),
        "datasets": datasets
    }


@router.get("/{dataset_id}")
def get_dataset_info(dataset_id: str):
    """
    Obtém informações completas sobre um dataset específico, incluindo schema.
    
    **Path Parameters:**
    - `dataset_id`: ID do dataset (ex: "covid-19-vacinacao", "surtos-srag")
    
    **Returns:**
    - `info`: Configuração do dataset
    - `schema`: Schema JSON com documentação completa dos campos
    
    **Exemplo:**
    ```
    GET /datasets/surtos-srag
    ```
    
    **Response:**
    ```json
    {
      "info": {
        "id": "surtos-srag",
        "name": "Síndrome Respiratória Aguda Grave (SRAG)",
        "description": "Vigilância da Síndrome Respiratória Aguda Grave",
        "table_name": "srag",
        "status": "implementado"
      },
      "schema": {
        "dataset": "surtos-srag",
        "fields": [...],
        "example_queries": [...]
      }
    }
    ```
    """
    
    if dataset_id not in DATASETS_CONFIG:
        available = get_available_datasets()
        logger.warning(f"Dataset '{dataset_id}' não encontrado. Disponíveis: {available}")
        return {
            "error": f"Dataset '{dataset_id}' não encontrado",
            "available_datasets": available,
            "success": False
        }
    
    try:
        config = DATASETS_CONFIG[dataset_id]
        schema = get_metadata_by_dataset(dataset_id)
        
        logger.info(f"Informações obtidas para dataset: {dataset_id}")
        return {
            "info": {
                "id": dataset_id,
                "name": config.get("name", ""),
                "description": config.get("description", ""),
                "table_name": config.get("table_name", ""),
                "objetivo_estrategico": config.get("objetivo_estrategico", ""),
                "dominio": config.get("dominio", ""),
                "status": config.get("status", "")
            },
            "schema": schema,
            "success": True
        }
    
    except Exception as e:
        logger.error(f"Erro ao obter informações de '{dataset_id}': {e}")
        return {
            "error": f"Erro ao carregar dataset: {str(e)}",
            "success": False
        }


@router.get("/{dataset_id}/fields")
def get_dataset_fields(dataset_id: str):
    """
    Lista todos os campos de um dataset com tipos e descrições.
    
    **Path Parameters:**
    - `dataset_id`: ID do dataset
    
    **Returns:**
    - `fields`: Lista de campos com tipo, descrição, exemplos
    
    **Exemplo:**
    ```
    GET /datasets/surtos-srag/fields
    ```
    """
    
    if dataset_id not in DATASETS_CONFIG:
        return {
            "error": f"Dataset '{dataset_id}' não encontrado",
            "success": False
        }
    
    try:
        schema = get_metadata_by_dataset(dataset_id)
        fields = schema.get("fields", [])
        
        logger.info(f"Campos obtidos para dataset: {dataset_id} ({len(fields)} campos)")
        return {
            "dataset_id": dataset_id,
            "total_fields": len(fields),
            "fields": fields,
            "success": True
        }
    
    except Exception as e:
        logger.error(f"Erro ao obter campos de '{dataset_id}': {e}")
        return {
            "error": f"Erro ao carregar campos: {str(e)}",
            "success": False
        }


@router.get("/{dataset_id}/examples")
def get_dataset_examples(dataset_id: str):
    """
    Obtém queries de exemplo para um dataset.
    
    **Path Parameters:**
    - `dataset_id`: ID do dataset
    
    **Returns:**
    - `examples`: Lista de queries exemplo com descrições
    
    **Exemplo:**
    ```
    GET /datasets/surtos-srag/examples
    ```
    """
    
    if dataset_id not in DATASETS_CONFIG:
        return {
            "error": f"Dataset '{dataset_id}' não encontrado",
            "success": False
        }
    
    try:
        schema = get_metadata_by_dataset(dataset_id)
        examples = schema.get("example_queries", [])
        
        logger.info(f"Exemplos obtidos para dataset: {dataset_id} ({len(examples)} exemplos)")
        return {
            "dataset_id": dataset_id,
            "total_examples": len(examples),
            "examples": examples,
            "success": True
        }
    
    except Exception as e:
        logger.error(f"Erro ao obter exemplos de '{dataset_id}': {e}")
        return {
            "error": f"Erro ao carregar exemplos: {str(e)}",
            "success": False
        }
