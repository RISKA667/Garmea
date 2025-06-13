# utils/error_handler.py
import logging
import traceback
from typing import Optional, Dict, Any
from enum import Enum
from functools import wraps

class ErrorType(Enum):
    PDF_READ_ERROR = "pdf_read_error"
    PARSING_ERROR = "parsing_error"
    VALIDATION_ERROR = "validation_error"
    DATABASE_ERROR = "database_error"
    CONFIGURATION_ERROR = "config_error"

class GarmeaError(Exception):
    """Exception de base pour Garmea"""
    def __init__(self, message: str, error_type: ErrorType, 
                 original_error: Optional[Exception] = None, 
                 context: Optional[Dict] = None):
        self.message = message
        self.error_type = error_type
        self.original_error = original_error
        self.context = context or {}
        super().__init__(self.message)

class ErrorHandler:
    """Gestionnaire d'erreurs centralisé et intelligent"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_stats = {}
        
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> GarmeaError:
        """Traite une erreur et retourne une GarmeaError structurée"""
        context = context or {}
        
        # Classifier l'erreur
        error_type = self._classify_error(error)
        
        # Créer un message utilisateur friendly
        user_message = self._create_user_message(error, error_type, context)
        
        # Logger avec le bon niveau
        self._log_error(error, error_type, context)
        
        # Statistiques
        self._update_stats(error_type)
        
        return GarmeaError(user_message, error_type, error, context)
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classifie automatiquement le type d'erreur"""
        error_class = error.__class__.__name__
        error_message = str(error).lower()
        
        if 'pdf' in error_message or 'fitz' in error_message:
            return ErrorType.PDF_READ_ERROR
        elif 'regex' in error_message or 'pattern' in error_message:
            return ErrorType.PARSING_ERROR
        elif 'validation' in error_message or 'chronology' in error_message:
            return ErrorType.VALIDATION_ERROR
        elif 'database' in error_message or 'sql' in error_message:
            return ErrorType.DATABASE_ERROR
        else:
            return ErrorType.PARSING_ERROR  # Par défaut
    
    def _create_user_message(self, error: Exception, error_type: ErrorType, 
                           context: Dict) -> str:
        """Crée des messages d'erreur compréhensibles pour l'utilisateur"""
        base_messages = {
            ErrorType.PDF_READ_ERROR: "Impossible de lire le fichier PDF. Vérifiez que le fichier n'est pas corrompu.",
            ErrorType.PARSING_ERROR: "Erreur lors de l'analyse du document. Le format pourrait ne pas être supporté.",
            ErrorType.VALIDATION_ERROR: "Les données extraites contiennent des incohérences chronologiques.",
            ErrorType.DATABASE_ERROR: "Erreur de base de données. Réessayez dans quelques instants.",
            ErrorType.CONFIGURATION_ERROR: "Erreur de configuration du système."
        }
        
        base_msg = base_messages.get(error_type, "Une erreur inattendue s'est produite.")
        
        # Ajouter contexte si pertinent
        if context.get('file_name'):
            base_msg += f" (Fichier: {context['file_name']})"
        if context.get('page_number'):
            base_msg += f" (Page: {context['page_number']})"
            
        return base_msg
    
    def _log_error(self, error: Exception, error_type: ErrorType, context: Dict):
        """Log l'erreur avec le niveau approprié"""
        error_msg = f"[{error_type.value}] {str(error)}"
        
        if context:
            error_msg += f" | Context: {context}"
        
        if error_type in [ErrorType.DATABASE_ERROR, ErrorType.CONFIGURATION_ERROR]:
            self.logger.error(error_msg, exc_info=True)
        else:
            self.logger.warning(error_msg)
    
    def _update_stats(self, error_type: ErrorType):
        """Met à jour les statistiques d'erreurs"""
        self.error_stats[error_type.value] = self.error_stats.get(error_type.value, 0) + 1

# Décorateur pour automatiser la gestion d'erreurs
def handle_errors(error_handler: ErrorHandler, context_func=None):
    """Décorateur pour automatiser la gestion d'erreurs"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {}
                if context_func:
                    context = context_func(*args, **kwargs)
                
                garmea_error = error_handler.handle_error(e, context)
                raise garmea_error
        return wrapper
    return decorator

# Exemple d'utilisation
error_handler = ErrorHandler()

@handle_errors(error_handler, lambda pdf_path, *args: {'file_name': pdf_path})
def read_pdf_safe(pdf_path: str) -> str:
    """Version sécurisée de la lecture PDF"""
    import fitz
    
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"Fichier PDF introuvable: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    content = ""
    
    for page_num in range(len(doc)):
        try:
            page = doc[page_num]
            content += page.get_text()
        except Exception as e:
            raise GarmeaError(
                f"Erreur lecture page {page_num + 1}",
                ErrorType.PDF_READ_ERROR,
                e,
                {'page_number': page_num + 1, 'file_name': pdf_path}
            )
    
    doc.close()
    return content