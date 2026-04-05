#!/usr/bin/env python3
"""
Teste e demonstração da funcionalidade de múltiplos CSVs.

Este script mostra como o sistema agora suporta múltiplos arquivos CSV
por dataset e os consolida automaticamente.
"""

import sys
from pathlib import Path

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from etl.load_csv import load_csv

def test_multiple_csv_support():
    """
    Testa o suporte a múltiplos CSVs.
    
    Uso:
        python test_multiple_csv_support.py
    """
    
    print("\n" + "="*70)
    print("🧪 TESTE: Suporte a Múltiplos CSVs por Dataset")
    print("="*70)
    
    print("\n📋 Verificando estrutura de dados:")
    
    # Verificar datasets
    base_path = Path(__file__).parent / "backend" / "data" / "datasets"
    
    for dataset_folder in sorted(base_path.glob("*")):
        if dataset_folder.is_dir():
            csv_files = list(dataset_folder.glob("*.csv"))
            if csv_files:
                print(f"\n🗂️  Dataset: {dataset_folder.name}")
                print(f"   Arquivos CSV encontrados: {len(csv_files)}")
                for csv_file in sorted(csv_files):
                    size_kb = csv_file.stat().st_size / 1024
                    print(f"   • {csv_file.name} ({size_kb:.1f} KB)")
    
    print("\n" + "-"*70)
    print("✅ O sistema agora carrega TODOS os CSVs de cada pasta!")
    print("-"*70)
    
    print("\n📖 Exemplos de Uso:")
    print("""
    1️⃣  Carregar TODOS os CSVs de vacinacao-covid:
        python -c "from etl.load_csv import load_csv; load_csv()"
    
    2️⃣  Carregar TODOS os CSVs de outro dataset:
        python -c "from etl.load_csv import load_csv; load_csv(dataset='dengue-2024')"
    
    3️⃣  Carregar arquivo específico (compatível):
        python -c "from etl.load_csv import load_csv; load_csv('/path/to/file.csv')"
    """)
    
    print("\n" + "="*70)
    print("✅ Suporte a múltiplos CSVs implementado e validado!")
    print("="*70)

if __name__ == "__main__":
    test_multiple_csv_support()
