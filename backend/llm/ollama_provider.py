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

    def generate(
        self,
        prompt: str,
        *,
        response_format: str | None = None,
        num_predict: int | None = None,
        temperature: float | None = None,
        timeout_s: int | None = None,
        max_retries: int | None = None,
    ) -> str:
        """
        Gera resposta com retry logic para 500 Server Errors
        """
        last_error = None
        effective_timeout = self.timeout if timeout_s is None else timeout_s
        effective_retries = self.max_retries if max_retries is None else max(1, max_retries)
        
        for attempt in range(1, effective_retries + 1):
            try:
                logger.debug(f"[{self.display_name}] Tentativa {attempt}/{effective_retries} para Ollama (modelo: {self.model})")
                logger.debug(f"Prompt size: {len(prompt)} chars")
                
                options = {
                    "temperature": 0.3 if temperature is None else temperature,
                    "top_p": 1,
                }
                if num_predict is not None:
                    options["num_predict"] = num_predict

                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": options,
                }
                if response_format:
                    payload["format"] = response_format

                response = requests.post(
                    self.url,
                    json=payload,
                    timeout=effective_timeout
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
                if attempt < effective_retries:
                    logger.info(f"Aguardando {self.retry_delay}s antes de retry...")
                    time.sleep(self.retry_delay)
                    
            except requests.exceptions.Timeout as e:
                last_error = str(e)
                logger.warning(f"[Tentativa {attempt}] Timeout ao conectar Ollama (timeout={effective_timeout}s)")
                if attempt < effective_retries:
                    logger.info(f"Aguardando {self.retry_delay}s antes de retry...")
                    time.sleep(self.retry_delay)
                    
            except requests.exceptions.HTTPError as e:
                last_error = str(e)
                if "500" in str(e):
                    logger.warning(f"[Tentativa {attempt}] Ollama retornou erro 500")
                    if attempt < effective_retries:
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
        logger.error(f"Todas as {effective_retries} tentativas falharam. Último erro: {last_error}")
        raise requests.exceptions.HTTPError(f"Ollama falhou após {effective_retries} tentativas: {last_error}")
