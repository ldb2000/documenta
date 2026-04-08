"""Utilitaires de gestion de fichiers."""

from __future__ import annotations

from pathlib import Path


def ensure_dir(path: Path) -> Path:
    """Crée le répertoire s'il n'existe pas."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_write(path: Path, content: str) -> None:
    """Écrit un fichier de manière sûre."""
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def truncate_content(content: str, max_chars: int = 8000) -> str:
    """Tronque le contenu si nécessaire en gardant le début et la fin."""
    if len(content) <= max_chars:
        return content
    half = max_chars // 2
    return content[:half] + "\n\n[... contenu tronqué ...]\n\n" + content[-half:]


def format_file_size(size_bytes: int) -> str:
    """Formate une taille en bytes de manière lisible."""
    for unit in ("o", "Ko", "Mo", "Go"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024  # type: ignore[assignment]
    return f"{size_bytes:.1f} To"
