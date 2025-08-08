#!/bin/bash
# Script pour générer les certificats TLS self-signed pour SaveOS

set -e

CERT_DIR="certs"
CERT_FILE="$CERT_DIR/cert.pem"
KEY_FILE="$CERT_DIR/key.pem"

echo "🔐 Génération des certificats TLS self-signed pour SaveOS..."

# Créer le répertoire des certificats
mkdir -p "$CERT_DIR"

# Générer la clé privée
echo "Génération de la clé privée..."
openssl genrsa -out "$KEY_FILE" 2048

# Générer le certificat self-signed
echo "Génération du certificat self-signed..."
openssl req -new -x509 -key "$KEY_FILE" -out "$CERT_FILE" -days 365 -subj "/C=FR/ST=France/L=Paris/O=SaveOS/OU=IT/CN=localhost"

# Permissions restrictives
chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

echo "✅ Certificats générés avec succès:"
echo "   Certificat: $CERT_FILE"
echo "   Clé privée: $KEY_FILE"
echo "   Validité: 365 jours"
echo ""
echo "⚠️  ATTENTION: Ces certificats sont self-signed et ne doivent être utilisés qu'en développement!"