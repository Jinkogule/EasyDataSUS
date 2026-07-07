import clickhouse_connect
import logging
import os
from dotenv import load_dotenv
from functools import lru_cache

load_dotenv()
logger = logging.getLogger(__name__)

# Configurações do ClickHouse
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "easydatasus_ro")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "easydatasus_ro")
CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "default")

@lru_cache(maxsize=1)
def get_client():
    """Retorna cliente ClickHouse com pool de conexão (cache)"""
    logger.info(f"Conectando ao ClickHouse: {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}")
    try:
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            username=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD,
            database=CLICKHOUSE_DATABASE,
            connect_timeout=10
        )
        # Testa a conexão
        client.query("SELECT 1")
        logger.info("Conexão com ClickHouse estabelecida")
        return client
    except Exception as e:
        logger.error(f"Erro ao conectar ao ClickHouse: {e}")
        raise

def run_query(sql: str, retry_count: int = 3):
    """Executa query no ClickHouse com retry logic"""
    
    logger.info(f"Executando query: {sql[:100]}...")
    
    for attempt in range(retry_count):
        try:
            client = get_client()
            result = client.query(sql)
            logger.info(f"Query executada com sucesso. Linhas: {len(result.result_rows)}")
            return result.result_rows
        
        except Exception as e:
            logger.error(f"Erro na query (tentativa {attempt + 1}/{retry_count}): {e}")
            
            # Limpa cache após erro para reconectar
            if attempt < retry_count - 1:
                get_client.cache_clear()
                logger.info("Cache limpo. Tentando novamente...")
            else:
                return {
                    "error": str(e),
                    "sql": sql,
                    "message": f"Falha na execução após {retry_count} tentativas"
                }
    
    return {"error": "Erro desconhecido", "sql": sql}