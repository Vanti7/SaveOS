# SaveOS - Système de sauvegarde centralisé

SaveOS est un système de sauvegarde centralisé avec agents multiplateforme (macOS, Windows, Linux) et un serveur central. Il offre des sauvegardes full/incrémentales avec restauration complète et granulaire, une API stateless, des workers pour l'exécution des jobs, un stockage S3-compatible et une interface web.

## 🏗️ Architecture

Le système SaveOS est composé de :

- **Interface Web** : Dashboard React pour la gestion centralisée
- **API FastAPI** : Interface REST pour la gestion des agents et jobs
- **Worker RQ** : Traitement asynchrone des jobs de sauvegarde
- **Agent CLI** : Client léger pour les machines à sauvegarder
- **PostgreSQL** : Base de données pour les métadonnées
- **Redis** : Queue pour les jobs asynchrones
- **MinIO** : Stockage S3-compatible pour les archives

## 🚀 Démarrage rapide

### Prérequis

- Docker et Docker Compose
- Python 3.8+ (pour l'agent)
- OpenSSL (pour les certificats TLS)

### 1. Cloner le projet

```bash
git clone <repository-url>
cd SaveOS
```

### 2. Démarrer les services

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

Ce script va :
- Générer les certificats TLS self-signed
- Construire les images Docker
- Démarrer tous les services
- Vérifier que l'API est accessible

### 3. Installer et tester l'agent

```bash
chmod +x scripts/test_agent.sh
./scripts/test_agent.sh
```

## 🔧 Configuration

### Services

Les services sont accessibles aux adresses suivantes :

- **Interface Web** : http://localhost:3000
- **API SaveOS** : https://localhost:8000
- **PostgreSQL** : localhost:5432 (saveos/saveos123)
- **Redis** : localhost:6379
- **MinIO Console** : http://localhost:9001 (saveos/saveos123456)

### Variables d'environnement notables

- `DASHBOARD_API_TOKEN` : token statique d'exploitation (bootstrap, scripts, CI) donnant un accès complet à l'API — voir [docs/adr/0001-restauration-granulaire-mvp.md](docs/adr/0001-restauration-granulaire-mvp.md). Le tableau de bord web ne l'utilise plus par défaut une fois la connexion en place (voir [docs/adr/0005-gestion-utilisateurs-roles.md](docs/adr/0005-gestion-utilisateurs-roles.md)). Même valeur côté `api` et `web`, jamais préfixée par `NEXT_PUBLIC_`.
- `JWT_SECRET_KEY` : secret de signature des JWT de session utilisateur (requis côté `api` pour que `/api/v1/auth/login` fonctionne — pas de défaut silencieux).
- `RESTORE_PACKAGE_DIR` : dossier partagé (`api` + `worker`) où sont stockés les paquets zip générés par une restauration. Défaut : `/tmp/restore_packages`.

### Agent

L'agent se configure automatiquement lors de la première utilisation. La configuration est stockée dans :

- **Windows** : `%APPDATA%\\SaveOS\\config.json`
- **macOS** : `~/Library/Application Support/SaveOS/config.json`
- **Linux** : `~/.config/saveos/config.json`

## 📖 Utilisation

### Interface Web

1. **Accédez au dashboard** : http://localhost:3000
2. **Téléchargez des agents** : Section "Téléchargements"
3. **Surveillez les agents** : Section "Agents" 
4. **Consultez les sauvegardes** : Section "Snapshots"
5. **Monitoring en temps réel** : Section "Monitoring"

### Connexion et rôles

Le tableau de bord exige désormais une connexion (email/mot de passe, `/login`) — voir [docs/adr/0005-gestion-utilisateurs-roles.md](docs/adr/0005-gestion-utilisateurs-roles.md). Deux rôles :

- **admin** : gère les utilisateurs et provisionne des agents, au sein de son propre tenant (section "Paramètres").
- **user** : accès en lecture/écriture aux agents/jobs/snapshots de son propre tenant.

`DASHBOARD_API_TOKEN` reste un secret d'exploitation (bootstrap, scripts, CI) — il n'est plus utilisé pour accéder au tableau de bord une fois la connexion en place.

### Multi-tenancy

Chaque agent appartient à un **tenant** (isolation des agents/jobs/snapshots, quota de stockage — voir [docs/adr/0004-multi-tenancy-avancee.md](docs/adr/0004-multi-tenancy-avancee.md)). La création de tenants reste une opération d'exploitation, via l'API avec `DASHBOARD_API_TOKEN` (pas depuis le tableau de bord) :

```bash
# 1. Créer un tenant (le secret d'enregistrement n'est affiché qu'ici, une seule fois)
curl -X POST https://localhost:8000/api/v1/tenants \
  -H "Authorization: Bearer $DASHBOARD_API_TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "acme"}'

# 2. Créer le premier admin de ce tenant (tenant_id = id renvoyé à l'étape 1)
curl -X POST "https://localhost:8000/api/v1/users?tenant_id=1" \
  -H "Authorization: Bearer $DASHBOARD_API_TOKEN" -H "Content-Type: application/json" \
  -d '{"email": "admin@acme.example", "password": "...", "role": "admin"}'

# 3. Se connecter sur /login avec ces identifiants — l'admin peut ensuite
#    créer d'autres utilisateurs de son tenant depuis les Paramètres.
```

### Installation d'agents

Deux options depuis l'interface web (section **"Téléchargements"**), pour chaque plateforme (Windows/macOS/Linux) — un tenant doit être sélectionné au préalable :

- **Installeur natif** (`.exe`/`.dmg`/`.deb`) : aucune dépendance Python requise, enregistre automatiquement l'agent comme service à démarrage automatique (tâche planifiée Windows, launchd macOS, systemd Linux) pendant l'installation. Construit et publié en asset sur chaque [GitHub Release](https://github.com/Vanti7/SaveOS/releases) par `.github/workflows/release.yml` (voir `packaging/` et `docs/adr/0002-packaging-agents.md`).
- **Package source** (`.zip`/`.tar.gz`) : code source de l'agent (`agent/`) pré-configuré avec token, URL serveur et secret d'enregistrement du tenant sélectionné, nécessite Python 3.8+ sur la machine cible.

Dans les deux cas, l'agent apparaît automatiquement dans la liste et commence à envoyer des heartbeats une fois enregistré (`saveos-agent register --registration-secret <secret>`, ou automatique pour l'installeur natif via le script d'installation).

### Commandes de l'agent (optionnel)

Avec l'installeur natif, utilisez directement le binaire (`saveos-agent` dans le PATH, ou l'exécutable installé). Avec le package source, `python -m agent.cli` :

```bash
# Vérifier le statut
saveos-agent status

# Lancer une sauvegarde manuelle
saveos-agent backup

# Mode daemon
saveos-agent daemon

# Gérer le service système (installé automatiquement par l'installeur natif)
saveos-agent service install|start|stop|status
```

### API REST

L'API expose les endpoints suivants :

- `POST /api/v1/agents/register` : Enregistrer un agent
- `POST /api/v1/agents/heartbeat` : Heartbeat d'agent
- `GET /api/v1/agents/stats` : Statistiques de l'agent
- `POST /api/v1/backup` : Créer un job de sauvegarde
- `GET /api/v1/backup/{agent_id}/snapshots` : Lister les snapshots
- `GET /api/v1/jobs/{job_id}` : Statut d'un job
- `GET /health` : Santé de l'API
- `GET /metrics` : Métriques Prometheus
- `GET /download/agent/{platform}` : Télécharger un agent
- `POST /api/v1/agents/provision` : Provisionner un agent (tableau de bord ou admin de ce tenant)
- `POST /api/v1/tenants` : Créer un tenant, retourne son secret d'enregistrement (tableau de bord uniquement)
- `GET /api/v1/tenants` : Lister les tenants (tableau de bord uniquement)
- `POST /api/v1/auth/login` : Connexion (email/mot de passe), émet un JWT
- `GET /api/v1/auth/me` : Informations de l'utilisateur connecté
- `POST /api/v1/users` : Créer un utilisateur (tableau de bord avec tenant_id, ou admin dans son propre tenant)
- `GET /api/v1/users` : Lister les utilisateurs (tableau de bord, ou admin limité à son propre tenant)

Documentation interactive disponible sur : https://localhost:8000/docs

## 🔐 Sécurité

### Chiffrement

- **Transport** : TLS 1.2+ obligatoire. En local (`docker-compose.yml`), certificat self-signed généré par `scripts/generate_certs.sh` (`CN=localhost`). En production (`docker-compose.prod.yml`), certificat Let's Encrypt valide obtenu automatiquement par Traefik (voir section suivante) — les clients (agent, dashboard) vérifient alors réellement le certificat (`verify_ssl`/`rejectUnauthorized` déduits de l'hôte, voir [docs/adr/0003-certificats-tls-production.md](docs/adr/0003-certificats-tls-production.md)).
- **Données** : Chiffrement côté client via Borg avec passphrase
- **Authentification** : Tokens provisionnés pour les agents

