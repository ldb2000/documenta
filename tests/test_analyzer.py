"""Tests pour le module d'analyse de projet."""

import tempfile
from pathlib import Path

from documenta.analyzer.project import ProjectAnalyzer
from documenta.config import DocumentaConfig


def test_scan_empty_project():
    """Test d'analyse d'un projet vide."""
    with tempfile.TemporaryDirectory() as tmpdir:
        analyzer = ProjectAnalyzer(Path(tmpdir))
        info = analyzer.analyze()
        assert info.name == Path(tmpdir).name
        assert info.files == []
        assert info.tech_stack.languages == []


def test_detect_python_project():
    """Test de détection d'un projet Python."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "main.py").write_text("print('hello')")
        (path / "requirements.txt").write_text("flask\nredis\n")

        analyzer = ProjectAnalyzer(path)
        info = analyzer.analyze()

        assert "Python" in info.tech_stack.languages
        assert "Flask" in info.tech_stack.frameworks
        assert info.tech_stack.package_manager == "pip"
        assert "main.py" in info.entry_points


def test_detect_node_project():
    """Test de détection d'un projet Node.js."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "index.js").write_text("console.log('hello')")
        (path / "package.json").write_text('{"dependencies": {"express": "^4.0"}}')

        analyzer = ProjectAnalyzer(path)
        info = analyzer.analyze()

        assert "JavaScript" in info.tech_stack.languages
        assert "Express.js" in info.tech_stack.frameworks
        assert info.tech_stack.package_manager == "npm"


def test_ignore_node_modules():
    """Test que node_modules est bien ignoré."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        nm = path / "node_modules" / "some_package"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("module.exports = {}")
        (path / "app.js").write_text("const x = 1;")

        analyzer = ProjectAnalyzer(path)
        info = analyzer.analyze()

        file_paths = [f.relative_path for f in info.files]
        assert "app.js" in file_paths
        assert not any("node_modules" in p for p in file_paths)


def test_build_tree():
    """Test de la construction de l'arborescence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "src").mkdir()
        (path / "src" / "main.py").write_text("")
        (path / "README.md").write_text("")

        analyzer = ProjectAnalyzer(path)
        info = analyzer.analyze()

        assert "src/" in info.tree_structure
        assert "main.py" in info.tree_structure
        assert "README.md" in info.tree_structure


def test_config_file_detection():
    """Test de détection des fichiers de configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "pyproject.toml").write_text("[project]\nname = 'test'")
        (path / "Dockerfile").write_text("FROM python:3.12")
        (path / "Makefile").write_text("all:\n\techo hello")

        config = DocumentaConfig(ignore_patterns=[])
        analyzer = ProjectAnalyzer(path, config)
        info = analyzer.analyze()

        assert "pyproject.toml" in info.config_files
        assert "Dockerfile" in info.config_files
        assert "Makefile" in info.config_files
