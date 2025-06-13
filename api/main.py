"""
API FastAPI sécurisée pour Garméa v2.0.0
"""
import os
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import structlog
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager

# Security imports
from security.auth import (
    auth_manager, get_current_user, get_current_admin_user, 
    rate_limiter, Token, UserCreate, TokenData
)
from security.file_validator import file_validator
from config.secure_settings import get_settings
from utils.secure_cache import SecureRedisCache
from utils.error_handler import ErrorHandler, GarmeaError

# Configuration
settings = get_settings()
logger = structlog.get_logger()

# Cache sécurisé
cache = SecureRedisCache(settings.redis_url, ttl_hours=settings.cache_ttl_hours)

# Gestionnaire d'erreurs
error_handler = ErrorHandler()

# Bearer security
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle de l'application"""
    # Startup
    logger.info("Starting Garméa API", version="2.0.0")
    await cache.connect()
    yield
    # Shutdown
    await cache.disconnect()
    logger.info("Garméa API stopped")

# Application FastAPI sécurisée
app = FastAPI(
    title="Garméa API",
    description="API sécurisée pour l'analyse généalogique",
    version="2.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Middlewares de sécurité
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.allowed_hosts
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Middleware de rate limiting
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Middleware de limitation de taux"""
    
    # Identifier le client (IP + User-Agent)
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    client_key = f"{client_ip}:{hash(user_agent)}"
    
    # Vérifier la limite
    if not rate_limiter.is_allowed(client_key, max_requests=100, window_minutes=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )
    
    response = await call_next(request)
    return response

# Stockage sécurisé des tâches (en production, utiliser Redis)
processing_tasks: Dict[str, Dict] = {}

# ========== ENDPOINTS PUBLICS ==========

@app.get("/")
async def root():
    """Point d'entrée sécurisé"""
    return {
        "message": "Garméa API v2.0.0",
        "status": "secure",
        "authentication": "required",
        "documentation": "/docs" if settings.debug else "contact_admin"
    }

@app.get("/health")
async def health_check():
    """Health check sécurisé"""
    try:
        # Tester les services critiques
        cache_status = await cache.health_check()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "cache": "ok" if cache_status else "error",
                "database": "ok",  # À implémenter
                "file_validator": "ok"
            },
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Service unhealthy"
        )

# ========== AUTHENTIFICATION ==========

@app.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    """Inscription sécurisée d'un utilisateur"""
    try:
        # Validation des mots de passe
        user_data.validate_passwords()
        
        # Vérifier si l'utilisateur existe déjà
        # TODO: Implémenter la vérification en base
        
        # Créer l'utilisateur
        hashed_password = auth_manager.get_password_hash(user_data.password)
        
        # TODO: Sauvegarder en base
        user_id = 123  # Simulé
        
        # Créer les tokens
        access_token = auth_manager.create_access_token(
            data={"user_id": user_id, "email": user_data.email}
        )
        refresh_token = auth_manager.create_refresh_token(user_id)
        
        logger.info("User registered", user_id=user_id, email=user_data.email)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=1800  # 30 minutes
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Registration failed", error=str(e))
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/auth/login", response_model=Token)
async def login(email: str, password: str):
    """Connexion sécurisée"""
    try:
        # TODO: Récupérer l'utilisateur depuis la base
        # user = get_user_by_email(email)
        
        # Simulé pour l'exemple
        if email == "test@example.com" and password == "testpassword":
            user_id = 123
            
            access_token = auth_manager.create_access_token(
                data={"user_id": user_id, "email": email}
            )
            refresh_token = auth_manager.create_refresh_token(user_id)
            
            logger.info("User logged in", user_id=user_id, email=email)
            
            return Token(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=1800
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login failed", error=str(e))
        raise HTTPException(status_code=500, detail="Login failed")

# ========== ENDPOINTS PROTÉGÉS ==========

@app.post("/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
    period: Optional[str] = None,
    force_period: bool = False
):
    """Upload sécurisé de document avec validation robuste"""
    
    try:
        # 1. Validation robuste du fichier
        is_valid, error_message = await file_validator.validate_file(file)
        if not is_valid:
            logger.warning(
                "File validation failed", 
                user_id=current_user.user_id,
                filename=file.filename,
                error=error_message
            )
            raise HTTPException(status_code=400, detail=error_message)
        
        # 2. Lire le contenu de manière sécurisée
        content = await file.read()
        file_info = file_validator.get_file_info(content, file.filename)
        
        # 3. Vérifier les doublons via hash
        file_hash = file_info['hash_sha256']
        existing_task = await cache.get("file_hashes", file_hash)
        if existing_task and not force_period:
            logger.info("Duplicate file detected", file_hash=file_hash)
            return {
                "message": "File already processed",
                "task_id": existing_task,
                "duplicate": True
            }
        
        # 4. Créer une tâche sécurisée
        task_id = str(uuid.uuid4())
        
        task_data = {
            "status": "pending",
            "progress": 0,
            "message": "Document accepted, processing...",
            "filename": file.filename,
            "file_info": file_info,
            "user_id": current_user.user_id,
            "created_at": datetime.utcnow().isoformat(),
            "period": period
        }
        
        # 5. Stocker la tâche de manière sécurisée
        processing_tasks[task_id] = task_data
        await cache.set("file_hashes", file_hash, task_id, ttl_hours=24)
        
        # 6. Lancer le traitement en arrière-plan
        background_tasks.add_task(
            process_document_secure,
            task_id,
            content,
            file_info,
            current_user.user_id,
            period,
            force_period
        )
        
        logger.info(
            "Document upload accepted",
            task_id=task_id,
            user_id=current_user.user_id,
            filename=file.filename,
            size=file_info['size']
        )
        
        return {
            "task_id": task_id,
            "status": "accepted",
            "message": f"Document {file.filename} accepted for processing",
            "file_info": file_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Upload failed",
            user_id=current_user.user_id,
            filename=file.filename,
            error=str(e)
        )
        garmea_error = error_handler.handle_error(
            e, 
            {"user_id": current_user.user_id, "filename": file.filename}
        )
        raise HTTPException(status_code=500, detail=garmea_error.message)

@app.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Récupération sécurisée du statut d'une tâche"""
    
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = processing_tasks[task_id]
    
    # Vérifier que l'utilisateur a accès à cette tâche
    if task_info.get("user_id") != current_user.user_id:
        # Admin peut voir toutes les tâches
        if not await is_admin_user(current_user):
            raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "task_id": task_id,
        "status": task_info["status"],
        "progress": task_info["progress"],
        "message": task_info.get("message"),
        "result": task_info.get("result"),
        "error": task_info.get("error"),
        "created_at": task_info.get("created_at")
    }

