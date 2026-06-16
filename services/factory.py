import os

from dotenv import load_dotenv

from services.ai_service import BaseAIService
from services.gemini_service import GeminiService
from services.openai_service import OpenAIService

# Garante que as variáveis do .env estejam carregadas
load_dotenv()


def get_ai_service() -> BaseAIService:
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIService()
    elif os.getenv("GEMINI_API_KEY"):
        return GeminiService()

    raise ValueError("Nenhum provedor de IA configurado. Por favor, forneça OPENAI_API_KEY ou GEMINI_API_KEY.")
