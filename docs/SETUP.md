# Guide d'installation et de configuration

## Prérequis

### Système
- **macOS** 13+ (Apple Silicon M1/M2/M3/M4/M5) ou **Linux** (x86_64 / ARM64)
- **RAM** : 16 Go minimum, 64 Go recommandé pour les grands modèles
- **Stockage** : ~30 Go pour les modèles LLM

### Logiciels requis
- **Python** 3.11 ou supérieur
- **Ollama** (runtime LLM local) — OU **LM Studio** pour les modèles MLX
- **draw.io** (optionnel, pour l'export PNG des diagrammes)
- **Git** (optionnel, pour l'analyse des infos de versioning)

## Installation

### 1. Installer Ollama

Ollama est le runtime qui exécute les LLMs localement sur votre machine.

```bash
# macOS (via Homebrew)
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

Vérifiez l'installation :
```bash
ollama --version
```

### 2. Démarrer le serveur Ollama

```bash
# Lancer le serveur (reste actif en arrière-plan)
ollama serve
```

> **Note macOS** : Si vous avez installé l'application Ollama.app, le serveur se lance automatiquement.

### 3. Télécharger les modèles LLM

```bash
# Modèle pour l'analyse de code (recommandé)
ollama pull deepseek-coder-v2:16b

# Modèle pour la rédaction de documentation
ollama pull mistral:7b

# Modèle pour la génération de diagrammes
ollama pull llama3.1:8b
```

> **Astuce 64 Go RAM** : Vous pouvez aussi installer des modèles plus gros :
> ```bash
> ollama pull qwen2.5-coder:14b    # Alternative code, très performant
> ollama pull mixtral:8x7b          # Alternative docs, excellent en français
> ```

### 3bis. (Optionnel) LM Studio pour les modèles MLX

Sur Apple Silicon (M1 → M5), les modèles **MLX** sont significativement plus rapides que leurs équivalents GGUF via Ollama. Documenta peut les utiliser via **LM Studio** qui expose une API OpenAI-compatible.

```bash
# 1. Installer LM Studio
# Télécharger depuis : https://lmstudio.ai
# Ou via Homebrew :
brew install --cask lm-studio

# 2. Dans LM Studio :
#    - Onglet "Search" : télécharger les modèles MLX voulus, ex :
#        mlx-community/gemma-4-26b-a4b-it-8bit
#        mlx-community/Qwen2.5-Coder-14B-Instruct-8bit
#    - Onglet "Developer" : charger un modèle et lancer le serveur local
#    - Le serveur écoute par défaut sur http://localhost:1234/v1

# 3. Vérifier que le serveur répond
curl http://localhost:1234/v1/models
```

Une fois LM Studio en marche, Documenta détecte automatiquement les modèles MLX (ceux avec un `/` dans le nom) et les route vers LM Studio au lieu d'Ollama.

### 4. Installer Documenta

```bash
# Cloner le projet
git clone <url-du-repo> documenta
cd documenta

# Installer en mode développement
pip install -e .

# Ou avec les dépendances de développement
pip install -e ".[dev]"
```

Vérifiez l'installation :
```bash
documenta version
```

### 5. (Optionnel) Installer draw.io pour l'export PNG

```bash
# macOS
brew install --cask drawio

# Linux (Snap)
snap install drawio

# Linux (Flatpak)
flatpak install flathub com.jgraph.drawio.desktop
```

## Configuration

### Variables d'environnement

Toutes les options sont configurables via des variables d'environnement préfixées par `DOCUMENTA_` :

```bash
# Créer un fichier .env ou exporter les variables
export DOCUMENTA_OLLAMA_BASE_URL="http://localhost:11434"
export DOCUMENTA_CODE_MODEL="deepseek-coder-v2:16b"
export DOCUMENTA_DOC_MODEL="mistral:7b"
export DOCUMENTA_DIAGRAM_MODEL="llama3.1:8b"
export DOCUMENTA_LANGUAGE="fr"
```

### Options en ligne de commande

Les options CLI sont prioritaires sur les variables d'environnement :

```bash
# Tout Ollama
documenta generate /mon/projet \
  --code-model qwen2.5-coder:14b \
  --doc-model mixtral:8x7b \
  --diagram-model llama3.1:8b \
  --output documentation \
  --lang fr \
  --no-png

# Backends mixtes : Ollama pour code/diagrammes, LM Studio (MLX) pour la doc
documenta generate /mon/projet \
  --code-model deepseek-coder-v2:16b \
  --code-backend ollama \
  --doc-model mlx-community/gemma-4-26b-a4b-it-8bit \
  --doc-backend lmstudio \
  --diagram-model llama3.1:8b \
  --diagram-backend ollama

# URL personnalisée (port custom, machine distante)
documenta generate /mon/projet \
  --doc-model gemma-4 \
  --doc-backend openai \
  --doc-url http://192.168.1.10:1234/v1
```

### Backends disponibles

Documenta supporte plusieurs backends LLM :

| Backend | URL par défaut | Description |
|---------|----------------|-------------|
| `ollama` | `http://localhost:11434` | Ollama (format GGUF) |
| `lmstudio` | `http://localhost:1234/v1` | LM Studio (idéal pour MLX) |
| `mlx` | `http://localhost:8080/v1` | mlx-lm server direct |
| `openai` | `http://localhost:1234/v1` | Tout endpoint OpenAI-compatible (vLLM, jan.ai, etc.) |

**Auto-détection** : les modèles dont le nom contient un `/` (ex: `mlx-community/gemma-4-26b-a4b-it-8bit`) utilisent automatiquement le backend `lmstudio`.

## Démarrage

### Générer la documentation d'un projet

```bash
# Documentation complète avec les options par défaut
documenta generate /chemin/vers/mon-projet

# Vérifier l'environnement avant de commencer
documenta check

# Voir les modèles disponibles et recommandés
documenta models
```

### Exemple de sortie

```
📚 Documenta - Génération de documentation
Projet : mon-projet
Sortie  : /chemin/vers/mon-projet/docs

✓ Architecture générée
✓ Schéma fonctionnel généré
✓ Documentation développement
✓ TODOs générés
✓ SETUP.md généré
✓ README.md généré
✓ 2 PNG exportés

📁 8 fichiers générés dans /chemin/vers/mon-projet/docs
```

## Commandes utiles

```bash
# Lancer les tests
pytest

# Lancer les tests avec couverture
pytest --cov=documenta

# Vérifier le code (lint)
ruff check documenta/

# Formater le code
ruff format documenta/
```

## Dépannage

### Ollama ne répond pas

```bash
# Vérifier que le serveur tourne
curl http://localhost:11434/api/tags

# Redémarrer Ollama
# macOS : relancer l'app Ollama
# Linux :
systemctl restart ollama
# ou
ollama serve
```

### Modèle trop lent

Si un modèle est lent, essayez un modèle plus petit :
```bash
# Remplacer deepseek-coder-v2:16b par une version plus légère
documenta generate /mon/projet --code-model codellama:7b
```

### Erreur de mémoire

Si vous manquez de RAM, réduisez la taille des modèles ou fermez d'autres applications :
```bash
# Utiliser des modèles plus petits
documenta generate /mon/projet \
  --code-model codellama:7b \
  --doc-model mistral:7b \
  --diagram-model gemma2:2b
```

### draw.io ne fonctionne pas pour l'export PNG

```bash
# Vérifier l'installation
which drawio || which draw.io

# Désactiver l'export PNG si besoin
documenta generate /mon/projet --no-png
```

### Le JSON généré est invalide

Les LLMs peuvent parfois générer du JSON malformé. Documenta inclut un parser tolérant et des fallbacks. Si le problème persiste, essayez un modèle plus gros pour la génération de diagrammes :
```bash
documenta generate /mon/projet --diagram-model llama3.1:70b
```
