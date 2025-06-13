#!/bin/bash

# Script de déploiement sécurisé pour Garméa
set -euo pipefail

# Configuration
PROJECT_NAME="garmea"
BACKUP_DIR="/backup"
LOG_FILE="/var/log/garmea-deploy.log"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction de logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

# Vérifications préalables
check_requirements() {
    log "Vérification des prérequis..."
    
    # Docker
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
    fi
    
    # Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose n'est pas installé"
    fi
    
    # Variables d'environnement critiques
    if [[ -z "${JWT_SECRET_KEY:-}" ]]; then
        error "JWT_SECRET_KEY n'est pas définie"
    fi
    
    if [[ -z "${DB_PASSWORD:-}" ]]; then
        error "DB_PASSWORD n'est pas définie"
    fi
    
    log "Prérequis validés ✓"
}

# Sauvegarde de la base de données
backup_database() {
    log "Sauvegarde de la base de données..."
    
    mkdir -p "$BACKUP_DIR"
    
    BACKUP_FILE="$BACKUP_DIR/garmea_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    docker-compose exec -T postgres pg_dump -U garmea_user garmea_db > "$BACKUP_FILE" || {
        warn "Impossible de créer la sauvegarde (première installation ?)"
    }
    
    # Garder seulement les 7 dernières sauvegardes
    find "$BACKUP_DIR" -name "garmea_backup_*.sql" -mtime +7 -delete
    
    log "Sauvegarde terminée: $BACKUP_FILE"
}

# Construction des images
build_images() {
    log "Construction des images Docker..."
    
    # Backend
    docker-compose build --no-cache garmea-api || error "Échec de la construction de l'API"
    
    # Frontend (si présent)
    if [[ -d "garmea-frontend" ]]; then
        docker-compose build --no-cache garmea-frontend || error "Échec de la construction du frontend"
    fi
    
    log "Images construites ✓"
}

# Test de sécurité
security_check() {
    log "Vérification de sécurité..."
    
    # Vérifier les ports exposés
    if netstat -tuln | grep -q ":5432.*0.0.0.0"; then
        warn "PostgreSQL exposé publiquement"
    fi
    
    if netstat -tuln | grep -q ":6379.*0.0.0.0"; then
        warn "Redis exposé publiquement"
    fi
    
    # Vérifier les permissions des fichiers sensibles
    if [[ -f ".env" ]]; then
        PERMS=$(stat -c "%a" .env)
        if [[ "$PERMS" != "600" ]]; then
            warn "Permissions du fichier .env non sécurisées (actuellement: $PERMS)"
            chmod 600 .env
        fi
    fi
    
    log "Vérification de sécurité terminée ✓"
}

# Déploiement
deploy() {
    log "Début du déploiement..."
    
    # Arrêter les services existants
    docker-compose down --remove-orphans
    
    # Démarrer les services de base d'abord
    docker-compose up -d postgres redis
    
    # Attendre que les services soient prêts
    log "Attente de la disponibilité des services..."
    sleep 10
    
    # Démarrer l'API
    docker-compose up -d garmea-api
    
    # Attendre que l'API soit prête
    log "Vérification de l'API..."
    for i in {1..30}; do
        if curl -f http://localhost:8000/health &>/dev/null; then
            log "API disponible ✓"
            break
        fi
        sleep 2
        if [[ $i -eq 30 ]]; then
            error "L'API ne répond pas après 60 secondes"
        fi
    done
    
    # Démarrer le frontend et nginx
    docker-compose up -d garmea-frontend nginx
    
    log "Déploiement terminé ✓"
}

# Test post-déploiement
post_deploy_tests() {
    log "Tests post-déploiement..."
    
    # Test de l'API
    if ! curl -f http://localhost:8000/health &>/dev/null; then
        error "L'API ne répond pas"
    fi
    
    # Test du frontend (si déployé)
    if docker-compose ps | grep -q garmea-frontend; then
        if ! curl -f http://localhost:3000 &>/dev/null; then
            warn "Le frontend ne répond pas"
        fi
    fi
    
    # Test de l'authentification
    AUTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST http://localhost:8000/auth/login \
        -H "Content-Type: application/json" \
        -d '{"email":"test","password":"test"}')
    
    if [[ "$AUTH_RESPONSE" == "401" ]]; then
        log "Authentification fonctionne ✓"
    else
        warn "Problème avec l'authentification (code: $AUTH_RESPONSE)"
    fi
    
    log "Tests terminés ✓"
}

# Affichage de l'état final
show_status() {
    log "État des services:"
    docker-compose ps
    
    log "URLs disponibles:"
    echo "  - API: http://localhost:8000"
    echo "  - Documentation: http://localhost:8000/docs"
    echo "  - Frontend: http://localhost:3000"
    echo "  - Santé API: http://localhost:8000/health"
}

# Fonction principale
main() {
    log "Déploiement de Garméa v2.0.0"
    
    check_requirements
    backup_database
    build_images
    security_check
    deploy
    post_deploy_tests
    show_status
    
    log "Déploiement réussi ! 🎉"
}

# Gestion des erreurs
trap 'error "Déploiement interrompu"' ERR

# Exécution
main "$@"