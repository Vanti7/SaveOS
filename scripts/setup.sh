#!/bin/bash
# Script de configuration et démarrage de SaveOS

set -e

echo "🚀 Configuration de SaveOS - Système de sauvegarde centralisé"
echo "============================================================="

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose n'est pas disponible. Veuillez installer Docker avec Compose plugin."
    exit 1
fi

# Générer les certificats TLS
echo "🔐 Génération des certificats TLS..."
chmod +x scripts/generate_certs.sh
./scripts/generate_certs.sh

# Arrêter les conteneurs existants s'ils existent
echo "🛑 Arrêt des conteneurs existants..."
docker compose down -v 2>/dev/null || true

# Construire les images
echo "🔨 Construction des images Docker..."
docker compose build

# Démarrer les services
echo "🚀 Démarrage des services..."
docker compose up -d

# Attendre que les services soient prêts
echo "⏳ Attente du démarrage des services..."
sleep 10

# Vérifier le statut des services
echo "🔍 Vérification du statut des services..."
docker compose ps

# Vérifier la santé de l'API
echo "🩺 Test de santé de l'API..."
for i in {1..10}; do
    if curl -k -f https://localhost:8000/health &> /dev/null; then
        echo "✅ API SaveOS accessible sur https://localhost:8000"
        break
    else
        echo "⏳ Tentative $i/10 - API pas encore prête..."
        sleep 5
    fi
done

# Afficher les informations de connexion
echo ""
echo "🎉 SaveOS démarré avec succès!"
echo "================================"
echo "📊 Services disponibles:"
echo "   • Interface Web:  http://localhost:3000"
echo "   • API SaveOS:     https://localhost:8000"
echo "   • PostgreSQL:     localhost:5432 (saveos/saveos123)"
echo "   • Redis:          localhost:6379"
echo "   • MinIO:          http://localhost:9001 (saveos/saveos123456)"
echo ""
echo "🔧 Étapes suivantes:"
echo "   1. Ouvrir l'interface web: http://localhost:3000"
echo "   2. Aller dans 'Téléchargements' pour installer des agents"
echo "   3. Télécharger et installer un agent sur vos machines"
echo "   4. Surveiller les sauvegardes depuis l'interface"
echo ""
echo "📝 Logs des services:"
echo "   docker compose logs -f"
echo ""
echo "🛑 Pour arrêter SaveOS:"
echo "   docker compose down"