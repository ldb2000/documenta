"""Analyseur statique d'imports et de dépendances entre fichiers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from documenta.analyzer.project import FileInfo


@dataclass
class ModuleDependency:
    """Dépendance entre deux modules/fichiers."""

    source: str  # fichier source
    target: str  # fichier/module importé
    import_name: str  # nom de l'import
    kind: str = "import"  # import, require, include, use


@dataclass
class DependencyGraph:
    """Graphe de dépendances entre fichiers du projet."""

    dependencies: list[ModuleDependency] = field(default_factory=list)
    modules: set[str] = field(default_factory=set)

    def get_connections(self) -> list[dict]:
        """Retourne les connexions au format attendu par DrawioBuilder."""
        connections = []
        seen = set()
        for dep in self.dependencies:
            key = (dep.source, dep.target)
            if key not in seen:
                seen.add(key)
                connections.append({
                    "from": dep.source,
                    "to": dep.target,
                    "label": dep.import_name,
                    "direction": "down",
                })
        return connections

    def get_module_groups(self) -> dict[str, list[str]]:
        """Regroupe les modules par dossier parent."""
        groups: dict[str, list[str]] = {}
        for mod in self.modules:
            parts = mod.split("/")
            group = parts[0] if len(parts) > 1 else "root"
            if group not in groups:
                groups[group] = []
            if mod not in groups[group]:
                groups[group].append(mod)
        return groups


# Patterns d'import par langage
PYTHON_IMPORT = re.compile(
    r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE
)
JS_IMPORT = re.compile(
    r"""(?:import\s+.*?\s+from\s+['"]([^'"]+)['"]|"""
    r"""require\s*\(\s*['"]([^'"]+)['"]\s*\))""",
    re.MULTILINE,
)
GO_IMPORT = re.compile(
    r"""^\s*(?:import\s+(?:"([^"]+)"|\(\s*((?:\s*"[^"]+"\s*)+)\s*\)))""",
    re.MULTILINE,
)
JAVA_IMPORT = re.compile(r"^\s*import\s+([\w.]+);", re.MULTILINE)
RUST_USE = re.compile(r"^\s*use\s+([\w:]+)", re.MULTILINE)


class ImportAnalyzer:
    """Analyse les imports pour construire un graphe de dépendances."""

    def __init__(self, project_root: Path, files: list[FileInfo]):
        self.project_root = project_root
        self.files = files
        self._file_map: dict[str, FileInfo] = {f.relative_path: f for f in files}

    def analyze(self) -> DependencyGraph:
        """Analyse tous les fichiers et retourne le graphe de dépendances."""
        graph = DependencyGraph()

        for f in self.files:
            if not f.content:
                continue

            graph.modules.add(f.relative_path)
            deps = self._extract_imports(f)

            for dep in deps:
                graph.dependencies.append(dep)
                graph.modules.add(dep.target)

        return graph

    def _extract_imports(self, file_info: FileInfo) -> list[ModuleDependency]:
        """Extrait les imports d'un fichier selon son langage."""
        ext = file_info.extension
        content = file_info.content or ""

        if ext == ".py":
            return self._extract_python_imports(file_info.relative_path, content)
        elif ext in (".js", ".ts", ".tsx", ".jsx", ".vue", ".svelte"):
            return self._extract_js_imports(file_info.relative_path, content)
        elif ext == ".go":
            return self._extract_go_imports(file_info.relative_path, content)
        elif ext in (".java", ".kt", ".scala"):
            return self._extract_java_imports(file_info.relative_path, content)
        elif ext == ".rs":
            return self._extract_rust_imports(file_info.relative_path, content)
        return []

    def _extract_python_imports(self, source: str, content: str) -> list[ModuleDependency]:
        deps = []
        for match in PYTHON_IMPORT.finditer(content):
            module = match.group(1) or match.group(2)
            if not module:
                continue
            resolved = self._resolve_python_module(source, module)
            if resolved:
                deps.append(ModuleDependency(
                    source=source, target=resolved,
                    import_name=module.split(".")[-1], kind="import",
                ))
        return deps

    def _resolve_python_module(self, source: str, module: str) -> str | None:
        """Résout un module Python vers un fichier du projet."""
        parts = module.split(".")
        # Essayer comme chemin direct
        candidates = [
            "/".join(parts) + ".py",
            "/".join(parts) + "/__init__.py",
            "/".join(parts),
        ]
        # Essayer relatif au dossier parent
        source_dir = str(Path(source).parent)
        if source_dir != ".":
            candidates.extend([
                source_dir + "/" + "/".join(parts) + ".py",
                source_dir + "/" + "/".join(parts) + "/__init__.py",
            ])

        for candidate in candidates:
            if candidate in self._file_map:
                return candidate
            # Chercher par dossier
            for existing in self._file_map:
                if existing.startswith(candidate.rstrip("/")):
                    return candidate.split("/")[0] if "/" in candidate else candidate

        # Si c'est un module interne au projet (premier segment = dossier existant)
        first_part = parts[0]
        for existing in self._file_map:
            if existing.startswith(first_part + "/"):
                return first_part + "/" + "/".join(parts[1:]) if len(parts) > 1 else first_part
        return None

    def _extract_js_imports(self, source: str, content: str) -> list[ModuleDependency]:
        deps = []
        for match in JS_IMPORT.finditer(content):
            module = match.group(1) or match.group(2)
            if not module:
                continue
            # Ignorer les modules npm (ne commencent pas par . ou /)
            if not module.startswith((".", "/")):
                continue
            resolved = self._resolve_js_module(source, module)
            if resolved:
                deps.append(ModuleDependency(
                    source=source, target=resolved,
                    import_name=Path(module).stem, kind="import",
                ))
        return deps

    def _resolve_js_module(self, source: str, module: str) -> str | None:
        """Résout un module JS/TS vers un fichier du projet."""
        source_dir = str(Path(source).parent)
        if source_dir == ".":
            base = module.lstrip("./")
        else:
            base = source_dir + "/" + module.lstrip("./")

        # Normaliser le chemin
        base = str(Path(base))

        extensions = ["", ".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte",
                       "/index.ts", "/index.tsx", "/index.js", "/index.jsx"]
        for ext in extensions:
            candidate = base + ext
            if candidate in self._file_map:
                return candidate
        return None

    def _extract_go_imports(self, source: str, content: str) -> list[ModuleDependency]:
        deps = []
        for match in GO_IMPORT.finditer(content):
            single = match.group(1)
            multi = match.group(2)
            modules = []
            if single:
                modules.append(single)
            if multi:
                modules.extend(re.findall(r'"([^"]+)"', multi))

            for module in modules:
                # Garder seulement les imports internes au projet
                parts = module.split("/")
                short_name = parts[-1]
                deps.append(ModuleDependency(
                    source=source, target=module,
                    import_name=short_name, kind="import",
                ))
        return deps

    def _extract_java_imports(self, source: str, content: str) -> list[ModuleDependency]:
        deps = []
        for match in JAVA_IMPORT.finditer(content):
            module = match.group(1)
            if module.startswith(("java.", "javax.", "org.junit")):
                continue
            parts = module.split(".")
            short_name = parts[-1]
            deps.append(ModuleDependency(
                source=source, target=module,
                import_name=short_name, kind="import",
            ))
        return deps

    def _extract_rust_imports(self, source: str, content: str) -> list[ModuleDependency]:
        deps = []
        for match in RUST_USE.finditer(content):
            module = match.group(1)
            if module.startswith("std::"):
                continue
            parts = module.split("::")
            short_name = parts[-1]
            deps.append(ModuleDependency(
                source=source, target=module.replace("::", "/"),
                import_name=short_name, kind="use",
            ))
        return deps
