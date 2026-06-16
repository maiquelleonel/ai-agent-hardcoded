import copy
import os
from typing import Any

from google import genai
from google.genai import types

from prompts import SYSTEM_PROMPT
from services.ai_service import BaseAIService


class GeminiService(BaseAIService):
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.system_prompt = SYSTEM_PROMPT

    def get_embedding(self, text: str) -> list[float]:
        response = self.client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=768,
            ),
        )
        return response.embeddings[0].values

    def generate_response(self, messages: list, response_schema=None, **kwargs) -> str:
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                continue
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

        config_params = {
            "system_instruction": self.system_prompt,
            "temperature": 0.65,
            "response_mime_type": "application/json",
        }
        if response_schema:
            config_params["response_schema"] = response_schema

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(**config_params),
        )
        return response.text

    def _clean_tool_definition(self, tool: dict) -> dict:
        clean_tool = copy.deepcopy(tool)
        if "parameters" in clean_tool and "additionalProperties" in clean_tool["parameters"]:
            del clean_tool["parameters"]["additionalProperties"]
        return clean_tool

    def generate_with_tools(self, messages: list, tools: list, **kwargs) -> Any:
        gemini_tools = []
        for t in tools:
            clean_t = self._clean_tool_definition(t)
            func_decl = types.FunctionDeclaration(
                name=clean_t["name"], description=clean_t["description"], parameters=clean_t["parameters"]
            )
            gemini_tools.append(types.Tool(function_declarations=[func_decl]))

        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=m["content"])])
            for m in messages
            if m["role"] != "system"
        ]

        return self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=self.system_prompt, tools=gemini_tools),
        )
