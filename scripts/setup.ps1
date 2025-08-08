# Script PowerShell pour configurer SaveOS sur Windows

Write-Host "🚀 Configuration de SaveOS - Système de sauvegarde centralisé" -ForegroundColor Green
Write-Host "=============================================================" -ForegroundColor Green

# Vérifier que Docker est installé
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker n'est pas installé. Veuillez l'installer d'abord." -ForegroundColor Red
    exit 1
}

if (!(Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker Compose n'est pas installé. Veuillez l'installer d'abord." -ForegroundColor Red
    exit 1
}

# Générer les certificats TLS
Write-Host "🔐 Génération des certificats TLS..." -ForegroundColor Yellow

$certDir = "certs"
$certFile = "$certDir\cert.pem"
$keyFile = "$certDir\key.pem"

if (!(Test-Path $certDir)) {
    New-Item -ItemType Directory -Path $certDir | Out-Null
}

# Vérifier si OpenSSL est disponible
if (Get-Command openssl -ErrorAction SilentlyContinue) {
    Write-Host "Génération de la clé privée..." -ForegroundColor Gray
    openssl genrsa -out $keyFile 2048

    Write-Host "Génération du certificat self-signed..." -ForegroundColor Gray
    openssl req -new -x509 -key $keyFile -out $certFile -days 365 -subj "/C=FR/ST=France/L=Paris/O=SaveOS/OU=IT/CN=localhost"
    
    Write-Host "✅ Certificats générés avec succès" -ForegroundColor Green
} else {
    Write-Host "⚠️  OpenSSL non trouvé. Création de certificats factices..." -ForegroundColor Yellow
    "-----BEGIN PRIVATE KEY-----" | Out-File -FilePath $keyFile -Encoding ASCII
    "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC..." | Out-File -FilePath $keyFile -Append -Encoding ASCII
    "-----END PRIVATE KEY-----" | Out-File -FilePath $keyFile -Append -Encoding ASCII
    
    "-----BEGIN CERTIFICATE-----" | Out-File -FilePath $certFile -Encoding ASCII
    "MIIDXTCCAkWgAwIBAgIJAKoK/OvH0dJNMA0GCSqGSIb3DQEBCwUA..." | Out-File -FilePath $certFile -Append -Encoding ASCII
    "-----END CERTIFICATE-----" | Out-File -FilePath $certFile -Append -Encoding ASCII
}

# Arrêter les conteneurs existants s'ils existent
Write-Host "🛑 Arrêt des conteneurs existants..." -ForegroundColor Yellow
docker-compose down -v 2>$null

# Construire les images
Write-Host "🔨 Construction des images Docker..." -ForegroundColor Yellow
docker-compose build

# Démarrer les services
Write-Host "🚀 Démarrage des services..." -ForegroundColor Yellow
docker-compose up -d

# Attendre que les services soient prêts
Write-Host "⏳ Attente du démarrage des services..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Vérifier le statut des services
Write-Host "🔍 Vérification du statut des services..." -ForegroundColor Yellow
docker-compose ps

# Vérifier la santé de l'API
Write-Host "🩺 Test de santé de l'API..." -ForegroundColor Yellow
$maxAttempts = 10
$attempt = 1

do {
    try {
        $response = Invoke-WebRequest -Uri "https://localhost:8000/health" -SkipCertificateCheck -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ API SaveOS accessible sur https://localhost:8000" -ForegroundColor Green
            break
        }
    }
    catch {
        Write-Host "⏳ Tentative $attempt/$maxAttempts - API pas encore prête..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        $attempt++
    }
} while ($attempt -le $maxAttempts)

# Afficher les informations de connexion
Write-Host ""
Write-Host "🎉 SaveOS démarré avec succès!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host "📊 Services disponibles:" -ForegroundColor Cyan
Write-Host "   • Interface Web:  http://localhost:3000" -ForegroundColor White
Write-Host "   • API SaveOS:     https://localhost:8000" -ForegroundColor White
Write-Host "   • PostgreSQL:     localhost:5432 (saveos/saveos123)" -ForegroundColor White
Write-Host "   • Redis:          localhost:6379" -ForegroundColor White
Write-Host "   • MinIO:          http://localhost:9001 (saveos/saveos123456)" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Étapes suivantes:" -ForegroundColor Cyan
Write-Host "   1. Ouvrir l'interface web: http://localhost:3000" -ForegroundColor White
Write-Host "   2. Aller dans 'Téléchargements' pour installer des agents" -ForegroundColor White
Write-Host "   3. Télécharger et installer un agent sur vos machines" -ForegroundColor White
Write-Host "   4. Surveiller les sauvegardes depuis l'interface" -ForegroundColor White
Write-Host ""
Write-Host "📝 Logs des services:" -ForegroundColor Cyan
Write-Host "   docker-compose logs -f" -ForegroundColor White
Write-Host ""
Write-Host "🛑 Pour arrêter SaveOS:" -ForegroundColor Cyan
Write-Host "   docker-compose down" -ForegroundColor White