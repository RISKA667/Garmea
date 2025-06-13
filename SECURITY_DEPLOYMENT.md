# 🔒 Guide de Déploiement Sécurisé - Garméa

## Étapes de Sécurisation Immédiate

### 1. Génération des Secrets
```bash
# Générer les clés et mots de passe sécurisés
chmod +x scripts/generate-secrets.sh
./scripts/generate-secrets.sh

# Créer un utilisateur PostgreSQL dédié
sudo -u postgres createuser --createdb --no-superuser --no-createrole garmea_user
sudo -u postgres psql -c "ALTER USER garmea_user PASSWORD 'VOTRE_MOT_DE_PASSE_FORT';"
sudo -u postgres createdb -O garmea_user garmea_db

# Permissions strictes pour les fichiers sensibles
chmod 600 .env
chmod 600 nginx/ssl/*
chmod +x scripts/*.sh

# Ownership correct
sudo chown -R root:docker docker-compose.yml
sudo chown -R nginx:nginx nginx/

# Générer les certificats SSL (Let's Encrypt recommandé)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Ou certificats auto-signés pour test
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem \
  -out nginx/ssl/fullchain.pem

  # Lancer le déploiement avec validation
chmod +x scripts/deploy.sh
sudo ./scripts/deploy.sh

# Tests automatisés
python -m pytest tests/test_security.py -v

# Scan de vulnérabilités (optionnel)
docker run --rm -v $(pwd):/app bandit -r /app -f json

