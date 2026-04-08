"""Configuration de Documenta."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class LLMModelConfig(BaseSettings):
    """Configuration d'un modèle LLM."""

    name: str = "mistral"
    temperature: float = 0.3
    context_length: int = 8192


class DocumentaConfig(BaseSettings):
    """Configuration globale de Documenta."""

    model_config = {"env_prefix": "DOCUMENTA_"}

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # Modèle pour l'analyse de code et l'architecture
    code_model: str = "deepseek-coder-v2:16b"
    # Modèle pour la rédaction de documentation
    doc_model: str = "mistral:7b"
    # Modèle pour les diagrammes et la synthèse
    diagram_model: str = "llama3.1:8b"

    # Températures par usage
    code_temperature: float = 0.1
    doc_temperature: float = 0.4
    diagram_temperature: float = 0.2

    # Contexte
    max_context_length: int = 16384
    max_file_size_kb: int = 500
    max_files_to_analyze: int = 150

    # Sortie
    output_dir: str = "docs"
    export_png: bool = True
    language: str = "fr"

    # Fichiers/dossiers à ignorer
    ignore_patterns: list[str] = Field(default_factory=lambda: [
        "node_modules", "__pycache__", ".git", ".venv", "venv",
        "dist", "build", ".next", ".nuxt", "target",
        "*.pyc", "*.pyo", "*.so", "*.dylib",
        "*.lock", "package-lock.json", "yarn.lock",
        "*.min.js", "*.min.css", "*.map",
        "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico", "*.svg",
        "*.woff", "*.woff2", "*.ttf", "*.eot",
        ".DS_Store", "Thumbs.db",
    ])

    def get_output_path(self, project_path: Path) -> Path:
        return project_path / self.output_dir
