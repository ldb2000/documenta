# Documentation de développement - Documenta

## Vue d'ensemble

Documenta est un outil CLI Python qui analyse automatiquement des projets logiciels et génère de la documentation complète en utilisant des LLMs open-source exécutés localement via Ollama.

### Objectif
Permettre à tout développeur de générer instantanément une documentation structurée et professionnelle pour n'importe quel projet, sans envoyer de code vers des services cloud.

### Périmètre
- Analyse statique de projets (structure, langages, frameworks, dépendances)
- Génération de documentation Markdown via LLMs
- Génération de diagrammes DrawIO (architecture et fonctionnel)
- Export PNG des diagrammes

## Architecture technique

### Vue d'ensemble

```
┌────────────────────────────────────────────────┐
│                    CLI (Typer)                   │
│                  documenta/cli.py                │
└─────────────────────┬──────────────────────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
┌─────────────┐ ┌──────────┐ ┌──────────────┐
│  Analyzer   │ │   LLM    │ │  Generators  │
│  (analyse)  │ │ (Ollama) │ │  (moteur)    │
└──────┬──────┘ └────┬─────┘ └──────┬───────┘
       │              │              │
       │              │         ┌────┴────┐
       │              │         ▼         ▼
       │              │    ┌────────┐ ┌────────┐
       │              │    │ DrawIO │ │ Prompts│
       │              │    │Builder │ │Builder │
       │              │    └────────┘ └────────┘
       │              │
       ▼              ▼
  ProjectInfo    Ollama API
  (dataclass)   (localhost)
```

### Couches

1. **CLI** (`documenta/cli.py`) : Interface utilisateur via Typer, parsing des arguments, orchestration haut niveau
2. **Analyzer** (`documenta/analyzer/`) : Analyse statique du projet cible (scan fichiers, détection stack, Git)
3. **LLM** (`documenta/llm/`) : Client Ollama async, gestion multi-modèles, templates de prompts
4. **Generators** (`documenta/generators/`) : Moteur d'orchestration de la génération, appels LLM parallèles
5. **DrawIO** (`documenta/drawio/`) : Construction XML mxGraph, export PNG via draw.io CLI
6. **Utils** (`documenta/utils/`) : Utilitaires fichiers, formatage

### Patterns et choix techniques

- **Async/await** : Les appels LLM sont asynchrones (httpx) pour paralléliser les générations
- **Multi-modèles** : Chaque type de génération utilise le modèle le plus adapté
- **Fallback** : Si le LLM échoue ou retourne du JSON invalide, des fallbacks basés sur l'analyse statique prennent le relais
- **Pydantic Settings** : Configuration centralisée avec support variables d'environnement

## Structure du code

```
documenta/
├── __init__.py              # Version
├── cli.py                   # Point d'entrée CLI (Typer)
├── config.py                # Configuration (Pydantic Settings)
├── analyzer/
│   ├── __init__.py
│   └── project.py           # Analyse de projet (scan, détection, Git)
├── llm/
│   ├── __init__.py
│   ├── client.py            # Client Ollama (httpx async)
│   └── prompts.py           # Templates de prompts pour chaque doc
├── generators/
│   ├── __init__.py
│   └── engine.py            # Moteur de génération (orchestration)
├── drawio/
│   ├── __init__.py
│   ├── builder.py           # Constructeur XML DrawIO
│   └── exporter.py          # Export PNG via draw.io CLI
└── utils/
    ├── __init__.py
    └── files.py              # Utilitaires fichiers
```

## Composants principaux

### ProjectAnalyzer (`analyzer/project.py`)

Analyse statique d'un projet :
- **Scan des fichiers** : Parcourt l'arborescence en respectant `.gitignore` et les patterns d'exclusion
- **Détection des langages** : Mapping extension → langage
- **Détection des frameworks** : Lecture des fichiers de config (package.json, requirements.txt, etc.)
- **Détection des bases de données** : Recherche de mots-clés dans les fichiers de config
- **Info Git** : Branche, remote, commits récents, contributeurs
- **Lecture du code** : Lit les fichiers sources importants avec un budget de caractères

### OllamaClient (`llm/client.py`)

