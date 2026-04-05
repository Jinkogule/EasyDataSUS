import requests
from llm.base import LLMProvider
import os
import logging

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    """Provider genérico para qualquer modelo Ollama"""

    def __init__(self, model_name: str = "deepseek-coder:6.7b-base-q4_K_M", display_name: str = "ollama"):
        self.url = os.getenv("OLLAMA_HOST", "http://localhost:11434") + "/api/generate"
        self.model = model_name
        self.display_name = display_name
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "180"))  # 3 minutos por padrão

    def generate(self, prompt: str) -> str:
        try:
            logger.debug(f"📤 [{self.display_name}] Enviando prompt para Ollama (modelo: {self.model}, timeout: {self.timeout}s)")
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
            logger.debug(f"📥 Resposta JSON recebida")
            
            result = response_json.get("response", "")
            logger.debug(f"✅ Resposta extraída ({len(result)} chars): {repr(result[:150])}")
            
            return result if result else ""
            
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Não conseguiu conectar ao Ollama em {self.url}")
            raise
        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout ao conectar Ollama (timeout={self.timeout}s)")
            raise
        except Exception as e:
            logger.error(f"❌ Erro ao gerar com Ollama ({self.display_name}): {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
