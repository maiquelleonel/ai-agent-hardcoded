import os
from typing import Any

from openai import OpenAI

from services.ai_service import BaseAIService


class OpenAIService(BaseAIService):
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")

    def get_embedding(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model="text-embedding-3-small", input=text)
        return response.data[0].embedding

    def generate_response(self, messages: list, **kwargs) -> str:
        response = self.client.chat.completions.create(model=self.model, messages=messages, **kwargs)
        return response.choices[0].message.content

    def generate_with_tools(self, messages: list, tools: list, **kwargs) -> Any:
        return self.client.chat.completions.create(model=self.model, messages=messages, tools=tools, **kwargs)
