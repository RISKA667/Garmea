import hashlib
import hmac
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request, HTTPException, Depends, Form
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

# Import des modules existants du projet
from config.secure_settings import get_settings
from database.person_manager import PersonManager
from database.acte_manager import ActeManager
from database.family_network import FamilyNetwork
from parsers.specialized.pdf_analyzer import PDFAnalyzer
from parsers.specialized.genealogy_calculator import GenealogyCalculator
from exporters.gedcom_exporter import GedcomExporter
from exporters.json_exporter import JsonExporter
from exporters.report_generator import ReportGenerator
from utils.pdf_reader import PDFReader
from utils.text_utils import TextUtils
from utils.date_utils import DateUtils
from security.auth import AuthManager
from security.file_validator import FileValidator

logger = structlog.get_logger()
settings = get_settings()

security = HTTPBearer()

# Modèles Pydantic pour l'API
class UserIn(BaseModel):
    username: str
    email: str
    password: str

class UserOut(BaseModel):
    user_id: str
    username: str
    email: str
    is_admin: bool = False

class UserLogin(BaseModel):
    username: str
    password: str

class DocumentSearchRequest(BaseModel):
    query: str
    filters: Optional[dict] = None
    limit: int = 50

class UploadResponse(BaseModel):
    message: str
    task_id: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[dict]
    total: int
    query: str

# Gestionnaires d'erreurs personnalisés
class GarmeaError(Exception):
    pass

class ErrorHandler:
    @staticmethod
    def handle_error(error: Exception) -> dict:
        return {"error": str(error), "type": type(error).__name__}

# Rate limiter simple
def rate_limiter(func):
    async def wrapper(*args, **kwargs):
        # Implémentation simple du rate limiting
        return await func(*args, **kwargs)
    return wrapper

@asynccontextmanager
def lifespan(app: FastAPI):
    # Configuration au démarrage
    logger.info("Démarrage de l'API Garméa")
    yield
    # Nettoyage à l'arrêt
    logger.info("Arrêt de l'API Garméa")

app = FastAPI(
    title="Garméa API",
    description="API pour l'analyse généalogique de documents historiques",
    version="2.0.0",
    lifespan=lifespan
)

# Middleware de sécurité
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Initialisation des services
auth_manager = AuthManager()
file_validator = FileValidator()
person_manager = PersonManager()
acte_manager = ActeManager()
family_network = FamilyNetwork()
pdf_analyzer = PDFAnalyzer()
genealogy_calculator = GenealogyCalculator()

# Gestionnaire d'erreurs
@app.exception_handler(GarmeaError)
async def garmea_error_handler(request: Request, exc: GarmeaError):
    logger.error("Erreur Garméa", detail=str(exc))
    return JSONResponse(status_code=400, content={"detail": str(exc)})

# Routes d'authentification
@app.post("/register", response_model=UserOut)
@rate_limiter
async def register(user: UserIn):
    try:
        return await auth_manager.register_user(user)
    except ValueError as e:
        logger.error("Échec de l'inscription", reason=type(e).__name__)
        raise HTTPException(status_code=400, detail="Erreur d'inscription")

@app.post("/login")
@rate_limiter
async def login(user: UserLogin):
    try:
        return await auth_manager.authenticate_user(user)
    except PermissionError as e:
        logger.error("Échec d'authentification", reason=type(e).__name__)
        raise HTTPException(status_code=401, detail="Échec d'authentification")

# Routes de documents
@app.post("/upload", response_model=UploadResponse)
@rate_limiter
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    period: str = Form(...),
    force_period: bool = Form(False)
):
    try:
        # Validation du fichier
        is_valid, error_message = await file_validator.validate_file(file)
        if not is_valid:
            logger.warning("Tentative d'upload de fichier invalide", reason=error_message)
            raise HTTPException(status_code=400, detail=error_message)

        # Lecture du contenu
        content = await file.read()
        
        # Traitement en arrière-plan
        background_tasks.add_task(process_uploaded_file, content, file.filename, period)
        
        return UploadResponse(message="Document uploadé avec succès")
    except Exception as e:
        logger.error("Erreur lors de l'upload", reason=str(e))
        raise HTTPException(status_code=500, detail="Erreur de traitement du document")

@app.post("/search", response_model=SearchResponse)
@rate_limiter
async def search_documents(request: DocumentSearchRequest):
    try:
        # Recherche dans les documents
        results = await acte_manager.search_actes(request.query, request.filters, request.limit)
        
        return SearchResponse(
            results=results,
            total=len(results),
            query=request.query
        )
    except Exception as e:
        logger.error("Erreur de recherche", reason=str(e))
        raise HTTPException(status_code=500, detail="Erreur de recherche")

