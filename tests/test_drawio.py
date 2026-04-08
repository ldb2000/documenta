"""Tests pour le module DrawIO."""

from documenta.drawio.builder import DrawioBuilder, parse_llm_json


def test_build_architecture_diagram():
    """Test de la génération d'un diagramme d'architecture."""
    builder = DrawioBuilder()

    arch_data = {
        "title": "Architecture Test",
        "layers": [
            {
                "name": "Frontend",
                "components": [
                    {"name": "React App", "description": "UI", "technology": "React", "files": []},
                ],
            },
            {
                "name": "Backend",
                "components": [
                    {"name": "API Server", "description": "API REST", "technology": "FastAPI", "files": []},
                ],
            },
        ],
        "connections": [
            {"from": "React App", "to": "API Server", "label": "HTTP/REST", "direction": "down"},
        ],
        "external_services": [
            {"name": "PostgreSQL", "type": "Database"},
        ],
    }

    xml = builder.build_architecture_diagram(arch_data)

    assert '<?xml version="1.0"' in xml
    assert "<mxfile" in xml
    assert "Architecture Test" in xml
    assert "Frontend" in xml
    assert "React App" in xml
    assert "API Server" in xml
    assert "PostgreSQL" in xml


def test_build_functional_diagram():
    """Test de la génération d'un diagramme fonctionnel."""
    builder = DrawioBuilder()

    func_data = {
        "title": "Schéma fonctionnel Test",
        "actors": [
            {"name": "Utilisateur", "description": "Utilisateur final"},
        ],
        "features": [
            {
                "name": "Connexion",
                "description": "Authentification",
                "actor": "Utilisateur",
                "steps": ["Saisir email", "Saisir mot de passe", "Valider"],
            },
        ],
        "flows": [
            {
                "name": "Flux de connexion",
                "steps": [
                    {"actor": "Utilisateur", "action": "Soumet le formulaire", "target": "API"},
                    {"actor": "API", "action": "Vérifie les credentials", "target": "DB"},
                ],
            },
        ],
    }

    xml = builder.build_functional_diagram(func_data)

    assert '<?xml version="1.0"' in xml
    assert "Utilisateur" in xml
    assert "Connexion" in xml


def test_parse_llm_json_clean():
    """Test de parsing JSON propre."""
    raw = '{"title": "test", "layers": []}'
    result = parse_llm_json(raw)
    assert result["title"] == "test"


def test_parse_llm_json_markdown():
    """Test de parsing JSON dans un bloc markdown."""
    raw = '```json\n{"title": "test", "layers": []}\n```'
    result = parse_llm_json(raw)
    assert result["title"] == "test"


def test_parse_llm_json_with_text():
    """Test de parsing JSON avec du texte autour."""
    raw = 'Voici le résultat:\n\n{"title": "test", "layers": []}\n\nVoilà!'
    result = parse_llm_json(raw)
    assert result["title"] == "test"


def test_parse_llm_json_invalid():
    """Test de parsing JSON invalide."""
    raw = "ceci n'est pas du JSON"
    result = parse_llm_json(raw)
    assert result == {}
