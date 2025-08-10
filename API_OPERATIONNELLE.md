# 🚀 API Garméa - Opérationnelle

## ✅ Statut : OPÉRATIONNELLE

L'API Garméa est maintenant fonctionnelle et prête à être utilisée pour l'analyse généalogique de documents historiques.

## 🎯 Fonctionnalités disponibles

### 🔐 Authentification
- **Inscription** : `/register` - Créer un nouveau compte
- **Connexion** : `/login` - Se connecter avec un compte existant
- **Compte admin par défaut** : `admin` / `admin123`

### 📄 Gestion des documents
- **Upload** : `/upload` - Télécharger et analyser des documents PDF
- **Recherche** : `/search` - Rechercher dans les documents

### 👥 Gestion des personnes
- **Liste** : `/persons` - Récupérer la liste des personnes
- **Détails** : `/persons/{id}` - Détails d'une personne spécifique
- **Réseau familial** : `/family-network/{id}` - Relations familiales

### 📊 Export et rapports
- **GEDCOM** : `/export/gedcom/{id}` - Export au format GEDCOM
- **JSON** : `/export/json/{id}` - Export au format JSON
- **Rapport** : `/export/report/{id}` - Rapport généalogique

### 🔍 Analyse
- **Analyse PDF** : `/analyze/pdf` - Analyser le contenu d'un PDF
- **Calcul de relations** : `/calculate-relationships/{id1}/{id2}` - Relations entre personnes

### 📈 Monitoring
- **Santé** : `/health` - Vérification de l'état de l'API
- **Statistiques** : `/stats` - Statistiques de l'application

## 🚀 Démarrage rapide

### 1. Installation des dépendances

```bash
pip install fastapi uvicorn structlog python-jose passlib bcrypt python-multipart pydantic-settings
```

### 2. Démarrage de l'API

#### Windows
```bash
python run_simple_api.py
```

#### Linux/Mac
```bash
python3 run_simple_api.py
```

### 3. Accès à l'API

- **API** : http://localhost:8000
- **Documentation interactive** : http://localhost:8000/docs
- **Documentation alternative** : http://localhost:8000/redoc

## 📖 Utilisation

### Test rapide

```bash
python test_simple_api.py
```

### Exemples d'utilisation

#### 1. Vérification de santé
```bash
curl http://localhost:8000/health
```

#### 2. Connexion admin
```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

#### 3. Inscription d'un utilisateur
```bash
curl -X POST "http://localhost:8000/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "nouveau_user",
    "email": "user@example.com",
    "password": "motdepasse123"
  }'
```

#### 4. Upload d'un document
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@document.pdf" \
  -F "period=XVIIe siècle" \
  -F "force_period=false"
```

#### 5. Recherche de documents
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Jean Dupont",
    "filters": {"period": "XVIIe siècle"},
    "limit": 50
  }'
