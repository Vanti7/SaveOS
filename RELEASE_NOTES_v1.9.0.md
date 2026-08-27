# SaveOS v1.9.0

**Date de publication :** 27/08/2026

## Changements

- Purge automatique des anciens snapshots selon la politique de rétention du tenant (daily/weekly/monthly), appliquée après chaque sauvegarde réussie
- Endpoint d'usage de quota par tenant (consommation réelle, pourcentage, coût estimé) et ajustement du quota/rétention après création
- Page d'accueil du tableau de bord connectée aux vraies données (statistiques, activité récente, actions rapides) au lieu de données simulées, carte d'utilisation du quota

## Installation

```bash
# Télécharger la version 1.9.0
git checkout v1.9.0

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
