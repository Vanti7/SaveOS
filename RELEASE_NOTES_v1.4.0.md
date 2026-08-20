# SaveOS v1.4.0

**Date de publication :** 20/08/2026

## Changements

- pytest et les tests web (Vitest) deviennent des gates bloquants en CI sur push/PR (auparavant aucun échec de test n'empêchait rien)
- Couverture ajoutée sur agent/config.py, agent/service.py et la génération de packages agent, jusqu'ici à 0%
- Installation de Vitest + React Testing Library, tests sur RestoreModal et la page snapshots
- Seuil de couverture pytest (--cov-fail-under=60) et correction des 3 tests cassés de test_basic.py

## Installation

```bash
# Télécharger la version 1.4.0
git checkout v1.4.0

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
