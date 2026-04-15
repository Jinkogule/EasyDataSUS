#!/usr/bin/env python3
"""Teste rápido para verificar se o SQL para leitos agora usa SUM em vez de COUNT"""

import sys
sys.path.insert(0, 'backend')

from services.sql_service import generate_sql
from config.datasets import get_dataset_config
import json

# Carregar metadata do dataset leitos
metadata_file = "backend/metadata/datasets/leitos/schema.json"

with open(metadata_file, 'r', encoding='utf-8') as f:
    metadata_json = f.read()

# Testar SQL generation
question = "Qual estado tem mais leitos de UTI adulto?"
print(f"Pergunta: {question}")
print()
print("="*80)

# Gerar SQL com o modelo deepseek-local
sql = generate_sql(question, metadata_json, "deepseek-local", "leitos")

if sql:
    print("SQL GERADO:")
    print(sql)
    print()
    
    # Verificar se usa SUM ou COUNT
    if "SUM(" in sql.upper():
        print("[CORRETO] SQL usa SUM()")
    else:
        print("[ERRADO] SQL nao usa SUM()")
    
    if "COUNT(*)" in sql.upper():
        print("[ERRADO] SQL usa COUNT(*) quando deveria usar SUM()")
    else:
        print("[OK] SQL nao usa COUNT(*)")
    
    if "UTI_ADULTO" in sql.upper():
        print("[CORRETO] SQL menciona UTI_ADULTO")
    else:
        print("[AVISO] SQL nao menciona UTI_ADULTO especificamente")
        
else:
    print("ERRO: Nao conseguiu gerar SQL")
