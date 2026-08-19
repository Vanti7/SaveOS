# SaveOS v1.1.1 - Notes de Version

## 🔧 Corrections et Améliorations

### Docker & Configuration
- ✅ **Dockerfile.api** : Ajout des dépendances de compilation manquantes (pkg-config, gcc, g++, libssl-dev)
- ✅ **requirements.txt** : Suppression de borgbackup==1.2.6 (conflit avec package système)
- ✅ **Scripts** : Correction des permissions d'exécution pour setup.sh et generate_certs.sh

### Interface Web
- ✅ **Dockerfile** : Correction de la dépendance package-lock.json manquante
- ✅ **CSS** : Remplacement des classes Tailwind personnalisées par des classes standards
- ✅ **Configuration** : Création d'un Dockerfile.dev pour le développement

### Développement
- ✅ **docker-compose.dev.yml** : Configuration simplifiée pour l'environnement de développement
- ✅ **Hot reload** : Support du rechargement automatique en mode développement
- ✅ **Volumes** : Configuration des volumes pour le développement local

### Corrections de Bugs
- 🐛 Résolution des erreurs de compilation Docker
- 🐛 Correction des conflits de ports lors du démarrage
- 🐛 Stabilisation du processus de setup automatique

### Sécurité & Réseau (suite au déploiement de test)
- 🔒 **Dockerfile.api** : l'API servait du HTTP en clair via `CMD` (les flags TLS n'étaient appliqués que dans le bloc `if __name__ == "__main__"`, jamais atteint sous uvicorn/Docker) — ajout de `--ssl-keyfile`/`--ssl-certfile` au `CMD`
- 🐛 **docker-compose.yml** : healthcheck de l'API en échec permanent (conséquence directe du point précédent, résolu par la correction TLS)
- 🐛 **docker-compose.yml / web** : healthcheck web pointait vers `/api/health`, route inexistante — ajout de la route `web/app/api/health/route.ts`
- 🐛 **NEXT_PUBLIC_API_URL** : la valeur `https://api:8000` (nom DNS interne Docker) était injoignable depuis le navigateur — séparation d'`API_URL` (interne, SSR) et `NEXT_PUBLIC_API_URL` (publique, surchargeable via `PUBLIC_API_URL`)

## 🚀 Utilisation

### Mode Développement
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Mode Production
```bash
./scripts/setup.sh
```

## 📊 Services Disponibles
- Interface Web: http://localhost:3000
- API SaveOS: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- MinIO: http://localhost:9001

---
**Version**: 1.1.1  
**Date**: 2026-08-19  
**Type**: Patch (Corrections et stabilité)