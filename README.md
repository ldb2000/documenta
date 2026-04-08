# Documenta

**Outil de documentation automatique de projets utilisant des LLMs open-source.**

Documenta analyse n'importe quel projet logiciel et génère automatiquement une documentation complète et structurée, incluant des diagrammes d'architecture et fonctionnels au format DrawIO, de la documentation de développement détaillée, et des guides d'installation.

**100% local** : tout tourne sur votre machine via [Ollama](https://ollama.com). Aucune donnée n'est envoyée vers le cloud.

---

## Fonctionnalités

- **Analyse automatique** : Scan de la structure, détection de la stack technique (langages, frameworks, bases de données, outils), lecture intelligente du code source, informations Git
- **3 LLMs spécialisés en parallèle** : Chaque type de documentation est généré par le modèle le plus adapté, exécutés simultanément pour un maximum de vitesse
- **Diagrammes DrawIO** : Génération automatique de diagrammes d'architecture et fonctionnels (XML mxGraph)
- **Export PNG** : Conversion automatique des `.drawio` en images haute résolution (si draw.io est installé)
- **Fallback intelligent** : Si un LLM échoue ou retourne du JSON invalide, un fallback basé sur l'analyse statique prend le relais
- **Configurable** : Modèles, températures, langue, patterns d'exclusion modifiables via CLI ou variables d'environnement

---

## Architecture multi-modèles

Documenta utilise **3 LLMs open-source différents**, chacun choisi pour sa spécialité :

| Modèle | Role | Fichiers generés | Pourquoi ce modele |
|--------|------|-------------------|-------------------|
| `deepseek-coder-v2:16b` | **Analyse de code** | `TODO.md` | Compréhension profonde du code, détection de dette technique, TODOs, patterns |
| `mistral:7b` | **Rédaction** | `DEVELOPMENT.md`, `SETUP.md`, `README.md` | Excellent en français, rapide, fluide en rédaction technique |
| `llama3.1:8b` | **Diagrammes** | `architecture.drawio`, `functional.drawio` | Bon raisonnement structuré, génère du JSON propre pour les diagrammes |

### Pourquoi plusieurs modèles ?

Un seul modèle généraliste ne peut pas exceller dans tous les domaines. En utilisant des modèles spécialisés :
- **Le modèle code** comprend les patterns, les imports, la structure et peut identifier la dette technique
- **Le modèle rédaction** produit du texte clair, bien structuré, en bon français
- **Le modèle diagramme** génère du JSON structuré fiable pour construire les diagrammes DrawIO

Avec **64 Go de RAM** sur un MacBook Pro M5, les 3 modèles (~18 Go total) tiennent en mémoire simultanément. Ollama garde les modèles chargés, donc il n'y a pas de rechargement entre les appels.

---

## Pipeline d'exécution parallèle

Le moteur de génération (`documenta/generators/engine.py`) orchestre les appels LLM en **4 phases**, avec un maximum de parallélisme via `asyncio.gather` :

```
                        ┌─────────────────────────────────────────┐
                        │         documenta generate /projet      │
                        └────────────────┬────────────────────────┘
                                         │
                        ┌────────────────▼────────────────────────┐
                        │        Phase 0 : Analyse statique       │
                        │  Scan fichiers, détection stack, Git    │
                        │  Lecture du code source prioritaire     │
                        └────────────────┬────────────────────────┘
                                         │
               ┌─────────────────────────┼─────────────────────────┐
               │                         │                         │
               ▼                         ▼                         ▼
  ┌────────────────────┐  ┌───────────────────────┐  ┌──────────────────┐
  │  Phase 1 (parallel)│  │   Phase 2 (parallel)  │  │  Phase 3         │
  │                    │  │                       │  │                  │
  │  architecture     ─┤  │  DEVELOPMENT.md  ─────┤  │  README.md  ─────┤
  │   .drawio          │  │   (mistral:7b)        │  │  (mistral:7b)    │
  │  (llama3.1:8b)     │  │                       │  │                  │
  │                    │  │  SETUP.md  ───────────┤  │  Dépend des      │
  │  functional       ─┤  │   (mistral:7b)        │  │  résultats       │
  │   .drawio          │  │                       │  │  précédents      │
  │  (llama3.1:8b)     │  │  TODO.md  ────��───────┤  │                  │
  │                    │  │   (deepseek-coder)    │  │                  │
  └────────────────────┘  └───────────────────────┘  └──────────────────┘
               │                         │                         │
               └─────────────────────────┼─────────────────────────┘
                                         │
                        ┌────────────────▼────────────────────────┐
                        │     Phase 4 : Export PNG (draw.io CLI)  │
                        │  architecture.drawio → architecture.png │
                        │  functional.drawio   → functional.png   │
                        └─────────────────────────────────────────┘
```

### Détail du code d'orchestration

```python
# Phase 1 : Architecture + Fonctionnel en parallèle (llama3.1:8b)
arch_result, func_result = await asyncio.gather(
    self._generate_architecture(),    # → llama3.1:8b → JSON → DrawIO XML
    self._generate_functional(),      # → llama3.1:8b → JSON → DrawIO XML
)

# Phase 2 : Documentation texte en parallèle (3 modèles simultanés)
dev_result, todo_result, setup_result = await asyncio.gather(
    self._generate_development_docs(),  # → mistral:7b        → Markdown
    self._generate_todo(),              # → deepseek-coder-v2  → Markdown
    self._generate_setup(),             # → mistral:7b         → Markdown
)

# Phase 3 : README (dépend des résultats précédents)
readme_result = await self._generate_readme()  # → mistral:7b → Markdown

# Phase 4 : Export PNG via draw.io CLI
png_files = self.exporter.export_all(self.output_dir)
```

Les Phases 1 et 2 sont **lancées séquentiellement** mais les appels au sein de chaque phase sont **parallèles**. Cela permet d'utiliser les 3 modèles en même temps et de réduire le temps total de génération.

---

## Stack technique

| Composant | Technologie | Role |
|-----------|-------------|------|
| Langage | Python 3.11+ | Base du projet |
| CLI | Typer + Rich | Interface utilisateur avec progress bars et couleurs |
| LLM Runtime | Ollama (local) | Exécution des modèles open-source sur Apple Silicon |
| Communication LLM | httpx (async) | Appels HTTP asynchrones pour le parallélisme |
| Analyse projet | GitPython, pathspec | Scan fichiers, respect .gitignore, info Git |
| Diagrammes | DrawIO XML (mxGraph) | Format standard, ouvrable dans draw.io |
| Export PNG | draw.io CLI | Conversion haute résolution (2x scale) |
| Configuration | Pydantic Settings | Validation + variables d'environnement |
| Templates | Jinja2 | Prêt pour des templates personnalisables |

---

## Démarrage rapide

### 1. Installer Ollama

```bash
# macOS (Homebrew)
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Télécharger les 3 modèles

```bash
ollama pull deepseek-coder-v2:16b   # ~9 Go - Analyse de code
ollama pull mistral:7b               # ~4 Go - Rédaction documentation
ollama pull llama3.1:8b              # ~5 Go - Génération de diagrammes
```

### 3. Installer Documenta

```bash
cd documenta
pip install -e .
```

### 4. Générer la documentation d'un projet

```bash
documenta generate /chemin/vers/mon-projet
```

### 5. (Optionnel) Installer draw.io pour l'export PNG

```bash
brew install --cask drawio   # macOS
snap install drawio          # Linux
```

---

## Utilisation

### Commandes disponibles

```bash
# Générer la documentation complète
documenta generate /chemin/vers/mon-projet

# Spécifier un répertoire de sortie
documenta generate /chemin/vers/mon-projet -o documentation

# Changer les modèles utilisés
documenta generate /chemin/vers/mon-projet \
  --code-model qwen2.5-coder:14b \
  --doc-model mixtral:8x7b \
  --diagram-model llama3.1:8b

# Désactiver l'export PNG
documenta generate /chemin/vers/mon-projet --no-png

# Vérifier l'environnement (Ollama, modèles, draw.io)
documenta check

# Voir les modèles recommandés et leur statut
documenta models

# Afficher la version
documenta version
```

### Exemple de sortie

```
📚 Documenta - Génération de documentation
Projet : mon-projet
Sortie  : /chemin/vers/mon-projet/docs

┌─────────────────────────────────┐
│ Analyse de 'mon-projet'        │
├──────────────────┬──────────────┤
│ Langages         │ Python, JS   │
│ Frameworks       │ FastAPI, Vue │
│ Bases de données │ PostgreSQL   │
│ Outils           │ Docker       │
│ Fichiers analysés│ 87           │
│ Fichiers lus     │ 42           │
└──────────────────┴──────────────┘

✓ Architecture générée
✓ Schéma fonctionnel généré
✓ Documentation développement
✓ TODOs générés
✓ SETUP.md généré
✓ README.md généré
✓ 2 PNG exportés

📁 8 fichiers générés dans /chemin/vers/mon-projet/docs
```

---

## Fichiers générés

Pour chaque projet analysé, Documenta génère :

```
mon-projet/
├── README.md                      # Présentation du projet (racine)
└── docs/
    ├── architecture.drawio        # Diagramme d'architecture technique (DrawIO)
    ├── architecture.png           # Export PNG haute résolution
    ├── functional.drawio          # Schéma fonctionnel / métier (DrawIO)
    ├── functional.png             # Export PNG haute résolution
    ├── DEVELOPMENT.md             # Documentation de développement détaillée
    ├── TODO.md                    # Points restants, dette technique, améliorations
    └── SETUP.md                   # Guide d'installation pas à pas
```

### Détail de chaque fichier

| Fichier | Généré par | Contenu |
|---------|-----------|---------|
| `architecture.drawio` | `llama3.1:8b` | Couches techniques (Frontend, Backend, DB, Infra), composants, connexions, services externes |
| `functional.drawio` | `llama3.1:8b` | Acteurs, fonctionnalités métier, flux utilisateur avec étapes |
| `DEVELOPMENT.md` | `mistral:7b` | Architecture, structure du code, composants, flux de données, API, sécurité, tests |
| `TODO.md` | `deepseek-coder-v2:16b` | TODOs/FIXME trouvés dans le code, fonctionnalités incomplètes, dette technique, prochaines étapes |
| `SETUP.md` | `mistral:7b` | Prérequis, installation, configuration, démarrage, commandes utiles, dépannage |
| `README.md` | `mistral:7b` | Présentation, fonctionnalités, stack, démarrage rapide, liens vers la doc |

---

## Configuration

### Variables d'environnement

Toutes les options sont configurables via des variables préfixées `DOCUMENTA_` :

| Variable | Défaut | Description |
|----------|--------|-------------|
| `DOCUMENTA_OLLAMA_BASE_URL` | `http://localhost:11434` | URL du serveur Ollama |
| `DOCUMENTA_CODE_MODEL` | `deepseek-coder-v2:16b` | Modèle pour l'analyse de code |
| `DOCUMENTA_DOC_MODEL` | `mistral:7b` | Modèle pour la rédaction |
| `DOCUMENTA_DIAGRAM_MODEL` | `llama3.1:8b` | Modèle pour les diagrammes |
| `DOCUMENTA_CODE_TEMPERATURE` | `0.1` | Température pour l'analyse (basse = précis) |
| `DOCUMENTA_DOC_TEMPERATURE` | `0.4` | Température pour la rédaction (moyenne = créatif) |
| `DOCUMENTA_DIAGRAM_TEMPERATURE` | `0.2` | Température pour les diagrammes (basse = structuré) |
| `DOCUMENTA_MAX_CONTEXT_LENGTH` | `16384` | Taille max du contexte envoyé au LLM |
| `DOCUMENTA_MAX_FILES_TO_ANALYZE` | `150` | Nombre max de fichiers à scanner |
| `DOCUMENTA_LANGUAGE` | `fr` | Langue de la documentation |
| `DOCUMENTA_EXPORT_PNG` | `true` | Activer/désactiver l'export PNG |

### Exemple `.env`

```bash
DOCUMENTA_OLLAMA_BASE_URL=http://localhost:11434
DOCUMENTA_CODE_MODEL=qwen2.5-coder:14b
DOCUMENTA_DOC_MODEL=mixtral:8x7b
DOCUMENTA_DIAGRAM_MODEL=llama3.1:8b
DOCUMENTA_LANGUAGE=fr
```

---

## Modèles recommandés

### Configuration par défaut (~18 Go RAM)

| Modèle | Usage | RAM | Vitesse | Qualité |
|--------|-------|-----|---------|---------|
| `deepseek-coder-v2:16b` | Analyse de code | ~9 Go | Moyenne | Excellente |
| `mistral:7b` | Rédaction docs | ~4 Go | Rapide | Très bonne |
| `llama3.1:8b` | Diagrammes | ~5 Go | Rapide | Bonne |

### Alternatives possibles

| Modèle | Usage | RAM | Note |
|--------|-------|-----|------|
| `qwen2.5-coder:14b` | Alternative code | ~8 Go | Très bon en code (Alibaba) |
| `codellama:13b` | Alternative code | ~7 Go | Spécialisé code (Meta) |
| `mixtral:8x7b` | Alternative docs | ~26 Go | Excellent en français, gourmand en RAM |
| `gemma2:9b` | Polyvalent | ~5 Go | Bon compromis (Google) |
| `llama3.1:70b` | Qualité maximale | ~40 Go | Le meilleur, mais lent |

### Profils de configuration selon la RAM

**16 Go RAM** (configuration légère) :
```bash
documenta generate /projet \
  --code-model codellama:7b \
  --doc-model mistral:7b \
  --diagram-model gemma2:2b
```

**32 Go RAM** (configuration standard) :
```bash
documenta generate /projet \
  --code-model deepseek-coder-v2:16b \
  --doc-model mistral:7b \
  --diagram-model llama3.1:8b
```

**64 Go RAM** (configuration maximale - MacBook Pro M5) :
```bash
documenta generate /projet \
  --code-model qwen2.5-coder:14b \
  --doc-model mixtral:8x7b \
  --diagram-model llama3.1:8b
```

---

## Structure du projet

```
documenta/
├── README.md                        # Ce fichier
├── pyproject.toml                   # Configuration Python, dépendances, scripts
├── requirements.txt                 # Dépendances pip
├── .gitignore
│
├��─ documenta/                       # Package Python principal
│   ├── __init__.py                  # Version (0.1.0)
│   ├── cli.py                       # CLI Typer (generate, check, models, version)
│   ├── config.py                    # Configuration Pydantic Settings
│   │
���   ├── analyzer/                    # Module d'analyse de projet
│   │   └── project.py              # ProjectAnalyzer : scan, détection stack, Git
│   │
│   ├── llm/                         # Module d'intégration LLM
│   │   ├── client.py               # OllamaClient : HTTP async, retry, multi-modèle
│   │   └── prompts.py              # PromptBuilder : templates contextuels par doc
│   │
│   ├── generators/                  # Module de génération
│   │   └── engine.py               # DocumentationEngine : orchestration parallèle
│   │
│   ├── drawio/                      # Module DrawIO
│   │   ├── builder.py              # DrawioBuilder : XML mxGraph, styles, layouts
│   │   └── exporter.py             # DrawioExporter : PNG via draw.io CLI
│   │
│   └── utils/                       # Utilitaires
│       └── files.py                 # Helpers fichiers (write, truncate, format)
│
├── tests/                           # Tests unitaires
│   ├── test_analyzer.py             # Tests analyse de projet
│   └── test_drawio.py              # Tests génération DrawIO + parsing JSON
│
└── docs/                            # Documentation de Documenta lui-même
    ├── architecture.drawio          # Diagramme d'architecture
    ├── functional.drawio            # Schéma fonctionnel
    ├── DEVELOPMENT.md               # Documentation de développement
    ├── TODO.md                      # Points restants
    └── SETUP.md                     # Guide d'installation
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/SETUP.md](docs/SETUP.md) | Guide d'installation et de configuration complet |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Documentation de développement détaillée |
| [docs/TODO.md](docs/TODO.md) | Points restants et améliorations prévues |
| [docs/architecture.drawio](docs/architecture.drawio) | Diagramme d'architecture technique |
| [docs/functional.drawio](docs/functional.drawio) | Schéma fonctionnel de l'application |

### Architecture

![Architecture de Documenta](docs/architecture.png)

### Schéma fonctionnel

![Schéma fonctionnel](docs/functional.png)

---

## Contribuer

1. Forkez le projet
2. Créez votre branche : `git checkout -b feature/ma-fonctionnalite`
3. Installez les dépendances de dev : `pip install -e ".[dev]"`
4. Lancez les tests : `pytest`
5. Vérifiez le lint : `ruff check documenta/`
6. Committez et poussez
7. Créez une Pull Request

---

## Licence

MIT
