from abc import ABC, abstractmethod


class BaseAIService(ABC):
    @abstractmethod
    def get_embedding(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def generate_response(self, messages: list, **kwargs) -> str:
        pass
