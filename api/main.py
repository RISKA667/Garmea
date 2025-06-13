# api/main.py - API REST moderne pour Garmea
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union
import asyncio
import uuid
import tempfile
import os
from pathlib import Path
import logging

# Imports de votre logique existante
from parsers.multi_period_parser import MultiPeriodParser, Period
from parsers.modern_nlp_parser import create_relationship_parser
from utils.smart_cache import SmartCache
from utils.error_handler import ErrorHandler, GarmeaError

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation FastAPI
app = FastAPI(
    title="Garmea API",
    description="API de traitement généalogique pour documents historiques français",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS pour permettre les requêtes frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation des services
cache = SmartCache()
error_handler = ErrorHandler()
multi_parser = MultiPeriodParser()
relationship_parser = create_relationship_parser()

# Stockage temporaire des tâches de traitement
processing_tasks = {}

# ========== MODÈLES PYDANTIC ==========

class DocumentUploadResponse(BaseModel):
    task_id: str
    status: str
    message: str

class ProcessingStatus(BaseModel):
    task_id: str
    status: str  # "pending", "processing", "completed", "error"
    progress: int  # 0-100
    message: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None

class PersonResult(BaseModel):
    id: str
    nom_complet: str
    prenom: Optional[str] = None
    nom: Optional[str] = None
    dates: Optional[str] = None
    professions: List[str] = []
    titres: List[str] = []
    notabilite: int = 0

class RelationshipResult(BaseModel):
    type: str  # "filiation", "mariage", "parrainage"
    personnes: Dict[str, str]
    confiance: float = 0.0
    source: Optional[str] = None

class DocumentAnalysisResult(BaseModel):
    document_id: str
    periode: str
    periode_detectee: Dict
    personnes: List[PersonResult]
    relations: List[RelationshipResult]
    actes: Dict
    statistiques: Dict
    confiance_globale: float

class SearchQuery(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    lieu: Optional[str] = None
    periode_debut: Optional[int] = None
    periode_fin: Optional[int] = None
    limit: int = Field(default=50, le=200)

# ========== ENDPOINTS PRINCIPAUX ==========

@app.get("/")
async def root():
    """Point d'entrée de l'API"""
    return {
        "message": "Garmea API v2.0.0",
        "status": "active",
        "docs": "/docs",
        "endpoints": {
            "upload": "/documents/upload",
            "status": "/tasks/{task_id}",
            "search": "/search",
            "stats": "/stats"
        }
    }

@app.get("/health")
async def health_check():
    """Vérification santé de l'API"""
    try:
        # Tester les composants critiques
        cache_stats = cache.get_stats()
        
        return {
            "status": "healthy",
            "services": {
                "cache": "ok" if cache_stats else "error",
                "parser": "ok",
                "nlp": "ok" if hasattr(relationship_parser, 'use_spacy') else "limited"
            },
            "cache_stats": cache_stats
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    period: Optional[str] = None,
    force_period: bool = False
):
    """Upload et traitement asynchrone d'un document PDF"""
    
    # Validation fichier
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont supportés")
    
    if file.size > 50 * 1024 * 1024:  # 50MB max
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 50MB)")
    
    # Générer un ID de tâche unique
    task_id = str(uuid.uuid4())
    
    # Initialiser le statut de traitement
    processing_tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Document reçu, traitement en attente...",
        "filename": file.filename
    }
    
    # Lancer le traitement en arrière-plan
    background_tasks.add_task(
        process_document_async,
        task_id,
        file,
        period,
        force_period
    )
    
    return DocumentUploadResponse(
        task_id=task_id,
        status="accepted",
        message=f"Document {file.filename} en cours de traitement"
    )

@app.get("/tasks/{task_id}", response_model=ProcessingStatus)
async def get_task_status(task_id: str):
    """Récupère le statut d'une tâche de traitement"""
    
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    
    task_info = processing_tasks[task_id]
    
    return ProcessingStatus(
        task_id=task_id,
        status=task_info["status"],
        progress=task_info["progress"],
        message=task_info.get("message"),
        result=task_info.get("result"),
        error=task_info.get("error")
    )

