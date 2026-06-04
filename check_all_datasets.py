#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Check all datasets
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from clickhouse_connect import get_client

client = get_client(host='localhost', port=8123, username='admin', password='admin')

datasets = [
    ('vacinacao', 'COVID-19 Vaccination'),
    ('srag', 'SRAG - Respiratory Syndrome'),
    ('atencao_basica', 'Primary Care (UBS)'),
    ('leitos', 'Hospital Beds'),
]

print("\n" + "="*80)
print("📊 CHECKING ALL DATASETS")
print("="*80 + "\n")

for table, desc in datasets:
    try:
        result = client.query(f"SELECT count() FROM {table}")
        count = result.result_rows[0][0] if result.result_rows else 0
        status = "✅" if count > 0 else "❌"
        print(f"{status} {table:20} ({desc:30}): {count:,} records")
    except Exception as e:
        print(f"❌ {table:20} ({desc:30}): ERROR - {str(e)[:40]}")

print("\n" + "="*80 + "\n")
