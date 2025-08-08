#!/bin/bash
# Script de release automatisé pour SaveOS

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
log_info() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_step() { echo -e "${BLUE}🔄 $1${NC}"; }

# Vérifications préliminaires
check_requirements() {
    log_step "Vérification des prérequis..."
    
    # Git
    if ! command -v git &> /dev/null; then
        log_error "Git non installé"
        exit 1
    fi
    
    # Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 non installé"
        exit 1
    fi
    
    # Docker (optionnel)
    if command -v docker &> /dev/null; then
        log_info "Docker disponible"
    else
        log_warn "Docker non disponible (tests limités)"
    fi
    
    # Vérifier qu'on est sur la branche main
    current_branch=$(git branch --show-current)
    if [ "$current_branch" != "main" ]; then
        log_error "Vous devez être sur la branche 'main' pour faire une release"
        exit 1
    fi
    
    # Vérifier qu'il n'y a pas de modifications non commitées
    if [ -n "$(git status --porcelain)" ]; then
        log_error "Il y a des modifications non commitées"
        git status
        exit 1
    fi
    
    log_info "Prérequis vérifiés"
}

# Menu interactif pour le type de version
select_version_type() {
    echo ""
    echo "🏷️  Sélectionnez le type de version:"
    echo "1) Patch (1.0.0 → 1.0.1) - Corrections de bugs"
    echo "2) Minor (1.0.0 → 1.1.0) - Nouvelles fonctionnalités"
    echo "3) Major (1.0.0 → 2.0.0) - Changements incompatibles"
    echo "4) Prerelease (1.0.0 → 1.0.1-alpha.1) - Version de test"
    echo ""
    
    while true; do
        read -p "Votre choix (1-4): " choice
        case $choice in
            1) VERSION_TYPE="patch"; break;;
            2) VERSION_TYPE="minor"; break;;
            3) VERSION_TYPE="major"; break;;
            4) VERSION_TYPE="prerelease"; break;;
            *) echo "Choix invalide";;
        esac
    done
    
    if [ "$VERSION_TYPE" = "prerelease" ]; then
        echo ""
        echo "Type de prerelease:"
        echo "1) alpha"
        echo "2) beta" 
        echo "3) rc (release candidate)"
        
        while true; do
            read -p "Votre choix (1-3): " pre_choice
            case $pre_choice in
                1) PRERELEASE_TYPE="alpha"; break;;
                2) PRERELEASE_TYPE="beta"; break;;
                3) PRERELEASE_TYPE="rc"; break;;
                *) echo "Choix invalide";;
            esac
        done
    fi
}

