"""Export des fichiers DrawIO vers PNG."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()


class DrawioExporter:
    """Exporte les fichiers .drawio en PNG."""

    DRAWIO_PATHS = [
        # macOS
        "/Applications/draw.io.app/Contents/MacOS/draw.io",
        "/Applications/drawio.app/Contents/MacOS/drawio",
        # Linux
        "/usr/bin/drawio",
        "/usr/local/bin/drawio",
        "/snap/bin/drawio",
        # Via PATH
        "drawio",
        "draw.io",
    ]

    def __init__(self):
        self._drawio_path: str | None = None

    def find_drawio(self) -> str | None:
        """Trouve l'exécutable draw.io sur le système."""
        if self._drawio_path:
            return self._drawio_path

        for path in self.DRAWIO_PATHS:
            if "/" in path:
                if Path(path).exists():
                    self._drawio_path = path
                    return path
            else:
                found = shutil.which(path)
                if found:
                    self._drawio_path = found
                    return found

        return None

    def export_to_png(
        self,
        drawio_path: Path,
        output_path: Path | None = None,
        scale: float = 2.0,
    ) -> Path | None:
        """Exporte un fichier .drawio en PNG.

        Args:
            drawio_path: Chemin vers le fichier .drawio
            output_path: Chemin de sortie PNG (par défaut même nom .png)
            scale: Facteur d'échelle (2.0 pour haute résolution)

        Returns:
            Le chemin du fichier PNG généré, ou None en cas d'échec.
        """
        drawio_exe = self.find_drawio()
        if not drawio_exe:
            console.print(
                "[yellow]⚠ draw.io non trouvé. Installe-le pour exporter en PNG :[/yellow]\n"
                "  macOS : brew install --cask drawio\n"
                "  Linux : snap install drawio"
            )
            return None

        if output_path is None:
            output_path = drawio_path.with_suffix(".png")

        try:
            result = subprocess.run(
                [
                    drawio_exe,
                    "--export",
                    "--format", "png",
                    "--scale", str(scale),
                    "--output", str(output_path),
                    str(drawio_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0 and output_path.exists():
                console.print(f"[green]✓ PNG exporté : {output_path.name}[/green]")
                return output_path
            else:
                stderr = result.stderr.strip()
                if stderr:
                    console.print(f"[yellow]⚠ Erreur export PNG: {stderr}[/yellow]")
                return None

        except subprocess.TimeoutExpired:
            console.print("[yellow]⚠ Timeout lors de l'export PNG[/yellow]")
            return None
        except FileNotFoundError:
            console.print("[yellow]⚠ draw.io introuvable pour l'export[/yellow]")
            return None
        except Exception as e:
            console.print(f"[yellow]⚠ Erreur export: {e}[/yellow]")
            return None

    def export_all(self, docs_dir: Path) -> list[Path]:
        """Exporte tous les fichiers .drawio d'un répertoire en PNG."""
        exported = []
        for drawio_file in docs_dir.glob("*.drawio"):
            png_path = self.export_to_png(drawio_file)
            if png_path:
                exported.append(png_path)
        return exported
