# SaveOS v1.2.0

**Date de publication :** 19/08/2026

## Changements

- Restauration granulaire : sélection de fichiers/dossiers dans un snapshot, téléchargement navigateur ou dépôt direct sur la machine agent
- Navigation dans le contenu d'une archive Borg depuis le tableau de bord
- Authentification double agent/tableau de bord (token dashboard)
- Pages Agents/Jobs/Snapshots du tableau de bord connectées à l'API réelle (fin des données simulées)
- Correction : sérialisation JSON de Job.config, ambiguïté de clé étrangère Job/Snapshot, kwarg RQ invalide

## Installation

```bash
# Télécharger la version 1.2.0
git checkout v1.2.0

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
