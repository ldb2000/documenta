"""Module d'intégration LLM via Ollama."""

from documenta.llm.client import OllamaClient
from documenta.llm.prompts import PromptBuilder

__all__ = ["OllamaClient", "PromptBuilder"]
