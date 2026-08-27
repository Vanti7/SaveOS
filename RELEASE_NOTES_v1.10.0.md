# SaveOS v1.10.0

**Date de publication :** 27/08/2026

## Changements

- Actions réelles Détails/Configurer/Supprimer sur un agent depuis le tableau de bord (GET/PATCH/DELETE /api/v1/agents/{agent_id})
- Correction : le token (haché) d'un agent n'est plus exposé dans les réponses de listing/détail

## Installation

```bash
# Télécharger la version 1.10.0
git checkout v1.10.0

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