# Saisie des changements
input_changes() {
    echo ""
    echo "📝 Décrivez les changements de cette version:"
    echo "   (Une ligne par changement, ligne vide pour terminer)"
    echo ""
    
    CHANGES=()
    while true; do
        read -p "Changement: " change
        if [ -z "$change" ]; then
            break
        fi
        CHANGES+=("$change")
    done
    
    if [ ${#CHANGES[@]} -eq 0 ]; then
        read -p "Message de commit (optionnel): " COMMIT_MESSAGE
    fi
}

# Exécution des tests
run_tests() {
    log_step "Exécution des tests..."
    
    # Tests Python (si disponibles)
    if [ -f "test_local.py" ]; then
        if python3 test_local.py; then
            log_info "Tests Python réussis"
        else
            log_warn "Certains tests Python ont échoué"
            read -p "Continuer malgré les échecs de tests? (y/N): " continue_tests
            if [ "$continue_tests" != "y" ]; then
                exit 1
            fi
        fi
    fi
    
    # Tests Docker (si disponible)
    if command -v docker &> /dev/null && [ -f "docker-compose.yml" ]; then
        log_step "Validation de la configuration Docker..."
        if docker-compose config > /dev/null 2>&1; then
            log_info "Configuration Docker valide"
        else
            log_error "Configuration Docker invalide"
            exit 1
        fi
    fi
}

# Création de la release
create_release() {
    log_step "Création de la release..."
    
    # Construire les arguments pour le script Python
    PYTHON_ARGS="bump --type $VERSION_TYPE"
    
    if [ -n "$COMMIT_MESSAGE" ]; then
        PYTHON_ARGS="$PYTHON_ARGS --message \"$COMMIT_MESSAGE\""
    fi
    
    if [ ${#CHANGES[@]} -gt 0 ]; then
        PYTHON_ARGS="$PYTHON_ARGS --changes"
        for change in "${CHANGES[@]}"; do
            PYTHON_ARGS="$PYTHON_ARGS \"$change\""
        done
    fi
    
    if [ -n "$PRERELEASE_TYPE" ]; then
        PYTHON_ARGS="$PYTHON_ARGS --prerelease $PRERELEASE_TYPE"
    fi
    
    # Exécuter le script de version
    NEW_VERSION=$(python3 scripts/version.py $PYTHON_ARGS | grep "Version.*prête" | sed 's/.*Version \([^ ]*\) prête.*/\1/')
    
    if [ -z "$NEW_VERSION" ]; then
        log_error "Erreur lors de la création de la version"
        exit 1
    fi
    
    log_info "Version $NEW_VERSION créée"
}

# Commit et tag Git
git_operations() {
    log_step "Opérations Git..."
    
    # Ajouter tous les fichiers modifiés
    git add .
    
    # Commit
    COMMIT_MSG="v$NEW_VERSION"
    if [ -n "$COMMIT_MESSAGE" ]; then
        COMMIT_MSG="$COMMIT_MSG: $COMMIT_MESSAGE"
    else
        COMMIT_MSG="$COMMIT_MSG: Release version $NEW_VERSION"
    fi
    
    git commit -m "$COMMIT_MSG"
    log_info "Commit créé: $COMMIT_MSG"
    
    # Tag
    git tag "v$NEW_VERSION" -m "Release version $NEW_VERSION"
    log_info "Tag créé: v$NEW_VERSION"
}

# Push vers le dépôt distant
push_release() {
    echo ""
    read -p "Pousser vers le dépôt distant? (y/N): " push_confirm
    
    if [ "$push_confirm" = "y" ]; then
        log_step "Push vers le dépôt distant..."
        
        git push origin main
        git push origin "v$NEW_VERSION"
        
        log_info "Release poussée vers le dépôt distant"
        
        echo ""
        log_info "🎉 Release v$NEW_VERSION terminée avec succès!"
        log_info "📝 Notes de version: RELEASE_NOTES_v$NEW_VERSION.md"
        log_info "🔗 Tag Git: v$NEW_VERSION"
    else
        echo ""
        log_info "Release créée localement"
        log_warn "N'oubliez pas de pousser:"
        echo "   git push origin main"
        echo "   git push origin v$NEW_VERSION"
    fi
}

# Fonction principale
main() {
    echo "🚀 SaveOS Release Manager"
    echo "========================="
    
    check_requirements
    select_version_type
    input_changes
    run_tests
    create_release
    git_operations
    push_release
    
    echo ""
    log_info "✨ Release terminée!"
}

# Gestion des arguments en ligne de commande
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [--auto]"
    echo ""
    echo "Options:"
    echo "  --help, -h    Afficher cette aide"
    echo "  --auto        Mode automatique (patch version)"
    echo ""
    echo "Mode interactif par défaut."
    exit 0
fi

if [ "$1" = "--auto" ]; then
    # Mode automatique pour CI/CD
    VERSION_TYPE="patch"
    COMMIT_MESSAGE="Automatic patch release"
    CHANGES=()
    
    check_requirements
    run_tests
    create_release
    git_operations
    
    # En mode auto, on pousse automatiquement
    git push origin main
    git push origin "v$NEW_VERSION"
    
    echo "✅ Automatic release v$NEW_VERSION completed"
else
    # Mode interactif
    main
fi