### Tokens

Chaque agent reçoit un token unique lors de l'enregistrement. Ce token est stocké de manière sécurisée et utilisé pour toutes les communications avec l'API.

### TLS en production (Traefik + Let's Encrypt)

`docker-compose.prod.yml` route `api`, `web` et le dashboard Traefik exclusivement via Traefik (aucun port direct publié) ; Traefik obtient un certificat Let's Encrypt par domaine via le challenge HTTP-01. Prérequis pour un déploiement réel :

- Variables d'environnement : `DOMAIN` (ex. `saveos.com`) et `ACME_EMAIL` (contact pour Let's Encrypt).
- Enregistrements DNS pointant vers le serveur : `api.${DOMAIN}`, `app.${DOMAIN}`, `traefik.${DOMAIN}`.
- Port 80 joignable depuis internet (challenge HTTP-01) en plus du port 443.

Le dashboard Traefik (`https://traefik.${DOMAIN}`) reste sans authentification applicative — accès restreint au réseau/pare-feu, voir [docs/adr/0003-certificats-tls-production.md](docs/adr/0003-certificats-tls-production.md) pour le détail et les limites.

## 📊 Monitoring

### Logs

Voir les logs des services :

```bash
# Tous les services
docker-compose logs -f

# Service spécifique
docker-compose logs -f api
docker-compose logs -f worker
```

