"""CLI principal de Documenta."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from documenta import __version__
from documenta.config import DocumentaConfig

app = typer.Typer(
    name="documenta",
    help="🗂️ Outil de documentation automatique de projets via LLMs open-source (Ollama)",
    no_args_is_help=True,
)
console = Console()


@app.command()
def generate(
    path: str = typer.Argument(
        ".",
        help="Chemin vers le projet à documenter",
    ),
    output: str = typer.Option(
        "docs", "--output", "-o",
        help="Répertoire de sortie pour la documentation",
    ),
    code_model: str = typer.Option(
        "deepseek-coder-v2:16b", "--code-model",
        help="Modèle LLM pour l'analyse de code",
    ),
    code_backend: str = typer.Option(
        None, "--code-backend",
        help="Backend du modèle code : ollama | lmstudio | mlx | openai",
    ),
    code_url: str = typer.Option(
        None, "--code-url",
        help="URL de l'API pour le modèle code (override du backend)",
    ),
    doc_model: str = typer.Option(
        "mistral:7b", "--doc-model",
        help="Modèle LLM pour la rédaction",
    ),
    doc_backend: str = typer.Option(
        None, "--doc-backend",
        help="Backend du modèle doc : ollama | lmstudio | mlx | openai",
    ),
    doc_url: str = typer.Option(
        None, "--doc-url",
        help="URL de l'API pour le modèle doc (override du backend)",
    ),
    diagram_model: str = typer.Option(
        "llama3.1:8b", "--diagram-model",
        help="Modèle LLM pour les diagrammes",
    ),
    diagram_backend: str = typer.Option(
        None, "--diagram-backend",
        help="Backend du modèle diagramme : ollama | lmstudio | mlx | openai",
    ),
    diagram_url: str = typer.Option(
        None, "--diagram-url",
        help="URL de l'API pour le modèle diagramme (override du backend)",
    ),
    ollama_url: str = typer.Option(
        "http://localhost:11434", "--ollama-url",
        help="URL du serveur Ollama (fallback)",
    ),
    no_png: bool = typer.Option(
        False, "--no-png",
        help="Désactiver l'export PNG des diagrammes",
    ),
    language: str = typer.Option(
        "fr", "--lang",
        help="Langue de la documentation (fr, en)",
    ),
) -> None:
    """Génère la documentation complète d'un projet."""
    project_path = Path(path).resolve()

    if not project_path.exists():
        console.print(f"[red]✗ Le chemin '{project_path}' n'existe pas.[/red]")
        raise typer.Exit(1)

    if not project_path.is_dir():
        console.print(f"[red]✗ '{project_path}' n'est pas un répertoire.[/red]")
        raise typer.Exit(1)

    config = DocumentaConfig(
        ollama_base_url=ollama_url,
        code_model=code_model,
        code_backend=code_backend,  # type: ignore[arg-type]
        code_url=code_url,
        doc_model=doc_model,
        doc_backend=doc_backend,  # type: ignore[arg-type]
        doc_url=doc_url,
        diagram_model=diagram_model,
        diagram_backend=diagram_backend,  # type: ignore[arg-type]
        diagram_url=diagram_url,
        output_dir=output,
        export_png=not no_png,
        language=language,
    )

    asyncio.run(_run_generation(project_path, config))


async def _run_generation(project_path: Path, config: DocumentaConfig) -> None:
    """Exécute la génération de documentation."""
    from documenta.analyzer.project import ProjectAnalyzer
    from documenta.generators.engine import DocumentationEngine

    # Phase 1 : Analyse du projet
    console.print("\n[bold cyan]📂 Analyse du projet...[/bold cyan]")
    analyzer = ProjectAnalyzer(project_path, config)
    project = analyzer.analyze()

    # Afficher le résumé de l'analyse
    _print_analysis_summary(project)

    # Phase 2 : Génération
    engine = DocumentationEngine(project, config)
    generated = await engine.generate_all()

    if not generated:
        console.print("[red]✗ Aucun fichier généré. Vérifiez qu'Ollama est lancé.[/red]")
        raise typer.Exit(1)

    console.print("\n[bold green]✓ Documentation générée avec succès ![/bold green]")


