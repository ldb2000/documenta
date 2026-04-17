"""Client LLM multi-backend (Ollama + OpenAI-compatible)."""

from __future__ import annotations

import httpx
from rich.console import Console

from documenta.config import Backend, DocumentaConfig

console = Console()


class LLMClient:
    """Client LLM unifié supportant Ollama et les API OpenAI-compatibles.

    Les API OpenAI-compatibles incluent : LM Studio, mlx-lm, vLLM, jan.ai,
    llama-cpp-python, et l'endpoint OpenAI-compat d'Ollama lui-même.
    """

    def __init__(self, config: DocumentaConfig | None = None):
        self.config = config or DocumentaConfig()

    async def _check_url(self, url: str, backend: Backend) -> bool:
        """Vérifie qu'un endpoint est accessible."""
        try:
            endpoint = (
                f"{url}/api/tags" if backend == "ollama" else f"{url}/models"
            )
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(endpoint)
                return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def check_connection(
        self, url: str | None = None, backend: Backend | None = None,
    ) -> bool:
        """Vérifie la connexion au backend par défaut."""
        b = backend or self.config.default_backend
        u = url or self.config.resolve_url(b)
        return await self._check_url(u, b)

    async def list_models(
        self, url: str | None = None, backend: Backend | None = None,
    ) -> list[str]:
        """Liste les modèles disponibles sur un backend."""
        b = backend or self.config.default_backend
        u = url or self.config.resolve_url(b)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if b == "ollama":
                    resp = await client.get(f"{u}/api/tags")
                    resp.raise_for_status()
                    data = resp.json()
                    return [m["name"] for m in data.get("models", [])]
                else:
                    # OpenAI-compatible
                    resp = await client.get(f"{u}/models")
                    resp.raise_for_status()
                    data = resp.json()
                    return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    async def generate(
        self,
        prompt: str,
        model: str,
        backend: Backend,
        url: str,
        temperature: float = 0.3,
        system_prompt: str | None = None,
    ) -> str:
        """Génère une réponse en choisissant le bon protocole selon le backend."""
        if backend == "ollama":
            return await self._generate_ollama(
                prompt, model, url, temperature, system_prompt,
            )
        return await self._generate_openai_compat(
            prompt, model, url, temperature, system_prompt,
        )

    async def _generate_ollama(
        self,
        prompt: str,
        model: str,
        url: str,
        temperature: float,
        system_prompt: str | None,
    ) -> str:
        """Appel Ollama natif."""
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

        return await self._post_with_retry(
            url=f"{url}/api/generate",
            payload=payload,
            response_key="response",
            model=model,
        )

    async def _generate_openai_compat(
        self,
        prompt: str,
        model: str,
        url: str,
        temperature: float,
        system_prompt: str | None,
    ) -> str:
        """Appel à une API OpenAI-compatible (LM Studio, mlx-lm, vLLM, etc.)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 8192,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                resp = await client.post(
                    f"{url}/chat/completions",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return ""
        except httpx.ConnectError:
            console.print(
                f"[red]✗ Impossible de se connecter à {url}.[/red]\n"
                "  Vérifiez que LM Studio / mlx-lm / votre serveur tourne."
            )
            return ""
        except Exception as e:
            console.print(f"[red]✗ Erreur LLM ({model} @ {url}): {e}[/red]")
            return ""

    async def _post_with_retry(
        self, url: str, payload: dict, response_key: str, model: str,
    ) -> str:
        """Appel HTTP POST avec retry."""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json().get(response_key, "")
        except httpx.TimeoutException:
            console.print(f"[yellow]⚠ Timeout pour {model}. Réessai...[/yellow]")
            try:
                async with httpx.AsyncClient(timeout=600.0) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    return resp.json().get(response_key, "")
            except Exception as e:
                console.print(f"[red]✗ Erreur avec {model}: {e}[/red]")
                return ""
        except httpx.ConnectError:
            console.print(
                f"[red]✗ Impossible de se connecter à {url}.[/red]"
            )
            return ""
        except Exception as e:
            console.print(f"[red]✗ Erreur LLM ({model}): {e}[/red]")
            return ""

    async def generate_for_code(self, prompt: str, system_prompt: str | None = None) -> str:
        """Génère avec le modèle d'analyse de code."""
        backend = self.config.resolve_backend(
            self.config.code_model, self.config.code_backend,
        )
        url = self.config.resolve_url(backend, self.config.code_url)
        return await self.generate(
            prompt=prompt,
            model=self.config.code_model,
            backend=backend,
            url=url,
            temperature=self.config.code_temperature,
            system_prompt=system_prompt,
        )

    async def generate_for_docs(self, prompt: str, system_prompt: str | None = None) -> str:
        """Génère avec le modèle de documentation."""
        backend = self.config.resolve_backend(
            self.config.doc_model, self.config.doc_backend,
        )
        url = self.config.resolve_url(backend, self.config.doc_url)
        return await self.generate(
            prompt=prompt,
            model=self.config.doc_model,
            backend=backend,
            url=url,
            temperature=self.config.doc_temperature,
            system_prompt=system_prompt,
        )

    async def generate_for_diagram(self, prompt: str, system_prompt: str | None = None) -> str:
        """Génère avec le modèle de diagrammes."""
        backend = self.config.resolve_backend(
            self.config.diagram_model, self.config.diagram_backend,
        )
        url = self.config.resolve_url(backend, self.config.diagram_url)
        return await self.generate(
            prompt=prompt,
            model=self.config.diagram_model,
            backend=backend,
            url=url,
            temperature=self.config.diagram_temperature,
            system_prompt=system_prompt,
        )

    async def ensure_model(self, model_name: str) -> bool:
        """Vérifie qu'un modèle est disponible."""
        available = await self.list_models()
        for m in available:
            if m == model_name or m.startswith(model_name.split(":")[0]):
                return True
        return False

    async def pull_model(self, model_name: str) -> bool:
        """Télécharge un modèle via Ollama (seulement pour backend Ollama)."""
        console.print(f"[cyan]⬇ Téléchargement du modèle {model_name}...[/cyan]")
        try:
            async with httpx.AsyncClient(timeout=1800.0) as client:
                resp = await client.post(
                    f"{self.config.ollama_base_url}/api/pull",
                    json={"name": model_name, "stream": False},
                )
                resp.raise_for_status()
                console.print(f"[green]✓ Modèle {model_name} téléchargé.[/green]")
                return True
        except Exception as e:
            console.print(f"[red]✗ Erreur téléchargement {model_name}: {e}[/red]")
            return False


# Alias rétro-compatible
OllamaClient = LLMClient
