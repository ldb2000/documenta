"""Parseur de diagrammes Mermaid vers structure intermédiaire pour DrawIO."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class MermaidNode:
    """Noeud dans un diagramme Mermaid."""

    id: str
    label: str
    shape: str = "rect"  # rect, round, diamond, cylinder, stadium, circle
    group: str | None = None


@dataclass
class MermaidEdge:
    """Connexion dans un diagramme Mermaid."""

    source: str
    target: str
    label: str = ""
    style: str = "solid"  # solid, dotted, thick


@dataclass
class MermaidSubgraph:
    """Sous-graphe (groupe) dans un diagramme Mermaid."""

    id: str
    label: str
    nodes: list[str] = field(default_factory=list)


@dataclass
class MermaidDiagram:
    """Diagramme Mermaid parsé."""

    direction: str = "TD"  # TD, LR, BT, RL
    nodes: dict[str, MermaidNode] = field(default_factory=dict)
    edges: list[MermaidEdge] = field(default_factory=list)
    subgraphs: list[MermaidSubgraph] = field(default_factory=list)
    title: str = ""


# Patterns de noeuds Mermaid
NODE_PATTERNS = [
    # id[label] - rectangle
    (re.compile(r"^\s*(\w+)\[\"?([^\"\\]+)\"?\]", re.MULTILINE), "rect"),
    (re.compile(r"^\s*(\w+)\[([^\]]+)\]", re.MULTILINE), "rect"),
    # id(label) - rectangle arrondi
    (re.compile(r"^\s*(\w+)\(\"?([^\"\\]+)\"?\)", re.MULTILINE), "round"),
    (re.compile(r"^\s*(\w+)\(([^)]+)\)", re.MULTILINE), "round"),
    # id{label} - losange
    (re.compile(r"^\s*(\w+)\{\"?([^\"\\]+)\"?\}", re.MULTILINE), "diamond"),
    (re.compile(r"^\s*(\w+)\{([^}]+)\}", re.MULTILINE), "diamond"),
    # id[(label)] - cylindre (database)
    (re.compile(r"^\s*(\w+)\[\(\"?([^\"\\]+)\"?\)\]", re.MULTILINE), "cylinder"),
    (re.compile(r"^\s*(\w+)\[\(([^)]+)\)\]", re.MULTILINE), "cylinder"),
    # id([label]) - stadium
    (re.compile(r"^\s*(\w+)\(\[\"?([^\"\\]+)\"?\]\)", re.MULTILINE), "stadium"),
    (re.compile(r"^\s*(\w+)\(\[([^\]]+)\]\)", re.MULTILINE), "stadium"),
    # id((label)) - cercle
    (re.compile(r"^\s*(\w+)\(\(\"?([^\"\\]+)\"?\)\)", re.MULTILINE), "circle"),
    (re.compile(r"^\s*(\w+)\(\(([^)]+)\)\)", re.MULTILINE), "circle"),
]

# Patterns de connexions Mermaid
EDGE_PATTERNS = [
    # A -->|label| B  ou  A -- label --> B
    re.compile(r"(\w+)\s*-->\|([^|]*)\|\s*(\w+)"),
    re.compile(r"(\w+)\s*--\s*\"?([^\">\-]*)\"?\s*-->\s*(\w+)"),
    # A --> B
    re.compile(r"(\w+)\s*-->\s*(\w+)"),
    # A -.->|label| B (dotted)
    re.compile(r"(\w+)\s*-\.->(?:\|([^|]*)\|)?\s*(\w+)"),
    # A -.-> B (dotted)
    re.compile(r"(\w+)\s*-\.->?\s*(\w+)"),
    # A ==>|label| B (thick)
    re.compile(r"(\w+)\s*==>(?:\|([^|]*)\|)?\s*(\w+)"),
    # A ==> B (thick)
    re.compile(r"(\w+)\s*==>\s*(\w+)"),
    # A --- B (no arrow)
    re.compile(r"(\w+)\s*---(?:\|([^|]*)\|)?\s*(\w+)"),
    re.compile(r"(\w+)\s*---\s*(\w+)"),
]

SUBGRAPH_START = re.compile(r"^\s*subgraph\s+(\w+)\s*\[?\"?([^\]\"\n]*)\"?\]?", re.MULTILINE)
SUBGRAPH_END = re.compile(r"^\s*end\s*$", re.MULTILINE)
DIRECTION = re.compile(r"^\s*(?:graph|flowchart)\s+(TD|TB|LR|RL|BT)", re.MULTILINE)


def parse_mermaid(raw_text: str) -> MermaidDiagram:
    """Parse un diagramme Mermaid textuel.

    Accepte du Mermaid brut ou dans des blocs ```mermaid ... ```.
    """
    text = _clean_mermaid_text(raw_text)
    diagram = MermaidDiagram()

    # Direction
    dir_match = DIRECTION.search(text)
    if dir_match:
        diagram.direction = dir_match.group(1)

    # Subgraphs
    _parse_subgraphs(text, diagram)

    # Noeuds
    _parse_nodes(text, diagram)

    # Connexions
    _parse_edges(text, diagram)

    # Assigner les noeuds aux subgraphs
    _assign_nodes_to_subgraphs(text, diagram)

    return diagram


def _clean_mermaid_text(raw: str) -> str:
    """Nettoie le texte Mermaid (retire les blocs markdown)."""
    text = raw.strip()
    if "```mermaid" in text:
        start = text.index("```mermaid") + 10
        end = text.rindex("```") if text.count("```") > 1 else len(text)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.rindex("```") if text.count("```") > 1 else len(text)
        text = text[start:end].strip()
    return text


def _parse_subgraphs(text: str, diagram: MermaidDiagram) -> None:
    """Parse les sous-graphes."""
    for match in SUBGRAPH_START.finditer(text):
        sg_id = match.group(1)
        sg_label = match.group(2).strip() or sg_id
        diagram.subgraphs.append(MermaidSubgraph(id=sg_id, label=sg_label))


def _parse_nodes(text: str, diagram: MermaidDiagram) -> None:
    """Parse les noeuds du diagramme."""
    found_ids: set[str] = set()

    for pattern, shape in NODE_PATTERNS:
        for match in pattern.finditer(text):
            node_id = match.group(1)
            if node_id in found_ids:
                continue
            if node_id in ("graph", "flowchart", "subgraph", "end", "style", "classDef"):
                continue
            label = match.group(2).strip()
            found_ids.add(node_id)
            diagram.nodes[node_id] = MermaidNode(id=node_id, label=label, shape=shape)


def _parse_edges(text: str, diagram: MermaidDiagram) -> None:
    """Parse les connexions."""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("graph ", "flowchart ", "subgraph ", "end", "%%", "style ", "classDef ")):
            continue
        _parse_edge_line(line, diagram)


def _parse_edge_line(line: str, diagram: MermaidDiagram) -> None:
    """Parse une ligne de connexion."""
    for pattern in EDGE_PATTERNS:
        match = pattern.search(line)
        if not match:
            continue

        groups = match.groups()
        if len(groups) == 3:
            source, label, target = groups
            label = label or ""
        elif len(groups) == 2:
            source, target = groups
            label = ""
        else:
            continue

        # Déterminer le style
        style = "solid"
        if "-.->" in line:
            style = "dotted"
        elif "==>" in line:
            style = "thick"

        # Enregistrer les noeuds implicites
        for node_id in (source, target):
            if node_id not in diagram.nodes:
                diagram.nodes[node_id] = MermaidNode(id=node_id, label=node_id)

        diagram.edges.append(MermaidEdge(
            source=source, target=target, label=label, style=style,
        ))
        return  # Une seule connexion par match


def _assign_nodes_to_subgraphs(text: str, diagram: MermaidDiagram) -> None:
    """Assigne les noeuds à leurs sous-graphes."""
    lines = text.splitlines()
    current_sg: MermaidSubgraph | None = None

    for line in lines:
        stripped = line.strip()

        sg_match = SUBGRAPH_START.match(stripped)
        if sg_match:
            sg_id = sg_match.group(1)
            current_sg = next((sg for sg in diagram.subgraphs if sg.id == sg_id), None)
            continue

        if stripped == "end":
            current_sg = None
            continue

        if current_sg:
            # Chercher des IDs de noeuds dans cette ligne
            for node_id in diagram.nodes:
                if re.search(rf"\b{re.escape(node_id)}\b", stripped):
                    if node_id not in current_sg.nodes:
                        current_sg.nodes.append(node_id)
                    diagram.nodes[node_id].group = current_sg.id
