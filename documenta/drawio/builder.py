"""Constructeur de fichiers DrawIO (XML mxGraph)."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field


@dataclass
class MxCell:
    """Cellule mxGraph (nœud ou connexion)."""

    id: str
    value: str = ""
    style: str = ""
    vertex: bool = True
    edge: bool = False
    source: str = ""
    target: str = ""
    parent: str = "1"
    x: float = 0
    y: float = 0
    width: float = 120
    height: float = 60

    def to_xml(self) -> str:
        escaped_value = html.escape(self.value)
        escaped_style = html.escape(self.style)

        if self.edge:
            return (
                f'      <mxCell id="{self.id}" value="{escaped_value}" '
                f'style="{escaped_style}" edge="1" parent="{self.parent}" '
                f'source="{self.source}" target="{self.target}">\n'
                f"        <mxGeometry relative=\"1\" as=\"geometry\" />\n"
                f"      </mxCell>"
            )
        return (
            f'      <mxCell id="{self.id}" value="{escaped_value}" '
            f'style="{escaped_style}" vertex="1" parent="{self.parent}">\n'
            f'        <mxGeometry x="{self.x}" y="{self.y}" '
            f'width="{self.width}" height="{self.height}" as="geometry" />\n'
            f"      </mxCell>"
        )


# Styles prédéfinis pour les différents types de composants
STYLES = {
    "layer_header": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor={color};fontColor=#ffffff;"
        "strokeColor=none;fontSize=14;fontStyle=1;arcSize=8;"
    ),
    "component": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor={color};fontColor=#333333;"
        "strokeColor={border};fontSize=11;arcSize=6;"
    ),
    "external": (
        "shape=cloud;whiteSpace=wrap;html=1;fillColor=#f5f5f5;fontColor=#333333;"
        "strokeColor=#666666;fontSize=11;"
    ),
    "database": (
        "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;"
        "size=15;fillColor={color};fontColor=#ffffff;strokeColor={border};fontSize=11;"
    ),
    "actor": (
        "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;"
        "html=1;outlineConnect=0;fillColor={color};strokeColor={border};fontSize=11;"
    ),
    "process": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor={color};fontColor=#ffffff;"
        "strokeColor={border};fontSize=11;arcSize=12;"
    ),
    "connection": (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
        "jettySize=auto;html=1;strokeColor=#666666;fontSize=10;"
        "fontColor=#333333;exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
    ),
    "connection_right": (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
        "jettySize=auto;html=1;strokeColor=#666666;fontSize=10;"
        "fontColor=#333333;"
    ),
}

# Palette de couleurs par couche
LAYER_COLORS = [
    {"header": "#1e3a5f", "bg": "#e8f0fe", "border": "#1e3a5f"},  # Bleu foncé
    {"header": "#0d652d", "bg": "#e6f4ea", "border": "#0d652d"},  # Vert
    {"header": "#7b1fa2", "bg": "#f3e5f5", "border": "#7b1fa2"},  # Violet
    {"header": "#e65100", "bg": "#fff3e0", "border": "#e65100"},  # Orange
    {"header": "#01579b", "bg": "#e1f5fe", "border": "#01579b"},  # Bleu clair
    {"header": "#b71c1c", "bg": "#ffebee", "border": "#b71c1c"},  # Rouge
]

DB_COLORS = {"color": "#01579b", "border": "#014477"}
ACTOR_COLORS = {"color": "#1e3a5f", "border": "#1e3a5f"}
PROCESS_COLORS = [
    {"color": "#1565c0", "border": "#0d47a1"},
    {"color": "#2e7d32", "border": "#1b5e20"},
    {"color": "#6a1b9a", "border": "#4a148c"},
    {"color": "#d84315", "border": "#bf360c"},
]


class DrawioBuilder:
    """Construit un fichier DrawIO à partir de données structurées."""

    def __init__(self):
        self._cells: list[MxCell] = []
        self._id_counter = 2  # 0 et 1 réservés par mxGraph
        self._id_map: dict[str, str] = {}

    def _next_id(self) -> str:
        cell_id = str(self._id_counter)
        self._id_counter += 1
        return cell_id

    def _register_id(self, name: str) -> str:
        cell_id = self._next_id()
        self._id_map[name] = cell_id
        return cell_id

    def _get_id(self, name: str) -> str | None:
        return self._id_map.get(name)

    def build_architecture_diagram(self, arch_json: dict) -> str:
        """Construit un diagramme d'architecture à partir du JSON LLM."""
        self._cells = []
        self._id_counter = 2
        self._id_map = {}

        y_offset = 20
        layer_width = 800
        component_width = 150
        component_height = 60
        padding = 20

        layers = arch_json.get("layers", [])

        for layer_idx, layer in enumerate(layers):
            colors = LAYER_COLORS[layer_idx % len(LAYER_COLORS)]
            components = layer.get("components", [])
            n_components = max(len(components), 1)

            # Dimensions de la couche
            row_width = n_components * (component_width + padding) + padding
            actual_width = max(layer_width, row_width)
            layer_height = 120

            # Header de la couche (rectangle de fond)
            layer_id = self._next_id()
            self._cells.append(MxCell(
                id=layer_id,
                value=layer.get("name", f"Layer {layer_idx}"),
                style=STYLES["layer_header"].format(color=colors["header"]),
                x=20, y=y_offset,
                width=actual_width, height=30,
            ))

            # Composants de la couche
            comp_y = y_offset + 45
            comp_x_start = 20 + (actual_width - n_components * (component_width + padding)) / 2

            for comp_idx, comp in enumerate(components):
                comp_name = comp.get("name", f"Component {comp_idx}")
                tech = comp.get("technology", "")
                label = f"<b>{comp_name}</b><br><i>{tech}</i>" if tech else f"<b>{comp_name}</b>"

                style = STYLES["component"].format(
                    color=colors["bg"], border=colors["border"]
                )
                comp_id = self._register_id(comp_name)
                self._cells.append(MxCell(
                    id=comp_id,
                    value=label,
                    style=style,
                    x=comp_x_start + comp_idx * (component_width + padding),
                    y=comp_y,
                    width=component_width,
                    height=component_height,
                ))

            y_offset += layer_height + 20

        # Services externes
        external_services = arch_json.get("external_services", [])
        if external_services:
            ext_x = 20
            for ext_idx, ext in enumerate(external_services):
                ext_name = ext.get("name", f"Service {ext_idx}")
                ext_type = ext.get("type", "")
                label = f"<b>{ext_name}</b><br><i>{ext_type}</i>"

                if "database" in ext_type.lower() or "db" in ext_type.lower():
                    style = STYLES["database"].format(**DB_COLORS)
                else:
                    style = STYLES["external"]

                ext_id = self._register_id(ext_name)
                self._cells.append(MxCell(
                    id=ext_id,
                    value=label,
                    style=style,
                    x=ext_x + ext_idx * 180,
                    y=y_offset,
                    width=150, height=70,
                ))

            y_offset += 100

        # Connexions
        for conn in arch_json.get("connections", []):
            src_id = self._get_id(conn.get("from", ""))
            tgt_id = self._get_id(conn.get("to", ""))
            if src_id and tgt_id:
                style_key = "connection_right" if conn.get("direction") == "right" else "connection"
                edge_id = self._next_id()
                self._cells.append(MxCell(
                    id=edge_id,
                    value=conn.get("label", ""),
                    style=STYLES[style_key],
                    edge=True,
                    source=src_id,
                    target=tgt_id,
                ))

        return self._to_xml(arch_json.get("title", "Architecture"))

    def build_functional_diagram(self, func_json: dict) -> str:
        """Construit un diagramme fonctionnel à partir du JSON LLM."""
        self._cells = []
        self._id_counter = 2
        self._id_map = {}

        # Acteurs à gauche
        actors = func_json.get("actors", [])
        actor_x = 40
        actor_y = 40

        for act_idx, actor in enumerate(actors):
            actor_name = actor.get("name", f"Acteur {act_idx}")
            style = STYLES["actor"].format(**ACTOR_COLORS)
            act_id = self._register_id(actor_name)
            self._cells.append(MxCell(
                id=act_id,
                value=actor_name,
                style=style,
                x=actor_x,
                y=actor_y + act_idx * 120,
                width=40, height=60,
            ))

        # Fonctionnalités
        features = func_json.get("features", [])
        feat_x = 200
        feat_y = 30

        for feat_idx, feat in enumerate(features):
            feat_name = feat.get("name", f"Feature {feat_idx}")
            description = feat.get("description", "")
            steps = feat.get("steps", [])
            steps_text = "<br>".join(f"• {s}" for s in steps[:5])
            label = f"<b>{feat_name}</b><br><i>{description}</i><br>{steps_text}"

            colors = PROCESS_COLORS[feat_idx % len(PROCESS_COLORS)]
            style = STYLES["process"].format(**colors)
            feat_id = self._register_id(feat_name)

            self._cells.append(MxCell(
                id=feat_id,
                value=label,
                style=style,
                x=feat_x + (feat_idx % 3) * 220,
                y=feat_y + (feat_idx // 3) * 160,
                width=200, height=120,
            ))

            # Lien acteur -> fonctionnalité
            actor_name = feat.get("actor", "")
            actor_id = self._get_id(actor_name)
            if actor_id:
                edge_id = self._next_id()
                self._cells.append(MxCell(
                    id=edge_id,
                    value="",
                    style=STYLES["connection_right"],
                    edge=True,
                    source=actor_id,
                    target=feat_id,
                ))

        # Flux
        flows = func_json.get("flows", [])
        flow_y = max(
            feat_y + ((len(features) - 1) // 3 + 1) * 160 + 40,
            actor_y + len(actors) * 120 + 40,
        )

        for flow_idx, flow in enumerate(flows):
            flow_name = flow.get("name", f"Flux {flow_idx}")
            colors = PROCESS_COLORS[flow_idx % len(PROCESS_COLORS)]

            # Titre du flux
            title_id = self._next_id()
            self._cells.append(MxCell(
                id=title_id,
                value=f"<b>▶ {flow_name}</b>",
                style=f"text;html=1;fontSize=13;fontStyle=1;fillColor=none;strokeColor=none;fontColor={colors['color']};",
                x=200, y=flow_y,
                width=600, height=30,
            ))
            flow_y += 40

            steps = flow.get("steps", [])
            prev_step_id = None
            for step_idx, step in enumerate(steps):
                action = step.get("action", "")
                actor_name = step.get("actor", "")
                target = step.get("target", "")
                label = f"<b>{actor_name}</b><br>{action}"
                if target:
                    label += f"<br>→ {target}"

                step_id = self._next_id()
                self._cells.append(MxCell(
                    id=step_id,
                    value=label,
                    style=STYLES["component"].format(
                        color=colors["color"] + "22", border=colors["border"]
                    ),
                    x=200 + step_idx * 180,
                    y=flow_y,
                    width=160, height=70,
                ))

                if prev_step_id:
                    edge_id = self._next_id()
                    self._cells.append(MxCell(
                        id=edge_id,
                        value="",
                        style=STYLES["connection_right"],
                        edge=True,
                        source=prev_step_id,
                        target=step_id,
                    ))
                prev_step_id = step_id

            flow_y += 110

        return self._to_xml(func_json.get("title", "Schéma fonctionnel"))

    def _to_xml(self, title: str = "Diagram") -> str:
        """Génère le XML DrawIO complet."""
        escaped_title = html.escape(title)
        cells_xml = "\n".join(cell.to_xml() for cell in self._cells)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="documenta" modified="2024-01-01T00:00:00.000Z" type="device">
  <diagram id="auto-generated" name="{escaped_title}">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1"
                  tooltips="1" connect="1" arrows="1" fold="1" page="1"
                  pageScale="1" pageWidth="1200" pageHeight="900"
                  math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
{cells_xml}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""


def parse_llm_json(raw_response: str) -> dict:
    """Parse le JSON d'une réponse LLM (gère les blocs markdown)."""
    text = raw_response.strip()

    # Retirer les blocs ```json ... ```
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.rindex("```") if text.count("```") > 1 else len(text)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.rindex("```") if text.count("```") > 1 else len(text)
        text = text[start:end].strip()

    # Trouver le premier { et le dernier }
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        text = text[brace_start : brace_end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Tenter de corriger les erreurs JSON courantes
        text = text.replace("'", '"')
        text = text.replace(",\n}", "\n}")
        text = text.replace(",\n]", "\n]")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}
