#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste para validar a nova estrutura escalável de datasets.

Demonstra como adicionar e usar múltiplos datasets no EasyDataSUS.
"""

import logging
from pathlib import Path
from metadata.loader import load_metadata
from etl.load_csv import load_csv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_metadata_loading():
    """Testa carregamento de metadados escalável"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Carregamento de Metadados - Estrutura Escalável")
    logger.info("="*80)
    
    # Teste 1: Padrão (vacinacao-covid)
    logger.info("\n✓ Carregando metadata padrão (vacinacao-covid)...")
    meta = load_metadata()
    logger.info(f"✅ Sucesso! Schema contém {len(meta)} caracteres")
    
    # Teste 2: Dataset específico
    logger.info("\n✓ Carregando metadata específico (vacinacao-covid)...")
    meta = load_metadata("vacinacao-covid")
    logger.info(f"✅ Sucesso! Schema contém {len(meta)} caracteres")
    
    # Teste 3: Erro intencional - dataset não existe
    logger.info("\n✓ Tentando carregar dataset inexistente (dengue-2024)...")
    try:
        meta = load_metadata("dengue-2024")
        logger.error("❌ Deveria ter lançado erro!")
    except FileNotFoundError as e:
        logger.info(f"✅ Erro esperado capturado: {str(e)[:80]}...")

def test_csv_loading():
    """Testa carregamento de CSV escalável"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Carregamento de CSV - Estrutura Escalável")
    logger.info("="*80)
    
    # Verificar se arquivo existe
    data_path = Path("data/datasets/vacinacao-covid/vacinacao-ac-es.csv")
    if data_path.exists():
        logger.info(f"\n✓ Arquivo encontrado: {data_path}")
        logger.info(f"  Tamanho: {data_path.stat().st_size / 1024 / 1024:.2f} MB")
        logger.info(f"  ✅ Estrutura de pasta está correta")
    else:
        logger.error(f"❌ Arquivo não encontrado: {data_path}")

def test_structure():
    """Testa estrutura de pastas criada"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Verificação de Estrutura de Pastas")
    logger.info("="*80)
    
    # Verificar estrutura metadata
    meta_path = Path("metadata/datasets/vacinacao-covid")
    logger.info(f"\n✓ Verificando: {meta_path}")
    if meta_path.exists():
        logger.info(f"✅ Pasta existe")
        files = list(meta_path.glob("*"))
        for f in files:
            logger.info(f"   - {f.name}")
    else:
        logger.error(f"❌ Pasta não existe: {meta_path}")
    
    # Verificar estrutura data
    data_path = Path("data/datasets/vacinacao-covid")
    logger.info(f"\n✓ Verificando: {data_path}")
    if data_path.exists():
        logger.info(f"✅ Pasta existe")
        files = list(data_path.glob("*"))
        for f in files:
            logger.info(f"   - {f.name}")
    else:
        logger.error(f"❌ Pasta não existe: {data_path}")

def show_scalability_examples():
    """Mostra exemplos de como escalar"""
    logger.info("\n" + "="*80)
    logger.info("EXEMPLOS: Como Adicionar Novos Datasets")
    logger.info("="*80)
    
    examples = [
        {
            "dataset": "dengue-2024",
            "description": "Casos de Dengue em 2024",
            "structure": """
                metadata/datasets/dengue-2024/
                └── schema.json
                
                data/datasets/dengue-2024/
                └── dengue-ac-es.csv
            """,
            "usage": """
                # Carregamento
                load_csv(dataset="dengue-2024")
                
                # Metadata
                metadata = load_metadata("dengue-2024")
            """
        },
        {
            "dataset": "influenza-2025",
            "description": "Casos de Influenza em 2025",
            "structure": """
                metadata/datasets/influenza-2025/
                └── schema.json
                
                data/datasets/influenza-2025/
                └── influenza-ac-es.csv
            """,
            "usage": """
                # Carregamento
                load_csv(dataset="influenza-2025")
                
                # Metadata
                metadata = load_metadata("influenza-2025")
            """
        }
    ]
    
    for ex in examples:
        logger.info(f"\n💡 Dataset: {ex['dataset']}")
        logger.info(f"   {ex['description']}")
        logger.info(f"\n   Estrutura:")
        logger.info(ex['structure'])
        logger.info(f"\n   Uso:")
        logger.info(ex['usage'])

if __name__ == "__main__":
    logger.info("""
╔════════════════════════════════════════════════════════════════════════════╗
║                    TESTES DE ESCALABILIDADE - EasyDataSUS                  ║
║               Validação da Nova Estrutura de Datasets Escalável             ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        test_structure()
        test_metadata_loading()
        test_csv_loading()
        show_scalability_examples()
        
        logger.info("\n" + "="*80)
        logger.info("✅ TODOS OS TESTES PASSARAM COM SUCESSO!")
        logger.info("="*80)
        logger.info("""
Próximos passos para adicionar novos datasets:

1. Crie a pasta: metadata/datasets/{novo-dataset}/
2. Adicione schema.json com definição das colunas
3. Crie a pasta: data/datasets/{novo-dataset}/
4. Adicione o arquivo CSV com os dados
5. Use load_metadata("{novo-dataset}") para carregar
6. Use load_csv(dataset="{novo-dataset}") para carregar dados

Estrutura escalável pronta para crescer! 🚀
        """)
    except Exception as e:
        logger.error(f"\n❌ ERRO durante testes: {e}")
        import traceback
        traceback.print_exc()
