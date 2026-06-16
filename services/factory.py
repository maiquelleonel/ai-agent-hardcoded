import os

from services.openai_service import OpenAIService

from services.ai_service import BaseAIService

# from services.gemini_service import GeminiService


def get_ai_service() -> BaseAIService:
    provider = os.getenv("AI_PROVIDER", "openai").lower()

    if provider == "openai":
        return OpenAIService()
    # elif provider == "gemini":
    #     return GeminiService()

    raise ValueError(f"Provider {provider} não suportado.")
