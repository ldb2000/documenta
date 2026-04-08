"""Analyseur de structure de projet."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import pathspec

from documenta.config import DocumentaConfig


@dataclass
class FileInfo:
    """Informations sur un fichier du projet."""

    path: Path
    relative_path: str
    extension: str
    size_bytes: int
    content: str | None = None


@dataclass
class TechStackInfo:
    """Informations sur la stack technique détectée."""

    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    databases: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    package_manager: str | None = None
    runtime: str | None = None


@dataclass
class GitInfo:
    """Informations Git du projet."""

    branch: str | None = None
    remote_url: str | None = None
    recent_commits: list[str] = field(default_factory=list)
    contributors: list[str] = field(default_factory=list)


@dataclass
class ProjectInfo:
    """Résultat complet de l'analyse d'un projet."""

    name: str
    root_path: Path
    tech_stack: TechStackInfo
    git_info: GitInfo
    files: list[FileInfo]
    tree_structure: str
    entry_points: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    source_summary: str = ""


# Détection des langages par extension
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript (React)", ".jsx": "JavaScript (React)",
    ".java": "Java", ".kt": "Kotlin", ".scala": "Scala",
    ".go": "Go", ".rs": "Rust", ".c": "C", ".cpp": "C++", ".h": "C/C++",
    ".cs": "C#", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
    ".dart": "Dart", ".lua": "Lua", ".r": "R", ".R": "R",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".sql": "SQL", ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
    ".sass": "SASS", ".less": "LESS", ".vue": "Vue.js", ".svelte": "Svelte",
}

# Détection des frameworks par fichiers de config
FRAMEWORK_DETECTION: dict[str, dict] = {
    "package.json": {"check_content": {
        "react": "React", "next": "Next.js", "nuxt": "Nuxt.js",
        "vue": "Vue.js", "angular": "Angular", "svelte": "Svelte",
        "express": "Express.js", "fastify": "Fastify", "nestjs": "NestJS",
        "electron": "Electron", "tailwindcss": "Tailwind CSS",
    }},
    "requirements.txt": {"check_content": {
        "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
        "streamlit": "Streamlit", "celery": "Celery", "sqlalchemy": "SQLAlchemy",
        "pandas": "Pandas", "numpy": "NumPy", "pytorch": "PyTorch",
        "tensorflow": "TensorFlow", "scrapy": "Scrapy",
    }},
    "pyproject.toml": {"check_content": {
        "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
        "sqlalchemy": "SQLAlchemy", "pydantic": "Pydantic",
    }},
    "Cargo.toml": {"framework": "Rust", "check_content": {
        "actix": "Actix", "rocket": "Rocket", "axum": "Axum", "tokio": "Tokio",
    }},
    "go.mod": {"framework": "Go"},
    "pom.xml": {"framework": "Java (Maven)", "check_content": {
        "spring": "Spring Boot",
    }},
    "build.gradle": {"framework": "Java (Gradle)", "check_content": {
        "spring": "Spring Boot",
    }},
    "Gemfile": {"framework": "Ruby", "check_content": {
        "rails": "Ruby on Rails", "sinatra": "Sinatra",
    }},
    "composer.json": {"framework": "PHP", "check_content": {
        "laravel": "Laravel", "symfony": "Symfony",
    }},
    "pubspec.yaml": {"framework": "Dart/Flutter"},
    "Dockerfile": {"tool": "Docker"},
    "docker-compose.yml": {"tool": "Docker Compose"},
    "docker-compose.yaml": {"tool": "Docker Compose"},
    ".github/workflows": {"tool": "GitHub Actions"},
    ".gitlab-ci.yml": {"tool": "GitLab CI"},
    "Jenkinsfile": {"tool": "Jenkins"},
    "Makefile": {"tool": "Make"},
    "terraform": {"tool": "Terraform"},
    ".env": {"tool": "dotenv"},
    "nginx.conf": {"tool": "Nginx"},
}

DATABASE_DETECTION: dict[str, str] = {
    "postgres": "PostgreSQL", "postgresql": "PostgreSQL",
    "mysql": "MySQL", "mariadb": "MariaDB",
    "mongo": "MongoDB", "redis": "Redis",
    "sqlite": "SQLite", "elasticsearch": "Elasticsearch",
    "rabbitmq": "RabbitMQ", "kafka": "Kafka",
}


class ProjectAnalyzer:
    """Analyse un projet pour en extraire les informations clés."""

    def __init__(self, project_path: Path, config: DocumentaConfig | None = None):
        self.project_path = project_path.resolve()
        self.config = config or DocumentaConfig()
        self._build_ignore_spec()

    def _build_ignore_spec(self) -> None:
        """Construit le spec d'exclusion à partir des patterns de config + .gitignore."""
        patterns = list(self.config.ignore_patterns)
        gitignore_path = self.project_path / ".gitignore"
        if gitignore_path.exists():
            patterns.extend(
                line.strip()
                for line in gitignore_path.read_text(errors="ignore").splitlines()
                if line.strip() and not line.startswith("#")
            )
        self._ignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    def analyze(self) -> ProjectInfo:
        """Analyse complète du projet."""
        files = self._scan_files()
        tech_stack = self._detect_tech_stack(files)
        git_info = self._get_git_info()
        tree = self._build_tree()
        entry_points = self._find_entry_points(files)
        config_files = self._find_config_files(files)

        # Lire le contenu des fichiers importants
        self._read_important_files(files)

        return ProjectInfo(
            name=self.project_path.name,
            root_path=self.project_path,
            tech_stack=tech_stack,
            git_info=git_info,
            files=files,
            tree_structure=tree,
            entry_points=entry_points,
            config_files=config_files,
        )

    def _scan_files(self) -> list[FileInfo]:
        """Scanne tous les fichiers du projet."""
        files: list[FileInfo] = []
        max_files = self.config.max_files_to_analyze

        for root, dirs, filenames in os.walk(self.project_path):
            root_path = Path(root)
            rel_root = root_path.relative_to(self.project_path)

            # Filtrer les répertoires exclus
            dirs[:] = [
                d for d in dirs
                if not self._ignore_spec.match_file(str(rel_root / d) + "/")
                and not d.startswith(".")
            ]

            for fname in filenames:
                if len(files) >= max_files:
                    break

                file_path = root_path / fname
                rel_path = str(file_path.relative_to(self.project_path))

                if self._ignore_spec.match_file(rel_path):
                    continue
                if fname.startswith(".") and fname not in (".env.example", ".gitignore"):
                    continue

                try:
                    stat = file_path.stat()
                    if stat.st_size > self.config.max_file_size_kb * 1024:
                        continue
                except OSError:
                    continue

                ext = file_path.suffix.lower()
                files.append(FileInfo(
                    path=file_path,
                    relative_path=rel_path,
                    extension=ext,
                    size_bytes=stat.st_size,
                ))

            if len(files) >= max_files:
                break

        return files

    def _detect_tech_stack(self, files: list[FileInfo]) -> TechStackInfo:
        """Détecte la stack technique du projet."""
        stack = TechStackInfo()
        lang_counts: dict[str, int] = {}

        # Détecter les langages par extension
        for f in files:
            lang = EXTENSION_LANGUAGE_MAP.get(f.extension)
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

        stack.languages = sorted(lang_counts, key=lang_counts.get, reverse=True)  # type: ignore[arg-type]

        # Détecter les frameworks et outils par fichiers de config
        existing_files = {f.relative_path for f in files}
        for config_file, detection in FRAMEWORK_DETECTION.items():
            found = config_file in existing_files or (self.project_path / config_file).exists()
            if not found:
                continue

            if "framework" in detection:
                fw = detection["framework"]
                if fw not in stack.frameworks:
                    stack.frameworks.append(fw)

            if "tool" in detection:
                tool = detection["tool"]
                if tool not in stack.tools:
                    stack.tools.append(tool)

            if "check_content" in detection:
                try:
                    content = (self.project_path / config_file).read_text(errors="ignore").lower()
                    for keyword, name in detection["check_content"].items():
                        if keyword in content and name not in stack.frameworks:
                            stack.frameworks.append(name)
                except (OSError, IsADirectoryError):
                    pass

        # Détecter les bases de données
        for f in files:
            if f.extension in (".yml", ".yaml", ".toml", ".json", ".env", ".txt", ".cfg", ".ini"):
                try:
                    content = f.path.read_text(errors="ignore").lower()
                    for keyword, db_name in DATABASE_DETECTION.items():
                        if keyword in content and db_name not in stack.databases:
                            stack.databases.append(db_name)
                except OSError:
                    pass

        # Détecter le package manager
        if "package.json" in existing_files:
            if (self.project_path / "yarn.lock").exists():
                stack.package_manager = "Yarn"
            elif (self.project_path / "pnpm-lock.yaml").exists():
                stack.package_manager = "pnpm"
            else:
                stack.package_manager = "npm"
            stack.runtime = "Node.js"
        elif "pyproject.toml" in existing_files or "requirements.txt" in existing_files:
            if (self.project_path / "poetry.lock").exists():
                stack.package_manager = "Poetry"
            elif (self.project_path / "Pipfile").exists():
                stack.package_manager = "Pipenv"
            elif (self.project_path / "uv.lock").exists():
                stack.package_manager = "uv"
            else:
                stack.package_manager = "pip"
            stack.runtime = "Python"

        return stack

    def _get_git_info(self) -> GitInfo:
        """Récupère les informations Git."""
        info = GitInfo()
        try:
            import git
            repo = git.Repo(self.project_path)
            info.branch = str(repo.active_branch)

            if repo.remotes:
                info.remote_url = repo.remotes[0].url

            for commit in repo.iter_commits(max_count=20):
                info.recent_commits.append(
                    f"{commit.hexsha[:8]} - {commit.summary} ({commit.author.name})"
                )
                author = commit.author.name
                if author not in info.contributors:
                    info.contributors.append(author)
        except Exception:
            pass

        return info

    def _build_tree(self, max_depth: int = 4) -> str:
        """Construit une représentation arborescente du projet."""
        lines: list[str] = [f"{self.project_path.name}/"]
        self._tree_walk(self.project_path, "", lines, 0, max_depth)
        return "\n".join(lines)

    def _tree_walk(
        self, path: Path, prefix: str, lines: list[str], depth: int, max_depth: int
    ) -> None:
        if depth >= max_depth:
            return

        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return

        # Filtrer les entrées
        filtered = []
        for entry in entries:
            rel = str(entry.relative_to(self.project_path))
            if entry.is_dir():
                rel += "/"
            if self._ignore_spec.match_file(rel):
                continue
            if entry.name.startswith(".") and entry.name not in (".gitignore",):
                continue
            filtered.append(entry)

        for i, entry in enumerate(filtered):
            is_last = i == len(filtered) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")

            if entry.is_dir():
                extension = "    " if is_last else "│   "
                self._tree_walk(entry, prefix + extension, lines, depth + 1, max_depth)

    def _find_entry_points(self, files: list[FileInfo]) -> list[str]:
        """Trouve les points d'entrée probables du projet."""
        entry_patterns = [
            "main.py", "app.py", "server.py", "index.py", "manage.py", "wsgi.py", "asgi.py",
            "main.ts", "main.js", "index.ts", "index.js", "server.ts", "server.js", "app.ts",
            "main.go", "main.rs", "Main.java", "Program.cs",
            "main.dart", "main.rb", "main.php",
            "src/main.py", "src/app.py", "src/index.ts", "src/main.ts",
            "src/index.js", "src/main.js", "src/main.go", "src/main.rs",
            "cmd/main.go", "cmd/server/main.go",
        ]
        found = []
        file_paths = {f.relative_path for f in files}
        for pattern in entry_patterns:
            if pattern in file_paths:
                found.append(pattern)
        return found

    def _find_config_files(self, files: list[FileInfo]) -> list[str]:
        """Trouve les fichiers de configuration."""
        config_extensions = {".toml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".conf", ".env"}
        config_names = {
            "Makefile", "Dockerfile", "Jenkinsfile", "Procfile",
            ".gitignore", ".editorconfig", ".prettierrc",
        }
        found = []
        for f in files:
            if f.extension in config_extensions or f.path.name in config_names:
                found.append(f.relative_path)
        return found

    def _read_important_files(self, files: list[FileInfo]) -> None:
        """Lit le contenu des fichiers sources importants."""
        source_extensions = {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
            ".kt", ".rb", ".php", ".cs", ".vue", ".svelte",
            ".sql", ".sh", ".yaml", ".yml", ".toml", ".json",
        }
        total_read = 0
        max_total = self.config.max_context_length * 4  # Budget total de caractères

        # Prioriser : entry points, configs, puis autres fichiers source
        priority_files = []
        source_files = []

        entry_set = set(self._find_entry_points(files))
        config_set = set(self._find_config_files(files))

        for f in files:
            if f.relative_path in entry_set:
                priority_files.insert(0, f)
            elif f.relative_path in config_set:
                priority_files.append(f)
            elif f.extension in source_extensions:
                source_files.append(f)

        for f in priority_files + source_files:
            if total_read >= max_total:
                break
            try:
                content = f.path.read_text(errors="ignore")
                if len(content) + total_read <= max_total:
                    f.content = content
                    total_read += len(content)
            except OSError:
                pass
