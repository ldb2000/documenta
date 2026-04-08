"""Tests pour le parseur Mermaid et la conversion DrawIO."""

from documenta.drawio.mermaid_parser import parse_mermaid
from documenta.drawio.builder import DrawioBuilder


SAMPLE_ARCH_MERMAID = """```mermaid
flowchart TD
    subgraph Frontend["Frontend"]
        UI[React App]
        Router[React Router]
    end
    subgraph Backend["Backend API"]
        API[FastAPI Server]
        Auth[Auth Service]
    end
    subgraph Data["Base de données"]
        DB[(PostgreSQL)]
        Cache[(Redis)]
    end

    UI -->|HTTP REST| API
    UI --> Router
    API -->|SQL| DB
    API -->|Cache| Cache
    API --> Auth
    Auth -.->|JWT| UI
```"""


SAMPLE_FUNC_MERMAID = """```mermaid
flowchart LR
    User((Utilisateur))
    Admin((Admin))

    subgraph AuthModule["Authentification"]
        Login[Connexion]
        Register[Inscription]
    end
    subgraph AppModule["Application"]
        Dashboard[Tableau de bord]
        Settings[Paramètres]
    end

    User -->|Se connecter| Login
    User -->|S'inscrire| Register
    Login -->|Succès| Dashboard
    Admin -->|Gérer| Settings
    Dashboard -.->|Données| User
```"""


def test_parse_mermaid_architecture():
    """Test du parsing d'un diagramme d'architecture."""
    diagram = parse_mermaid(SAMPLE_ARCH_MERMAID)

    assert diagram.direction == "TD"
    assert "UI" in diagram.nodes
    assert "API" in diagram.nodes
    assert "DB" in diagram.nodes
    assert diagram.nodes["DB"].shape == "cylinder"
    assert len(diagram.edges) >= 5
    assert len(diagram.subgraphs) == 3


def test_parse_mermaid_functional():
    """Test du parsing d'un diagramme fonctionnel."""
    diagram = parse_mermaid(SAMPLE_FUNC_MERMAID)

    assert diagram.direction == "LR"
    assert "User" in diagram.nodes
    assert diagram.nodes["User"].shape == "circle"
    assert len(diagram.edges) >= 4
    assert len(diagram.subgraphs) == 2


def test_mermaid_edges_have_labels():
    """Test que les labels des flèches sont bien parsés."""
    diagram = parse_mermaid(SAMPLE_ARCH_MERMAID)

    labeled_edges = [e for e in diagram.edges if e.label]
    assert len(labeled_edges) >= 3

    labels = {e.label for e in labeled_edges}
    assert "HTTP REST" in labels or "SQL" in labels


def test_mermaid_dotted_edges():
    """Test des flèches en pointillé."""
    diagram = parse_mermaid(SAMPLE_ARCH_MERMAID)

    dotted = [e for e in diagram.edges if e.style == "dotted"]
    assert len(dotted) >= 1


def test_mermaid_subgraph_assignment():
    """Test que les noeuds sont assignés aux bons sous-graphes."""
    diagram = parse_mermaid(SAMPLE_ARCH_MERMAID)

    frontend_sg = next(sg for sg in diagram.subgraphs if sg.id == "Frontend")
    assert "UI" in frontend_sg.nodes
    assert "Router" in frontend_sg.nodes

    data_sg = next(sg for sg in diagram.subgraphs if sg.id == "Data")
    assert "DB" in data_sg.nodes


def test_build_drawio_from_mermaid():
    """Test de la conversion complète Mermaid → DrawIO XML."""
    diagram = parse_mermaid(SAMPLE_ARCH_MERMAID)
    builder = DrawioBuilder()

    xml = builder.build_from_mermaid(diagram, title="Test Architecture")

    assert '<?xml version="1.0"' in xml
    assert "<mxfile" in xml
    assert "Test Architecture" in xml
    # Vérifier que les noeuds sont présents
    assert "React App" in xml
    assert "FastAPI Server" in xml
    assert "PostgreSQL" in xml
    # Vérifier que les flèches sont présentes (edge="1")
    assert 'edge="1"' in xml


def test_build_drawio_from_mermaid_horizontal():
    """Test de la conversion d'un diagramme LR."""
    diagram = parse_mermaid(SAMPLE_FUNC_MERMAID)
    builder = DrawioBuilder()

    xml = builder.build_from_mermaid(diagram, title="Test Fonctionnel")

    assert "Utilisateur" in xml
    assert "Connexion" in xml
    assert 'edge="1"' in xml


def test_parse_mermaid_empty():
    """Test du parsing d'un texte sans Mermaid."""
    diagram = parse_mermaid("Ceci n'est pas du Mermaid")
    assert len(diagram.nodes) == 0
    assert len(diagram.edges) == 0


def test_parse_mermaid_without_backticks():
    """Test du parsing de Mermaid sans blocs markdown."""
    raw = """flowchart TD
    A[Premier] --> B[Second]
    B --> C[Troisième]
"""
    diagram = parse_mermaid(raw)
    assert "A" in diagram.nodes
    assert "B" in diagram.nodes
    assert "C" in diagram.nodes
    assert len(diagram.edges) == 2
