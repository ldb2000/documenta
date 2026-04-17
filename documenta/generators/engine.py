"""Moteur principal de génération de documentation."""

from __future__ import annotations

import asyncio
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from documenta.analyzer.imports import ImportAnalyzer
from documenta.analyzer.project import ProjectInfo
from documenta.config import DocumentaConfig
from documenta.drawio.builder import DrawioBuilder, parse_llm_json
from documenta.drawio.exporter import DrawioExporter
from documenta.drawio.mermaid_parser import parse_mermaid
from documenta.llm.client import LLMClient
from documenta.llm.prompts import PromptBuilder
from documenta.utils.files import safe_write

console = Console()


class DocumentationEngine:
    """Orchestre la génération complète de la documentation."""

    def __init__(
        self,
        project: ProjectInfo,
        config: DocumentaConfig | None = None,
    ):
        self.project = project
        self.config = config or DocumentaConfig()
        self.llm = LLMClient(self.config)
        self.prompts = PromptBuilder(project)
        self.drawio = DrawioBuilder()
        self.exporter = DrawioExporter()
        self.output_dir = self.config.get_output_path(project.root_path)

    async def generate_all(self) -> dict[str, Path]:
        """Génère toute la documentation.

        Returns:
            Dictionnaire des fichiers générés {nom: chemin}.
        """
        generated: dict[str, Path] = {}

        console.print(Panel(
            f"[bold cyan]Documenta[/bold cyan] - Génération de documentation\n"
            f"Projet : [bold]{self.project.name}[/bold]\n"
            f"Sortie  : {self.output_dir}",
            title="📚 Documenta",
            border_style="cyan",
        ))

        # Vérifier la connexion et les modèles disponibles
        await self._check_models()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Génération parallèle des contenus via LLM
            # Phase 1 : Architecture + Fonctionnel (utilisent le modèle diagramme)
            task1 = progress.add_task("Génération de l'architecture...", total=None)
            task2 = progress.add_task("Génération du schéma fonctionnel...", total=None)

            arch_result, func_result = await asyncio.gather(
                self._generate_architecture(),
                self._generate_functional(),
            )

            if arch_result:
                generated["architecture.drawio"] = arch_result
                progress.update(task1, description="[green]✓ Architecture générée[/green]")
            else:
                progress.update(task1, description="[yellow]⚠ Architecture : échec[/yellow]")

            if func_result:
                generated["functional.drawio"] = func_result
                progress.update(task2, description="[green]✓ Schéma fonctionnel généré[/green]")
            else:
                progress.update(task2, description="[yellow]⚠ Schéma fonctionnel : échec[/yellow]")

            # Phase 2 : Documentation texte (parallèle)
            task3 = progress.add_task("Génération de la doc de développement...", total=None)
            task4 = progress.add_task("Génération des TODOs...", total=None)
            task5 = progress.add_task("Génération du SETUP.md...", total=None)

            dev_result, todo_result, setup_result = await asyncio.gather(
                self._generate_development_docs(),
                self._generate_todo(),
                self._generate_setup(),
            )

            if dev_result:
                generated["DEVELOPMENT.md"] = dev_result
                progress.update(task3, description="[green]✓ Documentation développement[/green]")
            else:
                progress.update(task3, description="[yellow]⚠ Doc développement : échec[/yellow]")

            if todo_result:
                generated["TODO.md"] = todo_result
                progress.update(task4, description="[green]✓ TODOs générés[/green]")
            else:
                progress.update(task4, description="[yellow]⚠ TODOs : échec[/yellow]")

            if setup_result:
                generated["SETUP.md"] = setup_result
                progress.update(task5, description="[green]✓ SETUP.md généré[/green]")
            else:
                progress.update(task5, description="[yellow]⚠ SETUP.md : échec[/yellow]")

            # Phase 3 : README (a besoin de connaître les fichiers générés)
            task6 = progress.add_task("Génération du README.md...", total=None)
            readme_result = await self._generate_readme()
            if readme_result:
                generated["README.md"] = readme_result
                progress.update(task6, description="[green]✓ README.md généré[/green]")
            else:
                progress.update(task6, description="[yellow]⚠ README.md : échec[/yellow]")

            # Phase 4 : Export PNG
            if self.config.export_png:
                task7 = progress.add_task("Export PNG des diagrammes...", total=None)
                png_files = self.exporter.export_all(self.output_dir)
                for png in png_files:
                    generated[png.name] = png
                if png_files:
                    progress.update(task7, description=f"[green]✓ {len(png_files)} PNG exportés[/green]")
                else:
                    progress.update(task7, description="[yellow]⚠ Export PNG : draw.io non disponible[/yellow]")

        # Résumé
        console.print()
        console.print(Panel(
            "\n".join(f"  ✓ {name}" for name in sorted(generated.keys())),
            title=f"📁 {len(generated)} fichiers générés dans {self.output_dir}",
            border_style="green",
        ))

        return generated

    async def _check_models(self) -> None:
        """Vérifie que les modèles requis sont disponibles sur leur backend."""
        models_config = [
            ("analyse de code", self.config.code_model,
             self.config.code_backend, self.config.code_url),
            ("documentation", self.config.doc_model,
             self.config.doc_backend, self.config.doc_url),
            ("diagrammes", self.config.diagram_model,
             self.config.diagram_backend, self.config.diagram_url),
        ]

        for usage, model, backend_opt, url_opt in models_config:
            backend = self.config.resolve_backend(model, backend_opt)
            url = self.config.resolve_url(backend, url_opt)

            # Vérifier la connexion au backend
            backend_ok = await self.llm._check_url(url, backend)
            if not backend_ok:
                console.print(
                    f"[red]✗ Backend {backend} ({url}) non accessible "
                    f"pour le modèle {usage}.[/red]"
                )
                continue

            # Vérifier la disponibilité du modèle
            available = await self.llm.list_models(url=url, backend=backend)
            model_base = model.split(":")[0].split("/")[-1]
            found = (
                model in available
                or any(m.startswith(model_base) or model in m for m in available)
            )

            if not found:
                console.print(
                    f"[yellow]⚠ Modèle '{model}' ({usage}) non trouvé sur "
                    f"{backend} @ {url}.[/yellow]"
                )
                if backend == "ollama":
                    console.print(f"  → Téléchargement via : ollama pull {model}")
                    await self.llm.pull_model(model)
                else:
                    console.print(
                        f"  → Téléchargez-le via LM Studio ou votre runtime MLX."
                    )
            else:
                console.print(
                    f"[dim]✓ {usage} : {model} disponible sur {backend}[/dim]"
                )

    async def _generate_architecture(self) -> Path | None:
        """Génère le diagramme d'architecture via Mermaid + analyse statique."""
        prompt = self.prompts.architecture_prompt()
        system = (
            "Tu es un architecte logiciel expert. Tu génères des diagrammes Mermaid "
            "précis et complets. Chaque composant DOIT avoir au moins une connexion (flèche). "
            "Sois exhaustif sur les relations entre composants."
        )

        response = await self.llm.generate_for_diagram(prompt, system_prompt=system)

        if response:
            diagram = parse_mermaid(response)

            # Enrichir avec les connexions détectées par l'analyse statique
            diagram = self._enrich_with_static_analysis(diagram)

            if diagram.nodes:
                # Sauvegarder le source Mermaid
                mermaid_path = self.output_dir / "architecture.mermaid.md"
                safe_write(mermaid_path, f"```mermaid\n{response.strip()}\n```")

                # Convertir en DrawIO
                xml = self.drawio.build_from_mermaid(diagram, title=f"Architecture de {self.project.name}")
                output_path = self.output_dir / "architecture.drawio"
                safe_write(output_path, xml)
                return output_path

        # Fallback : JSON classique si Mermaid échoue
        console.print("[yellow]⚠ Mermaid invalide, fallback sur le mode JSON[/yellow]")
        arch_data = self._fallback_architecture()
        xml = self.drawio.build_architecture_diagram(arch_data)
        output_path = self.output_dir / "architecture.drawio"
        safe_write(output_path, xml)
        return output_path

    async def _generate_functional(self) -> Path | None:
        """Génère le diagramme fonctionnel via Mermaid."""
        prompt = self.prompts.functional_prompt()
        system = (
            "Tu es un analyste fonctionnel expert. Tu génères des diagrammes Mermaid "
            "décrivant les flux utilisateur et les fonctionnalités métier. "
            "Chaque acteur et fonctionnalité DOIT avoir des flèches de connexion."
        )

        response = await self.llm.generate_for_diagram(prompt, system_prompt=system)

        if response:
            diagram = parse_mermaid(response)

            if diagram.nodes:
                # Sauvegarder le source Mermaid
                mermaid_path = self.output_dir / "functional.mermaid.md"
                safe_write(mermaid_path, f"```mermaid\n{response.strip()}\n```")

                # Convertir en DrawIO
                xml = self.drawio.build_from_mermaid(diagram, title=f"Schéma fonctionnel de {self.project.name}")
                output_path = self.output_dir / "functional.drawio"
                safe_write(output_path, xml)
                return output_path

        # Fallback
        console.print("[yellow]⚠ Mermaid invalide, fallback sur le mode JSON[/yellow]")
        func_data = self._fallback_functional()
        xml = self.drawio.build_functional_diagram(func_data)
        output_path = self.output_dir / "functional.drawio"
        safe_write(output_path, xml)
        return output_path

    def _enrich_with_static_analysis(self, diagram):
        """Enrichit un diagramme Mermaid avec les dépendances détectées statiquement."""
        from documenta.drawio.mermaid_parser import MermaidEdge, MermaidNode

        try:
            analyzer = ImportAnalyzer(self.project.root_path, self.project.files)
            dep_graph = analyzer.analyze()

            # Ajouter les connexions détectées dans les imports
            existing_edges = {(e.source, e.target) for e in diagram.edges}
            module_groups = dep_graph.get_module_groups()

            for dep in dep_graph.dependencies:
                # Simplifier les noms pour matcher les noeuds du diagramme
                src_short = dep.source.split("/")[0]
                tgt_short = dep.target.split("/")[0]

                # Chercher des noeuds correspondants dans le diagramme
                src_node = self._find_matching_node(diagram, src_short)
                tgt_node = self._find_matching_node(diagram, tgt_short)

                if src_node and tgt_node and src_node != tgt_node:
                    if (src_node, tgt_node) not in existing_edges:
                        existing_edges.add((src_node, tgt_node))
                        diagram.edges.append(MermaidEdge(
                            source=src_node,
                            target=tgt_node,
                            label=dep.import_name,
                            style="dotted",
                        ))
        except Exception:
            pass  # Ne pas échouer si l'analyse statique a un problème

        return diagram

    def _find_matching_node(self, diagram, name: str) -> str | None:
        """Trouve un noeud du diagramme dont le label ou l'ID correspond."""
        name_lower = name.lower()
        for node_id, node in diagram.nodes.items():
            if name_lower in node_id.lower() or name_lower in node.label.lower():
                return node_id
        return None

    async def _generate_development_docs(self) -> Path | None:
        """Génère la documentation de développement."""
        prompt = self.prompts.development_docs_prompt()
        system = (
            "Tu es un rédacteur technique senior. Tu rédiges de la documentation "
            "de développement claire, structurée et détaillée en français. "
            "Utilise le format Markdown."
        )

        response = await self.llm.generate_for_docs(prompt, system_prompt=system)
        if not response:
            return None

        output_path = self.output_dir / "DEVELOPMENT.md"
        safe_write(output_path, response)
        return output_path

    async def _generate_todo(self) -> Path | None:
        """Génère la liste des points restants."""
        prompt = self.prompts.todo_prompt()
        system = (
            "Tu es un développeur senior qui fait une revue de code approfondie. "
            "Tu identifies les TODOs, les améliorations nécessaires et la dette technique. "
            "Sois précis et actionnable."
        )

        response = await self.llm.generate_for_code(prompt, system_prompt=system)
        if not response:
            return None

        output_path = self.output_dir / "TODO.md"
        safe_write(output_path, response)
        return output_path

    async def _generate_setup(self) -> Path | None:
        """Génère le guide d'installation."""
        prompt = self.prompts.setup_prompt()
        system = (
            "Tu es un DevOps expert. Tu rédiges des guides d'installation "
            "clairs et complets. Chaque étape doit être vérifiable."
        )

        response = await self.llm.generate_for_docs(prompt, system_prompt=system)
        if not response:
            return None

        output_path = self.output_dir / "SETUP.md"
        safe_write(output_path, response)
        return output_path

    async def _generate_readme(self) -> Path | None:
        """Génère le README.md principal (à la racine du projet)."""
        prompt = self.prompts.readme_prompt()
        system = (
            "Tu es un développeur open-source expérimenté. Tu rédiges des README "
            "professionnels, clairs et engageants en français."
        )

        response = await self.llm.generate_for_docs(prompt, system_prompt=system)
        if not response:
            return None

        # Le README va à la racine du projet
        output_path = self.project.root_path / "README.md"
        safe_write(output_path, response)
        return output_path

    def _fallback_architecture(self) -> dict:
        """Architecture fallback basée sur l'analyse statique."""
        p = self.project
        layers = []

        # Détecter les couches à partir des langages et frameworks
        if any(fw in str(p.tech_stack.frameworks) for fw in ["React", "Vue", "Angular", "Svelte", "Next"]):
            layers.append({
                "name": "Frontend",
                "components": [{"name": fw, "description": "Interface utilisateur", "technology": fw, "files": []}
                               for fw in p.tech_stack.frameworks if fw in ["React", "Vue.js", "Angular", "Svelte", "Next.js"]],
            })

        backend_fws = [fw for fw in p.tech_stack.frameworks
                       if fw in ["FastAPI", "Django", "Flask", "Express.js", "NestJS", "Spring Boot"]]
        if backend_fws:
            layers.append({
                "name": "Backend / API",
                "components": [{"name": fw, "description": "Serveur applicatif", "technology": fw, "files": []}
                               for fw in backend_fws],
            })

        if p.tech_stack.databases:
            layers.append({
                "name": "Base de données",
                "components": [{"name": db, "description": "Stockage", "technology": db, "files": []}
                               for db in p.tech_stack.databases],
            })

        if not layers:
            layers.append({
                "name": "Application",
                "components": [
                    {"name": p.name, "description": "Application principale",
                     "technology": ", ".join(p.tech_stack.languages[:3]), "files": []}
                ],
            })

        return {
            "title": f"Architecture de {p.name}",
            "layers": layers,
            "connections": [],
            "external_services": [],
        }

    def _fallback_functional(self) -> dict:
        """Schéma fonctionnel fallback."""
        return {
            "title": f"Schéma fonctionnel de {self.project.name}",
            "actors": [{"name": "Utilisateur", "description": "Utilisateur de l'application"}],
            "features": [
                {"name": self.project.name, "description": "Fonctionnalité principale",
                 "actor": "Utilisateur", "steps": ["Lancer l'application", "Utiliser les fonctionnalités"]},
            ],
            "flows": [],
        }
