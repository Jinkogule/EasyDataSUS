#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Script para debugar carregamento SRAG"""

import pandas as pd
from clickhouse_driver import Client

csv_path = "backend/data/datasets/surtos-srag/INFLUD26-18-05-2026.csv"

# Ler dados
df = pd.read_csv(csv_path, encoding='latin-1', sep=';', on_bad_lines='skip', low_memory=False)
print(f"✓ {len(df):,} linhas lidas")

# Normalizar colunas
df.columns = df.columns.str.lower()

# Testar chunk maior
chunk = df.iloc[4000:4010].copy()
print(f"\n✓ Usando 10 linhas (índice 4000-4010) para teste")
print(f"  Tipo de todos os dados antes:")
for col in chunk.columns[:20]:
    print(f"    {col}: {chunk[col].dtype}")

# Datas
date_cols = ['dt_notific', 'dt_sin_pri', 'dt_nasc', 'dt_interna', 'dt_coleta', 'dt_evoluca']
for col in date_cols:
    if col in chunk.columns:
        chunk[col] = pd.to_datetime(chunk[col], errors='coerce')
        # Converter NaT para None (null no ClickHouse)
        chunk[col] = chunk[col].apply(lambda x: x.date() if pd.notna(x) else None)

# Converter para Int64 para nu_notific
int64_cols = ['nu_notific']
for col in int64_cols:
    if col in chunk.columns:
        chunk[col] = pd.to_numeric(chunk[col], errors='coerce')
        chunk[col] = chunk[col].fillna(0)
        chunk[col] = chunk[col].astype('int64')

# Inteiros outros
int32_cols = [col for col in chunk.columns if col.startswith(('co_', 'cs_', 'sem_', 'nu_idade')) or col in 
           ['febre', 'tosse', 'garganta', 'dispneia', 'diarreia', 'vomito',
            'cardiopati', 'diabetes', 'asma', 'pneumopati', 'imunodepre', 'renal',
            'obesidade', 'hospital', 'uti', 'amostra', 'pcr_resul', 'pos_pcrflu',
            'tp_flu_pcr', 'pcr_vsr', 'pcr_sars2', 'classi_fin', 'evolucao', 'vacina_cov']]

print(f"\n  Convertendo {len(int32_cols)} colunas para int32...")
for col in int32_cols:
    if col in chunk.columns:
        chunk[col] = pd.to_numeric(chunk[col], errors='coerce')
        chunk[col] = chunk[col].fillna(0)
        chunk[col] = chunk[col].astype('int32')

# Strings
str_cols = ['sg_uf_not', 'cs_sexo']
for col in str_cols:
    if col in chunk.columns:
        chunk[col] = chunk[col].astype(str)

# Preparar 37 colunas conforme no loader
columns = ['nu_notific', 'dt_notific', 'sem_not', 'dt_sin_pri', 'sg_uf_not', 'co_mun_not',
           'cs_sexo', 'dt_nasc', 'nu_idade_n', 'febre', 'tosse', 'garganta', 'dispneia',
           'diarreia', 'vomito', 'cardiopati', 'diabetes', 'asma', 'pneumopati',
           'imunodepre', 'renal', 'obesidade', 'hospital', 'dt_interna', 'co_mu_inte',
           'uti', 'amostra', 'dt_coleta', 'pcr_resul', 'pos_pcrflu', 'tp_flu_pcr',
           'pcr_vsr', 'pcr_sars2', 'classi_fin', 'evolucao', 'dt_evoluca', 'vacina_cov']
available_cols = [col for col in columns if col in chunk.columns]
chunk_clean = chunk[available_cols]

print(f"\n✓ Dtypes depois de conversão (primeiros 10):")
for col in available_cols[:10]:
    print(f"  {col}: {chunk_clean[col].dtype}")

# Criar tuples
print(f"\n✓ Criando tuplas...")
try:
    records = [tuple(row) for row in chunk_clean.values]
    print(f"✅ {len(records)} tuplas criadas com sucesso")
    print(f"  Primeira tupla: {records[0]}")
except Exception as e:
    print(f"❌ Erro ao criar tuplas: {e}")
    exit(1)

# Testar inserção
print(f"\n✓ Testando inserção no ClickHouse...")
client = Client('localhost', port=9000, user='admin', password='admin')
cols_str = ', '.join(available_cols)
try:
    client.execute(f'INSERT INTO srag ({cols_str}) VALUES', records)
    print(f"✅ Inserção bem-sucedida!")
except Exception as e:
    print(f"❌ Erro na inserção: {e}")
    import traceback
    traceback.print_exc()
