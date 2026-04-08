# Points restants et améliorations

## Fonctionnalités à implémenter

### 🔴 Critique

- [ ] **Support multi-langue des prompts** : Les prompts sont actuellement en français uniquement. Ajouter le support anglais et rendre les templates de prompts configurables par langue.
- [ ] **Gestion du contexte LLM** : Implémenter un chunking intelligent quand le projet dépasse la fenêtre de contexte du modèle. Actuellement, les fichiers sont tronqués de manière basique.

### 🟡 Important

- [ ] **Cache des résultats LLM** : Mettre en cache les réponses LLM pour éviter de re-générer lors de modifications mineures. Utiliser un hash du contenu analysé comme clé de cache.
- [ ] **Mode incrémental** : Ne re-générer que la documentation des fichiers modifiés depuis la dernière exécution (utiliser les timestamps Git).
- [ ] **Personnalisation des templates** : Permettre aux utilisateurs de fournir leurs propres templates de prompts (fichier `.documenta/prompts/` dans le projet).
- [ ] **Support de plus de formats de sortie** : AsciiDoc, reStructuredText, Confluence Wiki en plus de Markdown.
- [ ] **Génération de diagrammes de séquence** : Ajouter des diagrammes de séquence pour les flux importants (format Mermaid ou DrawIO).
- [ ] **Analyse des dépendances** : Générer un graphe de dépendances entre modules/packages.

### 🟢 Nice-to-have

- [ ] **Interface web** : Ajouter une interface web (Streamlit ou FastAPI + HTMX) pour visualiser et éditer la documentation générée.
- [ ] **Plugin IDE** : Extension VS Code pour lancer Documenta directement depuis l'éditeur.
- [ ] **Génération de changelog** : Analyser l'historique Git pour générer un CHANGELOG.md automatique.
- [ ] **Support monorepo** : Détecter et documenter séparément les sous-projets dans un monorepo.
- [ ] **Benchmark de modèles** : Comparer la qualité de sortie entre différents modèles pour chaque type de documentation.
- [ ] **Export PDF** : Convertir la documentation Markdown en PDF avec mise en page professionnelle.

## Améliorations techniques

### 🟡 Important

- [ ] **Tests d'intégration** : Ajouter des tests d'intégration avec un serveur Ollama mocké (via `respx` ou `pytest-httpx`).
- [ ] **Validation JSON stricte** : Utiliser des schémas Pydantic pour valider les réponses JSON des LLMs au lieu du parsing approximatif.
- [ ] **Retry avec backoff exponentiel** : Améliorer la stratégie de retry pour les appels LLM (actuellement un seul retry).
- [ ] **Streaming des réponses** : Supporter le streaming Ollama pour afficher la progression en temps réel.
- [ ] **Limiter la concurrence LLM** : Utiliser un semaphore asyncio pour limiter les appels parallèles à Ollama (éviter la surcharge mémoire).

### 🟢 Nice-to-have

- [ ] **Métriques de qualité** : Évaluer la qualité de la documentation générée (couverture, lisibilité).
- [ ] **CI/CD** : Ajouter une GitHub Action pour exécuter Documenta automatiquement sur les PRs.
- [ ] **Pre-commit hook** : Hook pour re-générer la documentation si des fichiers sources ont changé.
- [ ] **Support Windows** : Tester et adapter les chemins draw.io pour Windows.

## Dette technique identifiée

- [ ] **`_read_important_files`** : La priorisation des fichiers à lire est basique (entry points → configs → sources). Implémenter un scoring plus intelligent basé sur l'importance des fichiers (imports, centralité dans le graphe de dépendances).
- [ ] **Taille du prompt `_project_context`** : Le contexte peut devenir très grand pour les projets complexes. Implémenter une stratégie de résumé par module plutôt que d'inclure le code brut.
- [ ] **Couplage engine/prompts** : Le `DocumentationEngine` utilise directement `PromptBuilder`. Extraire une interface pour faciliter les tests et la personnalisation.

## Prochaines étapes suggérées

1. Implémenter le cache des résultats LLM (quick win, gros impact sur la productivité)
2. Ajouter les tests d'intégration avec mock Ollama
3. Supporter le streaming des réponses pour un meilleur feedback utilisateur
4. Ajouter la gestion multi-langue
5. Implémenter le mode incrémental
