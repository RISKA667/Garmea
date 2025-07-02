import hashlib
import hmac
import os
from contextlib import asynccontextmanager
from datetime import datetime

import structlog
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request, HTTPException, Depends, Form
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from fastapi.openapi.utils import get_openapi

try:
    from app.services.auth import auth_manager, get_current_user, get_current_admin_user, is_admin_user
    from app.services.cache import SecureRedisCache
    from app.services.search import search_documents, process_uploaded_file
    from app.services.logger import configure_logging
    from app.services.validator import file_validator
    from app.schemas.user import UserIn, UserOut, UserLogin
    from app.schemas.document import DocumentSearchRequest
    from app.exceptions import ErrorHandler, GarmeaError
    from app.rate_limiter import rate_limiter
except ImportError as import_error:
    raise RuntimeError("Critical import failed: " + str(import_error))

import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

logger = structlog.get_logger()

security = HTTPBearer()

@asynccontextmanager
def lifespan(app: FastAPI):
    configure_logging()
    sentry_sdk.init(dsn=os.getenv("SENTRY_DSN", ""), traces_sample_rate=1.0)
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.garmedoc.fr"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://garmedoc.fr"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(SentryAsgiMiddleware)

cache = SecureRedisCache(ttl=600)  # 10 minutes cache

@app.exception_handler(GarmeaError)
async def garmea_error_handler(request: Request, exc: GarmeaError):
    logger.error("Handled GarmeaError", detail=str(exc))
    return JSONResponse(status_code=400, content={"detail": str(exc)})

@app.post("/register", response_model=UserOut)
@rate_limiter
async def register(user: UserIn):
    try:
        return await auth_manager.register_user(user)
    except ValueError as e:
        logger.error("Registration failed", reason=type(e).__name__)
        raise HTTPException(status_code=400, detail="Registration error")

@app.post("/login")
@rate_limiter
async def login(user: UserLogin):
    try:
        return await auth_manager.authenticate_user(user)
    except PermissionError as e:
        logger.error("Authentication failed", reason=type(e).__name__)
        raise HTTPException(status_code=401, detail="Authentication failed")

@app.post("/upload")
@rate_limiter
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    period: str = Form(...),
    force_period: bool = Form(False),
    current_user: dict = Depends(get_current_user)
):
    is_valid, error_message = await file_validator.validate_file(file)
    if not is_valid:
        logger.warning("Invalid file upload attempt", user_id=current_user.user_id, reason=error_message)
        raise HTTPException(status_code=400, detail=error_message)

    content = await file.read()
    file_hash = hmac.new(os.getenv("SECRET_KEY", "default_key").encode(), content, hashlib.sha256).hexdigest()
    cache_key = f"upload_{current_user.user_id}_{file_hash}_{period}"

    if await cache.exists(cache_key):
        logger.info("Duplicate upload detected", user_id=current_user.user_id)
        raise HTTPException(status_code=409, detail="Document already processed.")

    existing_task = await cache.get(cache_key)
    if existing_task and not force_period:
        logger.info("Existing task found", user_id=current_user.user_id)
        return {"message": "Task already in progress or completed."}

    try:
        await cache.set(cache_key, "processing")
        background_tasks.add_task(process_uploaded_file, content, file.filename, period, current_user.user_id)
        return {"message": "Document upload accepted"}
    except RuntimeError as e:
        logger.error("Upload processing failed", user_id=current_user.user_id, reason=type(e).__name__)
        raise HTTPException(status_code=500, detail="Upload processing error")

@app.post("/search")
@rate_limiter
async def search(request: DocumentSearchRequest, current_user: dict = Depends(get_current_user)):
    try:
        query = request.dict()
        raw_key = str(sorted(query.items()))
        cache_hash = hmac.new(os.getenv("SECRET_KEY", "default_key").encode(), raw_key.encode(), hashlib.sha256).hexdigest()
        cache_key = f"search_{current_user.user_id}_{cache_hash}"

        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.info("Cache hit", key=cache_key)
            return cached_result

        result = await search_documents(query, current_user.user_id)
        await cache.set(cache_key, result)
        return result
    except RuntimeError as e:
        logger.error("Search error", user_id=current_user.user_id, reason=type(e).__name__)
        raise HTTPException(status_code=500, detail="Search failed")

@app.get("/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_admin_user)):
    try:
        if not is_admin_user(current_user):
            logger.warning("Unauthorized admin access attempt", user_id=current_user.user_id)
            raise HTTPException(status_code=403, detail="Unauthorized")

        stats = {
            "users": await auth_manager.count_users(),
            "documents": await cache.count_keys(prefix="upload_"),
            "searches": await cache.count_keys(prefix="search_")
        }
        return stats
    except RuntimeError as e:
        logger.error("Admin stats retrieval failed", reason=type(e).__name__)
        raise HTTPException(status_code=500, detail="Stats retrieval failed")

# === EXTENDED ROADMAP PREP (non-fonctionnel ici mais base prévue) ===
# - CI/CD : GitHub Actions avec tests, lint, Bandit automatique
# - Audit Log : journalisation des actions utilisateur (à ajouter côté services)
# - Metrics : export Prometheus pour Grafana via middleware personnalisé
# - RGPD : ajout d'une route de suppression utilisateur, export de données, anonymisation
# - Billing : future intégration Stripe / gestion quotas API par utilisateur
# - ACL : rôles et permissions avancés à définir dans services/auth/acl.py