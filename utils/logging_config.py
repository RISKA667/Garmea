import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

def setup_logging(level: str = "INFO", 
                 log_file: Optional[str] = None,
                 console_output: bool = True) -> logging.Logger:
    """Configuration centralisée du logging"""
    
    # Créer le répertoire de logs si nécessaire
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configuration du logger principal
    logger = logging.getLogger('genealogy_parser')
    logger.setLevel(getattr(logging, level.upper()))
    
    # Éviter les doublons de handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Format des messages
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler pour la console
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Handler pour fichier
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

class PerformanceLogger:
    """Logger spécialisé pour mesurer les performances"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.timers = {}
    
    def start_timer(self, operation: str):
        """Démarre un timer pour une opération"""
        self.timers[operation] = datetime.now()
        self.logger.debug(f"Démarrage: {operation}")
    
    def end_timer(self, operation: str):
        """Termine un timer et log la durée"""
        if operation in self.timers:
            duration = datetime.now() - self.timers[operation]
            self.logger.info(f"Terminé: {operation} - Durée: {duration.total_seconds():.2f}s")
            del self.timers[operation]
        else:
            self.logger.warning(f"Timer non trouvé pour: {operation}")
    
    def log_stats(self, stats: dict, prefix: str = "Stats"):
        """Log des statistiques formatées"""
        self.logger.info(f"=== {prefix} ===")
        for key, value in stats.items():
            self.logger.info(f"{key}: {value}")