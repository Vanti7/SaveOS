#!/bin/bash
# Script de validation complète de l'installation SaveOS

set -e

echo "🔍 Validation de l'installation SaveOS"
echo "======================================"

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
log_info() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Vérifications des prérequis
echo "📋 Vérification des prérequis..."

if command -v docker &> /dev/null; then
    log_info "Docker installé: $(docker --version)"
else
    log_error "Docker non installé"
    exit 1
fi

if command -v docker-compose &> /dev/null; then
    log_info "Docker Compose installé: $(docker-compose --version)"
else
    log_error "Docker Compose non installé"
    exit 1
fi

if command -v python3 &> /dev/null; then
    log_info "Python installé: $(python3 --version)"
else
    log_error "Python 3 non installé"
    exit 1
fi

# Vérification des fichiers du projet
echo ""
echo "📁 Vérification des fichiers du projet..."

required_files=(
    "docker-compose.yml"
    "requirements.txt"
    "api/main.py"
    "worker/tasks.py"
    "agent/cli.py"
    "scripts/setup.sh"
    "README.md"
)

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        log_info "Fichier présent: $file"
    else
        log_error "Fichier manquant: $file"
        exit 1
    fi
done

# Vérification de la structure des répertoires
echo ""
echo "📂 Vérification de la structure des répertoires..."

required_dirs=(
    "api"
    "worker"
    "agent"
    "scripts"
    "tests"
)

for dir in "${required_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
        log_info "Répertoire présent: $dir"
    else
        log_error "Répertoire manquant: $dir"
        exit 1
    fi
done

# Vérification de la syntaxe Python
echo ""
echo "🐍 Vérification de la syntaxe Python..."

python_files=(
    "api/main.py"
    "api/database.py"
    "api/schemas.py"
    "api/auth.py"
    "worker/tasks.py"
    "agent/cli.py"
    "agent/config.py"
    "agent/api_client.py"
)

for file in "${python_files[@]}"; do
    if python3 -m py_compile "$file" 2>/dev/null; then
        log_info "Syntaxe valide: $file"
    else
        log_error "Erreur de syntaxe: $file"
        exit 1
    fi
done

# Vérification des dépendances Python
echo ""
echo "📦 Vérification des dépendances Python..."

if pip3 show fastapi &> /dev/null; then
    log_info "FastAPI disponible"
else
    log_warn "FastAPI non installé (sera installé avec requirements.txt)"
fi

# Test de la configuration Docker Compose
echo ""
echo "🐳 Validation de la configuration Docker Compose..."

if docker-compose config &> /dev/null; then
    log_info "Configuration Docker Compose valide"
else
    log_error "Configuration Docker Compose invalide"
    exit 1
fi

# Vérification des ports disponibles
echo ""
echo "🔌 Vérification des ports..."

ports=(8000 5432 6379 9000 9001)

for port in "${ports[@]}"; do
    if ! netstat -tuln 2>/dev/null | grep ":$port " &> /dev/null; then
        log_info "Port $port disponible"
    else
        log_warn "Port $port déjà utilisé"
    fi
done

# Test des scripts
echo ""
echo "🔧 Vérification des scripts..."

scripts=(
    "scripts/setup.sh"
    "scripts/generate_certs.sh"
    "scripts/test_agent.sh"
)

for script in "${scripts[@]}"; do
    if [[ -x "$script" ]]; then
        log_info "Script exécutable: $script"
    else
        log_warn "Script non exécutable: $script (sera corrigé)"
        chmod +x "$script"
    fi
done

echo ""
echo "🎉 Validation terminée avec succès!"
echo ""
echo "🚀 Prochaines étapes:"
echo "   1. Lancer: ./scripts/setup.sh"
echo "   2. Tester: ./scripts/test_agent.sh"
echo "   3. Consulter: README.md"
echo ""
echo "📖 Documentation complète dans README.md"