### Métriques

Deux endpoints exposent de vraies métriques au format d'exposition Prometheus :

- `https://localhost:8000/metrics` (API) : `saveos_agents_total{status}`, `saveos_jobs_total{type,status}`, `saveos_snapshots_total`, `saveos_snapshots_size_bytes_total` — jauges recalculées depuis la base à chaque scrape.
- `http://localhost:9200/metrics` (worker) : `saveos_worker_jobs_total{job_type,outcome}`, `saveos_worker_job_duration_seconds{job_type}` — compteurs événementiels réels (le worker exécute chaque job dans un processus enfant forké par RQ ; les métriques sont agrégées via le mode multiprocess de `prometheus_client`, voir `worker/run.py`).

**En production**, aucun Prometheus/Grafana n'est auto-hébergé par ce dépôt : un Grafana + Zabbix externes scrapent directement ces deux endpoints (adresses dans `deploy/environments.yml`, section `production.monitoring`).

**En local**, `docker-compose.yml` inclut un stack Prometheus + Grafana de confort pour visualiser ces métriques sans accès à l'infra de prod :

- Prometheus : http://localhost:9090 (cibles sur `/targets`)
- Grafana : http://localhost:3001 (`admin` / `$GRAFANA_PASSWORD`, défaut `admin`) — datasource et dashboard « SaveOS - Vue d'ensemble » provisionnés automatiquement (`deploy/grafana/`)

## 🛠️ Développement

### Structure du projet