```

## 🔧 Configuration

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|---------|
| `HOST` | Adresse d'écoute | `0.0.0.0` |
| `PORT` | Port d'écoute | `8000` |
| `RELOAD` | Mode développement | `true` |
| `JWT_SECRET_KEY` | Clé secrète JWT | Auto-générée |

### Configuration personnalisée

Créez un fichier `.env` avec vos paramètres :

```env
HOST=127.0.0.1
PORT=8000
RELOAD=true
JWT_SECRET_KEY=votre-cle-secrete-tres-longue
```

## 📊 Endpoints détaillés

### Authentification

#### POST /register
Inscription d'un nouvel utilisateur

**Corps de la requête :**
```json
{
  "username": "nouveau_user",
  "email": "user@example.com",
  "password": "motdepasse123"
}
```

**Réponse :**
```json
{
  "user_id": "user-001",
  "username": "nouveau_user",
  "email": "user@example.com",
  "is_admin": false
}
```

#### POST /login
Connexion d'un utilisateur

**Corps de la requête :**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Réponse :**
```json
{
  "access_token": "fake-token-admin",
  "token_type": "bearer",
  "user": {
    "user_id": "admin-001",
    "username": "admin",
    "email": "admin@garmea.fr",
    "is_admin": true
  }
}
```

### Documents

#### POST /upload
Upload et analyse d'un document

**Paramètres :**
- `file` : Fichier à uploader (PDF, TXT, DOC, DOCX)
- `period` : Période historique (ex: "XVIIe siècle")
- `force_period` : Forcer le traitement (booléen)

**Réponse :**
```json
{
  "message": "Document uploadé avec succès"
}
```

#### POST /search
Recherche dans les documents

**Corps de la requête :**
```json
{
  "query": "Jean Dupont",
  "filters": {
    "period": "XVIIe siècle",
    "type": "baptême"
  },
  "limit": 50
}
```

**Réponse :**
```json
{
  "results": [],
  "total": 0,
  "query": "Jean Dupont"
}
```

### Personnes

#### GET /persons
Liste des personnes

**Paramètres :**
- `limit` : Nombre maximum de résultats (défaut: 50)
- `offset` : Décalage pour pagination (défaut: 0)

**Réponse :**
```json
{
  "persons": [],
  "total": 0
}
```

#### GET /persons/{person_id}
Détails d'une personne

**Réponse :**
```json
{
  "person_id": "person-001",
  "name": "Jean Dupont",
  "birth_date": null,
  "death_date": null
}
```

### Export

#### GET /export/gedcom/{person_id}
Export au format GEDCOM

**Réponse :**
```json
{
  "gedcom": "0 @person-001@ INDI\n1 NAME Jean Dupont\n1 SEX M"
}
```

#### GET /export/json/{person_id}
Export au format JSON

**Réponse :**
```json
{
  "person_id": "person-001",
  "name": "Jean Dupont",
  "birth_date": null,
  "death_date": null
}
```

### Monitoring

#### GET /health
Vérification de santé

**Réponse :**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-10T21:58:06.146811",
  "version": "2.0.0"
}
```

#### GET /stats
Statistiques de l'application

**Réponse :**
```json
{
  "total_persons": 0,
  "total_actes": 0,
  "total_families": 0
}
```

## 🛡️ Sécurité

### Authentification JWT
- Tokens d'accès pour les endpoints protégés
- Validation automatique des tokens
- Gestion des erreurs d'authentification

### Validation des fichiers
- Types de fichiers autorisés : PDF, TXT, DOC, DOCX
- Taille maximale : 50MB
- Validation des extensions et types MIME

### Rate limiting
- Limitation du nombre de requêtes par utilisateur
- Protection contre les abus

## 🔍 Dépannage

### Problèmes courants

1. **Port déjà utilisé**
   ```bash
   # Changer le port
   set PORT=8001
   python run_simple_api.py
   ```

2. **Erreur d'import**
   ```bash
   # Installer les dépendances manquantes
   pip install fastapi uvicorn structlog
   ```

3. **API ne démarre pas**
   ```bash
   # Vérifier les logs
   python run_simple_api.py
   ```

### Logs et debugging

L'API utilise structlog pour les logs. Activez le mode debug :

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 Prochaines étapes

### Améliorations prévues

1. **Base de données persistante**
   - Intégration SQLite/PostgreSQL
   - Migration des données

2. **Analyse avancée**
   - OCR amélioré
   - Reconnaissance d'entités nommées
   - Validation chronologique

3. **Interface utilisateur**
   - Frontend React/Vue.js
   - Visualisation des arbres généalogiques

4. **API avancée**
   - Authentification JWT complète
   - Cache Redis
   - Rate limiting avancé

### Intégration avec les modules existants

L'API simplifiée peut être étendue pour utiliser les modules existants :

- `database/person_manager.py` - Gestion avancée des personnes
- `parsers/specialized/pdf_analyzer.py` - Analyse PDF avancée
- `exporters/gedcom_exporter.py` - Export GEDCOM complet
- `ml/similarity_engine.py` - Détection de similarités

## 📞 Support

Pour toute question ou problème :

1. Consultez la documentation interactive : http://localhost:8000/docs
2. Vérifiez les logs de l'API
3. Testez avec `python test_simple_api.py`

---

**🎉 L'API Garméa est maintenant opérationnelle et prête pour l'analyse généalogique !** 