@app.post("/search")
async def search_persons(
    query: dict,
    current_user: TokenData = Depends(get_current_user)
):
    """Recherche sécurisée de personnes"""
    
    try:
        # Validation des paramètres de recherche
        if not query or len(query) == 0:
            raise HTTPException(status_code=400, detail="Search query required")
        
        # Créer une clé de cache sécurisée
        cache_key = f"search_{current_user.user_id}_{hash(str(sorted(query.items())))}"
        
        # Vérifier le cache
        cached_result = await cache.get("searches", cache_key)
        if cached_result:
            logger.info("Search cache hit", user_id=current_user.user_id)
            return {"source": "cache", "results": cached_result}
        
        # Effectuer la recherche
        results = await perform_secure_search(query, current_user)
        
        # Mettre en cache
        await cache.set("searches", cache_key, results, ttl_hours=1)
        
        logger.info(
            "Search performed",
            user_id=current_user.user_id,
            query=query,
            results_count=len(results)
        )
        
        return {
            "source": "database",
            "query": query,
            "total_results": len(results),
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Search failed", user_id=current_user.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Search failed")

# ========== ENDPOINTS ADMIN ==========

@app.get("/admin/stats")
async def get_admin_stats(admin_user: TokenData = Depends(get_current_admin_user)):
    """Statistiques administrateur"""
    
    return {
        "total_users": 1234,  # TODO: Depuis la base
        "active_tasks": len([t for t in processing_tasks.values() if t["status"] == "processing"]),
        "completed_tasks": len([t for t in processing_tasks.values() if t["status"] == "completed"]),
        "failed_tasks": len([t for t in processing_tasks.values() if t["status"] == "failed"]),
        "cache_stats": await cache.get_stats(),
        "system_health": "ok"
    }

# ========== FONCTIONS UTILITAIRES ==========

async def process_document_secure(
    task_id: str,
    content: bytes,
    file_info: dict,
    user_id: int,
    period: Optional[str],
    force_period: bool
):
    """Traitement sécurisé d'un document"""
    
    try:
        # Mettre à jour le statut
        processing_tasks[task_id]["status"] = "processing"
        processing_tasks[task_id]["progress"] = 10
        
        # TODO: Intégrer votre logic de parsing ici
        # result = genealogy_parser.process_document(content.decode(), period)
        
        # Simulation
        await asyncio.sleep(2)
        processing_tasks[task_id]["progress"] = 50
        
        await asyncio.sleep(2)
        processing_tasks[task_id]["progress"] = 90
        
        # Résultat simulé
        result = {
            "persons_found": 10,
            "relationships": 15,
            "confidence": 0.85
        }
        
        # Finaliser
        processing_tasks[task_id].update({
            "status": "completed",
            "progress": 100,
            "message": "Processing completed successfully",
            "result": result,
            "completed_at": datetime.utcnow().isoformat()
        })
        
        logger.info(
            "Document processed successfully",
            task_id=task_id,
            user_id=user_id,
            filename=file_info["filename"]
        )
        
    except Exception as e:
        logger.error(
            "Document processing failed",
            task_id=task_id,
            user_id=user_id,
            error=str(e)
        )
        
        processing_tasks[task_id].update({
            "status": "failed",
            "message": f"Processing failed: {str(e)}",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat()
        })

async def perform_secure_search(query: dict, user: TokenData) -> List[dict]:
    """Recherche sécurisée avec vérification des permissions"""
    
    # TODO: Implémenter la vraie logique de recherche
    # Filtrer selon les permissions de l'utilisateur
    
    return [
        {
            "id": "person_1",
            "name": "Jean Dupont",
            "dates": "1850-1920",
            "location": "Lyon",
            "confidence": 0.95
        }
    ]

async def is_admin_user(user: TokenData) -> bool:
    """Vérifie si l'utilisateur a les droits admin"""
    # TODO: Vérifier en base de données
    return user.email and "admin" in user.email

# ========== GESTIONNAIRES D'ERREURS ==========

@app.exception_handler(GarmeaError)
async def garmea_exception_handler(request: Request, exc: GarmeaError):
    """Gestionnaire d'erreurs Garméa"""
    logger.error(
        "Garmea error",
        error_type=exc.error_type.value,
        message=exc.message,
        context=exc.context
    )
    
    return HTTPException(
        status_code=400,
        detail={
            "error": exc.error_type.value,
            "message": exc.message
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Gestionnaire d'erreurs général"""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    
    return HTTPException(
        status_code=500,
        detail="Internal server error"
    )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.secure_main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )