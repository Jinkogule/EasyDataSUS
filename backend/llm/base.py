from abc import ABC, abstractmethod

class LLMProvider(ABC):

    @abstractmethod
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
        pass