```
SaveOS/
├── web/                # Interface Web React
│   ├── app/           # Pages Next.js
│   ├── components/    # Composants React
│   └── lib/           # Utilitaires et API
├── api/                # API FastAPI
│   ├── main.py        # Point d'entrée
│   ├── database.py    # Modèles SQLAlchemy
│   ├── schemas.py     # Schémas Pydantic
│   └── auth.py        # Authentification
├── worker/            # Worker RQ
│   └── tasks.py       # Tâches asynchrones
├── agent/             # Agent CLI
│   ├── cli.py         # Interface CLI
│   ├── config.py      # Configuration
│   └── api_client.py  # Client API
├── scripts/           # Scripts utilitaires
├── docker-compose.yml # Services Docker
└── requirements.txt   # Dépendances Python
```

### Tests

```bash
# Suite Python (API, worker, agent) — fixtures SQLite, aucun service externe requis
pytest tests/ -m "not integration" --cov=api --cov=worker --cov=agent --cov-report=term-missing

# Suite web (Vitest)
cd web && npm run test

# Test manuel complet de l'agent contre une stack locale réelle
./scripts/test_agent.sh
```

`pytest`/`npm run test` sont bloquants en CI (`.github/workflows/simple-ci.yml`, voir `docs/CI-CD.md`) — un test qui échoue fait échouer le job sur toute PR ou push.

### Base de données

Les tables sont créées automatiquement par SQLAlchemy au démarrage de l'API. Le schéma inclut :

- `tenants` : Locataires (multi-tenancy)
- `users` : Utilisateurs
- `agents` : Agents de sauvegarde
- `jobs` : Jobs de sauvegarde/restauration
- `snapshots` : Archives Borg

## 🚫 Limitations du MVP

- Dashboard Traefik en production sans authentification applicative (voir [docs/adr/0003-certificats-tls-production.md](docs/adr/0003-certificats-tls-production.md))
- Gestion des tenants (création/liste) réservée à l'API + `DASHBOARD_API_TOKEN`, pas d'interface web (voir [docs/adr/0005-gestion-utilisateurs-roles.md](docs/adr/0005-gestion-utilisateurs-roles.md))
- Pas de restauration granulaire via l'interface
- Monitoring limité (pas de Grafana intégré)

## 🔄 Maintenance

### Arrêter les services

```bash
docker-compose down
```

### Mise à jour

```bash
git pull
docker-compose build
docker-compose up -d
```

### Sauvegarde des données

Les données persistantes sont stockées dans des volumes Docker :

```bash
# Sauvegarder les volumes
docker run --rm -v saveos_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
docker run --rm -v saveos_minio_data:/data -v $(pwd):/backup alpine tar czf /backup/minio_backup.tar.gz -C /data .
```

## 📞 Support

Pour le support et les questions :

1. Vérifiez les logs : `docker-compose logs -f`
2. Vérifiez la santé des services : `docker-compose ps`
3. Testez l'API : `curl -k https://localhost:8000/health`

## 📋 TODO / Roadmap

- [x] Interface web React ✅
- [x] Téléchargement d'agents depuis l'interface ✅
- [x] Provisioning automatique des agents ✅
- [x] Restauration granulaire via l'interface ✅
- [x] Monitoring avancé (Grafana) ✅
- [x] Tests automatisés ✅
- [x] Packaging des agents (exe/dmg/deb) ✅
- [x] Certificats TLS valides ✅
- [x] Multi-tenancy avancée ✅
- [x] Gestion des utilisateurs et rôles ✅
- [ ] Facturation et quotas

## 📄 Licence

**GNU Affero General Public License v3.0 (AGPL-3.0)**

SaveOS est distribué sous licence AGPL-3.0, qui garantit que :

✅ **Le code reste ouvert** même pour les services réseau  
✅ **Les améliorations** doivent être partagées avec la communauté  
✅ **Usage libre** pour projets open source et usage personnel  
✅ **Licence commerciale** disponible pour usage propriétaire  

**Pourquoi AGPL-3.0 ?**
- Protège contre l'usage commercial sans contribution
- Encourage l'innovation collaborative
- Permet un modèle économique viable
- Garantit la pérennité du projet

Pour usage commercial sans obligations AGPL, contactez : license@saveos.local

Voir [LICENSE](LICENSE) pour le texte complet et [LICENSE.md](LICENSE.md) pour les détails.