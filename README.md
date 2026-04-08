# Documenta

**Outil de documentation automatique de projets utilisant des LLMs open-source.**

Documenta analyse n'importe quel projet logiciel et génère automatiquement une documentation complète et structurée, incluant des diagrammes d'architecture et fonctionnels au format DrawIO, de la documentation de développement détaillée, et des guides d'installation.

## Fonctionnalités

- **Analyse automatique** : Détection de la stack technique, des langages, frameworks, bases de données et outils
- **Multi-LLM** : Utilise plusieurs modèles open-source via [Ollama](https://ollama.com) pour des résultats optimaux
  - Modèle spécialisé code pour l'analyse (DeepSeek Coder)
  - Modèle rédactionnel pour la documentation (Mistral)
  - Modèle structurel pour les diagrammes (Llama 3.1)
- **Diagrammes DrawIO** : Génération de diagrammes d'architecture et fonctionnels
- **Export PNG** : Conversion automatique des diagrammes en images (si draw.io est installé)
- **100% local** : Aucune donnée n'est envoyée à des services cloud

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Langage | Python 3.11+ |
| CLI | Typer + Rich |
| LLM Runtime | Ollama (local) |
| Communication LLM | httpx (async) |
| Analyse projet | GitPython, pathspec |
| Diagrammes | DrawIO XML (mxGraph) |
| Export PNG | draw.io CLI |
| Configuration | Pydantic Settings |

## Démarrage rapide

```bash
# 1. Installer Ollama
curl -fsSL https://ollama.com/install.sh | sh   # Linux
# ou : brew install ollama                       # macOS

# 2. Télécharger les modèles recommandés
ollama pull mistral:7b
ollama pull deepseek-coder-v2:16b
ollama pull llama3.1:8b

# 3. Installer Documenta
cd documenta
pip install -e .

# 4. Générer la documentation d'un projet
documenta generate /chemin/vers/mon-projet

# 5. (Optionnel) Installer draw.io pour les exports PNG
brew install --cask drawio   # macOS
```

## Utilisation

```bash
# Générer la documentation avec les options par défaut
documenta generate /chemin/vers/mon-projet

# Spécifier un répertoire de sortie
documenta generate /chemin/vers/mon-projet -o documentation

# Utiliser d'autres modèles
documenta generate /chemin/vers/mon-projet \
  --code-model qwen2.5-coder:14b \
  --doc-model mixtral:8x7b

# Vérifier la configuration
documenta check

# Voir les modèles recommandés
documenta models
```

## Documentation

| Document | Description |
|----------|-------------|
| [docs/SETUP.md](docs/SETUP.md) | Guide d'installation et de configuration |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Documentation de développement détaillée |
| [docs/TODO.md](docs/TODO.md) | Points restants et améliorations prévues |
| [docs/architecture.drawio](docs/architecture.drawio) | Diagramme d'architecture technique |
| [docs/functional.drawio](docs/functional.drawio) | Schéma fonctionnel de l'application |

### Architecture

![Architecture de Documenta](docs/architecture.png)

### Schéma fonctionnel

![Schéma fonctionnel](docs/functional.png)

## Fichiers générés

Pour chaque projet analysé, Documenta génère dans le répertoire `docs/` :

```
docs/
├── architecture.drawio    # Diagramme d'architecture (DrawIO)
├── architecture.png       # Export PNG du diagramme
├── functional.drawio      # Schéma fonctionnel (DrawIO)
├── functional.png         # Export PNG du schéma
├── DEVELOPMENT.md         # Documentation de développement détaillée
├── TODO.md                # Points restants et améliorations
└── SETUP.md               # Guide d'installation
README.md                  # README à la racine du projet
```

## Configuration

Documenta est configurable via variables d'environnement ou en ligne de commande :

| Variable | Défaut | Description |
|----------|--------|-------------|
| `DOCUMENTA_OLLAMA_BASE_URL` | `http://localhost:11434` | URL du serveur Ollama |
| `DOCUMENTA_CODE_MODEL` | `deepseek-coder-v2:16b` | Modèle pour l'analyse de code |
| `DOCUMENTA_DOC_MODEL` | `mistral:7b` | Modèle pour la rédaction |
| `DOCUMENTA_DIAGRAM_MODEL` | `llama3.1:8b` | Modèle pour les diagrammes |
| `DOCUMENTA_LANGUAGE` | `fr` | Langue de la documentation |

## Modèles recommandés (MacBook Pro M5 64 Go)

Avec 64 Go de RAM, vous pouvez utiliser les modèles suivants simultanément :

| Modèle | Usage | RAM | Note |
|--------|-------|-----|------|
| `deepseek-coder-v2:16b` | Analyse de code | ~9 Go | Excellente compréhension du code |
| `mistral:7b` | Rédaction docs | ~4 Go | Bon français, rapide |
| `llama3.1:8b` | Diagrammes | ~5 Go | Bon raisonnement structuré |
| `qwen2.5-coder:14b` | Alternative code | ~8 Go | Très bon en code |
| `mixtral:8x7b` | Alternative docs | ~26 Go | Excellent mais gourmand |

## Contribuer

1. Forkez le projet
2. Créez votre branche (`git checkout -b feature/ma-fonctionnalite`)
3. Installez les dépendances de dev : `pip install -e ".[dev]"`
4. Lancez les tests : `pytest`
5. Committez vos changements
6. Poussez et créez une Pull Request

## Licence

MIT
