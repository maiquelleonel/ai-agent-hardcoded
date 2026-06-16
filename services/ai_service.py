from abc import ABC, abstractmethod
from typing import Any


class BaseAIService(ABC):
    @abstractmethod
    def get_embedding(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def generate_with_tools(self, messages: list, tools: list, **kwargs) -> Any:
        pass
