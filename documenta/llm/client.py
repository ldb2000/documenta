"""Client Ollama pour interagir avec les LLMs locaux."""

from __future__ import annotations

import httpx
from rich.console import Console

from documenta.config import DocumentaConfig

console = Console()


class OllamaClient:
    """Client pour communiquer avec Ollama en local."""

    def __init__(self, config: DocumentaConfig | None = None):
        self.config = config or DocumentaConfig()
        self.base_url = self.config.ollama_base_url

    async def check_connection(self) -> bool:
        """Vérifie que Ollama est accessible."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def list_models(self) -> list[str]:
        """Liste les modèles disponibles localement."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Génère une réponse avec un modèle LLM.

        Args:
            prompt: Le prompt utilisateur.
            model: Le modèle à utiliser (par défaut doc_model).
            temperature: La température de génération.
            system_prompt: Prompt système optionnel.

        Returns:
            La réponse générée par le LLM.
        """
        model = model or self.config.doc_model
        temperature = temperature if temperature is not None else self.config.doc_temperature

        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": self.config.max_context_length,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
        except httpx.TimeoutException:
            console.print(f"[yellow]⚠ Timeout pour le modèle {model}. Réessai...[/yellow]")
            # Retry une fois avec un timeout plus long
            try:
                async with httpx.AsyncClient(timeout=600.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                    )
                    resp.raise_for_status()
                    return resp.json().get("response", "")
            except Exception as e:
                console.print(f"[red]✗ Erreur avec {model}: {e}[/red]")
                return ""
        except httpx.ConnectError:
            console.print(
                f"[red]✗ Impossible de se connecter à Ollama ({self.base_url}). "
                "Vérifiez qu'Ollama est lancé.[/red]"
            )
            return ""
        except Exception as e:
            console.print(f"[red]✗ Erreur LLM ({model}): {e}[/red]")
            return ""

    async def generate_for_code(self, prompt: str, system_prompt: str | None = None) -> str:
        """Génère avec le modèle d'analyse de code."""
        return await self.generate(
            prompt=prompt,
            model=self.config.code_model,
            temperature=self.config.code_temperature,
            system_prompt=system_prompt,
        )

    async def generate_for_docs(self, prompt: str, system_prompt: str | None = None) -> str:
        """Génère avec le modèle de documentation."""
        return await self.generate(
            prompt=prompt,
            model=self.config.doc_model,
            temperature=self.config.doc_temperature,
            system_prompt=system_prompt,
        )

    async def generate_for_diagram(self, prompt: str, system_prompt: str | None = None) -> str:
        """Génère avec le modèle de diagrammes."""
        return await self.generate(
            prompt=prompt,
            model=self.config.diagram_model,
            temperature=self.config.diagram_temperature,
            system_prompt=system_prompt,
        )

    async def ensure_model(self, model_name: str) -> bool:
        """Vérifie qu'un modèle est disponible, sinon propose de le télécharger."""
        available = await self.list_models()
        # Vérifier nom exact ou préfixe
        for m in available:
            if m == model_name or m.startswith(model_name.split(":")[0]):
                return True
        return False

    async def pull_model(self, model_name: str) -> bool:
        """Télécharge un modèle via Ollama."""
        console.print(f"[cyan]⬇ Téléchargement du modèle {model_name}...[/cyan]")
        try:
            async with httpx.AsyncClient(timeout=1800.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name, "stream": False},
                )
                resp.raise_for_status()
                console.print(f"[green]✓ Modèle {model_name} téléchargé.[/green]")
                return True
        except Exception as e:
            console.print(f"[red]✗ Erreur téléchargement {model_name}: {e}[/red]")
            return False
