# SaveOS v1.9.3

**Date de publication :** 27/08/2026

## Changements

- Correction : le package source téléchargé (Téléchargements) est désormais réellement connecté au provisioning (hostname et token du provisioning embarqués directement, plus de secret de tenant à ressaisir à la main)
- Nouvelle commande agent.cli configure --token, pour un agent déjà provisionné côté serveur (aucun appel réseau)

## Installation

```bash
# Télécharger la version 1.9.3
git checkout v1.9.3

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
