#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para testar FASE 5 - Integração com LLMs
Valida: metadata loader, dataset detection, schema loading
"""

import sys
import logging
from pathlib import Path
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend to path
backend_path = str(Path(__file__).parent.parent)
sys.path.insert(0, backend_path)
os.chdir(backend_path)

from metadata.loader import load_metadata, get_available_datasets, get_metadata_by_dataset
from config.datasets import DATASETS_CONFIG, get_table_name
from routes.query import _detect_dataset_for_question


def test_metadata_loader():
    """Test loading metadata for all datasets"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Metadata Loader")
    logger.info("="*80)
    
    datasets = get_available_datasets()
    logger.info(f"✓ Datasets disponíveis: {len(datasets)}")
    for ds in datasets:
        logger.info(f"  - {ds}")
    
    # Tentar carregar cada dataset
    for dataset in datasets:
        try:
            metadata = load_metadata(dataset)
            logger.info(f"✓ Carregado {dataset}")
        except Exception as e:
            logger.error(f"✗ Erro ao carregar {dataset}: {e}")
            return False
    
    return True


def test_dataset_config():
    """Test dataset configuration mapping"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Dataset Configuration")
    logger.info("="*80)
    
    for dataset_id, config in DATASETS_CONFIG.items():
        try:
            table = get_table_name(dataset_id)
            logger.info(f"✓ {dataset_id} → {table}")
            logger.info(f"  Name: {config['name']}")
            logger.info(f"  Domain: {config['dominio']}")
            logger.info(f"  OE: {config['objetivo_estrategico']}")
        except Exception as e:
            logger.error(f"✗ Error with {dataset_id}: {e}")
            return False
    
    return True


def test_dataset_detection():
    """Test automatic dataset detection from questions"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Dataset Detection from Questions")
    logger.info("="*80)
    
    test_questions = [
        ("Quantas vacinas foram aplicadas em SP?", "covid-19-vacinacao"),
        ("Qual é a capacidade de leitos no Brasil?", "leitos"),
        ("Quantos casos de SRAG foram notificados?", "surtos-srag"),
        ("Quais UBS têm coordenadas geográficas?", "atencao-basica"),
    ]
    
    passed = 0
    for question, expected_dataset in test_questions:
        detected = _detect_dataset_for_question(question)
        if detected == expected_dataset:
            logger.info(f"✓ '{question[:50]}...'")
            logger.info(f"  → Detectado: {detected}")
            passed += 1
        else:
            logger.warning(f"⚠ '{question[:50]}...'")
            logger.info(f"  Esperado: {expected_dataset}, Detectado: {detected}")
    
    logger.info(f"\nResultado: {passed}/{len(test_questions)} detectadas corretamente")
    return passed == len(test_questions)


def test_metadata_by_dataset():
    """Test loading metadata as dictionary"""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Metadata as Dictionary")
    logger.info("="*80)
    
    for dataset in get_available_datasets():
        try:
            metadata = get_metadata_by_dataset(dataset)
            
            # Verificar campos essenciais
            essential_keys = ["dataset", "fields"]
            missing = [k for k in essential_keys if k not in metadata]
            
            if missing:
                logger.warning(f"⚠ {dataset}: Faltam keys {missing}")
            else:
                num_fields = len(metadata.get("fields", []))
                num_examples = len(metadata.get("example_queries", []))
                logger.info(f"✓ {dataset}: {num_fields} campos, {num_examples} exemplos")
                
        except Exception as e:
            logger.error(f"✗ Erro ao carregar {dataset}: {e}")
            return False
    
    return True


def main():
    """Execute all tests"""
    logger.info("\n" + "="*80)
    logger.info("🧪 FASE 5 - TESTES DE INTEGRAÇÃO COM LLMs")
    logger.info("="*80)
    
    tests = [
        ("Metadata Loader", test_metadata_loader),
        ("Dataset Configuration", test_dataset_config),
        ("Dataset Detection", test_dataset_detection),
        ("Metadata Dictionary", test_metadata_by_dataset),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"\n✗ Erro em {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Resumo
    logger.info("\n" + "="*80)
    logger.info("📊 RESUMO DOS TESTES")
    logger.info("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        logger.info(f"{status} {name}")
    
    logger.info(f"\nTotal: {passed}/{total} testes passaram")
    
    if passed == total:
        logger.info("\n✅ TODOS OS TESTES PASSARAM - FASE 5 PRONTA!")
        return 0
    else:
        logger.error(f"\n❌ {total - passed} teste(s) falharam")
        return 1


if __name__ == "__main__":
    sys.exit(main())