Client HTTP async pour Ollama :
- **Vérification de connexion** : `check_connection()`
- **Liste des modèles** : `list_models()`
- **Génération** : `generate()` avec retry automatique sur timeout
- **Méthodes spécialisées** : `generate_for_code()`, `generate_for_docs()`, `generate_for_diagram()`
- **Gestion des modèles** : `ensure_model()`, `pull_model()`

### PromptBuilder (`llm/prompts.py`)

Construit les prompts contextualisés pour chaque type de documentation :
- Injecte le contexte complet du projet (structure, stack, code source)
- Prompts spécifiques pour architecture (JSON), fonctionnel (JSON), dev docs, TODO, SETUP, README
- Gère la troncature du code source pour respecter les limites de contexte

### DocumentationEngine (`generators/engine.py`)

Orchestre la génération complète :
- Vérifie l'environnement (Ollama, modèles)
- Génère les diagrammes en parallèle (Phase 1)
- Génère la documentation texte en parallèle (Phase 2)
- Génère le README (Phase 3, nécessite les résultats précédents)
- Exporte les PNG (Phase 4)

### DrawioBuilder (`drawio/builder.py`)

Construit des fichiers DrawIO (XML mxGraph) :
- **Architecture** : Couches horizontales avec composants, connexions et services externes
- **Fonctionnel** : Acteurs, fonctionnalités, flux avec étapes
- **Parsing JSON tolérant** : Gère les réponses LLM mal formées (blocs markdown, JSON approximatif)

### DrawioExporter (`drawio/exporter.py`)

Export PNG via le CLI draw.io :
- Recherche automatique de l'exécutable sur macOS et Linux
- Export haute résolution (scale 2x)
- Gestion propre des erreurs et timeouts

## Flux de données

```
Projet cible
     │
     ▼
ProjectAnalyzer.analyze()
     │
     ├─→ scan_files()         → Liste de FileInfo
     ├─→ detect_tech_stack()  → TechStackInfo
     ├─→ get_git_info()       → GitInfo
     ├─→ build_tree()         → String (arborescence)
     └─→ read_important_files() → Contenu des fichiers
     │
     ▼
ProjectInfo (dataclass)
     │
     ▼
PromptBuilder (construit les prompts avec le contexte)
     │
     ├─→ architecture_prompt()  ──→ LLM (diagram_model) ──→ JSON ──→ DrawIO XML
     ├─→ functional_prompt()    ──→ LLM (diagram_model) ──→ JSON ──→ DrawIO XML
     ├─→ development_docs_prompt() ──→ LLM (doc_model) ──→ Markdown
     ├─→ todo_prompt()          ──→ LLM (code_model) ──→ Markdown
     ├─→ setup_prompt()         ──→ LLM (doc_model) ──→ Markdown
     └─→ readme_prompt()        ──→ LLM (doc_model) ──→ Markdown
     │
     ▼
Fichiers dans docs/
     │
     ▼ (optionnel)
DrawioExporter → PNG
```

## API et interfaces

### CLI

| Commande | Description |
|----------|-------------|
| `documenta generate <path>` | Génère la documentation |
| `documenta check` | Vérifie l'environnement |
| `documenta models` | Liste les modèles recommandés |
| `documenta version` | Affiche la version |

### Fonctions clés

```python
# Analyse
analyzer = ProjectAnalyzer(Path("/mon/projet"), config)
project_info = analyzer.analyze()  # → ProjectInfo

# Génération
engine = DocumentationEngine(project_info, config)
generated = await engine.generate_all()  # → dict[str, Path]

# LLM
client = OllamaClient(config)
response = await client.generate(prompt, model="mistral:7b")

# DrawIO
builder = DrawioBuilder()
xml = builder.build_architecture_diagram(arch_json)
```

## Tests

```bash
# Lancer tous les tests
pytest

# Tests avec verbose
pytest -v

# Tests d'un module spécifique
pytest tests/test_analyzer.py
pytest tests/test_drawio.py
```

Les tests couvrent :
- Analyse de projets (Python, Node.js, projets vides)
- Exclusion de fichiers (node_modules, .gitignore)
- Construction de l'arborescence
- Génération de diagrammes DrawIO
- Parsing JSON tolérant des réponses LLM
