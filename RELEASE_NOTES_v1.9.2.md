# SaveOS v1.9.2

**Date de publication :** 27/08/2026

## Changements

- Correction : VERSION manquant des images Docker (api/prod), l'installeur natif (GET /download/agent/{platform}/installer) plantait systématiquement
- Correction : TenantProvider appelait GET /api/v1/tenants à chaque navigation pour une session utilisateur, échouant systématiquement (403) puisque réservé au token dashboard statique

## Installation

```bash
# Télécharger la version 1.9.2
git checkout v1.9.2

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
