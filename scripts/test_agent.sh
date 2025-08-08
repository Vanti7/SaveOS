#!/bin/bash
# Script de test de l'agent SaveOS

set -e

echo "🧪 Test de l'agent SaveOS"
echo "========================="

# Vérifier que Python est installé
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé."
    exit 1
fi

# Vérifier que l'API est accessible
echo "🔍 Vérification de l'API..."
if ! curl -k -f https://localhost:8000/health &> /dev/null; then
    echo "❌ API SaveOS non accessible. Assurez-vous que les services sont démarrés."
    echo "   Lancez: ./scripts/setup.sh"
    exit 1
fi

# Installer l'agent en mode développement
echo "📦 Installation de l'agent..."
pip install -e . &> /dev/null || {
    echo "❌ Erreur lors de l'installation de l'agent."
    echo "   Essayez: pip install -r requirements.txt"
    exit 1
}

# Créer un répertoire de test
TEST_DIR="/tmp/saveos_test_$(date +%s)"
mkdir -p "$TEST_DIR"
echo "Test file $(date)" > "$TEST_DIR/test_file.txt"

echo "📁 Répertoire de test créé: $TEST_DIR"

# Enregistrer l'agent
echo "📝 Enregistrement de l'agent..."
python -m agent.cli register --api-url https://localhost:8000

# Vérifier le statut
echo "📊 Vérification du statut..."
python -m agent.cli status

# Lancer une sauvegarde de test
echo "💾 Lancement d'une sauvegarde de test..."
python -m agent.cli backup --source-paths "$TEST_DIR" --wait

# Lister les snapshots
echo "📸 Liste des snapshots..."
python -m agent.cli snapshots

# Nettoyer le répertoire de test
rm -rf "$TEST_DIR"

echo ""
echo "✅ Test de l'agent terminé avec succès!"
echo "🎉 SaveOS est opérationnel!"
echo ""
echo "💡 Commandes utiles:"
echo "   • Voir la config: python -m agent.cli config-show"
echo "   • Mode daemon: python -m agent.cli daemon"
echo "   • Aide: python -m agent.cli --help"