@app.command()
def check(
    ollama_url: str = typer.Option(
        "http://localhost:11434",
        "--ollama-url",
        help="URL du serveur Ollama",
    ),
) -> None:
    """Vérifie la configuration (Ollama, modèles, draw.io)."""
    asyncio.run(_run_check(ollama_url))


async def _run_check(ollama_url: str) -> None:
    """Vérifie l'environnement."""
    from documenta.config import DEFAULT_BACKEND_URLS
    from documenta.drawio.exporter import DrawioExporter
    from documenta.llm.client import LLMClient

    config = DocumentaConfig(ollama_base_url=ollama_url)
    llm = LLMClient(config)

    console.print(Panel("[bold]Vérification de l'environnement Documenta[/bold]", border_style="cyan"))

    # Vérifier chaque backend connu
    backends_table = Table(title="Backends LLM")
    backends_table.add_column("Backend", style="cyan")
    backends_table.add_column("URL", style="white")
    backends_table.add_column("Statut", style="bold")
    backends_table.add_column("Modèles", style="dim")

    for backend_name in ("ollama", "lmstudio", "mlx"):
        url = DEFAULT_BACKEND_URLS[backend_name]
        if backend_name == "ollama":
            url = ollama_url
        connected = await llm._check_url(url, backend_name)  # type: ignore[arg-type]
        if connected:
            models = await llm.list_models(url=url, backend=backend_name)  # type: ignore[arg-type]
            models_str = f"{len(models)} modèle(s)" if models else "aucun"
            backends_table.add_row(backend_name, url, "[green]✓ accessible", models_str)
        else:
            backends_table.add_row(backend_name, url, "[dim]✗ non accessible", "—")

    console.print(backends_table)

    # Vérifier les modèles configurés
    console.print("\n[bold]Modèles configurés pour la génération :[/bold]")
    for label, model, backend_opt, url_opt in [
        ("Code   ", config.code_model, config.code_backend, config.code_url),
        ("Docs   ", config.doc_model, config.doc_backend, config.doc_url),
        ("Diagram", config.diagram_model, config.diagram_backend, config.diagram_url),
    ]:
        backend = config.resolve_backend(model, backend_opt)
        url = config.resolve_url(backend, url_opt)
        available = await llm.list_models(url=url, backend=backend)
        found = any(
            m == model or m.startswith(model.split(":")[0]) for m in available
        )
        status = "[green]✓" if found else "[red]✗ non trouvé"
        console.print(f"  {label} : {status} [cyan]{model}[/cyan] → {backend} @ {url}[/]")

    # Vérifier draw.io
    exporter = DrawioExporter()
    drawio_path = exporter.find_drawio()
    if drawio_path:
        console.print(f"[green]✓ draw.io trouvé : {drawio_path}[/green]")
    else:
        console.print(
            "[yellow]⚠ draw.io non trouvé (export PNG désactivé)[/yellow]\n"
            "  macOS : brew install --cask drawio\n"
            "  Linux : snap install drawio"
        )


@app.command()
def models(
    ollama_url: str = typer.Option(
        "http://localhost:11434",
        "--ollama-url",
        help="URL du serveur Ollama",
    ),
) -> None:
    """Liste les modèles recommandés et leur statut."""
    asyncio.run(_run_models(ollama_url))


