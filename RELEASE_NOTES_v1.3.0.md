# SaveOS v1.3.0

**Date de publication :** 20/08/2026

## Changements

- Instrumentation Prometheus réelle sur /metrics de l'API (jauges agents/jobs/snapshots dérivées de la DB)
- Endpoint /metrics dédié du worker avec compteurs événementiels réels (jobs traités, durée, succès/échec), mode multiprocess prometheus_client
- Stack Prometheus + Grafana local (docker-compose.yml) avec dashboard auto-provisionné, pour visualiser les métriques sans accès au monitoring externe de production
- Retrait du stack Prometheus/Grafana auto-hébergé mort de docker-compose.prod.yml (la prod réelle utilise un Grafana + Zabbix externes)

## Installation

```bash
# Télécharger la version 1.3.0
git checkout v1.3.0

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
