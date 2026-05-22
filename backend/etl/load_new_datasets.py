#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para carregar dados SRAG e Atenção Básica no ClickHouse
Processa CSVs em chunks para otimizar memória
"""

import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
import sys

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from clickhouse_driver import Client
except ImportError:
    logger.error("❌ clickhouse-driver não instalado. Execute: pip install clickhouse-driver")
    sys.exit(1)


class ClickHouseLoader:
    """Carregador de dados para ClickHouse com suporte a chunks"""
    
    def __init__(self, host='localhost', port=9000, database='default', user='admin', password='admin'):
        """
        Inicializa conexão com ClickHouse
        
        Args:
            host: Endereço do servidor ClickHouse
            port: Porta do ClickHouse
            database: Banco de dados alvo
            user: Usuário ClickHouse
            password: Senha ClickHouse
        """
        try:
            self.client = Client(host, port=port, database=database, user=user, password=password)
            self.client.execute("SELECT 1")
            logger.info(f"✅ Conectado ao ClickHouse em {host}:{port}")
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao ClickHouse: {e}")
            raise
    
    def load_srag(self, csv_path, chunk_size=5000):
        """
        Carrega dados SRAG em chunks
        
        Args:
            csv_path: Caminho do arquivo CSV
            chunk_size: Tamanho de cada chunk para inserção
        
        Returns:
            int: Total de registros carregados
        """
        logger.info(f"\n{'='*80}")
        logger.info("📥 CARREGANDO SRAG")
        logger.info(f"{'='*80}")
        
        csv_path = Path(csv_path)
        if not csv_path.exists():
            logger.error(f"❌ Arquivo não encontrado: {csv_path}")
            return 0
        
        try:
            # Carregar dados
            logger.info(f"Lendo arquivo: {csv_path} (tamanho: {csv_path.stat().st_size / 1024 / 1024:.2f} MB)")
            df = pd.read_csv(csv_path, encoding='latin-1', sep=';', on_bad_lines='skip')
            logger.info(f"✓ Arquivo carregado: {len(df):,} registros lidos")
            
        except Exception as e:
            logger.error(f"❌ Erro ao ler CSV: {e}")
            return 0
        
        # Preparar dados
        df.columns = df.columns.str.lower()
        
        # Conversão de tipos
        logger.info("🔄 Preparando dados...")
        
        # Converter datas - usar data padrão (1900-01-01) para valores nulos
        from datetime import date as date_type
        default_date = date_type(1900, 1, 1)
        
        date_cols = ['dt_notific', 'dt_sin_pri', 'dt_nasc', 'dt_interna', 'dt_coleta', 'dt_evoluca']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                # Usar default_date para NaT
                df[col] = df[col].apply(lambda x: x.date() if pd.notna(x) else default_date)
        
        # Converter para Int32/Int64 valores inteiros - IMPORTANTE: usar fillna antes de astype
        # Int64: campos com números muito grandes (IDs de notificação)
        int64_cols = ['nu_notific']
        for col in int64_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(0)
                df[col] = df[col].astype('int64')
        
        # Int32: outros campos inteiros
        int32_cols = [col for col in df.columns if col.startswith(('co_', 'cs_', 'sem_', 'nu_idade')) or col in 
                   ['febre', 'tosse', 'garganta', 'dispneia', 'diarreia', 'vomito',
                    'cardiopati', 'diabetes', 'asma', 'pneumopati', 'imunodepre', 'renal',
                    'obesidade', 'hospital', 'uti', 'amostra', 'pcr_resul', 'pos_pcrflu',
                    'tp_flu_pcr', 'pcr_vsr', 'pcr_sars2', 'classi_fin', 'evolucao', 'vacina_cov']]
        
        for col in int32_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(0)
                # Converter para int32, mas limitar valores válidos
                df[col] = df[col].astype('int32')
        
        # Converter strings
        str_cols = ['sg_uf_not', 'cs_sexo']
        for col in str_cols:
            if col in df.columns:
                df[col] = df[col].astype(str)
        
        # Preparar columnas para inserção (apenas as que existem na tabela)
        columns = ['nu_notific', 'dt_notific', 'sem_not', 'dt_sin_pri', 'sg_uf_not', 'co_mun_not',
                   'cs_sexo', 'dt_nasc', 'nu_idade_n', 'febre', 'tosse', 'garganta', 'dispneia',
                   'diarreia', 'vomito', 'cardiopati', 'diabetes', 'asma', 'pneumopati',
                   'imunodepre', 'renal', 'obesidade', 'hospital', 'dt_interna', 'co_mu_inte',
                   'uti', 'amostra', 'dt_coleta', 'pcr_resul', 'pos_pcrflu', 'tp_flu_pcr',
                   'pcr_vsr', 'pcr_sars2', 'classi_fin', 'evolucao', 'dt_evoluca', 'vacina_cov']
        
        # Filtrar apenas colunas que existem no dataframe
        available_cols = [col for col in columns if col in df.columns]
        df_clean = df[available_cols]
        
        logger.info(f"✓ Usando {len(available_cols)} colunas para inserção")
        
        # Inserir em chunks
        total_inserted = 0
        num_chunks = (len(df_clean) + chunk_size - 1) // chunk_size
        
        logger.info(f"\n⏱️  Inserindo {len(df_clean):,} registros em {num_chunks} chunks de {chunk_size}...")
        
        for i in range(0, len(df_clean), chunk_size):
            chunk = df_clean.iloc[i:i+chunk_size]
            records = [tuple(row) for row in chunk.values]
            
            try:
                cols_str = ', '.join(available_cols)
                self.client.execute(f'INSERT INTO srag ({cols_str}) VALUES', records)
                total_inserted += len(records)
                
                pct = (total_inserted / len(df_clean)) * 100
                logger.info(f"  ✓ {total_inserted:,}/{len(df_clean):,} ({pct:.1f}%)")
                
            except Exception as e:
                logger.error(f"  ✗ Erro ao inserir chunk {i//chunk_size + 1}: {e}")
        
        logger.info(f"\n✅ SRAG: {total_inserted:,} registros inseridos com sucesso")
        return total_inserted
    
    def load_atencao_basica(self, csv_path, chunk_size=5000):
        """
        Carrega dados de Atenção Básica (UBS)
        
        Args:
            csv_path: Caminho do arquivo CSV
            chunk_size: Tamanho de cada chunk
        
        Returns:
            int: Total de registros carregados
        """
        logger.info(f"\n{'='*80}")
        logger.info("📥 CARREGANDO ATENÇÃO BÁSICA (UBS)")
        logger.info(f"{'='*80}")
        
        csv_path = Path(csv_path)
        if not csv_path.exists():
            logger.error(f"❌ Arquivo não encontrado: {csv_path}")
            return 0
        
        try:
            logger.info(f"Lendo arquivo: {csv_path} (tamanho: {csv_path.stat().st_size / 1024 / 1024:.2f} MB)")
            df = pd.read_csv(csv_path, encoding='utf-8', sep=';', on_bad_lines='skip')
            logger.info(f"✓ Arquivo carregado: {len(df):,} registros lidos")
            
        except Exception as e:
            logger.error(f"❌ Erro ao ler CSV: {e}")
            return 0
        
        # Preparar dados
        df.columns = df.columns.str.lower()
        
        logger.info("🔄 Preparando dados...")
        
        # Converter tipos
        df['cnes'] = pd.to_numeric(df['cnes'], errors='coerce').fillna(0).astype('int32')
        df['uf'] = pd.to_numeric(df['uf'], errors='coerce').fillna(0).astype('int32')
        df['ibge'] = pd.to_numeric(df['ibge'], errors='coerce').fillna(0).astype('int32')
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce').astype('float64')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce').astype('float64')
        
        # Strings
        df['nome'] = df['nome'].astype(str)
        df['logradouro'] = df['logradouro'].astype(str)
        df['bairro'] = df['bairro'].astype(str)
        
        columns = ['cnes', 'uf', 'ibge', 'nome', 'logradouro', 'bairro', 'latitude', 'longitude']
        available_cols = [col for col in columns if col in df.columns]
        df_clean = df[available_cols]
        
        logger.info(f"✓ Usando {len(available_cols)} colunas para inserção")
        
        # Inserir em chunks
        total_inserted = 0
        num_chunks = (len(df_clean) + chunk_size - 1) // chunk_size
        
        logger.info(f"\n⏱️  Inserindo {len(df_clean):,} registros em {num_chunks} chunks...")
        
        for i in range(0, len(df_clean), chunk_size):
            chunk = df_clean.iloc[i:i+chunk_size]
            records = [tuple(row) for row in chunk.values]
            
            try:
                cols_str = ', '.join(available_cols)
                self.client.execute(f'INSERT INTO atencao_basica ({cols_str}) VALUES', records)
                total_inserted += len(records)
                
                pct = (total_inserted / len(df_clean)) * 100
                logger.info(f"  ✓ {total_inserted:,}/{len(df_clean):,} ({pct:.1f}%)")
                
            except Exception as e:
                logger.error(f"  ✗ Erro ao inserir chunk {i//chunk_size + 1}: {e}")
        
        logger.info(f"\n✅ ATENÇÃO BÁSICA: {total_inserted:,} registros inseridos com sucesso")
        return total_inserted
    
    def verify_load(self):
        """
        Verifica se os dados foram carregados corretamente
        
        Returns:
            bool: True se ambas as tabelas têm dados
        """
        logger.info(f"\n{'='*80}")
        logger.info("📊 VERIFICAÇÃO DE CARREGAMENTO")
        logger.info(f"{'='*80}\n")
        
        try:
            srag_count = self.client.execute("SELECT COUNT(*) FROM srag")[0][0]
            ubs_count = self.client.execute("SELECT COUNT(*) FROM atencao_basica")[0][0]
            
            # Estatísticas adicionais
            srag_dates = self.client.execute(
                "SELECT MIN(dt_notific), MAX(dt_notific) FROM srag"
            )[0]
            
            ubs_ufs = self.client.execute(
                "SELECT COUNT(DISTINCT uf) FROM atencao_basica"
            )[0][0]
            
            logger.info(f"📈 SRAG:")
            logger.info(f"  • Total de registros: {srag_count:,}")
            logger.info(f"  • Período: {srag_dates[0]} a {srag_dates[1]}")
            logger.info(f"  • Hospitalizações: {self.client.execute('SELECT SUM(IF(hospital=1, 1, 0)) FROM srag')[0][0]:,}")
            logger.info(f"  • Óbitos: {self.client.execute('SELECT SUM(IF(evolucao=2, 1, 0)) FROM srag')[0][0]:,}")
            
            logger.info(f"\n🏥 ATENÇÃO BÁSICA:")
            logger.info(f"  • Total de UBS: {ubs_count:,}")
            logger.info(f"  • Estados cobertos: {ubs_ufs}")
            
            logger.info(f"\n{'='*80}")
            if srag_count > 0 and ubs_count > 0:
                logger.info("✅ CARREGAMENTO CONCLUÍDO COM SUCESSO!")
                logger.info(f"{'='*80}\n")
                return True
            else:
                logger.error("❌ Erro: Uma ou ambas as tabelas estão vazias!")
                logger.error(f"{'='*80}\n")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro na verificação: {e}")
            return False


def main():
    """Executa o carregamento completo"""
    logger.info("\n" + "="*80)
    logger.info("🚀 CARREGADOR DE DADOS - EASYDATASUS")
    logger.info("="*80 + "\n")
    
    # Caminhos dos arquivos
    srag_csv = Path("backend/data/datasets/surtos-srag/INFLUD26-18-05-2026.csv")
    ubs_csv = Path("backend/data/datasets/atencao-basica/Unidades_Basicas_Saude-UBS.csv")
    
    # Verificar arquivos
    if not srag_csv.exists():
        logger.error(f"❌ Arquivo SRAG não encontrado: {srag_csv}")
        return False
    
    if not ubs_csv.exists():
        logger.error(f"❌ Arquivo UBS não encontrado: {ubs_csv}")
        return False
    
    logger.info(f"✓ Arquivo SRAG: {srag_csv}")
    logger.info(f"✓ Arquivo UBS: {ubs_csv}\n")
    
    # Inicializar loader
    try:
        loader = ClickHouseLoader()
    except Exception as e:
        logger.error(f"❌ Não foi possível conectar ao ClickHouse: {e}")
        return False
    
    # Carregar dados
    srag_loaded = loader.load_srag(str(srag_csv))
    ubs_loaded = loader.load_atencao_basica(str(ubs_csv))
    
    # Verificar
    success = loader.verify_load()
    
    return success and srag_loaded > 0 and ubs_loaded > 0


if __name__ == '__main__':
    start_time = datetime.now()
    
    try:
        success = main()
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if success:
            logger.info(f"⏱️  Tempo total: {elapsed:.1f}s")
            sys.exit(0)
        else:
            logger.error("❌ Carregamento incompleto ou com erros!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Carregamento interrompido pelo usuário")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Erro não esperado: {e}")
        sys.exit(1)