async def _run_models(ollama_url: str) -> None:
    """Affiche les modèles recommandés."""
    from documenta.llm.client import LLMClient

    config = DocumentaConfig(ollama_base_url=ollama_url)
    llm = LLMClient(config)

    available = await llm.list_models()
    available_base = {m.split(":")[0] for m in available}

    recommended = [
        ("deepseek-coder-v2:16b", "Analyse de code", "ollama", "~9 Go", "Excellente compréhension du code"),
        ("mistral:7b", "Rédaction docs", "ollama", "~4 Go", "Bon français, rapide"),
        ("llama3.1:8b", "Diagrammes/synthèse", "ollama", "~5 Go", "Bon raisonnement structuré"),
        ("codellama:13b", "Alternative code", "ollama", "~7 Go", "Spécialisé code (Meta)"),
        ("qwen2.5-coder:14b", "Alternative code", "ollama", "~8 Go", "Très bon en code (Alibaba)"),
        ("mixtral:8x7b", "Alternative docs", "ollama", "~26 Go", "Excellent mais gourmand"),
        ("gemma2:9b", "Polyvalent", "ollama", "~5 Go", "Bon compromis (Google)"),
        ("mlx-community/gemma-4-26b-a4b-it-8bit", "Rédaction docs", "lmstudio/mlx", "~26 Go", "Optimisé Apple Silicon (MLX 8-bit)"),
        ("mlx-community/Llama-3.1-8B-Instruct-8bit", "Diagrammes", "lmstudio/mlx", "~9 Go", "Optimisé Apple Silicon"),
        ("mlx-community/Qwen2.5-Coder-14B-Instruct-8bit", "Analyse code", "lmstudio/mlx", "~15 Go", "Code + MLX"),
    ]

    table = Table(title="🤖 Modèles LLM recommandés pour Documenta")
    table.add_column("Modèle", style="cyan", no_wrap=True)
    table.add_column("Usage", style="white")
    table.add_column("Backend", style="magenta")
    table.add_column("Taille", style="yellow")
    table.add_column("Note", style="dim")
    table.add_column("Statut", style="bold")

    for model, usage, backend, size, note in recommended:
        model_base = model.split(":")[0].split("/")[-1]
        installed = (
            model_base in available_base
            or model in available
            or any(model in m for m in available)
        )
        status = "[green]✓ Installé" if installed else "[dim]Non installé"
        table.add_row(model, usage, backend, size, note, status)

    console.print(table)
    console.print("\n[bold]Installation :[/bold]")
    console.print("  Ollama         : [cyan]ollama pull <nom_du_modèle>[/cyan]")
    console.print("  LM Studio/MLX  : Télécharger via l'interface LM Studio")
    console.print("\n[dim]Sur MacBook Pro M5 64 Go, vous pouvez combiner Ollama + LM Studio pour les modèles MLX.[/dim]")


@app.command()
def version() -> None:
    """Affiche la version de Documenta."""
    console.print(f"Documenta v{__version__}")


def _print_analysis_summary(project) -> None:  # noqa: ANN001
    """Affiche le résumé de l'analyse du projet."""
    table = Table(title=f"Analyse de '{project.name}'")
    table.add_column("Propriété", style="cyan")
    table.add_column("Valeur", style="white")

    table.add_row("Langages", ", ".join(project.tech_stack.languages) or "—")
    table.add_row("Frameworks", ", ".join(project.tech_stack.frameworks) or "—")
    table.add_row("Bases de données", ", ".join(project.tech_stack.databases) or "—")
    table.add_row("Outils", ", ".join(project.tech_stack.tools) or "—")
    table.add_row("Package manager", project.tech_stack.package_manager or "—")
    table.add_row("Fichiers analysés", str(len(project.files)))
    table.add_row("Points d'entrée", ", ".join(project.entry_points) or "—")

    files_with_content = sum(1 for f in project.files if f.content)
    table.add_row("Fichiers lus", str(files_with_content))

    if project.git_info.branch:
        table.add_row("Branche Git", project.git_info.branch)
    if project.git_info.contributors:
        table.add_row("Contributeurs", ", ".join(project.git_info.contributors[:5]))

    console.print(table)
