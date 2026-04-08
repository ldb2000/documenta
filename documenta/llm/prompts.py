"""Templates de prompts pour la génération de documentation."""

from __future__ import annotations

from documenta.analyzer.project import ProjectInfo
from documenta.utils.files import truncate_content


class PromptBuilder:
    """Construit les prompts pour chaque type de documentation."""

    def __init__(self, project: ProjectInfo):
        self.project = project

    def _project_context(self, include_code: bool = False) -> str:
        """Construit le contexte commun du projet."""
        p = self.project
        ctx = f"""# Projet : {p.name}

## Structure du projet
```
{p.tree_structure}
```

## Stack technique
- Langages : {', '.join(p.tech_stack.languages) or 'Non détecté'}
- Frameworks : {', '.join(p.tech_stack.frameworks) or 'Non détecté'}
- Bases de données : {', '.join(p.tech_stack.databases) or 'Non détecté'}
- Outils : {', '.join(p.tech_stack.tools) or 'Non détecté'}
- Package manager : {p.tech_stack.package_manager or 'Non détecté'}
- Runtime : {p.tech_stack.runtime or 'Non détecté'}

## Points d'entrée
{chr(10).join(f'- {e}' for e in p.entry_points) or '- Non détecté'}

## Fichiers de configuration
{chr(10).join(f'- {c}' for c in p.config_files[:20]) or '- Aucun'}
"""

        if include_code:
            ctx += "\n## Code source principal\n"
            for f in p.files:
                if f.content:
                    ctx += f"\n### {f.relative_path}\n```\n{truncate_content(f.content, 4000)}\n```\n"

        return ctx

    def architecture_prompt(self) -> str:
        """Prompt pour générer l'architecture en Mermaid."""
        return f"""{self._project_context(include_code=True)}

---

En te basant sur l'analyse ci-dessus, génère un diagramme d'architecture technique de ce projet au format **Mermaid flowchart**.

Règles STRICTES :
- Utilise `flowchart TD` (top-down)
- Crée des `subgraph` pour chaque couche (Frontend, Backend, API, Database, Infrastructure, etc.)
- Chaque composant doit être un noeud avec un ID court et un label descriptif
- Utilise `[(label)]` pour les bases de données (cylindre)
- Utilise `([label])` pour les services externes
- TOUTES les connexions entre composants doivent avoir des flèches `-->` avec des labels `|label|`
- Utilise `-.->` pour les connexions optionnelles ou asynchrones
- Utilise `==>` pour les flux de données principaux
- Sois exhaustif sur les connexions : chaque composant doit avoir au moins une flèche

Exemple de format attendu :
```mermaid
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
```

Réponds UNIQUEMENT avec le bloc ```mermaid, sans texte avant ou après."""

    def functional_prompt(self) -> str:
        """Prompt pour générer le schéma fonctionnel en Mermaid."""
        return f"""{self._project_context(include_code=True)}

---

En te basant sur l'analyse ci-dessus, génère un diagramme fonctionnel / métier de cette application au format **Mermaid flowchart**.

Règles STRICTES :
- Utilise `flowchart LR` (left-to-right)
- Les acteurs (Utilisateur, Admin, Système) sont des noeuds ronds `((Acteur))`
- Les fonctionnalités sont des rectangles `[Fonctionnalité]`
- Les décisions/conditions sont des losanges `{{Condition}}`
- Les bases de données sont des cylindres `[(Base)]`
- Crée des `subgraph` pour regrouper les fonctionnalités par domaine
- TOUTES les interactions doivent avoir des flèches avec labels descriptifs
- Montre les flux utilisateur principaux de bout en bout
- Utilise `-->` pour les actions, `-.->` pour les réponses/retours

Exemple de format attendu :
```mermaid
flowchart LR
    User((Utilisateur))

    subgraph Auth["Authentification"]
        Login[Page de connexion]
        Register[Inscription]
    end
    subgraph App["Application"]
        Dashboard[Tableau de bord]
        Profile[Mon profil]
    end
    subgraph Data["Données"]
        DB[(Base de données)]
    end

    User -->|Se connecter| Login
    User -->|S'inscrire| Register
    Login -->|Succès| Dashboard
    Register -->|Créer compte| DB
    Dashboard -->|Consulter| Profile
    Profile -->|Sauvegarder| DB
    DB -.->|Données| Dashboard
```

Réponds UNIQUEMENT avec le bloc ```mermaid, sans texte avant ou après."""

    def development_docs_prompt(self) -> str:
        """Prompt pour la documentation de développement détaillée."""
        return f"""{self._project_context(include_code=True)}

---

Rédige une documentation de développement détaillée en français pour ce projet.
La documentation doit être en Markdown et couvrir :

1. **Vue d'ensemble** : Objectif du projet, contexte, périmètre
2. **Architecture technique** : Description des couches, patterns utilisés, choix techniques
3. **Structure du code** : Organisation des fichiers et répertoires, conventions
4. **Composants principaux** : Description détaillée de chaque module/composant important
5. **Flux de données** : Comment les données circulent dans l'application
6. **API et interfaces** : Endpoints, signatures de fonctions clés, contrats
7. **Gestion des erreurs** : Stratégie de gestion des erreurs
8. **Sécurité** : Mesures de sécurité implémentées
9. **Performance** : Optimisations, caching, etc.
10. **Tests** : Stratégie de tests, couverture

Sois précis et référence les fichiers du projet. Format Markdown propre."""

    def todo_prompt(self) -> str:
        """Prompt pour identifier les points restants."""
        return f"""{self._project_context(include_code=True)}

---

En analysant le code source, identifie les points restants à faire dans ce projet.
Cherche les indices suivants :
- Commentaires TODO, FIXME, HACK, XXX, OPTIMIZE dans le code
- Fonctions vides ou avec des `pass`, `...`, `NotImplementedError`
- Tests manquants ou incomplets
- Documentation manquante
- Gestion d'erreurs absente
- Améliorations possibles de performance
- Problèmes de sécurité potentiels
- Code dupliqué à factoriser
- Dépendances à mettre à jour

Fournis le résultat en Markdown structuré avec :
1. **TODOs trouvés dans le code** (avec fichier et ligne si possible)
2. **Fonctionnalités incomplètes**
3. **Améliorations techniques recommandées**
4. **Dette technique identifiée**
5. **Prochaines étapes suggérées**

Priorise chaque item : 🔴 Critique, 🟡 Important, 🟢 Nice-to-have"""

    def setup_prompt(self) -> str:
        """Prompt pour générer le SETUP.md."""
        return f"""{self._project_context()}

---

Rédige un guide SETUP.md complet en français pour installer et démarrer ce projet.

Le guide doit inclure :
1. **Prérequis** : OS, langages, outils requis avec versions minimales
2. **Installation** : Étapes d'installation pas à pas
3. **Configuration** : Variables d'environnement, fichiers de config à créer
4. **Démarrage** : Commandes pour lancer l'application (dev et production)
5. **Commandes utiles** : Tests, lint, build, migrations, etc.
6. **Dépannage** : Problèmes courants et solutions

Utilise des blocs de code bash pour les commandes.
Sois concis mais complet. Format Markdown."""

    def readme_prompt(self) -> str:
        """Prompt pour générer le README.md principal."""
        return f"""{self._project_context()}

---

Rédige un README.md professionnel en français pour ce projet.

Structure attendue :
1. **Titre et description** : Badge(s) si pertinent, description courte
2. **Fonctionnalités** : Liste des fonctionnalités principales
3. **Stack technique** : Technologies utilisées
4. **Démarrage rapide** : Les 3-5 commandes essentielles pour démarrer
5. **Documentation** : Liens vers les docs dans le dossier docs/
   - 📐 Architecture (docs/architecture.drawio + PNG)
   - 📋 Schéma fonctionnel (docs/functional.drawio + PNG)
   - 📖 Documentation de développement (docs/DEVELOPMENT.md)
   - ✅ Points restants (docs/TODO.md)
   - 🔧 Guide d'installation (docs/SETUP.md)
6. **Contribuer** : Comment contribuer au projet
7. **Licence** : Mention de licence

Format Markdown propre et professionnel."""
