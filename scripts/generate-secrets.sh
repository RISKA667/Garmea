#!/bin/bash

# Générateur de secrets sécurisés pour Garméa
set -euo pipefail

# Génération de clés sécurisées
generate_jwt_secret() {
    openssl rand -hex 32
}

generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

generate_encryption_key() {
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
}

# Créer le fichier .env
create_env_file() {
    local env_file=".env"
    
    if [[ -f "$env_file" ]]; then
        echo "Le fichier .env existe déjà. Sauvegarde en .env.backup"
        cp "$env_file" "$env_file.backup"
    fi
    
    cat > "$env_file" << EOF
# Configuration Garméa - Générée automatiquement le $(date)

# Application
DEBUG=false
APP_NAME=Garméa
VERSION=2.0.0

# Sécurité
JWT_SECRET_KEY=$(generate_jwt_secret)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Base de données
DATABASE_URL=postgresql://garmea_user:$(generate_password)@postgres:5432/garmea_db
DB_PASSWORD=$(generate_password)
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# Cache Redis
REDIS_URL=redis://:$(generate_password)@redis:6379/0
REDIS_PASSWORD=$(generate_password)
CACHE_TTL_HOURS=24
CACHE_ENCRYPTION_KEY=$(generate_encryption_key)

# Réseau et sécurité
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,localhost
CORS_ORIGINS=https://yourdomain.com,http://localhost:3000

# Fichiers
MAX_FILE_SIZE=52428800
UPLOAD_DIR=/app/uploads

# Rate limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_MINUTES=60

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/logs/garmea.log

# Monitoring
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=30
EOF

    # Sécuriser le fichier
    chmod 600 "$env_file"
    
    echo "Fichier .env créé avec succès"
    echo "IMPORTANT: Sauvegardez ces secrets en lieu sûr !"
}

main() {
    echo "Génération des secrets pour Garméa..."
    create_env_file
    echo "Terminé !"
}

main "$@"