@app.post("/search")
async def search_persons(query: SearchQuery):
    """Recherche de personnes dans la base de données"""
    
    try:
        # Créer une clé de cache pour la recherche
        cache_key = f"search_{hash(str(query.dict()))}"
        
        # Vérifier le cache
        cached_result = cache.get("searches", cache_key)
        if cached_result:
            return {"source": "cache", "results": cached_result}
        
        # Simuler une recherche (à remplacer par votre vraie logique)
        results = await perform_search(query)
        
        # Mettre en cache le résultat
        cache.set("searches", cache_key, results, ttl_hours=1)
        
        return {
            "source": "database",
            "query": query.dict(),
            "total_results": len(results),
            "results": results
        }
        
    except Exception as e:
        garmea_error = error_handler.handle_error(e, {"query": query.dict()})
        raise HTTPException(status_code=500, detail=garmea_error.message)

@app.get("/stats")
async def get_global_stats():
    """Statistiques globales de l'API"""
    
    return {
        "api_version": "2.0.0",
        "active_tasks": len([t for t in processing_tasks.values() if t["status"] == "processing"]),
        "completed_tasks": len([t for t in processing_tasks.values() if t["status"] == "completed"]),
        "cache_stats": cache.get_stats(),
        "supported_periods": [p.value for p in Period],
        "parser_stats": {
            "nlp_available": hasattr(relationship_parser, 'use_spacy'),
            "periods_supported": len(multi_parser.period_parsers)
        }
    }

@app.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Annule une tâche de traitement"""
    
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    
    task = processing_tasks[task_id]
    
    if task["status"] == "completed":
        raise HTTPException(status_code=400, detail="Impossible d'annuler une tâche terminée")
    
    # Marquer comme annulée
    processing_tasks[task_id]["status"] = "cancelled"
    processing_tasks[task_id]["message"] = "Tâche annulée par l'utilisateur"
    
    return {"message": "Tâche annulée avec succès"}

# ========== FONCTIONS UTILITAIRES ==========

async def process_document_async(
    task_id: str,
    file: UploadFile,
    period: Optional[str],
    force_period: bool
):
    """Traitement asynchrone d'un document"""
    
    try:
        # Mise à jour du statut
        processing_tasks[task_id]["status"] = "processing"
        processing_tasks[task_id]["progress"] = 10
        processing_tasks[task_id]["message"] = "Lecture du fichier PDF..."
        
        # Sauvegarder temporairement le fichier
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Mise à jour du statut
            processing_tasks[task_id]["progress"] = 30
            processing_tasks[task_id]["message"] = "Extraction du texte..."
            
            # Lire le PDF (utiliser votre logique existante)
            from utils.pdf_reader import PDFReader
            pdf_reader = PDFReader()
            text_content = pdf_reader.read_pdf_file(temp_path)
            
            # Mise à jour du statut
            processing_tasks[task_id]["progress"] = 50
            processing_tasks[task_id]["message"] = "Détection de la période..."
            
            # Déterminer la période
            forced_period = None
            if force_period and period:
                try:
                    forced_period = Period(period)
                except ValueError:
                    pass
            
            # Mise à jour du statut
            processing_tasks[task_id]["progress"] = 70
            processing_tasks[task_id]["message"] = "Analyse généalogique..."
            
            # Traitement avec parser multi-périodes
            result = multi_parser.parse_document(text_content, forced_period)
            
            # Mise à jour du statut
            processing_tasks[task_id]["progress"] = 90
            processing_tasks[task_id]["message"] = "Finalisation..."
            
            # Formater le résultat pour l'API
            formatted_result = format_api_result(result, file.filename)
            
            # Tâche terminée
            processing_tasks[task_id]["status"] = "completed"
            processing_tasks[task_id]["progress"] = 100
            processing_tasks[task_id]["message"] = "Traitement terminé avec succès"
            processing_tasks[task_id]["result"] = formatted_result
            
        finally:
            # Nettoyer le fichier temporaire
            os.unlink(temp_path)
    
    except Exception as e:
        # Gérer l'erreur
        garmea_error = error_handler.handle_error(e, {
            "task_id": task_id,
            "filename": file.filename
        })
        
        processing_tasks[task_id]["status"] = "error"
        processing_tasks[task_id]["error"] = garmea_error.message
        processing_tasks[task_id]["message"] = f"Erreur: {garmea_error.message}"

