#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple test to verify data is loaded correctly
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from clickhouse_connect import get_client

client = get_client(host='localhost', port=8123, username='admin', password='admin')

# Test 1: Check if table exists
print("\n[TEST 1] Checking if 'vacinacao' table exists...")
try:
    result = client.query("SELECT count() FROM vacinacao")
    total = result.result_rows[0][0] if result.result_rows else 0
    print(f"✅ Table exists with {total:,} records")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Test 2: Sample query - count by state
print("\n[TEST 2] Counting vaccines by state (first 10)...")
try:
    result = client.query("""
        SELECT 
            paciente_endereco_uf as state,
            count() as count
        FROM vacinacao
        GROUP BY state
        ORDER BY count DESC
        LIMIT 10
    """)
    print(f"✅ Results:")
    for row in result.result_rows:
        print(f"   {row[0]}: {row[1]:,}")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Test 3: Specific query - SP vaccines
print("\n[TEST 3] Counting vaccines applied in SP...")
try:
    result = client.query("""
        SELECT count() FROM vacinacao
        WHERE paciente_endereco_uf = 'SP'
    """)
    sp_count = result.result_rows[0][0] if result.result_rows else 0
    print(f"✅ SP has {sp_count:,} vaccine records")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

print("\n✅ ALL TESTS PASSED!\n")
