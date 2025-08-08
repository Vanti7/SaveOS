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

### Installation d'agents

1. Dans l'interface web, allez dans **"Téléchargements"**
2. Choisissez votre plateforme (Windows/macOS/Linux)
3. Entrez le nom de la machine (hostname)
4. **Le système génère automatiquement un package pré-configuré** avec :
   - Token d'authentification unique
   - Configuration serveur
   - Scripts d'installation
5. Transférez et exécutez le package sur la machine cible
6. **L'agent apparaît automatiquement dans la liste** et commence à envoyer des heartbeats

### Commandes de l'agent (optionnel)

```bash
# Vérifier le statut
python agent.py status

# Lancer une sauvegarde manuelle
python agent.py backup

# Mode daemon
python agent.py daemon
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
- `POST /api/v1/agents/provision` : Provisionner un agent

Documentation interactive disponible sur : https://localhost:8000/docs

## 🔐 Sécurité

### Chiffrement

- **Transport** : TLS 1.2+ obligatoire (certificats self-signed pour le MVP)
- **Données** : Chiffrement côté client via Borg avec passphrase
- **Authentification** : Tokens provisionnés pour les agents

### Tokens

Chaque agent reçoit un token unique lors de l'enregistrement. Ce token est stocké de manière sécurisée et utilisé pour toutes les communications avec l'API.

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

Les métriques Prometheus sont disponibles sur `/metrics` de l'API.

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
# Test complet de l'agent
./scripts/test_agent.sh

# Tests unitaires (à implémenter)
pytest tests/
```

### Base de données

Les tables sont créées automatiquement par SQLAlchemy au démarrage de l'API. Le schéma inclut :

- `tenants` : Locataires (multi-tenancy)
- `users` : Utilisateurs
- `agents` : Agents de sauvegarde
- `jobs` : Jobs de sauvegarde/restauration
- `snapshots` : Archives Borg

## 🚫 Limitations du MVP

- Certificats TLS self-signed (non adaptés à la production)
- Multi-tenancy basique
- Pas de restauration granulaire via l'interface
- Authentification simplifiée (pas de gestion utilisateurs)
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
- [ ] Restauration granulaire via l'interface
- [ ] Monitoring avancé (Grafana)
- [ ] Tests automatisés
- [ ] Packaging des agents (exe/dmg/deb)
- [ ] Certificats TLS valides
- [ ] Multi-tenancy avancée
- [ ] Gestion des utilisateurs et rôles
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