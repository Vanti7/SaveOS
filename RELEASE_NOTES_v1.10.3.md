# SaveOS v1.10.3

**Date de publication :** 11/09/2026

## Changements

- worker : job.snapshot_id restait à NULL après un backup réussi (assigné avant flush)
- Sécurité : next.js 14.0.4 -> 14.2.35 (vulnérabilité critique corrigée)
- Docker : images web migrées de node:18-alpine (EOL) vers node:20-alpine

## Installation

```bash
# Télécharger la version 1.10.3
git checkout v1.10.3

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
