# SaveOS v1.10.2

**Date de publication :** 11/09/2026

## Changements

- Déploiement staging : le build de l'image web échouait systématiquement (module vitest/config introuvable) faute de devDependencies installées dans le stage de build
- CI : le build de l'image web (stage web-builder) est désormais vérifié à chaque PR, de façon bloquante
- Ajout de .dockerignore (racine et web/), jusque-là ignoré par erreur par .gitignore

## Installation

```bash
# Télécharger la version 1.10.2
git checkout v1.10.2

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
