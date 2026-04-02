import requests
from llm.base import LLMProvider
import os
import logging
import time

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    """Provider genérico para qualquer modelo Ollama com retry logic"""

    def __init__(self, model_name: str = "deepseek-coder:6.7b-base-q4_K_M", display_name: str = "ollama"):
        self.url = os.getenv("OLLAMA_HOST", "http://localhost:11434") + "/api/generate"
        self.model = model_name
        self.display_name = display_name
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "180"))  # 3 minutos por padrão
        self.max_retries = 3
        self.retry_delay = 2  # segundos

    def generate(self, prompt: str) -> str:
        """
        Gera resposta com retry logic para 500 Server Errors
        """
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"[{self.display_name}] Tentativa {attempt}/{self.max_retries} para Ollama (modelo: {self.model})")
                logger.debug(f"Prompt size: {len(prompt)} chars")
                
                response = requests.post(
                    self.url,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "temperature": 0.3,
                        "top_p": 1
                    },
                    timeout=self.timeout
                )
                response.raise_for_status()
                response_json = response.json()
                logger.debug(f"Resposta JSON recebida")
                
                result = response_json.get("response", "")
                logger.debug(f"Resposta extraída ({len(result)} chars): {repr(result[:150])}")
                
                return result if result else ""
                
            except requests.exceptions.ConnectionError as e:
                last_error = str(e)
                logger.warning(f"[Tentativa {attempt}] Não conseguiu conectar ao Ollama em {self.url}")
                if attempt < self.max_retries:
                    logger.info(f"Aguardando {self.retry_delay}s antes de retry...")
                    time.sleep(self.retry_delay)
                    
            except requests.exceptions.Timeout as e:
                last_error = str(e)
                logger.warning(f"[Tentativa {attempt}] Timeout ao conectar Ollama (timeout={self.timeout}s)")
                if attempt < self.max_retries:
                    logger.info(f"Aguardando {self.retry_delay}s antes de retry...")
                    time.sleep(self.retry_delay)
                    
            except requests.exceptions.HTTPError as e:
                last_error = str(e)
                if "500" in str(e):
                    logger.warning(f"[Tentativa {attempt}] Ollama retornou erro 500")
                    if attempt < self.max_retries:
                        logger.info(f"Aguardando {self.retry_delay}s antes de retry...")
                        time.sleep(self.retry_delay)
                        continue
                logger.error(f"Erro HTTP no Ollama ({self.display_name}): {e}")
                raise
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Erro ao gerar com Ollama ({self.display_name}): {e}")
                raise
        
        # Se chegou aqui, todas as tentativas falharam
        logger.error(f"Todas as {self.max_retries} tentativas falharam. Último erro: {last_error}")
        raise requests.exceptions.HTTPError(f"Ollama falhou após {self.max_retries} tentativas: {last_error}")
