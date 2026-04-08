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
        "docs",
        "--output", "-o",
        help="Répertoire de sortie pour la documentation",
    ),
    code_model: str = typer.Option(
        "deepseek-coder-v2:16b",
        "--code-model",
        help="Modèle LLM pour l'analyse de code",
    ),
    doc_model: str = typer.Option(
        "mistral:7b",
        "--doc-model",
        help="Modèle LLM pour la rédaction",
    ),
    diagram_model: str = typer.Option(
        "llama3.1:8b",
        "--diagram-model",
        help="Modèle LLM pour les diagrammes",
    ),
    ollama_url: str = typer.Option(
        "http://localhost:11434",
        "--ollama-url",
        help="URL du serveur Ollama",
    ),
    no_png: bool = typer.Option(
        False,
        "--no-png",
        help="Désactiver l'export PNG des diagrammes",
    ),
    language: str = typer.Option(
        "fr",
        "--lang",
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
        doc_model=doc_model,
        diagram_model=diagram_model,
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
    from documenta.drawio.exporter import DrawioExporter
    from documenta.llm.client import OllamaClient

    config = DocumentaConfig(ollama_base_url=ollama_url)
    llm = OllamaClient(config)

    console.print(Panel("[bold]Vérification de l'environnement Documenta[/bold]", border_style="cyan"))

    # Vérifier Ollama
    connected = await llm.check_connection()
    if connected:
        console.print("[green]✓ Ollama accessible[/green]")
        models = await llm.list_models()
        if models:
            table = Table(title="Modèles disponibles")
            table.add_column("Modèle", style="cyan")
            for m in models:
                table.add_row(m)
            console.print(table)
        else:
            console.print("[yellow]⚠ Aucun modèle installé[/yellow]")

        # Vérifier les modèles requis
        needed = [config.code_model, config.doc_model, config.diagram_model]
        for model in needed:
            found = await llm.ensure_model(model)
            status = "[green]✓" if found else "[red]✗ manquant"
            console.print(f"  {status} {model}[/]")
    else:
        console.print(
            "[red]✗ Ollama non accessible[/red]\n"
            "  Installez Ollama : https://ollama.com\n"
            "  Lancez-le       : ollama serve"
        )

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
    from documenta.llm.client import OllamaClient

    config = DocumentaConfig(ollama_base_url=ollama_url)
    llm = OllamaClient(config)

    available = await llm.list_models()
    available_base = {m.split(":")[0] for m in available}

    recommended = [
        ("deepseek-coder-v2:16b", "Analyse de code", "~9 Go", "Excellente compréhension du code"),
        ("mistral:7b", "Rédaction docs", "~4 Go", "Bon français, rapide"),
        ("llama3.1:8b", "Diagrammes/synthèse", "~5 Go", "Bon raisonnement structuré"),
        ("codellama:13b", "Alternative code", "~7 Go", "Spécialisé code (Meta)"),
        ("qwen2.5-coder:14b", "Alternative code", "~8 Go", "Très bon en code (Alibaba)"),
        ("mixtral:8x7b", "Alternative docs", "~26 Go", "Excellent mais gourmand"),
        ("gemma2:9b", "Polyvalent", "~5 Go", "Bon compromis (Google)"),
    ]

    table = Table(title="🤖 Modèles LLM recommandés pour Documenta")
    table.add_column("Modèle", style="cyan", no_wrap=True)
    table.add_column("Usage", style="white")
    table.add_column("Taille", style="yellow")
    table.add_column("Note", style="dim")
    table.add_column("Statut", style="bold")

    for model, usage, size, note in recommended:
        model_base = model.split(":")[0]
        installed = model_base in available_base or model in available
        status = "[green]✓ Installé" if installed else "[dim]Non installé"
        table.add_row(model, usage, size, note, status)

    console.print(table)
    console.print("\nInstaller un modèle : [cyan]ollama pull <nom_du_modèle>[/cyan]")
    console.print("Avec 64 Go de RAM, vous pouvez utiliser tous ces modèles simultanément !")


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
