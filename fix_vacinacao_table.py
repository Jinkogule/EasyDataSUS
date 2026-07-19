#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para criar a tabela canônica 'vacinacao'.
"""

import sys
from pathlib import Path
import logging
import os

import clickhouse_connect
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / "backend"))

load_dotenv(Path(__file__).parent / "backend" / ".env")

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client = clickhouse_connect.get_client(
    host=os.getenv("CLICKHOUSE_HOST", "localhost"),
    port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
    username=os.getenv("CLICKHOUSE_ADMIN_USER", "easydatasus_admin"),
    password=os.getenv("CLICKHOUSE_ADMIN_PASSWORD", "easydatasus_admin"),
    database=os.getenv("CLICKHOUSE_DATABASE", "default"),
)

logger.info("Criando tabela 'vacinacao' (compatível com init.sql)...")
try:
    client.query("""
    CREATE TABLE IF NOT EXISTS vacinacao (
        document_id String,
        paciente_id String,
        paciente_idade Int32,
        paciente_dataNascimento Nullable(Date32),
        paciente_enumSexoBiologico Nullable(String),
        paciente_racaCor_codigo Nullable(String),
        paciente_racaCor_valor Nullable(String),
        paciente_endereco_coIbgeMunicipio Nullable(String),
        paciente_endereco_coPais Nullable(String),
        paciente_endereco_nmMunicipio Nullable(String),
        paciente_endereco_nmPais Nullable(String),
        paciente_endereco_uf String,
        paciente_endereco_cep Nullable(String),
        paciente_nacionalidade_enumNacionalidade Nullable(String),
        estabelecimento_valor Nullable(String),
        estabelecimento_razaoSocial Nullable(String),
        estalecimento_noFantasia Nullable(String),
        estabelecimento_municipio_codigo Nullable(String),
        estabelecimento_municipio_nome Nullable(String),
        estabelecimento_uf Nullable(String),
        vacina_grupoAtendimento_codigo Nullable(String),
        vacina_grupoAtendimento_nome Nullable(String),
        vacina_categoria_codigo Nullable(String),
        vacina_categoria_nome Nullable(String),
        vacina_lote Nullable(String),
        vacina_fabricante_nome Nullable(String),
        vacina_fabricante_referencia Nullable(String),
        vacina_dataAplicacao Nullable(Date),
        vacina_descricao_dose Nullable(String),
        vacina_codigo Nullable(String),
        vacina_nome Nullable(String),
        sistema_origem Nullable(String)
    ) ENGINE = MergeTree()
    ORDER BY (paciente_endereco_uf, paciente_id)
    PARTITION BY toYYYYMM(vacina_dataAplicacao);
    """)
    logger.info("✅ Tabela 'vacinacao' criada")
except Exception as e:
    logger.warning(f"⚠️  Tabela 'vacinacao' já existe: {str(e)[:50]}")

logger.info("\nVerificando tabelas...")
result = client.query("SHOW TABLES").result_rows
tables = [r[0] for r in result]
logger.info(f"Tabelas: {', '.join(tables)}")

if 'vacinacao' in tables:
    logger.info("✅ 'vacinacao' existe")
