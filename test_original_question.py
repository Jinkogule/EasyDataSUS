#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test the original question directly without LLM
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from clickhouse_connect import get_client

client = get_client(host='localhost', port=8123, username='admin', password='admin')

print("\n" + "="*80)
print("🧪 TESTE: Quantas vacinas foram aplicadas em SP?")
print("="*80 + "\n")

# Direct query
sql = """
    SELECT count() as total_vacinas
    FROM vacinacao
    WHERE paciente_endereco_uf = 'SP'
"""

print(f"[SQL]\n{sql}\n")

try:
    result = client.query(sql)
    if result.result_rows:
        total = result.result_rows[0][0]
        print(f"[RESULTADO]")
        print(f"✅ Total de vacinas aplicadas em SP: {total:,}")
    else:
        print("❌ No results")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

print("\n" + "="*80)
print("✅ QUERY FUNCIONA CORRETAMENTE!")
print("="*80 + "\n")
