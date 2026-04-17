"""Configuration de Documenta."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings

Backend = Literal["ollama", "openai", "lmstudio", "mlx"]


# URLs par défaut selon le backend
DEFAULT_BACKEND_URLS: dict[str, str] = {
    "ollama": "http://localhost:11434",
    "lmstudio": "http://localhost:1234/v1",
    "mlx": "http://localhost:8080/v1",
    "openai": "http://localhost:1234/v1",
}


class DocumentaConfig(BaseSettings):
    """Configuration globale de Documenta."""

    model_config = {"env_prefix": "DOCUMENTA_"}

    # URL de base par défaut (Ollama)
    ollama_base_url: str = "http://localhost:11434"

    # Backend par défaut (pour les modèles sans backend explicite)
    default_backend: Backend = "ollama"

    # Modèles et leurs backends
    code_model: str = "mlx-community/gemma-4-26b-a4b-it-8bit"
    code_backend: Backend | None = None
    code_url: str | None = None

    doc_model: str = "mlx-community/gemma-4-26b-a4b-it-8bit"
    doc_backend: Backend | None = None
    doc_url: str | None = None

    diagram_model: str = "mlx-community/gemma-4-26b-a4b-it-8bit"
    diagram_backend: Backend | None = None
    diagram_url: str | None = None

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

    def resolve_backend(self, model_name: str, explicit: Backend | None = None) -> Backend:
        """Détermine le backend pour un modèle donné."""
        if explicit:
            return explicit
        # Auto-détection : les modèles avec un / sont typiquement MLX/HF
        if "/" in model_name or model_name.startswith("mlx-"):
            return "lmstudio"
        return self.default_backend

    def resolve_url(self, backend: Backend, explicit: str | None = None) -> str:
        """Détermine l'URL pour un backend donné."""
        if explicit:
            return explicit
        if backend == "ollama":
            return self.ollama_base_url
        return DEFAULT_BACKEND_URLS.get(backend, self.ollama_base_url)