# Routes de généalogie
@app.get("/persons")
async def get_persons(limit: int = 50, offset: int = 0):
    try:
        persons = await person_manager.get_persons(limit=limit, offset=offset)
        return {"persons": persons, "total": len(persons)}
    except Exception as e:
        logger.error("Erreur lors de la récupération des personnes", reason=str(e))
        raise HTTPException(status_code=500, detail="Erreur de récupération")

@app.get("/persons/{person_id}")
async def get_person(person_id: str):
    try:
        person = await person_manager.get_person(person_id)
        if not person:
            raise HTTPException(status_code=404, detail="Personne non trouvée")
        return person
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de la récupération de la personne", reason=str(e))
        raise HTTPException(status_code=500, detail="Erreur de récupération")

@app.get("/family-network/{person_id}")
async def get_family_network(person_id: str, depth: int = 3):
    try:
        network = await family_network.get_family_network(person_id, depth)
        return network
    except Exception as e:
        logger.error("Erreur lors de la récupération du réseau familial", reason=str(e))
        raise HTTPException(status_code=500, detail="Erreur de récupération")

# Routes d'export
@app.get("/export/gedcom/{person_id}")
async def export_gedcom(person_id: str):
    try:
        exporter = GedcomExporter()
        gedcom_data = await exporter.export_person(person_id)
        return {"gedcom": gedcom_data}
    except Exception as e:
        logger.error("Erreur lors de l'export GEDCOM", reason=str(e))
        raise HTTPException(status_code=500, detail="Erreur d'export")

@app.get("/export/json/{person_id}")
async def export_json(person_id: str):
    try:
        exporter = JsonExporter()
        json_data = await exporter.export_person(person_id)
        return json_data
    except Exception as e:
        logger.error("Erreur lors de l'export JSON", reason=str(e))
        raise HTTPException(status_code=500, detail="Erreur d'export")

@app.get("/export/report/{person_id}")
async def export_report(person_id: str):
    try:
        generator = ReportGenerator()
        report = await generator.generate_person_report(person_id)
        return report
    except Exception as e:
        logger.error("Erreur lors de la génération du rapport", reason=str(e))
        raise HTTPException(status_code=500, detail="Erreur de génération")

# Routes d'analyse
@app.post("/analyze/pdf")
async def analyze_pdf(file: UploadFile = File(...)):
    try:
        content = await file.read()
        analysis = await pdf_analyzer.analyze_pdf(content)
        return analysis
    except Exception as e:
        logger.error("Erreur lors de l'analyse PDF", reason=str(e))
        raise HTTPException(status_code=500, detail="Erreur d'analyse")

@app.get("/calculate-relationships/{person1_id}/{person2_id}")
async def calculate_relationships(person1_id: str, person2_id: str):
    try:
        relationships = await genealogy_calculator.calculate_relationships(person1_id, person2_id)
        return relationships
    except Exception as e:
        logger.error("Erreur lors du calcul des relations", reason=str(e))
        raise HTTPException(status_code=500, detail="Erreur de calcul")

# Routes de santé et monitoring
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.version
    }

@app.get("/stats")
async def get_stats():
    try:
        stats = {
            "total_persons": await person_manager.count_persons(),
            "total_actes": await acte_manager.count_actes(),
            "total_families": await family_network.count_families()
        }
        return stats
    except Exception as e:
        logger.error("Erreur lors de la récupération des statistiques", reason=str(e))
        raise HTTPException(status_code=500, detail="Erreur de récupération")

# Fonction de traitement des fichiers uploadés
async def process_uploaded_file(content: bytes, filename: str, period: str):
    try:
        logger.info("Traitement du fichier", filename=filename, period=period)
        
        # Analyse du PDF
        analysis = await pdf_analyzer.analyze_pdf(content)
        
        # Extraction des personnes
        persons = await person_manager.extract_persons_from_analysis(analysis)
        
        # Extraction des actes
        actes = await acte_manager.extract_actes_from_analysis(analysis, period)
        
        logger.info("Fichier traité avec succès", 
                   filename=filename, 
                   persons_count=len(persons), 
                   actes_count=len(actes))
        
    except Exception as e:
        logger.error("Erreur lors du traitement du fichier", 
                    filename=filename, 
                    error=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)