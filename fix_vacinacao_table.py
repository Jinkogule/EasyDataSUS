#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para criar a tabela 'vacinacao' (compatível com init.sql original)
e criar alias para 'covid_vacinacao'
"""

import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from db.clickhouse import get_client

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client = get_client()

logger.info("Criando tabela 'vacinacao' (compatível com init.sql)...")
try:
    client.query("""
    CREATE TABLE IF NOT EXISTS vacinacao (
        document_id String,
        paciente_id String,
        paciente_idade Int32,
        paciente_dataNascimento Nullable(Date),
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

logger.info("\nCriando view 'covid_vacinacao' como alias para 'vacinacao'...")
try:
    client.query("DROP VIEW IF EXISTS covid_vacinacao;")
    client.query("CREATE VIEW covid_vacinacao AS SELECT * FROM vacinacao;")
    logger.info("✅ View 'covid_vacinacao' criada (aponta para 'vacinacao')")
except Exception as e:
    logger.error(f"❌ Erro ao criar view: {e}")

logger.info("\nVerificando tabelas...")
result = client.query("SHOW TABLES").result_rows
tables = [r[0] for r in result]
logger.info(f"Tabelas: {', '.join(tables)}")

if 'vacinacao' in tables:
    logger.info("✅ 'vacinacao' existe")
if 'covid_vacinacao' in tables:
    logger.info("✅ 'covid_vacinacao' (view) existe")
