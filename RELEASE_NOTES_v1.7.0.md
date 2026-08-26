# SaveOS v1.7.0

**Date de publication :** 26/08/2026

## Changements

- Isolation multi-tenant réelle : tenants créables (POST/GET /api/v1/tenants), listes agents/jobs/snapshots filtrables par tenant_id, quota de stockage appliqué aux sauvegardes
- Secret d'enregistrement par tenant requis pour l'auto-enregistrement d'un agent (fermait un enregistrement totalement ouvert, sans authentification)
- provision_agent exige désormais le token dashboard et un tenant_id explicite (fermait une émission de token non authentifiée)
- Correction : Agent.hostname unique par tenant seulement, plus globalement
- Tableau de bord : sélecteur de tenant (barre latérale), carte de gestion des tenants dans les paramètres

## Installation

```bash
# Télécharger la version 1.7.0
git checkout v1.7.0

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
