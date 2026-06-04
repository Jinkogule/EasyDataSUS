#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script para validar que a pergunta original funciona
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from services.sql_service import generate_sql
from db.clickhouse import run_query
from services.interpretation_service import interpret_result
from metadata.loader import load_metadata
import json

# Teste da pergunta original
question = "Quantas vacinas foram aplicadas em SP?"
dataset = "covid-19-vacinacao"
model = "deepseek-local"

print(f"\n{'='*80}")
print(f"🧪 TESTE: {question}")
print(f"{'='*80}\n")

# 1. Carregar metadata
print(f"[1/4] Carregando metadata do dataset '{dataset}'...")
try:
    metadata = load_metadata(dataset)
    if isinstance(metadata, dict):
        metadata = json.dumps(metadata, ensure_ascii=False)
    print(f"✅ Metadata carregada")
except Exception as e:
    print(f"❌ Erro: {e}")
    sys.exit(1)

# 2. Gerar SQL
print(f"\n[2/4] Gerando SQL via LLM '{model}'...")
try:
    sql = generate_sql(question, metadata, model, dataset)
    if not sql:
        print(f"❌ Nenhum SQL foi gerado")
        sys.exit(1)
    print(f"✅ SQL gerado:\n")
    print(f"   {sql}\n")
except Exception as e:
    print(f"❌ Erro: {e}")
    sys.exit(1)

# 3. Executar query
print(f"[3/4] Executando query no ClickHouse...")
try:
    result = run_query(sql)
    if isinstance(result, dict) and "error" in result:
        print(f"❌ Erro no ClickHouse: {result['error']}")
        sys.exit(1)
    
    if isinstance(result, list):
        print(f"✅ Query executada")
        print(f"   Resultado: {len(result)} linhas")
        if result:
            print(f"   Primeira linha: {result[0]}")
    else:
        print(f"✅ Query executada")
        print(f"   Resultado: {result}\n")
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Interpretar resultado
print(f"\n[4/4] Interpretando resultado...")
try:
    interpretation = interpret_result(question, result, model, dataset)
    if isinstance(interpretation, dict):
        if "error" in interpretation:
            print(f"⚠️  Aviso na interpretação: {interpretation.get('error')}")
        else:
            print(f"✅ Interpretação:")
            print(f"   {interpretation.get('insight', str(interpretation))}")
    else:
        print(f"✅ Interpretação:")
        print(f"   {interpretation}")
except Exception as e:
    print(f"⚠️  Erro na interpretação: {e}")

print(f"\n{'='*80}")
print(f"✅ TESTE CONCLUÍDO COM SUCESSO!")
print(f"{'='*80}\n")
