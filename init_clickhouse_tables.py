#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para recriar todas as tabelas do ClickHouse com os nomes corretos.
Este script resolve o problema de tabelas faltando após restart do container.

Uso:
    python init_clickhouse_tables.py
"""

import sys
from pathlib import Path
import logging
import os

import clickhouse_connect
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / "backend"))

load_dotenv(Path(__file__).parent / "backend" / ".env")


def get_admin_client():
    """Cliente administrativo usado exclusivamente para criar o schema."""
    return clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
        username=os.getenv("CLICKHOUSE_ADMIN_USER", "easydatasus_admin"),
        password=os.getenv("CLICKHOUSE_ADMIN_PASSWORD", "easydatasus_admin"),
        database=os.getenv("CLICKHOUSE_DATABASE", "default"),
        connect_timeout=10,
    )

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_tables():
    """Create all required tables in ClickHouse"""
    
    logger.info("Conectando ao ClickHouse...")
    try:
        client = get_admin_client()
    except Exception as e:
        logger.error(f"Erro ao conectar: {e}")
        return False
    
    tables_sql = [
        # ========== 1. COVID-19 VACINAÇÃO ==========
        ("""
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
        """, "vacinacao"),
        
        # ========== 2. LEITOS ==========
        ("""
        CREATE TABLE IF NOT EXISTS leitos (
            COMP String,
            REGIAO String,
            UF String,
            CO_IBGE String,
            MUNICIPIO String,
            MOTIVO_DESABILITACAO String,
            CNES String,
            NOME_ESTABELECIMENTO String,
            RAZAO_SOCIAL String,
            TP_GESTAO String,
            CO_TIPO_UNIDADE String,
            DS_TIPO_UNIDADE String,
            NATUREZA_JURIDICA String,
            DESC_NATUREZA_JURIDICA String,
            NO_LOGRADOURO String,
            NU_ENDERECO String,
            NO_COMPLEMENTO String,
            NO_BAIRRO String,
            CO_CEP String,
            NU_TELEFONE String,
            NO_EMAIL String,
            LEITOS_EXISTENTES Int32,
            LEITOS_SUS Int32,
            UTI_TOTAL_EXIST Int32,
            UTI_TOTAL_SUS Int32,
            UTI_ADULTO_EXIST Int32,
            UTI_ADULTO_SUS Int32,
            UTI_PEDIATRICO_EXIST Int32,
            UTI_PEDIATRICO_SUS Int32,
            UTI_NEONATAL_EXIST Int32,
            UTI_NEONATAL_SUS Int32,
            UTI_CORONARIANA_EXIST Int32,
            UTI_CORONARIANA_SUS Int32,
            UTI_QUEIMADO_EXIST Int32,
            UTI_QUEIMADO_SUS Int32
        ) ENGINE = MergeTree()
        ORDER BY (UF, MUNICIPIO, CNES);
        """, "leitos"),
        
        # ========== 3. SRAG ==========
        ("""
        CREATE TABLE IF NOT EXISTS srag (
            nu_notific Int64,
            dt_notific Date,
            sem_not Int32,
            sem_pri Nullable(Int32),
            dt_sin_pri Nullable(Date),
            sg_uf_not String,
            sg_uf Nullable(String),
            co_mun_not Int32,
            co_mun_res Nullable(Int32),
            nu_idade_n Nullable(Int32),
            tp_idade Nullable(Int32),
            cs_sexo Nullable(String),
            dt_nasc Nullable(Date),
            id_municip Int32,
            co_regiao Int32,
            classi_fin Int32,
            evolucao Int32,
            dt_evoluca Nullable(Date),
            dt_interna Nullable(Date),
            co_mu_inte Nullable(Int32),
            dt_encerra Nullable(Date),
            dt_digita Nullable(Date),
            dt_notif Nullable(Date),
            febre Int32,
            tosse Int32,
            garganta Int32,
            dispneia Int32,
            desc_resp Int32,
            saturacao Int32,
            diarreia Int32,
            vomito Int32,
            outro_sin Int32,
            cardiopati Int32,
            hematologi Int32,
            hepatica Int32,
            asma Int32,
            diabetes Int32,
            neurologic Int32,
            pneumopati Int32,
            imunodepre Int32,
            renal Int32,
            obesidade Int32,
            hospital Int32,
            uti Int32,
            amostra Nullable(Int32),
            dt_coleta Nullable(Date),
            suport_ven Int32,
            ventilatad Int32,
            antiviral Int32,
            antibiotico Int32,
            antitromb Int32,
            corticoide Int32,
            outro_medic Int32,
            pcr_sars2 Int32,
            pos_pcrflu Int32,
            tp_flu_pcr Nullable(Int32),
            pcr_vsr Int32,
            pcr_para Int32,
            pcr_outro Int32,
            pcr_resul Int32,
            vacina_cov Nullable(Int32),
            dose_1_cov Nullable(Date),
            dose_2_cov Nullable(Date)
        ) ENGINE = MergeTree()
        ORDER BY (dt_notific, sg_uf_not, co_mun_not)
        PARTITION BY toYYYYMM(dt_notific);
        """, "srag"),
        
        # ========== 4. ATENÇÃO BÁSICA (UBS) ==========
        ("""
        CREATE TABLE IF NOT EXISTS atencao_basica (
            cnes Int32,
            uf String,
            ibge Int32,
            nome String,
            logradouro String,
            bairro String,
            latitude Float64,
            longitude Float64
        ) ENGINE = MergeTree()
        ORDER BY (ibge, cnes)
        PARTITION BY uf;
        """, "atencao_basica"),
    ]
    
    # Criar tabelas
    logger.info("\n" + "="*80)
    logger.info("CRIANDO TABELAS")
    logger.info("="*80 + "\n")
    
    for sql, table_name in tables_sql:
        try:
            logger.info(f"Criando {table_name}...")
            client.query(sql)
            logger.info(f"✅ {table_name} criada com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao criar {table_name}: {e}")
            return False
    
    # Criar índices
    logger.info("\n" + "="*80)
    logger.info("CRIANDO ÍNDICES")
    logger.info("="*80 + "\n")
    
    indexes = [
        ("ALTER TABLE vacinacao ADD INDEX idx_uf paciente_endereco_uf TYPE set(0);", "vacinacao.idx_uf"),
        ("ALTER TABLE vacinacao ADD INDEX idx_municipio paciente_endereco_nmMunicipio TYPE set(0);", "vacinacao.idx_municipio"),
        ("ALTER TABLE vacinacao ADD INDEX idx_data vacina_dataAplicacao TYPE set(0);", "vacinacao.idx_data"),
        ("ALTER TABLE vacinacao ADD INDEX idx_vacina vacina_nome TYPE set(0);", "vacinacao.idx_vacina"),
        ("ALTER TABLE leitos ADD INDEX idx_uf UF TYPE set(0);", "leitos.idx_uf"),
        ("ALTER TABLE leitos ADD INDEX idx_municipio MUNICIPIO TYPE set(0);", "leitos.idx_municipio"),
        ("ALTER TABLE leitos ADD INDEX idx_tipo DS_TIPO_UNIDADE TYPE set(0);", "leitos.idx_tipo"),
        ("ALTER TABLE leitos ADD INDEX idx_gestao TP_GESTAO TYPE set(0);", "leitos.idx_gestao"),
        ("ALTER TABLE srag ADD INDEX idx_srag_uf sg_uf_not TYPE set(0);", "srag.idx_uf"),
        ("ALTER TABLE srag ADD INDEX idx_srag_municipio co_mun_not TYPE set(0);", "srag.idx_municipio"),
        ("ALTER TABLE srag ADD INDEX idx_srag_hospital hospital TYPE set(0);", "srag.idx_hospital"),
        ("ALTER TABLE srag ADD INDEX idx_srag_evolucao evolucao TYPE set(0);", "srag.idx_evolucao"),
        ("ALTER TABLE srag ADD INDEX idx_srag_classi classi_fin TYPE set(0);", "srag.idx_classi"),
        ("ALTER TABLE srag ADD INDEX idx_srag_pcr pcr_sars2 TYPE set(0);", "srag.idx_pcr"),
        ("ALTER TABLE atencao_basica ADD INDEX idx_ubs_uf uf TYPE set(0);", "atencao_basica.idx_uf"),
        ("ALTER TABLE atencao_basica ADD INDEX idx_ubs_ibge ibge TYPE set(0);", "atencao_basica.idx_ibge"),
        ("ALTER TABLE atencao_basica ADD INDEX idx_ubs_cnes cnes TYPE set(0);", "atencao_basica.idx_cnes"),
    ]
    
    for sql, idx_name in indexes:
        try:
            logger.info(f"Criando {idx_name}...")
            client.query(sql)
            logger.info(f"✅ {idx_name} criado")
        except Exception as e:
            # Índices podem já existir, não é erro fatal
            logger.warning(f"⚠️  {idx_name}: {str(e)[:50]}...")
    
    # Verificar tabelas
    logger.info("\n" + "="*80)
    logger.info("VERIFICAÇÃO DE TABELAS CRIADAS")
    logger.info("="*80 + "\n")
    
    try:
        result = client.query("SHOW TABLES")
        tables = [r[0] for r in result.result_rows]
        logger.info(f"Tabelas no banco: {', '.join(tables)}\n")
        
        for table_name in ['vacinacao', 'leitos', 'srag', 'atencao_basica']:
            if table_name in tables:
                logger.info(f"✅ {table_name} existe")
            else:
                logger.error(f"❌ {table_name} NÃO foi criada!")
                return False
    except Exception as e:
        logger.error(f"Erro ao verificar tabelas: {e}")
        return False
    
    logger.info("\n" + "="*80)
    logger.info("✅ TODAS AS TABELAS CRIADAS COM SUCESSO!")
    logger.info("="*80 + "\n")
    
    return True


if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)
