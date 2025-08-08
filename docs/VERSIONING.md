# Guide de Versioning SaveOS

## 🏷️ Système de Versioning

SaveOS utilise le **Semantic Versioning** (SemVer) pour gérer les versions de manière professionnelle.

### Format : `MAJOR.MINOR.PATCH`

- **MAJOR** : Changements incompatibles avec les versions précédentes
- **MINOR** : Nouvelles fonctionnalités compatibles avec l'API existante
- **PATCH** : Corrections de bugs compatibles

### Exemples :
- `1.0.0` → `1.0.1` : Correction de bugs
- `1.0.0` → `1.1.0` : Nouvelle fonctionnalité
- `1.0.0` → `2.0.0` : Changement majeur incompatible

## 🛠️ Outils de Versioning

### Script de Version (`scripts/version.py`)

Gestionnaire central des versions qui met à jour automatiquement :
- `VERSION` (fichier principal)
- `web/package.json` (interface web)
- `setup.py` (agent Python)
- `CHANGELOG.md` (historique)

#### Commandes :

```bash
# Afficher la version actuelle
python scripts/version.py current

# Informations détaillées
python scripts/version.py info

# Incrémenter une version
python scripts/version.py bump --type [major|minor|patch|prerelease]
```

#### Exemples :

```bash
# Correction de bug : 1.0.0 → 1.0.1
python scripts/version.py bump --type patch --message "Correction du bug XYZ"

# Nouvelle fonctionnalité : 1.0.1 → 1.1.0
python scripts/version.py bump --type minor --message "Ajout de la restauration granulaire"

# Version majeure : 1.1.0 → 2.0.0
python scripts/version.py bump --type major --message "Nouvelle architecture API"

# Version de test : 1.0.0 → 1.0.1-alpha.1
python scripts/version.py bump --type prerelease --prerelease alpha
```

#### Avec changements détaillés :

```bash
python scripts/version.py bump --type minor \
  --message "Ajout du monitoring avancé" \
  --changes "Dashboard Grafana" "Métriques personnalisées" "Alertes email"
```

### Script de Release (`scripts/release.sh`)

Script interactif complet pour créer une release :

```bash
# Mode interactif (recommandé)
./scripts/release.sh

# Mode automatique (CI/CD)
./scripts/release.sh --auto
```

Le script effectue :
1. ✅ Vérifications préliminaires (Git, dépendances)
2. 🏷️ Sélection du type de version
3. 📝 Saisie des changements
4. 🧪 Exécution des tests
5. 📦 Création de la version
6. 🔖 Commit et tag Git
7. 🚀 Push vers le dépôt distant

## 📋 Workflow de Release

### 1. Développement

```bash
# Développer les fonctionnalités
git checkout -b feature/nouvelle-fonctionnalite
# ... développement ...
git commit -m "Ajout de la nouvelle fonctionnalité"
```

### 2. Merge vers main

```bash
git checkout main
git merge feature/nouvelle-fonctionnalite
```

### 3. Créer une release

```bash
# Option A : Script interactif (recommandé)
./scripts/release.sh

# Option B : Commande directe
python scripts/version.py bump --type minor \
  --message "Nouvelle fonctionnalité X" \
  --changes "Fonctionnalité A" "Amélioration B" "Correction C"
```

### 4. Publier

```bash
git add .
git commit -m "v1.1.0: Nouvelle fonctionnalité X"
git tag v1.1.0
git push origin main --tags
```

## 📁 Fichiers Gérés Automatiquement

Le système met à jour automatiquement :

| Fichier | Description |
|---------|-------------|
| `VERSION` | Version principale du projet |
| `web/package.json` | Version de l'interface web |
| `setup.py` | Version de l'agent Python |
| `CHANGELOG.md` | Historique détaillé des changements |
| `RELEASE_NOTES_vX.X.X.md` | Notes de version spécifiques |

## 🏗️ Types de Versions

### Patch (1.0.0 → 1.0.1)
**Quand utiliser :** Corrections de bugs, améliorations mineures

**Exemples :**
- Correction d'un bug dans l'agent
- Amélioration des performances
- Mise à jour de dépendances
- Corrections de typos

### Minor (1.0.0 → 1.1.0)
**Quand utiliser :** Nouvelles fonctionnalités compatibles

**Exemples :**
- Nouvelle page dans l'interface web
- Nouveau endpoint API
- Nouvelle commande agent
- Amélioration UX majeure

### Major (1.0.0 → 2.0.0)
**Quand utiliser :** Changements incompatibles

**Exemples :**
- Nouvelle version d'API incompatible
- Changement de format de base de données
- Suppression de fonctionnalités
- Nouvelle architecture

### Prerelease (1.0.0 → 1.0.1-alpha.1)
**Quand utiliser :** Versions de test

**Types :**
- `alpha` : Version très précoce, instable
- `beta` : Version de test, plus stable
- `rc` : Release Candidate, presque finale

## 🤖 Intégration CI/CD

### GitHub Actions

```yaml
name: Release
on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Create Release
        run: ./scripts/release.sh --auto
```

### Automatisation

```bash
# Release automatique patch (pour hotfixes)
./scripts/release.sh --auto

# Release avec validation manuelle
./scripts/release.sh
```

## 📊 Suivi des Versions

### Historique complet

Consultez `CHANGELOG.md` pour l'historique détaillé de toutes les versions.

### Notes de version

Chaque version génère un fichier `RELEASE_NOTES_vX.X.X.md` avec :
- Date de publication
- Liste des changements
- Instructions d'installation
- Informations de compatibilité

### Tags Git

Toutes les versions sont taguées dans Git :

```bash
# Lister toutes les versions
git tag

# Checkout d'une version spécifique
git checkout v1.0.1

# Voir les changements entre versions
git log v1.0.0..v1.0.1
```

## 🔍 Bonnes Pratiques

### 1. Messages de Commit
```bash
# ✅ Bon
git commit -m "fix: correction du bug de connexion agent"
git commit -m "feat: ajout du dashboard monitoring"
git commit -m "docs: mise à jour du README"

# ❌ Mauvais
git commit -m "fix bug"
git commit -m "update"
```

### 2. Branches
```bash
# Fonctionnalités
feature/nom-fonctionnalite

# Corrections
fix/nom-du-bug

# Releases
release/v1.1.0
```

### 3. Tests avant Release
- ✅ Tests unitaires passent
- ✅ Configuration Docker valide
- ✅ Documentation à jour
- ✅ CHANGELOG mis à jour

## 🆘 Dépannage

### Erreur de version invalide
```bash
# Vérifier le format
python scripts/version.py info

# Réinitialiser si nécessaire
echo "1.0.0" > VERSION
```

### Conflit de merge sur VERSION
```bash
# Résoudre manuellement et utiliser
python scripts/version.py bump --type patch
```

### Rollback d'une version
```bash
# Supprimer le tag local et distant
git tag -d v1.0.1
git push origin :refs/tags/v1.0.1

# Revenir à la version précédente
echo "1.0.0" > VERSION
```

---

Ce système de versioning professionnel garantit une gestion cohérente et traçable de toutes les versions de SaveOS.