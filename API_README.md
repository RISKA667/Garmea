# API Garméa - Guide d'utilisation

## 🚀 Démarrage rapide

### 1. Installation des dépendances

```bash
pip install -r requirements.txt
```

### 2. Configuration

Copiez le fichier de configuration :
```bash
cp env.example .env
```

Modifiez le fichier `.env` selon votre environnement :
- `JWT_SECRET_KEY` : Clé secrète pour les tokens JWT
- `DATABASE_URL` : URL de votre base de données
- `REDIS_URL` : URL de Redis (optionnel)

### 3. Démarrage de l'API

```bash
python run_api.py
```

L'API sera accessible sur `http://localhost:8000`

## 📚 Documentation interactive

- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

## 🔐 Authentification

### Inscription d'un utilisateur

```bash
curl -X POST "http://localhost:8000/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "utilisateur",
    "email": "user@example.com",
    "password": "motdepasse123"
  }'
```

### Connexion

```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "utilisateur",
    "password": "motdepasse123"
  }'
```

### Utilisation du token

```bash
curl -X GET "http://localhost:8000/persons" \
  -H "Authorization: Bearer VOTRE_TOKEN_JWT"
```

## 📄 Endpoints principaux

### Documents

#### Upload de document
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Authorization: Bearer VOTRE_TOKEN" \
  -F "file=@document.pdf" \
  -F "period=XVIIe siècle" \
  -F "force_period=false"
```

#### Recherche de documents
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Authorization: Bearer VOTRE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Jean Dupont",
    "filters": {"period": "XVIIe siècle"},
    "limit": 50
  }'
```

### Personnes

#### Liste des personnes
```bash
curl -X GET "http://localhost:8000/persons?limit=50&offset=0" \
  -H "Authorization: Bearer VOTRE_TOKEN"
```

#### Détails d'une personne
```bash
curl -X GET "http://localhost:8000/persons/PERSON_ID" \
  -H "Authorization: Bearer VOTRE_TOKEN"
```

#### Réseau familial
```bash
curl -X GET "http://localhost:8000/family-network/PERSON_ID?depth=3" \
  -H "Authorization: Bearer VOTRE_TOKEN"
```

### Export

#### Export GEDCOM
```bash
curl -X GET "http://localhost:8000/export/gedcom/PERSON_ID" \
  -H "Authorization: Bearer VOTRE_TOKEN"
```

#### Export JSON
```bash
curl -X GET "http://localhost:8000/export/json/PERSON_ID" \
  -H "Authorization: Bearer VOTRE_TOKEN"
```

#### Rapport généalogique
```bash
curl -X GET "http://localhost:8000/export/report/PERSON_ID" \
  -H "Authorization: Bearer VOTRE_TOKEN"
```

### Analyse

#### Analyse de PDF
```bash
curl -X POST "http://localhost:8000/analyze/pdf" \
  -H "Authorization: Bearer VOTRE_TOKEN" \
  -F "file=@document.pdf"
```

#### Calcul de relations
```bash
curl -X GET "http://localhost:8000/calculate-relationships/PERSON1_ID/PERSON2_ID" \
  -H "Authorization: Bearer VOTRE_TOKEN"
```

### Monitoring

#### Vérification de santé
```bash
curl -X GET "http://localhost:8000/health"
```

#### Statistiques
```bash
curl -X GET "http://localhost:8000/stats" \
  -H "Authorization: Bearer VOTRE_TOKEN"
```

## 🔧 Configuration avancée

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|---------|
| `HOST` | Adresse d'écoute | `0.0.0.0` |
| `PORT` | Port d'écoute | `8000` |
| `RELOAD` | Mode développement | `true` |
| `JWT_SECRET_KEY` | Clé secrète JWT | Requis |
| `DATABASE_URL` | URL de la base de données | Requis |
| `REDIS_URL` | URL de Redis | `redis://localhost:6379/0` |
| `MAX_FILE_SIZE` | Taille max des fichiers | `52428800` (50MB) |

### Base de données

L'API supporte plusieurs types de bases de données :

- **SQLite** (développement) : `sqlite:///./garmea.db`
- **PostgreSQL** (production) : `postgresql://user:pass@localhost/garmea`
- **MySQL** : `mysql://user:pass@localhost/garmea`

### Cache Redis

Redis est optionnel mais recommandé pour les performances :

```bash
# Installation Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Démarrage
sudo systemctl start redis-server
```

## 🛡️ Sécurité

### Authentification JWT

- Tokens d'accès valides 30 minutes par défaut
- Tokens de rafraîchissement valides 7 jours
- Validation automatique des tokens sur les endpoints protégés

### Validation des fichiers

- Types autorisés : PDF, TXT, DOC, DOCX
- Taille maximale : 50MB par défaut
- Validation MIME et signature de fichiers
- Scan antivirus simulé

### Rate limiting

- 100 requêtes par heure par utilisateur par défaut
- Configuration via variables d'environnement

## 🐳 Docker

### Démarrage avec Docker Compose

```bash
docker-compose up -d
```

### Image Docker personnalisée

```bash
docker build -t garmea-api .
docker run -p 8000:8000 garmea-api
```

## 📊 Monitoring et logs

### Logs

Les logs sont écrits dans `logs/garmea.log` par défaut.

### Métriques

Métriques Prometheus disponibles sur `/metrics` (si activées).

### Health check

Endpoint `/health` pour vérifier l'état de l'API.

## 🧪 Tests

### Tests unitaires

```bash
pytest tests/
```

### Tests d'intégration

```bash
pytest tests/ -m integration
```

## 🚨 Dépannage

### Erreurs courantes

1. **ImportError** : Vérifiez que toutes les dépendances sont installées
2. **JWT_SECRET_KEY manquante** : Définissez cette variable dans `.env`
3. **Base de données inaccessible** : Vérifiez l'URL de la base de données
4. **Port déjà utilisé** : Changez le port dans `.env`

### Logs de débogage

Activez le mode debug dans `.env` :
```
DEBUG=true
LOG_LEVEL=DEBUG
```

## 📞 Support

Pour toute question ou problème :
- Consultez la documentation interactive : http://localhost:8000/docs
- Vérifiez les logs dans `logs/garmea.log`
- Consultez le README principal du projet 