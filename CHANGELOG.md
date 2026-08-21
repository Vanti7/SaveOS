# Changelog SaveOS

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [Non publié]
## [1.5.0] - 2026-08-21

### ✨ Nouvelles fonctionnalités

- Installeurs natifs de l'agent (Windows .exe via Inno Setup, macOS .pkg/.dmg, Linux .deb) construits et publiés sur chaque GitHub Release
- ServiceManager enfin câblé dans le CLI (saveos-agent service install/start/stop/status), adapté aux exécutables figés
- Nouveau endpoint /download/agent/{platform}/installer (redirection vers l'asset GitHub Release de la version courante)
- Le package source téléchargeable (/download/agent/{platform}) empaquette désormais le vrai code de l'agent, plus une copie obsolète

---

## [1.4.0] - 2026-08-20

### ✨ Nouvelles fonctionnalités

- pytest et les tests web (Vitest) deviennent des gates bloquants en CI sur push/PR (auparavant aucun échec de test n'empêchait rien)
- Couverture ajoutée sur agent/config.py, agent/service.py et la génération de packages agent, jusqu'ici à 0%
- Installation de Vitest + React Testing Library, tests sur RestoreModal et la page snapshots
- Seuil de couverture pytest (--cov-fail-under=60) et correction des 3 tests cassés de test_basic.py

---

## [1.3.0] - 2026-08-20

### ✨ Nouvelles fonctionnalités

- Instrumentation Prometheus réelle sur /metrics de l'API (jauges agents/jobs/snapshots dérivées de la DB)
- Endpoint /metrics dédié du worker avec compteurs événementiels réels (jobs traités, durée, succès/échec), mode multiprocess prometheus_client
- Stack Prometheus + Grafana local (docker-compose.yml) avec dashboard auto-provisionné, pour visualiser les métriques sans accès au monitoring externe de production
- Retrait du stack Prometheus/Grafana auto-hébergé mort de docker-compose.prod.yml (la prod réelle utilise un Grafana + Zabbix externes)

---

## [1.2.0] - 2026-08-19

### ✨ Nouvelles fonctionnalités

- Restauration granulaire : sélection de fichiers/dossiers dans un snapshot, téléchargement navigateur ou dépôt direct sur la machine agent
- Navigation dans le contenu d'une archive Borg depuis le tableau de bord
- Authentification double agent/tableau de bord (token dashboard)
- Pages Agents/Jobs/Snapshots du tableau de bord connectées à l'API réelle (fin des données simulées)
- Correction : sérialisation JSON de Job.config, ambiguïté de clé étrangère Job/Snapshot, kwarg RQ invalide

---


### Prévu
- Certificats TLS valides
- Multi-tenancy avancée
- Gestion des utilisateurs et authentification

---

## [1.0.0] - 2024-12-15

### 🎉 Version initiale complète

**SaveOS v1.0.0** - Système de sauvegarde centralisé avec interface web complète.

### Ajouté
#### Interface Web
- **Dashboard React/Next.js** avec statistiques en temps réel
- **Gestion des agents** : liste, statut, monitoring
- **Page de téléchargement d'agents** avec génération automatique
- **Provisioning automatique** des agents avec tokens pré-configurés
- **Monitoring des jobs** en temps réel
- **Navigation des snapshots** avec historique
- **Paramètres système** centralisés
- **Design responsive** avec Tailwind CSS

#### API REST
- **Endpoints complets** pour la gestion des agents
- **Système d'authentification** par tokens
- **Provisioning automatique** : `POST /api/v1/agents/provision`
- **Téléchargement d'agents** : `GET /download/agent/{platform}`
- **Génération de packages** pré-configurés (ZIP/TAR.GZ)
- **Endpoints de monitoring** : `/health`, `/metrics`
- **Documentation OpenAPI** automatique

#### Agent CLI
- **Support multiplateforme** : Windows, macOS, Linux
- **Configuration automatique** selon l'OS
- **Enregistrement automatique** auprès du serveur
- **Mode daemon** avec heartbeats toutes les 5 minutes
- **Gestion des services système** (systemd, launchd, tâches planifiées)
- **Interface CLI complète** avec commandes intuitives
- **Gestion sécurisée des tokens**

#### Worker & Jobs
- **Worker RQ** pour traitement asynchrone
- **Intégration Borg** pour sauvegardes chiffrées
- **Gestion des jobs** : backup, restore, check
- **Mise à jour automatique** de la base de données
- **Gestion des erreurs** et logging détaillé
- **Support des repositories** locaux et S3

#### Base de données
- **Schéma PostgreSQL complet** avec SQLAlchemy
- **Tables optimisées** : tenants, users, agents, jobs, snapshots
- **Relations cohérentes** et contraintes d'intégrité
- **Indexation** pour les performances
- **Support multi-tenant** (basique)

#### Infrastructure
- **Docker Compose** complet avec 6 services
- **Images Docker optimisées** pour production
- **Volumes persistants** pour les données
- **Configuration réseau** sécurisée
- **Health checks** pour tous les services
- **Support MinIO** pour stockage S3-compatible

#### Scripts & Outils
- **Scripts d'installation** pour Linux/macOS et Windows
- **Scripts de test** automatisés
- **Génération automatique** de certificats TLS
- **Validation d'installation** complète
- **Makefile** avec commandes de développement

#### Documentation
- **README complet** avec guide d'utilisation
- **Documentation d'architecture** détaillée
- **Guide d'installation** pas-à-pas
- **Exemples de configuration**
- **Troubleshooting** et FAQ

### Sécurité
- **Chiffrement côté client** avec Borg
- **Transport TLS** avec certificats self-signed
- **Tokens d'authentification** sécurisés
- **Isolation des agents** par tenant
- **Permissions restrictives** sur les fichiers de configuration

### Performance
- **Architecture stateless** pour l'API
- **Workers asynchrones** avec Redis
- **Base de données optimisée** avec index
- **Caching** et optimisations diverses
- **Support de la scalabilité horizontale**

### Compatibilité
- **Python 3.8+** requis
- **Support complet** : Windows 10+, macOS 10.15+, Linux (Ubuntu/CentOS/Debian)
- **Docker** et Docker Compose
- **PostgreSQL 15+**, **Redis 7+**, **MinIO** latest

---

## Schéma de versioning

### Format : `MAJOR.MINOR.PATCH`

- **MAJOR** : Changements incompatibles avec les versions précédentes
- **MINOR** : Nouvelles fonctionnalités compatibles
- **PATCH** : Corrections de bugs compatibles

### Exemples futurs :
- `1.0.1` : Correction de bugs
- `1.1.0` : Nouvelle fonctionnalité (ex: restauration granulaire)
- `2.0.0` : Changement majeur (ex: nouvelle API incompatible)

### Tags de pré-version :
- `1.1.0-alpha.1` : Version alpha
- `1.1.0-beta.1` : Version beta
- `1.1.0-rc.1` : Release candidate

---

## Notes de migration

### Depuis version antérieure
Première version - pas de migration nécessaire.

### Prochaines versions
Les notes de migration seront documentées ici pour chaque version majeure.

---

## Contributeurs

- **Développement initial** : Assistant IA Claude
- **Spécifications** : Équipe SaveOS
- **Architecture** : Basée sur les meilleures pratiques industrielles

---

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.