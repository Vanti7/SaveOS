# SaveOS v1.6.0

**Date de publication :** 26/08/2026

## Changements

- Traefik route désormais réellement api/web vers Let's Encrypt en production (certificat valide, plus seulement le dashboard Traefik)
- verify_ssl/rejectUnauthorized déduits de l'hôte côté agent, API et dashboard web (fin de la désactivation systématique de la vérification TLS)
- Correction : conflit container_name/deploy.replicas rendant docker-compose.prod.yml structurellement invalide
- Dashboard Traefik retiré de l'exposition directe non authentifiée sur le port 8080

## Installation

```bash
# Télécharger la version 1.6.0
git checkout v1.6.0

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