def format_api_result(parser_result: Dict, filename: str) -> DocumentAnalysisResult:
    """Formate le résultat du parser pour l'API"""
    
    # Extraire les informations principales
    personnes = []
    if 'personnes' in parser_result:
        for i, personne in enumerate(parser_result['personnes']):
            personnes.append(PersonResult(
                id=f"person_{i}",
                nom_complet=personne.get('nom_complet', ''),
                dates=personne.get('dates', ''),
                professions=personne.get('professions', '').split(', ') if personne.get('professions') else [],
                titres=personne.get('titres', '').split(', ') if personne.get('titres') else [],
                notabilite=personne.get('notabilite', 0)
            ))
    
    relations = []
    if 'filiations' in parser_result:
        for filiation in parser_result['filiations']:
            relations.append(RelationshipResult(
                type="filiation",
                personnes={
                    "enfant": filiation.get('enfant', ''),
                    "pere": filiation.get('pere', ''),
                    "mere": filiation.get('mere', '')
                },
                confiance=0.8  # À ajuster selon votre logique
            ))
    
    return DocumentAnalysisResult(
        document_id=str(uuid.uuid4()),
        periode=parser_result.get('lieu', 'Inconnu'),
        periode_detectee=parser_result.get('period_info', {}),
        personnes=personnes,
        relations=relations,
        actes=parser_result.get('actes', {}),
        statistiques=parser_result.get('statistiques', {}),
        confiance_globale=0.75  # À calculer selon votre logique
    )

async def perform_search(query: SearchQuery) -> List[Dict]:
    """Effectue une recherche dans la base de données"""
    
    # Simuler une recherche (remplacer par vraie logique de BDD)
    results = []
    
    # Exemple de résultats simulés
    if query.nom:
        results.append({
            "id": "person_1",
            "nom_complet": f"{query.prenom or 'Jean'} {query.nom}",
            "dates": "1850-1920",
            "lieu": query.lieu or "Lyon",
            "score": 0.95
        })
    
    return results

# ========== GESTION D'ERREURS GLOBALE ==========

@app.exception_handler(GarmeaError)
async def garmea_exception_handler(request, exc: GarmeaError):
    """Gestionnaire global des erreurs Garmea"""
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.error_type.value,
            "message": exc.message,
            "context": exc.context
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Gestionnaire global des autres erreurs"""
    garmea_error = error_handler.handle_error(exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": garmea_error.message
        }
    )

# ========== LANCEMENT ==========

if __name__ == "__main__":
    import uvicorn
    
    # Configuration de développement
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

# Instructions de déploiement
"""
INSTALLATION ET LANCEMENT:

1. Installer les dépendances:
   pip install fastapi uvicorn python-multipart

2. Lancer l'API en développement:
   python api/main.py

3. Lancer l'API en production:
   uvicorn api.main:app --host 0.0.0.0 --port 8000

4. Documentation automatique:
   http://localhost:8000/docs
   http://localhost:8000/redoc

5. Test de santé:
   curl http://localhost:8000/health

INTÉGRATION FRONTEND:
- Remplacer les appels directs au backend par des requêtes HTTP à cette API
- Utiliser le système de tâches asynchrones pour les gros documents
- Implémenter un polling du statut pour suivre les traitements
"""