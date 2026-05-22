#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de análise da estrutura de datasets SRAG e UBS
Gera relatórios detalhados sobre colunas, tipos, valores faltantes, etc.
"""

import pandas as pd
import json
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_dataset(csv_path, output_name, encoding='utf-8'):
    """Analisa estrutura de um dataset e gera relatório"""
    
    logger.info(f"\n{'='*80}")
    logger.info(f"ANÁLISE: {output_name}")
    logger.info(f"{'='*80}\n")
    
    # Carregar dados (com fallback para latin-1)
    # Note: Os arquivos do DataSUS usam delimitador ';' (ponto-e-vírgula)
    try:
        df = pd.read_csv(csv_path, encoding=encoding, sep=';', nrows=50000, on_bad_lines='skip')
        logger.info(f"✓ Arquivo carregado com encoding {encoding}")
    except Exception as e:
        logger.warning(f"Falha com {encoding}, tentando latin-1...")
        try:
            df = pd.read_csv(csv_path, encoding='latin-1', sep=';', nrows=50000, on_bad_lines='skip')
            logger.info(f"✓ Arquivo carregado com encoding latin-1")
        except Exception as e2:
            logger.error(f"Erro ao carregar: {e2}")
            return None
    
    # Informações básicas
    logger.info(f"\n📊 INFORMAÇÕES BÁSICAS:")
    logger.info(f"  • Total de registros (amostra): {len(df):,}")
    logger.info(f"  • Total de colunas: {len(df.columns)}")
    logger.info(f"  • Tamanho em memória: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    
    # Detalhes de colunas
    logger.info(f"\n📋 COLUNAS E TIPOS:")
    logger.info("-" * 100)
    
    columns_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        non_null = df[col].notna().sum()
        null_count = df[col].isna().sum()
        null_pct = (null_count / len(df)) * 100
        unique = df[col].nunique()
        
        col_info = {
            "nome": col,
            "tipo": dtype,
            "nao_nulos": int(non_null),
            "nulos": int(null_count),
            "percentual_nulos": round(null_pct, 2),
            "valores_unicos": int(unique)
        }
        columns_info.append(col_info)
        
        logger.info(
            f"  {col:35} | tipo: {dtype:12} | não-nulos: {non_null:7,} "
            f"| nulos: {null_pct:5.1f}% | únicos: {unique:6,}"
        )
    
    # Estatísticas numéricas
    logger.info(f"\n📈 ESTATÍSTICAS NUMÉRICAS:")
    logger.info("-" * 100)
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        stats = df[numeric_cols].describe()
        logger.info(stats.to_string())
    else:
        logger.info("  (Nenhuma coluna numérica)")
    
    # Amostra de dados
    logger.info(f"\n📑 AMOSTRA DE 5 LINHAS:")
    logger.info("-" * 100)
    logger.info(df.head().to_string())
    
    # Valores únicos para colunas categóricas
    logger.info(f"\n🏷️  PRIMEIROS VALORES ÚNICOS (COLUNAS CATEGÓRICAS):")
    logger.info("-" * 100)
    categorical_cols = df.select_dtypes(include=['object']).columns
    for col in categorical_cols[:5]:  # Primeiras 5 colunas categóricas
        unique_vals = df[col].dropna().unique()[:10]
        logger.info(f"  {col}: {list(unique_vals)}")
    
    # Compilar summary
    summary = {
        "nome_dataset": output_name,
        "total_registros": int(len(df)),
        "total_colunas": len(df.columns),
        "colunas": [col_info for col_info in columns_info],
        "tipos_resumo": {
            "numericos": int(df.select_dtypes(include=['number']).shape[1]),
            "texto": int(df.select_dtypes(include=['object']).shape[1]),
            "data": int(df.select_dtypes(include=['datetime64']).shape[1])
        },
        "qualidade": {
            "colunas_completas": int((df.notna().sum() == len(df)).sum()),
            "colunas_incompletas": int((df.notna().sum() < len(df)).sum()),
            "percentual_completude_media": round(
                (df.notna().sum().sum() / (len(df) * len(df.columns))) * 100, 2
            )
        }
    }
    
    logger.info(f"\n✅ Análise concluída para {output_name}")
    return summary

def main():
    """Executa análise de ambos os datasets"""
    
    logger.info("🚀 INICIANDO ANÁLISE DE DATASETS...\n")
    
    # Caminhos dos arquivos
    srag_path = Path("backend/data/datasets/surtos-srag/INFLUD26-18-05-2026.csv")
    ubs_path = Path("backend/data/datasets/atencao-basica/Unidades_Basicas_Saude-UBS.csv")
    
    # Verificar se arquivos existem
    if not srag_path.exists():
        logger.error(f"❌ Arquivo SRAG não encontrado: {srag_path}")
        return
    if not ubs_path.exists():
        logger.error(f"❌ Arquivo UBS não encontrado: {ubs_path}")
        return
    
    logger.info(f"✓ Arquivo SRAG encontrado: {srag_path}")
    logger.info(f"✓ Arquivo UBS encontrado: {ubs_path}\n")
    
    # Analisar SRAG
    logger.info("\n" + "="*80)
    logger.info("INICIANDO ANÁLISE: SRAG")
    logger.info("="*80 + "\n")
    summary_srag = analyze_dataset(
        str(srag_path),
        'SRAG - Síndrome Respiratória Aguda Grave (2019-2026)',
        encoding='latin-1'
    )
    
    # Analisar UBS
    logger.info("\n" + "="*80)
    logger.info("INICIANDO ANÁLISE: UBS")
    logger.info("="*80 + "\n")
    summary_ubs = analyze_dataset(
        str(ubs_path),
        'UBS - Unidades Básicas de Saúde',
        encoding='utf-8'
    )
    
    # Salvar summaries em JSON
    output_dir = Path("docs/experimentos")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if summary_srag:
        srag_json_path = output_dir / "analise-srag.json"
        with open(srag_json_path, 'w', encoding='utf-8') as f:
            json.dump(summary_srag, f, ensure_ascii=False, indent=2)
        logger.info(f"\n💾 Análise SRAG salva: {srag_json_path}")
    
    if summary_ubs:
        ubs_json_path = output_dir / "analise-ubs.json"
        with open(ubs_json_path, 'w', encoding='utf-8') as f:
            json.dump(summary_ubs, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Análise UBS salva: {ubs_json_path}")
    
    logger.info(f"\n{'='*80}")
    logger.info("✅ ANÁLISES CONCLUÍDAS COM SUCESSO!")
    logger.info(f"{'='*80}\n")

if __name__ == "__main__":
    main()
