import csv
import logging
import sys
from datetime import datetime
from pathlib import Path
import subprocess

# Adicionar diretório parent (backend/) ao path para permitir imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import clickhouse_connect
from config.datasets import get_table_name

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_clickhouse_client():
    """Conecta ao ClickHouse"""
    try:
        logger.info("Conectando ao ClickHouse...")
        client = clickhouse_connect.get_client(
            host="localhost",
            port=8123,
            username="admin",
            password="admin",
            database="default"
        )
        logger.info("Conectado ao ClickHouse")
        return client
    except Exception as e:
        logger.error(f"Erro ao conectar ao ClickHouse: {e}")
        sys.exit(1)

def table_exists(client, dataset: str = "covid-19-vacinacao"):
    """
    Verifica se tabela do dataset existe no ClickHouse.
    
    Args:
        client: Cliente ClickHouse
        dataset: Dataset a verificar (padrão: "covid-19-vacinacao")
    
    Returns:
        True se tabela existe, False caso contrário
    """
    try:
        table_name = get_table_name(dataset)
        result = client.query(f"SELECT 1 FROM {table_name} LIMIT 1")
        return True
    except Exception:
        return False

def load_csv(csv_path: str = None, dataset: str = "covid-19-vacinacao"):
    """
    Carrega CSV(s) para ClickHouse usando TSV format.
    Suporta múltiplos arquivos na mesma pasta!
    
    Args:
        csv_path (str): Caminho completo de um arquivo CSV.
                       Se None, carrega TODOS os CSVs em data/datasets/{dataset}/
        dataset (str): Nome do dataset. Padrão: "covid-19-vacinacao"
                      Exemplos: "covid-19-vacinacao", "dengue-2024", "influenza-2025"
    
    Estrutura esperada de dados (suporta múltiplos CSVs):
        data/
        └── datasets/
            ├── covid-19-vacinacao/
            │   ├── vacinacao-ac-es.csv
            │   ├── vacinacao-sp-mg.csv
            │   └── vacinacao-rs.csv
            ├── dengue-2024/
            │   ├── dengue-ac-es.csv
            │   └── dengue-sp-rj.csv
            └── influenza-2025/
                └── influenza-ac-es.csv
    
    Uso:
        load_csv()  # Carrega TODOS os CSVs em covid-19-vacinacao/
        load_csv(dataset="dengue-2024")  # Carrega TODOS em dengue-2024/
        load_csv("/path/to/custom.csv", "custom")  # Carrega apenas esse arquivo
    """
    csv_files = []
    
    if csv_path is None:
        # Usar estrutura padrão de datasets - CARREGAR TODOS OS CSVs
        base_path = Path(__file__).parent.parent / "data" / "datasets" / dataset
        csv_files = sorted(list(base_path.glob("*.csv")))
        if not csv_files:
            logger.error(f"Nenhum arquivo CSV encontrado em {base_path}")
            sys.exit(1)
        logger.info(f"Encontrados {len(csv_files)} arquivo(s) CSV no dataset '{dataset}':")
        for f in csv_files:
            logger.info(f"   • {f.name}")
    else:
        # Arquivo customizado específico
        custom_file = Path(csv_path)
        if not custom_file.exists():
            logger.error(f"Arquivo não encontrado: {csv_path}")
            sys.exit(1)
        csv_files = [custom_file]
    
    client = get_clickhouse_client()
    
    # FIXO: Obter nome da tabela dinamicamente
    try:
        table_name = get_table_name(dataset)
    except ValueError as e:
        logger.error(f"Dataset error - {e}")
        sys.exit(1)
    
    # FIXO: Verificar se tabela existe (usando tabela dinâmica)
    if not table_exists(client, dataset):
        logger.error(f"Table error - Table '{table_name}' não existe. Execute o init.sql primeiro.")
        sys.exit(1)
    
    # FIXO: Limpar dados antigos quando carregando múltiplos arquivos (tabela dinâmica)
    if len(csv_files) > 1 or csv_path is None:
        logger.info("Limpando dados antigos da tabela...")
        try:
            client.command(f"TRUNCATE TABLE {table_name}")
            logger.info("Tabela limpa - pronta para novos dados")
        except Exception as e:
            logger.warning(f"Não conseguiu limpar tabela (pode estar vazia): {e}")
    
    # ========================================================================
    # CARREGAR TODOS OS ARQUIVOS
    # ========================================================================
    total_rows_all = 0
    total_errors_all = 0
    
    try:
        for file_idx, csv_file in enumerate(csv_files, 1):
            logger.info(f"\n[{file_idx}/{len(csv_files)}] Carregando: {csv_file.name}")
            
            # Ler CSV e converter para TSV
            logger.info("Convertendo CSV para TSV...")
            tsv_lines = []
            row_count = 0
            error_count = 0
            
            with open(csv_file, encoding="utf-8") as f:
                # Ler como CSV com delimitador ;
                reader = csv.DictReader(f, delimiter=";")
                
                # Header order para ClickHouse
                headers = [
                    "document_id", "paciente_id", "paciente_idade", "paciente_dataNascimento",
                    "paciente_enumSexoBiologico", "paciente_racaCor_codigo", "paciente_racaCor_valor",
                    "paciente_endereco_coIbgeMunicipio", "paciente_endereco_coPais",
                    "paciente_endereco_nmMunicipio", "paciente_endereco_nmPais",
                    "paciente_endereco_uf", "paciente_endereco_cep",
                    "paciente_nacionalidade_enumNacionalidade", "estabelecimento_valor",
                    "estabelecimento_razaoSocial", "estalecimento_noFantasia",
                    "estabelecimento_municipio_codigo", "estabelecimento_municipio_nome",
                    "estabelecimento_uf", "vacina_grupoAtendimento_codigo",
                    "vacina_grupoAtendimento_nome", "vacina_categoria_codigo",
                    "vacina_categoria_nome", "vacina_lote", "vacina_fabricante_nome",
                    "vacina_fabricante_referencia", "vacina_dataAplicacao",
                    "vacina_descricao_dose", "vacina_codigo", "vacina_nome", "sistema_origem"
                ]
                
                for idx, r in enumerate(reader, 1):
                    try:
                        # Processar cada field
                        row = []
                        
                        row.append(r.get("document_id") or "UNKNOWN")
                        row.append(r.get("paciente_id") or "UNKNOWN")
                        
                        # Idade - inteiro
                        try:
                            row.append(int(r.get("paciente_idade", 0) or 0))
                        except:
                            row.append(0)
                        
                        # Data Nascimento
                        data_nasc = r.get("paciente_dataNascimento", "").strip()
                        if data_nasc and len(data_nasc) >= 10:
                            row.append(data_nasc[:10])  # YYYY-MM-DD
                        else:
                            row.append("1900-01-01")
                        
                        row.append(r.get("paciente_enumSexoBiologico") or "")
                        row.append(r.get("paciente_racaCor_codigo") or "")
                        row.append(r.get("paciente_racaCor_valor") or "")
                        row.append(r.get("paciente_endereco_coIbgeMunicipio") or "")
                        row.append(r.get("paciente_endereco_coPais") or "")
                        row.append(r.get("paciente_endereco_nmMunicipio") or "")
                        row.append(r.get("paciente_endereco_nmPais") or "")
                        
                        # UF - com fallback
                        uf = r.get("paciente_endereco_uf") or r.get("estabelecimento_uf") or "XX"
                        row.append(uf)
                        
                        row.append(r.get("paciente_endereco_cep") or "")
                        row.append(r.get("paciente_nacionalidade_enumNacionalidade") or "")
                        row.append(r.get("estabelecimento_valor") or "")
                        row.append(r.get("estabelecimento_razaoSocial") or "")
                        row.append(r.get("estalecimento_noFantasia") or "")
                        row.append(r.get("estabelecimento_municipio_codigo") or "")
                        row.append(r.get("estabelecimento_municipio_nome") or "")
                        row.append(r.get("estabelecimento_uf") or "")
                        row.append(r.get("vacina_grupoAtendimento_codigo") or "")
                        row.append(r.get("vacina_grupoAtendimento_nome") or "")
                        row.append(r.get("vacina_categoria_codigo") or "")
                        row.append(r.get("vacina_categoria_nome") or "")
                        row.append(r.get("vacina_lote") or "")
                        row.append(r.get("vacina_fabricante_nome") or "")
                        row.append(r.get("vacina_fabricante_referencia") or "")
                        
                        # Data Aplicação
                        data_aplic = r.get("vacina_dataAplicacao", "").strip()
                        if data_aplic and len(data_aplic) >= 10:
                            row.append(data_aplic[:10])  # YYYY-MM-DD
                        else:
                            row.append("1900-01-01")
                        
                        row.append(r.get("vacina_descricao_dose") or "")
                        row.append(r.get("vacina_codigo") or "")
                        row.append(r.get("vacina_nome") or "")
                        row.append(r.get("sistema_origem") or "")
                        
                        # Adicionar linha com LF (não CRLF)
                        tsv_lines.append("\t".join(str(f) for f in row))
                        row_count += 1
                        
                        if idx % 10000 == 0:
                            logger.info(f"  {idx} linhas lidas... ({row_count} parsed)")
                    
                    except Exception as e:
                        error_count += 1
                        if error_count <= 5:
                            logger.warning(f"Erro na linha {idx}: {e}")
            
            logger.info(f"CSV convertido: {row_count} linhas válidas, {error_count} erros")
            total_rows_all += row_count
            total_errors_all += error_count
            
            if row_count == 0:
                logger.warning(f"Nenhuma linha válida em {csv_file.name} - pulando arquivo")
                continue
            
            # Juntar linhas com apenas LF (Unix line ending)
            tsv_content = "\n".join(tsv_lines) + "\n"
            
            # Usar pipe direto para stdin com encoding UTF-8
            cmd = [
                'docker', 'exec', '-i', 'easydatasus-clickhouse', 
                'clickhouse-client', '-u', 'admin', '--password', 'admin', 
                '-d', 'default', 
                '-q', f'INSERT INTO {table_name} FORMAT TSV'
            ]
            
            logger.info(f"Executando INSERT para {csv_file.name}...")
            # Converter conteúdo para bytes em UTF-8 e enviar
            result = subprocess.run(
                cmd, 
                input=tsv_content.encode('utf-8'),  # Enviar como bytes UTF-8
                capture_output=True
            )
            
            if result.returncode != 0:
                stderr = result.stderr.decode('utf-8', errors='replace')
                logger.error(f"Erro no INSERT para {csv_file.name}: {stderr}")
                sys.exit(1)
            
            stdout = result.stdout.decode('utf-8', errors='replace')
            if stdout:
                logger.info(f"{stdout.strip()}")
            
            logger.info(f"{csv_file.name} carregado com sucesso ({row_count} registros)")
        
        # ========================================================================
        # ESTATÍSTICAS FINAIS (CONSOLIDADAS)
        # ========================================================================
        if total_rows_all == 0:
            logger.error("Nenhuma linha válida foi carregada em nenhum arquivo")
            sys.exit(1)
        
        logger.info("\n" + "="*70)
        logger.info("RESUMO FINAL DE CARGA")
        logger.info("="*70)
        logger.info(f"Total de arquivos processados: {len(csv_files)}")
        logger.info(f"Total de linhas carregadas: {total_rows_all}")
        logger.info(f"Total de erros: {total_errors_all}")
        
        # Mostrar total de registros na tabela
        result = client.query("SELECT COUNT(*) FROM vacinacao")
        total = result.result_rows[0][0]
        logger.info(f"Total de registros na tabela: {total:,}")
        
        # Distribuição por estado
        result = client.query("SELECT paciente_endereco_uf, COUNT(*) FROM vacinacao GROUP BY paciente_endereco_uf ORDER BY COUNT(*) DESC")
        logger.info("Distribuição por estado:")
        for row in result.result_rows:
            logger.info(f"   {row[0]}: {row[1]:,} registros")
            
    except Exception as e:
        logger.error(f"Erro durante carga: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Carregar CSVs de datasets para ClickHouse",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXEMPLOS:
  python load_csv.py                              # Carrega covid-19-vacinacao (padrão)
  python load_csv.py --dataset dengue-2024       # Carrega dengue-2024
  python load_csv.py --dataset influenza-2025    # Carrega influenza-2025
  python load_csv.py --all                        # Carrega TODOS os datasets
  python load_csv.py --file /path/to/custom.csv  # Carrega arquivo customizado
        """
    )
    
    parser.add_argument(
        '--dataset',
        type=str,
        default="covid-19-vacinacao",
        help='Dataset a carregar (padrão: covid-19-vacinacao)'
    )
    parser.add_argument(
        '--file',
        type=str,
        default=None,
        help='Caminho de arquivo específico a carregar'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Carregar TODOS os datasets encontrados em data/datasets/'
    )
    
    args = parser.parse_args()
    
    if args.all:
        # Descobrir e carregar todos os datasets
        datasets_path = Path(__file__).parent.parent / "data" / "datasets"
        datasets = [d.name for d in datasets_path.iterdir() if d.is_dir()]
        
        if not datasets:
            logger.error(f"Nenhum dataset encontrado em {datasets_path}")
            sys.exit(1)
        
        logger.info(f"Carregando {len(datasets)} dataset(s): {', '.join(datasets)}\n")
        for dataset in sorted(datasets):
            logger.info(f"\n{'='*70}")
            logger.info(f"INICIANDO: {dataset}")
            logger.info(f"{'='*70}\n")
            try:
                load_csv(dataset=dataset)
            except SystemExit:
                logger.error(f"Erro ao carregar {dataset}, continuando com próximo...")
                continue
        
        logger.info(f"\n{'='*70}")
        logger.info(f"CARGA COMPLETA DE TODOS OS DATASETS")
        logger.info(f"{'='*70}")
    else:
        # Carregar dataset específico ou arquivo
        if args.file:
            load_csv(csv_path=args.file, dataset=args.dataset)
        else:
            load_csv(dataset=args.dataset)
