# SaveOS v1.9.1

**Date de publication :** 27/08/2026

## Changements

- Correction : GET /api/v1/tenants/{id} plantait (500) contre une vraie base PostgreSQL (SUM() renvoie decimal.Decimal, pas int, incompatible avec le calcul du coût estimé)

## Installation

```bash
# Télécharger la version 1.9.1
git checkout v1.9.1

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
