# SaveOS v1.5.0

**Date de publication :** 21/08/2026

## Changements

- Installeurs natifs de l'agent (Windows .exe via Inno Setup, macOS .pkg/.dmg, Linux .deb) construits et publiés sur chaque GitHub Release
- ServiceManager enfin câblé dans le CLI (saveos-agent service install/start/stop/status), adapté aux exécutables figés
- Nouveau endpoint /download/agent/{platform}/installer (redirection vers l'asset GitHub Release de la version courante)
- Le package source téléchargeable (/download/agent/{platform}) empaquette désormais le vrai code de l'agent, plus une copie obsolète

## Installation

```bash
# Télécharger la version 1.5.0
git checkout v1.5.0

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
