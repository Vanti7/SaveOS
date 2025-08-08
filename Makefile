# Makefile pour SaveOS - Système de sauvegarde centralisé

.PHONY: help setup start stop restart logs clean test install-agent

# Variables
DOCKER_COMPOSE = docker-compose
PYTHON = python3

help: ## Affiche l'aide
	@echo "SaveOS - Système de sauvegarde centralisé"
	@echo "=========================================="
	@echo "Commandes disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Configuration initiale et démarrage des services
	@echo "🚀 Configuration de SaveOS..."
	chmod +x scripts/*.sh
	./scripts/setup.sh

start: ## Démarre les services
	@echo "▶️  Démarrage des services..."
	$(DOCKER_COMPOSE) up -d

stop: ## Arrête les services
	@echo "⏹️  Arrêt des services..."
	$(DOCKER_COMPOSE) down

restart: ## Redémarre les services
	@echo "🔄 Redémarrage des services..."
	$(DOCKER_COMPOSE) restart

logs: ## Affiche les logs des services
	$(DOCKER_COMPOSE) logs -f

logs-api: ## Affiche les logs de l'API
	$(DOCKER_COMPOSE) logs -f api

logs-worker: ## Affiche les logs du worker
	$(DOCKER_COMPOSE) logs -f worker

status: ## Affiche le statut des services
	$(DOCKER_COMPOSE) ps

build: ## Reconstruit les images Docker
	$(DOCKER_COMPOSE) build

clean: ## Nettoie les conteneurs et volumes
	@echo "🧹 Nettoyage..."
	$(DOCKER_COMPOSE) down -v
	docker system prune -f

install-agent: ## Installe l'agent en mode développement
	@echo "📦 Installation de l'agent..."
	pip install -e .

test-agent: ## Teste l'agent
	@echo "🧪 Test de l'agent..."
	chmod +x scripts/test_agent.sh
	./scripts/test_agent.sh

certs: ## Génère les certificats TLS
	@echo "🔐 Génération des certificats..."
	chmod +x scripts/generate_certs.sh
	./scripts/generate_certs.sh

dev: ## Mode développement (avec rechargement automatique)
	@echo "🔧 Mode développement..."
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up

backup-data: ## Sauvegarde les données des volumes Docker
	@echo "💾 Sauvegarde des données..."
	mkdir -p backups
	docker run --rm -v saveos_postgres_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/postgres_$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .
	docker run --rm -v saveos_minio_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/minio_$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .

health: ## Vérifie la santé des services
	@echo "🩺 Vérification de la santé..."
	@curl -k -f https://localhost:8000/health || echo "❌ API non accessible"
	@curl -f http://localhost:9000/minio/health/live || echo "❌ MinIO non accessible"

install-deps: ## Installe les dépendances Python
	pip install -r requirements.txt

format: ## Formate le code Python
	black api/ worker/ agent/
	isort api/ worker/ agent/

lint: ## Vérifie le code avec flake8
	flake8 api/ worker/ agent/

requirements: ## Met à jour requirements.txt
	pip freeze > requirements.txt

# === VERSIONING ===

version: ## Affiche la version actuelle
	python scripts/version.py current

version-info: ## Informations détaillées sur la version
	python scripts/version.py info

version-patch: ## Incrémente la version patch (1.0.0 → 1.0.1)
	python scripts/version.py bump --type patch

version-minor: ## Incrémente la version minor (1.0.0 → 1.1.0)
	python scripts/version.py bump --type minor

version-major: ## Incrémente la version major (1.0.0 → 2.0.0)
	python scripts/version.py bump --type major

version-alpha: ## Crée une version alpha (1.0.0 → 1.0.1-alpha.1)
	python scripts/version.py bump --type prerelease --prerelease alpha

version-beta: ## Crée une version beta (1.0.0 → 1.0.1-beta.1)
	python scripts/version.py bump --type prerelease --prerelease beta

version-rc: ## Crée une version release candidate (1.0.0 → 1.0.1-rc.1)
	python scripts/version.py bump --type prerelease --prerelease rc

release: ## Lance le processus de release interactif
	./scripts/release.sh

release-auto: ## Release automatique (patch)
	./scripts/release.sh --auto