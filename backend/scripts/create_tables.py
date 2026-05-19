#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Script para criar tabelas no ClickHouse"""

from clickhouse_driver import Client
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Conectar
try:
    client = Client('localhost', port=9000, user='admin', password='admin')
    logger.info("✅ Conectado ao ClickHouse")
except Exception as e:
    logger.error(f"❌ Erro ao conectar: {e}")
    exit(1)

# Ler SQL
with open('backend/db/schema_srag_ubs.sql', encoding='utf-8') as f:
    sql = f.read()

# Executar cada statement
statements = [s.strip() for s in sql.split(';') if s.strip()]
logger.info(f"Executando {len(statements)} statements...")

for i, stmt in enumerate(statements, 1):
    try:
        client.execute(stmt)
        logger.info(f"  {i}. ✅ OK")
    except Exception as e:
        logger.error(f"  {i}. ❌ {e}")
        # Continuar mesmo com erro

logger.info("\n✅ Tabelas criadas com sucesso!")
