import csv
import logging
import sys
from datetime import datetime
from pathlib import Path
import subprocess

import clickhouse_connect

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
        logger.info("✅ Conectado ao ClickHouse")
        return client
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao ClickHouse: {e}")
        sys.exit(1)

def table_exists(client):
    """Verifica se tabela 'vacinacao' existe"""
    try:
        result = client.query("SELECT 1 FROM vacinacao LIMIT 1")
        return True
    except Exception:
        return False

def load_csv(csv_path: str = None, dataset: str = "vacinacao-covid"):
    """
    Carrega CSV para ClickHouse usando TSV format.
    
    Args:
        csv_path (str): Caminho completo do arquivo CSV.
                       Se None, usa data/datasets/{dataset}/
        dataset (str): Nome do dataset. Padrão: "vacinacao-covid"
    """
    if csv_path is None:
        base_path = Path(__file__).parent.parent / "data" / "datasets" / dataset
        csv_files = list(base_path.glob("*.csv"))
        if not csv_files:
            logger.error(f"❌ Nenhum arquivo CSV encontrado em {base_path}")
            sys.exit(1)
        csv_path = str(csv_files[0])
    
    csv_file = Path(csv_path)
    
    if not csv_file.exists():
        logger.error(f"❌ Arquivo não encontrado: {csv_path}")
        sys.exit(1)
    
    logger.info(f"📂 Carregando arquivo: {csv_path}")
    
    client = get_clickhouse_client()
    
    # Verificar se tabela existe
    if not table_exists(client):
        logger.error("❌ Tabela 'vacinacao' não existe. Execute o init.sql primeiro.")
        sys.exit(1)
    
    # Ler CSV e converter para TSV
    logger.info("📝 Convertendo CSV para TSV...")
    tsv_lines = []
    row_count = 0
    error_count = 0
    
    try:
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
                        logger.info(f"  📥 {idx} linhas lidas... ({row_count} parsed)")
                
                except Exception as e:
                    error_count += 1
                    if error_count <= 5:
                        logger.warning(f"  ⚠️ Erro na linha {idx}: {e}")
        
        logger.info(f"✅ CSV convertido: {row_count} linhas válidas, {error_count} erros")
        
        if row_count == 0:
            logger.error("❌ Nenhuma linha válida para inserir")
            sys.exit(1)
        
        # Juntar linhas com apenas LF (Unix line ending)
        tsv_content = "\n".join(tsv_lines) + "\n"
        
        # Usar pipe direto para stdin com encoding UTF-8
        cmd = [
            'docker', 'exec', '-i', 'easydatasus-clickhouse', 
            'clickhouse-client', '-u', 'admin', '--password', 'admin', 
            '-d', 'default', 
            '-q', 'INSERT INTO vacinacao FORMAT TSV'
        ]
        
        logger.info(f"Executando INSERT via pipe...")
        # Converter conteúdo para bytes em UTF-8 e enviar
        result = subprocess.run(
            cmd, 
            input=tsv_content.encode('utf-8'),  # Enviar como bytes UTF-8
            capture_output=True
        )
        
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='replace')
            logger.error(f"❌ Erro no INSERT: {stderr}")
            sys.exit(1)
        
        stdout = result.stdout.decode('utf-8', errors='replace')
        if stdout:
            logger.info(f"✅ {stdout.strip()}")
        
        logger.info("✅ Carga finalizada com sucesso!")
        
        # Mostrar estatísticas
        result = client.query("SELECT COUNT(*) FROM vacinacao")
        total = result.result_rows[0][0]
        logger.info(f"📊 Total de registros na tabela: {total}")
        
        # Distribuição por estado
        result = client.query("SELECT paciente_endereco_uf, COUNT(*) FROM vacinacao GROUP BY paciente_endereco_uf ORDER BY COUNT(*) DESC")
        logger.info("📍 Distribuição por estado:")
        for row in result.result_rows:
            logger.info(f"   {row[0]}: {row[1]} registros")
        
    except Exception as e:
        logger.error(f"❌ Erro durante carga: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    load_csv()  # Carrega da estrutura padrão: data/datasets/vacinacao-covid/
