#!/usr/bin/env python3
"""
CodexGenea - Parseur Généalogique Avancé
=========================================

Module principal pour l'analyse et le traitement de documents généalogiques
français de l'Ancien Régime. Ce parseur spécialisé traite les registres
paroissiaux, actes de baptême, mariage et sépulture avec correction OCR
intégrée et extraction intelligente des informations familiales.

Fonctionnalités principales:
- Lecture et traitement de documents PDF et texte
- Correction automatique des erreurs OCR
- Extraction et normalisation des noms de personnes
- Reconnaissance des titres nobiliaires et religieux
- Gestion des abréviations historiques
- Export multi-formats (JSON, TXT, GEDCOM)
- Validation chronologique des données
- Cache intelligent pour optimiser les performances

Auteur: Garméa Parser Team
Version: 3.0.0
Licence: MIT
Date: 2024-2025

Exemples d'utilisation:
    python main.py document.pdf                    # Traitement PDF complet
    python main.py document.txt -o resultats/      # Fichier texte avec sortie personnalisée
    python main.py document.pdf --pdf-pages 50     # Limiter à 50 pages
    python main.py demo                            # Mode démonstration
    python main.py --test                          # Tests intégrés
"""

import argparse
import json
import logging
import re
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
import warnings
from functools import lru_cache, wraps
from collections import defaultdict, Counter
import hashlib

# Suppression des avertissements non critiques
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

# === IMPORTS CONDITIONNELS ===
try:
    import fitz  # PyMuPDF pour la lecture PDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from parsers.base.text_parser import TextParser
    from parsers.base.name_extractor import NameExtractor  
    from database.person_manager import PersonManager
    HAS_PARSERS = True
except ImportError as e:
    print(f"Modules parsers manquants: {e}")
    HAS_PARSERS = False

# === CONSTANTES GLOBALES ===
VERSION = "3.0.0"
AUTHOR = "Garméa Parser Team"
LICENSE = "MIT"

# Codes de sortie standardisés
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_INTERRUPTED = 130
EXIT_CONFIG_ERROR = 2
EXIT_DEPENDENCY_ERROR = 3


class Config:
    """
    Configuration centralisée du parseur généalogique.
    
    Cette classe contient toutes les constantes et paramètres de configuration
    utilisés par le système. Elle permet une gestion centralisée et cohérente
    des paramètres de traitement.
    
    Attributes:
        DEFAULT_OUTPUT_DIR: Répertoire de sortie par défaut
        DEFAULT_LOGS_DIR: Répertoire des logs par défaut
        DEFAULT_CONFIG_FILE: Fichier de configuration par défaut
        MAX_PDF_PAGES: Nombre maximum de pages PDF à traiter
        MAX_TEXT_LENGTH: Longueur maximale du texte à traiter
        CHUNK_SIZE: Taille des chunks pour le traitement par blocs
        CACHE_SIZE: Taille du cache pour optimiser les performances
        ENABLE_OCR_CORRECTIONS: Activation des corrections OCR
        ENABLE_VALIDATION: Activation de la validation des données
        SUPPORTED_TEXT_FORMATS: Formats de texte supportés
        SUPPORTED_PDF_FORMATS: Formats PDF supportés
    """
    
    # === RÉPERTOIRES ===
    DEFAULT_OUTPUT_DIR = Path("output")
    DEFAULT_LOGS_DIR = Path("logs")
    DEFAULT_CONFIG_FILE = Path("config/settings.json")
    
    # === LIMITES DE TRAITEMENT ===
    MAX_PDF_PAGES = 500
    MAX_TEXT_LENGTH = 1_000_000
    CHUNK_SIZE = 100_000
    CACHE_SIZE = 5000
    
    # === OPTIONS DE TRAITEMENT ===
    ENABLE_OCR_CORRECTIONS = True
    ENABLE_VALIDATION = True
    
    # === FORMATS SUPPORTÉS ===
    SUPPORTED_TEXT_FORMATS = {'.txt', '.md', '.rtf'}
    SUPPORTED_PDF_FORMATS = {'.pdf'}
    
    # === SEUILS DE QUALITÉ ===
    MIN_NAME_CONFIDENCE = 0.6
    MIN_DATE_CONFIDENCE = 0.7
    MIN_RELATIONSHIP_CONFIDENCE = 0.8
    
    # === PARAMÈTRES DE PERFORMANCE ===
    PROGRESS_UPDATE_INTERVAL = 0.5  # secondes
    MEMORY_CLEANUP_THRESHOLD = 1000  # documents
    
    @classmethod
    def get_all_supported_formats(cls) -> set:
        """
        Retourne l'ensemble de tous les formats supportés.
        
        Returns:
            set: Ensemble des extensions de fichiers supportées
        """
        return cls.SUPPORTED_TEXT_FORMATS | cls.SUPPORTED_PDF_FORMATS
    
    @classmethod
    def validate_config(cls, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide et normalise une configuration.
        
        Args:
            config_dict: Dictionnaire de configuration à valider
            
        Returns:
            Dict[str, Any]: Configuration validée et normalisée
            
        Raises:
            ValueError: Si la configuration est invalide
        """
        validated = {}
        
        # Validation des paramètres numériques
        for key, default_value in [
            ('max_pdf_pages', cls.MAX_PDF_PAGES),
            ('max_text_length', cls.MAX_TEXT_LENGTH),
            ('chunk_size', cls.CHUNK_SIZE),
            ('cache_size', cls.CACHE_SIZE)
        ]:
            value = config_dict.get(key, default_value)
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"Paramètre invalide {key}: {value}")
            validated[key] = value
        
        # Validation des booléens
        for key, default_value in [
            ('enable_ocr_corrections', cls.ENABLE_OCR_CORRECTIONS),
            ('enable_validation', cls.ENABLE_VALIDATION)
        ]:
            value = config_dict.get(key, default_value)
            if not isinstance(value, bool):
                raise ValueError(f"Paramètre invalide {key}: {value}")
            validated[key] = value
        
        return validated
    
class LoggingSetup:
    """
    Configuration et gestion du système de logging.
    
    Cette classe fournit des méthodes pour configurer le système de logging
    de manière cohérente et centralisée, avec support pour les logs console
    et fichier.
    """
    
    @staticmethod
    def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> logging.Logger:
        """
        Configure le système de logging.
        
        Args:
            verbose: Active le mode debug si True
            log_file: Chemin vers le fichier de log (optionnel)
            
        Returns:
            logging.Logger: Logger configuré
            
        Raises:
            OSError: Si impossible de créer le répertoire de logs
        """
        try:
            Config.DEFAULT_LOGS_DIR.mkdir(exist_ok=True)
        except OSError as e:
            raise OSError(f"Impossible de créer le répertoire de logs: {e}")
        
        level = logging.DEBUG if verbose else logging.INFO
        
        # Formatter personnalisé avec couleurs pour la console
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Logger principal
        logger = logging.getLogger('garmeae_parser')
        logger.setLevel(level)
        
        # Nettoyage des handlers existants
        if logger.handlers:
            logger.handlers.clear()
        
        # Handler console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Handler fichier (optionnel)
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except OSError as e:
                logger.warning(f"Impossible de créer le fichier de log {log_file}: {e}")
        
        return logger
    
    @staticmethod
    def get_logger(name: str = None) -> logging.Logger:
        """
        Récupère un logger configuré.
        
        Args:
            name: Nom du logger (optionnel)
            
        Returns:
            logging.Logger: Logger configuré
        """
        return logging.getLogger(name or 'garmeae_parser')

class EnhancedPDFReader:
    """
    Lecteur PDF optimisé avec gestion d'erreurs avancée.
    
    Cette classe fournit des fonctionnalités avancées pour la lecture et
    l'analyse de documents PDF, avec support pour le traitement par blocs,
    la gestion de la mémoire et l'optimisation des performances.
    
    Attributes:
        logger: Logger pour les messages de diagnostic
        stats: Statistiques de traitement
        _page_cache: Cache pour les pages déjà lues
        _text_cache: Cache pour les textes extraits
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialise le lecteur PDF.
        
        Args:
            logger: Logger personnalisé (optionnel)
        """
        self.logger = logger or LoggingSetup.get_logger(__name__)
        
        # Statistiques de traitement
        self.stats = {
            'pages_processed': 0,
            'total_chars': 0,
            'processing_time': 0.0,
            'errors': 0,
            'warnings': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Caches pour optimiser les performances
        self._page_cache = {}
        self._text_cache = {}
        self._max_cache_size = 100
    
    @property
    def can_read_pdf(self) -> bool:
        """
        Vérifie si la lecture PDF est disponible.
        
        Returns:
            bool: True si PyMuPDF est disponible
        """
        return HAS_PYMUPDF
    
    def _clear_caches(self):
        """Nettoie les caches pour libérer la mémoire."""
        if len(self._page_cache) > self._max_cache_size:
            self._page_cache.clear()
        if len(self._text_cache) > self._max_cache_size:
            self._text_cache.clear()
    
    def _get_cache_key(self, pdf_path: Path, page_num: int) -> str:
        """Génère une clé de cache unique."""
        return f"{pdf_path.stem}_{page_num}"
    
    def get_pdf_info(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Récupère les informations détaillées d'un fichier PDF.
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            Dict[str, Any]: Informations détaillées du PDF
            
        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            PermissionError: Si pas de permission de lecture
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"Fichier PDF introuvable: {pdf_path}")
        
        if not pdf_path.is_file():
            raise ValueError(f"Le chemin ne correspond pas à un fichier: {pdf_path}")
        
        # Informations de base
        basic_info = {
            'file_name': pdf_path.name,
            'file_size_mb': round(pdf_path.stat().st_size / (1024 * 1024), 2),
            'can_process': False,
            'estimated_time_minutes': 0.0,
            'file_path': str(pdf_path.absolute())
        }
        
        if not self.can_read_pdf:
            basic_info['error'] = 'PyMuPDF non disponible'
            return basic_info
        
        try:
            with fitz.open(str(pdf_path)) as doc:
                # Informations du document
                basic_info.update({
                    'pages': len(doc),
                    'can_process': True,
                    'metadata': {
                        'title': doc.metadata.get('title', ''),
                        'author': doc.metadata.get('author', ''),
                        'subject': doc.metadata.get('subject', ''),
                        'creator': doc.metadata.get('creator', ''),
                        'creation_date': doc.metadata.get('creationDate', ''),
                        'modification_date': doc.metadata.get('modDate', '')
                    },
                    'estimated_time_minutes': round(len(doc) * 0.05, 2),
                    'file_format': 'PDF',
                    'version': doc.metadata.get('format', 'PDF')
                })
                
                # Analyse d'un échantillon de page
                sample_page = doc[0] if len(doc) > 0 else None
                if sample_page:
                    sample_text = sample_page.get_text()
                    basic_info.update({
                        'has_text': len(sample_text.strip()) > 100,
                        'sample_text_length': len(sample_text),
                        'sample_text_preview': sample_text[:200] + '...' if len(sample_text) > 200 else sample_text,
                        'text_density': round(len(sample_text) / max(sample_page.rect.width * sample_page.rect.height, 1), 4)
                    })
                
        except Exception as e:
            basic_info['error'] = str(e)
            self.logger.error(f"Erreur lecture info PDF: {e}")
            self.stats['errors'] += 1
        
        return basic_info
    
    def read_pdf_file(self, pdf_path: Union[str, Path], 
                     max_pages: Optional[int] = None,
                     page_range: Optional[Tuple[int, int]] = None,
                     progress_callback: Optional[Callable] = None) -> str:
        """
        Lit et extrait le texte d'un fichier PDF avec optimisations.
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            max_pages: Nombre maximum de pages à traiter
            page_range: Plage de pages spécifique (début, fin)
            progress_callback: Fonction de callback pour le progrès
            
        Returns:
            str: Texte extrait du PDF
            
        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ImportError: Si PyMuPDF n'est pas disponible
            ValueError: Si la plage de pages est invalide
        """
        start_time = time.time()
        pdf_path = Path(pdf_path)
        
        # Validation du fichier
        if not pdf_path.exists():
            raise FileNotFoundError(f"Fichier PDF introuvable: {pdf_path}")
        
        if not pdf_path.is_file():
            raise ValueError(f"Le chemin ne correspond pas à un fichier: {pdf_path}")
        
        if not self.can_read_pdf:
            raise ImportError("PyMuPDF requis mais non disponible. Installez avec: pip install PyMuPDF")
        
        self.logger.info(f"📖 Lecture PDF: {pdf_path.name}")
        
        try:
            with fitz.open(str(pdf_path)) as doc:
                total_pages = len(doc)
                self.logger.info(f"📄 Document: {total_pages} pages")
                
                # Calcul de la plage de pages
                start_page, end_page = self._calculate_page_range(
                    total_pages, max_pages, page_range)
                
                self.logger.info(f"🎯 Traitement pages {start_page + 1} à {end_page}")
                
                # Traitement optimisé par blocs
                text_parts = []
                pages_processed = 0
                total_chars = 0
                
                # Traitement par blocs pour optimiser la mémoire
                block_size = min(50, end_page - start_page)  # 50 pages par bloc
                
                for block_start in range(start_page, end_page, block_size):
                    block_end = min(block_start + block_size, end_page)
                    
                    for page_num in range(block_start, block_end):
                        try:
                            # Vérification du cache
                            cache_key = self._get_cache_key(pdf_path, page_num)
                            if cache_key in self._text_cache:
                                page_text = self._text_cache[cache_key]
                                self.stats['cache_hits'] += 1
                            else:
                                page = doc[page_num]
                                page_text = page.get_text()
                                self._text_cache[cache_key] = page_text
                                self.stats['cache_misses'] += 1
                            
                            if page_text.strip():
                                text_parts.append(f"\n--- PAGE {page_num + 1} ---\n")
                                text_parts.append(page_text)
                                total_chars += len(page_text)
                            else:
                                self.logger.warning(f"⚠️ Page {page_num + 1} sans texte")
                                self.stats['warnings'] += 1
                            
                            pages_processed += 1
                            
                            # Mise à jour du progrès
                            if progress_callback:
                                progress = (pages_processed / (end_page - start_page)) * 100
                                progress_callback(progress, page_num + 1, end_page)
                            
                            # Logs de progression
                            if pages_processed % 25 == 0:
                                self.logger.info(f"⏳ Progression: {pages_processed}/{end_page - start_page} pages")
                            
                        except Exception as e:
                            self.logger.error(f"❌ Erreur page {page_num + 1}: {e}")
                            self.stats['errors'] += 1
                            continue
                    
                    # Nettoyage du cache après chaque bloc
                    self._clear_caches()
                
                # Assemblage du texte final
                full_text = '\n'.join(text_parts)
                
                # Mise à jour des statistiques
                processing_time = time.time() - start_time
                self.stats.update({
                    'pages_processed': pages_processed,
                    'total_chars': total_chars,
                    'processing_time': processing_time,
                    'pages_per_second': pages_processed / max(processing_time, 0.001),
                    'chars_per_second': total_chars / max(processing_time, 0.001)
                })
                
                self.logger.info(
                    f"✅ PDF lu avec succès: {pages_processed} pages, "
                    f"{total_chars:,} caractères, "
                    f"{processing_time:.2f}s "
                    f"({self.stats['pages_per_second']:.1f} pages/s)"
                )
                
                return full_text
                
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"❌ Erreur lecture PDF: {e}")
            raise
    
    def _calculate_page_range(self, total_pages: int, 
                            max_pages: Optional[int],
                            page_range: Optional[Tuple[int, int]]) -> Tuple[int, int]:
        """
        Calcule la plage de pages à traiter (0-indexé).
        
        Args:
            total_pages: Nombre total de pages dans le document
            max_pages: Nombre maximum de pages à traiter
            page_range: Plage spécifique (début, fin) en 1-indexé
            
        Returns:
            Tuple[int, int]: Plage de pages (début, fin) en 0-indexé
            
        Raises:
            ValueError: Si la plage de pages est invalide
        """
        
        if page_range:
            start, end = page_range
            # Validation de la plage
            if start < 1 or end < start:
                raise ValueError(f"Plage invalide: {start}-{end}")
            
            # Convertir en 0-indexé et valider
            start_page = max(0, start - 1)
            end_page = min(total_pages, end)
        else:
            start_page = 0
            end_page = min(total_pages, max_pages) if max_pages else total_pages
        
        # Validation finale
        if start_page >= end_page:
            raise ValueError(f"Plage de pages invalide: {start_page + 1}-{end_page}")
        
        if start_page >= total_pages:
            raise ValueError(f"Page de début {start_page + 1} dépasse le nombre total de pages {total_pages}")
        
        return start_page, end_page
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Retourne les statistiques détaillées de traitement.
        
        Returns:
            Dict[str, Any]: Statistiques complètes avec métriques de performance
        """
        stats = self.stats.copy()
        
        # Calcul des métriques de performance
        if stats['processing_time'] > 0:
            stats['pages_per_second'] = round(stats['pages_processed'] / stats['processing_time'], 2)
            stats['chars_per_second'] = round(stats['total_chars'] / stats['processing_time'], 2)
            stats['avg_chars_per_page'] = round(stats['total_chars'] / max(stats['pages_processed'], 1), 2)
        
        # Métriques de cache
        total_cache_operations = stats['cache_hits'] + stats['cache_misses']
        if total_cache_operations > 0:
            stats['cache_hit_rate'] = round(stats['cache_hits'] / total_cache_operations * 100, 2)
        else:
            stats['cache_hit_rate'] = 0.0
        
        # Métriques de qualité
        if stats['pages_processed'] > 0:
            stats['error_rate'] = round(stats['errors'] / stats['pages_processed'] * 100, 2)
            stats['warning_rate'] = round(stats['warnings'] / stats['pages_processed'] * 100, 2)
        else:
            stats['error_rate'] = 0.0
            stats['warning_rate'] = 0.0
        
        # Informations sur la mémoire
        stats['cache_size'] = len(self._text_cache)
        stats['memory_usage_mb'] = round(
            (len(self._text_cache) * 1024 + len(self._page_cache) * 512) / (1024 * 1024), 2
        )
        
        return stats
    
    def reset_statistics(self):
        """Réinitialise toutes les statistiques."""
        self.stats = {
            'pages_processed': 0,
            'total_chars': 0,
            'processing_time': 0.0,
            'errors': 0,
            'warnings': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        self._clear_caches()

class EnhancedGenealogyParser:
    """
    Parseur généalogique principal avec intégration OCR complète.
    
    Cette classe est le cœur du système de traitement généalogique. Elle coordonne
    l'ensemble des parsers spécialisés pour extraire, normaliser et valider les
    informations des documents généalogiques français de l'Ancien Régime.
    
    Fonctionnalités principales:
    - Normalisation et correction OCR du texte
    - Extraction intelligente des noms de personnes
    - Reconnaissance des titres nobiliaires et religieux
    - Gestion des abréviations historiques
    - Validation chronologique des données
    - Cache intelligent pour optimiser les performances
    - Export multi-formats des résultats
    
    Attributes:
        logger: Logger pour les messages de diagnostic
        config: Configuration du parseur
        _text_parser: Parser de texte (lazy loading)
        _name_extractor: Extracteur de noms (lazy loading)
        _person_manager: Gestionnaire de personnes (lazy loading)
        stats: Statistiques de traitement
        _processing_cache: Cache pour optimiser les traitements répétitifs
    """
    
    def __init__(self, config_path: Optional[str] = None, 
                 logger: Optional[logging.Logger] = None):
        """
        Initialise le parseur généalogique.
        
        Args:
            config_path: Chemin vers le fichier de configuration (optionnel)
            logger: Logger personnalisé (optionnel)
            
        Raises:
            ValueError: Si la configuration est invalide
            OSError: Si le fichier de configuration ne peut être lu
        """
        self.logger = logger or LoggingSetup.get_logger(__name__)
        
        # Chargement et validation de la configuration
        try:
            self.config = self._load_config(config_path)
            self.config = Config.validate_config(self.config)
        except Exception as e:
            self.logger.error(f"Erreur de configuration: {e}")
            raise
        
        # Initialisation des composants (lazy loading)
        self._text_parser = None
        self._name_extractor = None  
        self._person_manager = None
        
        # Cache pour optimiser les traitements
        self._processing_cache = {}
        self._max_cache_size = 1000
        
        # Statistiques de traitement
        self.stats = {
            'documents_processed': 0,
            'total_persons': 0,
            'total_corrections': 0,
            'processing_time': 0.0,
            'errors_handled': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'ocr_corrections_applied': 0,
            'names_extracted': 0,
            'persons_created': 0
        }
        
        self.logger.info("🔧 Parseur généalogique initialisé")
        self.logger.debug(f"Configuration: {self.config}")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Charge la configuration depuis un fichier ou utilise les défauts.
        
        Args:
            config_path: Chemin vers le fichier de configuration (optionnel)
            
        Returns:
            Dict[str, Any]: Configuration chargée et validée
            
        Raises:
            OSError: Si le fichier de configuration ne peut être lu
            json.JSONDecodeError: Si le fichier JSON est malformé
        """
        
        # Configuration par défaut
        default_config = {
            'enable_ocr_corrections': Config.ENABLE_OCR_CORRECTIONS,
            'enable_validation': Config.ENABLE_VALIDATION,
            'cache_size': Config.CACHE_SIZE,
            'max_text_length': Config.MAX_TEXT_LENGTH,
            'chunk_size': Config.CHUNK_SIZE,
            'min_name_confidence': Config.MIN_NAME_CONFIDENCE,
            'min_date_confidence': Config.MIN_DATE_CONFIDENCE,
            'min_relationship_confidence': Config.MIN_RELATIONSHIP_CONFIDENCE,
            'progress_update_interval': Config.PROGRESS_UPDATE_INTERVAL,
            'memory_cleanup_threshold': Config.MEMORY_CLEANUP_THRESHOLD
        }
        
        # Chargement depuis fichier si spécifié
        if config_path:
            config_file = Path(config_path)
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        file_config = json.load(f)
                    
                    # Validation des clés de configuration
                    valid_keys = set(default_config.keys())
                    invalid_keys = set(file_config.keys()) - valid_keys
                    if invalid_keys:
                        self.logger.warning(f"Clés de configuration invalides ignorées: {invalid_keys}")
                    
                    # Mise à jour avec les valeurs du fichier
                    default_config.update({k: v for k, v in file_config.items() if k in valid_keys})
                    self.logger.info(f"📋 Configuration chargée: {config_path}")
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Erreur JSON dans le fichier de configuration: {e}")
                    raise
                except OSError as e:
                    self.logger.error(f"Erreur lecture fichier de configuration: {e}")
                    raise
            else:
                self.logger.warning(f"Fichier de configuration introuvable: {config_path}")
        
        return default_config
    
    def _clear_processing_cache(self):
        """Nettoie le cache de traitement pour libérer la mémoire."""
        if len(self._processing_cache) > self._max_cache_size:
            self._processing_cache.clear()
            self.logger.debug("Cache de traitement nettoyé")
    
    def _get_cache_key(self, text: str, operation: str) -> str:
        """Génère une clé de cache unique pour un texte et une opération."""
        content_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return f"{operation}_{content_hash[:16]}"
    
    def _update_stats(self, **kwargs):
        """Met à jour les statistiques de traitement."""
        for key, value in kwargs.items():
            if key in self.stats:
                if isinstance(value, (int, float)):
                    self.stats[key] += value
                else:
                    self.stats[key] = value
    
    @property
    def text_parser(self) -> 'TextParser':
        """
        Parser de texte avec lazy loading.
        
        Returns:
            TextParser: Instance du parser de texte
            
        Raises:
            ImportError: Si les modules parsers ne sont pas disponibles
        """
        if not HAS_PARSERS:
            raise ImportError("Modules parsers non disponibles")
        
        if self._text_parser is None:
            try:
                self._text_parser = TextParser(self.config)
                self.logger.debug("📝 TextParser initialisé")
            except Exception as e:
                self.logger.error(f"Erreur initialisation TextParser: {e}")
                raise
        
        return self._text_parser
    
    @property
    def name_extractor(self) -> 'NameExtractor':
        """
        Extracteur de noms avec lazy loading.
        
        Returns:
            NameExtractor: Instance de l'extracteur de noms
            
        Raises:
            ImportError: Si les modules parsers ne sont pas disponibles
        """
        if not HAS_PARSERS:
            raise ImportError("Modules parsers non disponibles")
        
        if self._name_extractor is None:
            try:
                self._name_extractor = NameExtractor(self.config)
                self.logger.debug("👤 NameExtractor initialisé")
            except Exception as e:
                self.logger.error(f"Erreur initialisation NameExtractor: {e}")
                raise
        
        return self._name_extractor
    
    @property  
    def person_manager(self) -> 'PersonManager':
        """
        Gestionnaire de personnes avec lazy loading.
        
        Returns:
            PersonManager: Instance du gestionnaire de personnes
            
        Raises:
            ImportError: Si les modules parsers ne sont pas disponibles
        """
        if not HAS_PARSERS:
            raise ImportError("Modules parsers non disponibles")
        
        if self._person_manager is None:
            try:
                cache_size = self.config.get('cache_size', Config.CACHE_SIZE)
                self._person_manager = PersonManager(cache_size)
                self.logger.debug("🏛️ PersonManager initialisé")
            except Exception as e:
                self.logger.error(f"Erreur initialisation PersonManager: {e}")
                raise
        
        return self._person_manager
    
    def process_document(self, text: str, 
                        source_info: Optional[Dict[str, Any]] = None,
                        progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Traite un document généalogique complet avec optimisations.
        
        Cette méthode coordonne l'ensemble du processus de traitement :
        1. Normalisation et correction OCR du texte
        2. Segmentation du document en sections logiques
        3. Extraction des noms de personnes
        4. Création et gestion des entités personnes
        5. Validation et enrichissement des données
        
        Args:
            text: Texte du document à traiter
            source_info: Informations sur la source du document
            progress_callback: Fonction de callback pour le progrès
            
        Returns:
            Dict[str, Any]: Rapport complet de traitement
            
        Raises:
            ValueError: Si le texte est vide ou invalide
            RuntimeError: Si une erreur critique survient pendant le traitement
        """
        start_time = time.time()
        
        # Validation du texte d'entrée
        if not text or not text.strip():
            raise ValueError("Le texte à traiter ne peut pas être vide")
        
        # Informations de source par défaut
        source_info = source_info or {
            'lieu': 'Document généalogique',
            'type': 'registre_paroissial',
            'date_traitement': datetime.now().isoformat(),
            'source_id': hashlib.md5(text.encode('utf-8')).hexdigest()[:16]
        }
        
        self.logger.info(f"🚀 Début traitement: {source_info.get('lieu', 'Source inconnue')}")
        self.logger.debug(f"Longueur du texte: {len(text):,} caractères")
        
        try:
            # Validation et troncature du texte si nécessaire
            if len(text) > self.config['max_text_length']:
                original_length = len(text)
                text = text[:self.config['max_text_length']]
                self.logger.warning(
                    f"Texte tronqué: {original_length:,} → {len(text):,} caractères "
                    f"(limite: {self.config['max_text_length']:,})"
                )
            
            # Initialisation du rapport de traitement
            report = {
                'source_info': source_info,
                'processing_metadata': {
                    'start_time': datetime.now().isoformat(),
                    'text_length': len(text),
                    'enable_ocr': self.config['enable_ocr_corrections'],
                    'enable_validation': self.config['enable_validation'],
                    'parser_version': VERSION
                },
                'results': {},
                'statistics': {},
                'errors': [],
                'warnings': []
            }
            
            # === ÉTAPE 1: NORMALISATION DU TEXTE ===
            self._update_progress(progress_callback, 10, "Normalisation du texte...")
            
            try:
                # Vérification du cache pour la normalisation
                cache_key = self._get_cache_key(text, 'normalization')
                if cache_key in self._processing_cache:
                    norm_result = self._processing_cache[cache_key]
                    self.stats['cache_hits'] += 1
                    self.logger.debug("Normalisation récupérée du cache")
                else:
                    if HAS_PARSERS:
                        norm_result = self.text_parser.normalize_text(text)
                        self._processing_cache[cache_key] = norm_result
                        self.stats['cache_misses'] += 1
                    else:
                        norm_result = {
                            'normalized': text,
                            'ocr_corrections': [],
                            'abbreviations_expanded': [],
                            'improvement_ratio': 0.0
                        }
                        report['warnings'].append("Modules parsers non disponibles - normalisation basique")
                
                normalized_text = norm_result['normalized']
                
                # Enrichissement du rapport
                report['results']['text_normalization'] = {
                    'ocr_corrections': norm_result.get('ocr_corrections', []),
                    'abbreviations_expanded': norm_result.get('abbreviations_expanded', []),
                    'improvement_ratio': norm_result.get('improvement_ratio', 0.0),
                    'original_length': norm_result.get('original_length', len(text)),
                    'final_length': norm_result.get('final_length', len(normalized_text)),
                    'compression_ratio': norm_result.get('compression_ratio', 1.0)
                }
                
                # Mise à jour des statistiques
                ocr_corrections_count = len(norm_result.get('ocr_corrections', []))
                self._update_stats(
                    total_corrections=ocr_corrections_count,
                    ocr_corrections_applied=ocr_corrections_count
                )
                
                self.logger.info(
                    f"📝 Normalisation terminée: {len(normalized_text):,} caractères, "
                    f"{ocr_corrections_count} corrections OCR"
                )
                
            except Exception as e:
                self.logger.error(f"❌ Erreur normalisation: {e}")
                normalized_text = text
                report['errors'].append(f"Normalisation: {str(e)}")
                self._update_stats(errors_handled=1)
            
            # === ÉTAPE 2: SEGMENTATION ===
            self._update_progress(progress_callback, 25, "Segmentation du document...")
            
            try:
                # Cache pour la segmentation
                cache_key = self._get_cache_key(normalized_text, 'segmentation')
                if cache_key in self._processing_cache:
                    segments = self._processing_cache[cache_key]
                    self.stats['cache_hits'] += 1
                else:
                    if HAS_PARSERS:
                        segments = self.text_parser.extract_segments(normalized_text)
                        self._processing_cache[cache_key] = segments
                        self.stats['cache_misses'] += 1
                    else:
                        segments = [{'type': 'text', 'content': normalized_text}]
                        report['warnings'].append("Modules parsers non disponibles - segmentation basique")
                
                # Analyse des segments
                segments_by_type = self._count_segments_by_type(segments)
                total_segments = len(segments)
                
                report['results']['segmentation'] = {
                    'total_segments': total_segments,
                    'segments_by_type': segments_by_type,
                    'avg_segment_length': sum(len(s.get('text', '')) for s in segments) / max(total_segments, 1),
                    'quality_distribution': self._analyze_segment_quality(segments)
                }
                
                self.logger.info(f"📋 Segmentation terminée: {total_segments} segments")
                
            except Exception as e:
                self.logger.error(f"❌ Erreur segmentation: {e}")
                segments = [{'type': 'text', 'content': normalized_text}]
                report['errors'].append(f"Segmentation: {str(e)}")
                self._update_stats(errors_handled=1)
            
            # === ÉTAPE 3: EXTRACTION DES NOMS ===
            self._update_progress(progress_callback, 50, "Extraction des noms...")
            
            try:
                # Cache pour l'extraction des noms
                cache_key = self._get_cache_key(normalized_text, 'name_extraction')
                if cache_key in self._processing_cache:
                    persons_data = self._processing_cache[cache_key]
                    self.stats['cache_hits'] += 1
                else:
                    if HAS_PARSERS:
                        persons_data = self.name_extractor.extract_names(normalized_text)
                        self._processing_cache[cache_key] = persons_data
                        self.stats['cache_misses'] += 1
                    else:
                        persons_data = []
                        report['warnings'].append("Modules parsers non disponibles - extraction basique")
                
                # Analyse des noms extraits
                total_names = len(persons_data)
                names_with_corrections = sum(1 for p in persons_data if p.get('ocr_corrected', False))
                high_confidence_names = sum(1 for p in persons_data if p.get('confidence', 0) > 0.8)
                
                report['results']['name_extraction'] = {
                    'total_names': total_names,
                    'names_with_corrections': names_with_corrections,
                    'high_confidence_names': high_confidence_names,
                    'avg_confidence': sum(p.get('confidence', 0) for p in persons_data) / max(total_names, 1),
                    'sample_names': [p['full_name'] for p in persons_data[:10]],
                    'name_types': self._analyze_name_types(persons_data)
                }
                
                self._update_stats(names_extracted=total_names)
                
                self.logger.info(
                    f"👥 Extraction terminée: {total_names} noms, "
                    f"{names_with_corrections} corrigés, "
                    f"{high_confidence_names} haute confiance"
                )
                
            except Exception as e:
                self.logger.error(f"❌ Erreur extraction noms: {e}")
                persons_data = []
                report['errors'].append(f"Extraction noms: {str(e)}")
                self._update_stats(errors_handled=1)
            
            # === ÉTAPE 4: CRÉATION DES PERSONNES ===
            self._update_progress(progress_callback, 75, "Création des personnes...")
            
            created_persons = []
            try:
                if HAS_PARSERS and persons_data:
                    # Traitement par lots pour optimiser les performances
                    batch_size = 50
                    total_batches = (len(persons_data) + batch_size - 1) // batch_size
                    
                    for batch_idx in range(total_batches):
                        start_idx = batch_idx * batch_size
                        end_idx = min(start_idx + batch_size, len(persons_data))
                        batch_data = persons_data[start_idx:end_idx]
                        
                        for person_data in batch_data:
                            try:
                                # Validation des données de la personne
                                if not person_data.get('full_name'):
                                    continue
                                
                                person = self.person_manager.find_or_create_person(
                                    person_data['full_name'],
                                    {
                                        'source': source_info.get('lieu', 'Source'),
                                        'extraction_data': person_data,
                                        'source_id': source_info.get('source_id', ''),
                                        'extraction_confidence': person_data.get('confidence', 0.0)
                                    }
                                )
                                created_persons.append(person)
                                
                            except Exception as e:
                                self.logger.warning(f"⚠️ Erreur création personne '{person_data.get('full_name', 'N/A')}': {e}")
                                continue
                        
                        # Mise à jour du progrès pour les lots
                        if progress_callback:
                            batch_progress = 75 + (batch_idx + 1) / total_batches * 15
                            progress_callback(batch_progress, f"Lot {batch_idx + 1}/{total_batches}")
                    
                    # Statistiques du gestionnaire de personnes
                    person_stats = self.person_manager.get_enhanced_statistics()
                    
                    report['results']['person_creation'] = {
                        'total_persons': len(created_persons),
                        'persons_created': len([p for p in created_persons if p.id_personne]),
                        'persons_found': len([p for p in created_persons if not p.id_personne]),
                        'cache_statistics': person_stats,
                        'avg_confidence': sum(p.confiance for p in created_persons) / max(len(created_persons), 1)
                    }
                    
                    self._update_stats(persons_created=len(created_persons))
                    
                    self.logger.info(
                        f"🏛️ Création terminée: {len(created_persons)} personnes "
                        f"({person_stats.get('total_persons', 0)} total en cache)"
                    )
                else:
                    report['results']['person_creation'] = {
                        'status': 'no_data_or_parsers_unavailable',
                        'total_persons': 0
                    }
                    report['warnings'].append("Aucune donnée de personne à traiter")
                
            except Exception as e:
                self.logger.error(f"❌ Erreur création personnes: {e}")
                report['errors'].append(f"Création personnes: {str(e)}")
                self._update_stats(errors_handled=1)
            
            # === FINALISATION ===
            self._update_progress(progress_callback, 90, "Finalisation...")
            
            processing_time = time.time() - start_time
            
            # Mise à jour des statistiques globales
            self._update_stats(
                documents_processed=1,
                total_persons=len(created_persons),
                processing_time=processing_time
            )
            
            # Nettoyage du cache si nécessaire
            if self.stats['documents_processed'] % self.config.get('memory_cleanup_threshold', 1000) == 0:
                self._clear_processing_cache()
                self.logger.debug("Nettoyage périodique du cache effectué")
            
            # Finalisation du rapport
            report['processing_metadata'].update({
                'end_time': datetime.now().isoformat(),
                'processing_time_seconds': round(processing_time, 3),
                'errors_count': len(report['errors']),
                'warnings_count': len(report['warnings']),
                'success_rate': self._calculate_success_rate(report)
            })
            
            # Génération des statistiques détaillées
            report['statistics'] = self._generate_processing_statistics()
            
            # Validation finale des résultats
            if self.config.get('enable_validation', True):
                validation_result = self._validate_results(report)
                report['validation'] = validation_result
            
            self._update_progress(progress_callback, 100, "Traitement terminé!")
            
            self.logger.info(
                f"✅ Traitement terminé en {processing_time:.2f}s - "
                f"{len(created_persons)} personnes, "
                f"{len(report['errors'])} erreurs, "
                f"{len(report['warnings'])} avertissements"
            )
            
            return report
            
        except Exception as e:
            self._update_stats(errors_handled=1)
            self.logger.error(f"❌ Erreur critique traitement: {e}")
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _count_segments_by_type(self, segments: List[Dict]) -> Dict[str, int]:
        """
        Compte les segments par type.
        
        Args:
            segments: Liste des segments à analyser
            
        Returns:
            Dict[str, int]: Comptage par type de segment
        """
        counts = defaultdict(int)
        for segment in segments:
            seg_type = segment.get('type', 'unknown')
            counts[seg_type] += 1
        return dict(counts)
    
    def _analyze_segment_quality(self, segments: List[Dict]) -> Dict[str, Any]:
        """
        Analyse la qualité des segments.
        
        Args:
            segments: Liste des segments à analyser
            
        Returns:
            Dict[str, Any]: Analyse de la qualité
        """
        if not segments:
            return {'avg_quality': 0.0, 'quality_distribution': {}}
        
        qualities = [s.get('quality_score', 0.0) for s in segments]
        avg_quality = sum(qualities) / len(qualities)
        
        # Distribution de qualité
        quality_ranges = {
            'excellent': len([q for q in qualities if q >= 0.8]),
            'good': len([q for q in qualities if 0.6 <= q < 0.8]),
            'fair': len([q for q in qualities if 0.4 <= q < 0.6]),
            'poor': len([q for q in qualities if q < 0.4])
        }
        
        return {
            'avg_quality': round(avg_quality, 3),
            'quality_distribution': quality_ranges,
            'total_segments': len(segments)
        }
    
    def _analyze_name_types(self, persons_data: List[Dict]) -> Dict[str, int]:
        """
        Analyse les types de noms extraits.
        
        Args:
            persons_data: Données des personnes extraites
            
        Returns:
            Dict[str, int]: Comptage par type de nom
        """
        name_types = defaultdict(int)
        
        for person in persons_data:
            name_type = person.get('name_type', 'unknown')
            name_types[name_type] += 1
            
            # Analyse des titres
            if person.get('has_noble_title'):
                name_types['noble'] += 1
            if person.get('has_religious_title'):
                name_types['religious'] += 1
        
        return dict(name_types)
    
    def _update_progress(self, callback: Optional[Callable], 
                        progress: int, message: str):
        """
        Met à jour le progrès si callback fourni.
        
        Args:
            callback: Fonction de callback pour le progrès
            progress: Pourcentage de progression (0-100)
            message: Message descriptif
        """
        if callback and callable(callback):
            try:
                callback(progress, message)
            except Exception as e:
                self.logger.debug(f"Erreur callback progrès: {e}")
    
    def _calculate_success_rate(self, report: Dict[str, Any]) -> float:
        """
        Calcule le taux de succès du traitement.
        
        Args:
            report: Rapport de traitement
            
        Returns:
            float: Taux de succès (0.0 à 1.0)
        """
        total_operations = 0
        successful_operations = 0
        
        # Normalisation
        if 'text_normalization' in report['results']:
            total_operations += 1
            if not report['results']['text_normalization'].get('errors'):
                successful_operations += 1
        
        # Segmentation
        if 'segmentation' in report['results']:
            total_operations += 1
            if report['results']['segmentation'].get('total_segments', 0) > 0:
                successful_operations += 1
        
        # Extraction des noms
        if 'name_extraction' in report['results']:
            total_operations += 1
            if report['results']['name_extraction'].get('total_names', 0) > 0:
                successful_operations += 1
        
        # Création des personnes
        if 'person_creation' in report['results']:
            total_operations += 1
            if report['results']['person_creation'].get('total_persons', 0) > 0:
                successful_operations += 1
        
        return round(successful_operations / max(total_operations, 1), 3)
    
    def _validate_results(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide les résultats du traitement.
        
        Args:
            report: Rapport de traitement
            
        Returns:
            Dict[str, Any]: Résultats de validation
        """
        validation = {
            'is_valid': True,
            'issues': [],
            'recommendations': []
        }
        
        # Validation de la normalisation
        if 'text_normalization' in report['results']:
            norm = report['results']['text_normalization']
            if norm.get('improvement_ratio', 0) < 0.1:
                validation['issues'].append("Faible amélioration du texte")
                validation['recommendations'].append("Vérifier la qualité OCR du document source")
        
        # Validation de l'extraction des noms
        if 'name_extraction' in report['results']:
            names = report['results']['name_extraction']
            if names.get('total_names', 0) == 0:
                validation['issues'].append("Aucun nom extrait")
                validation['recommendations'].append("Vérifier le contenu du document")
            elif names.get('avg_confidence', 0) < 0.6:
                validation['issues'].append("Confiance moyenne faible pour les noms")
                validation['recommendations'].append("Améliorer la qualité du texte source")
        
        # Validation de la création des personnes
        if 'person_creation' in report['results']:
            persons = report['results']['person_creation']
            if persons.get('total_persons', 0) == 0:
                validation['issues'].append("Aucune personne créée")
                validation['recommendations'].append("Vérifier l'extraction des noms")
        
        # Validation globale
        if validation['issues']:
            validation['is_valid'] = False
        
        return validation
    
    def _generate_processing_statistics(self) -> Dict[str, Any]:
        """
        Génère des statistiques détaillées du traitement.
        
        Returns:
            Dict[str, Any]: Statistiques complètes
        """
        
        base_stats = {
            'global': self.stats.copy(),
            'performance': {
                'avg_processing_time': round(
                    self.stats['processing_time'] / max(self.stats['documents_processed'], 1), 3
                ),
                'corrections_per_document': round(
                    self.stats['total_corrections'] / max(self.stats['documents_processed'], 1), 2
                ),
                'persons_per_document': round(
                    self.stats['total_persons'] / max(self.stats['documents_processed'], 1), 2
                ),
                'cache_efficiency': round(
                    self.stats['cache_hits'] / max(self.stats['cache_hits'] + self.stats['cache_misses'], 1) * 100, 2
                )
            },
            'quality_metrics': {
                'error_rate': round(
                    self.stats['errors_handled'] / max(self.stats['documents_processed'], 1) * 100, 2
                ),
                'ocr_correction_rate': round(
                    self.stats['ocr_corrections_applied'] / max(self.stats['total_corrections'], 1) * 100, 2
                )
            }
        }
        
        # Statistiques des parsers si disponibles
        if HAS_PARSERS:
            try:
                if self._text_parser:
                    base_stats['text_parser'] = self._text_parser.get_stats()
                if self._person_manager:
                    base_stats['person_manager'] = self._person_manager.get_enhanced_statistics()
            except Exception as e:
                self.logger.debug(f"Erreur récupération stats parsers: {e}")
        
        return base_stats
    
    def export_results(self, report: Dict[str, Any], 
                      output_dir: Path, 
                      formats: List[str] = None) -> Dict[str, str]:
        formats = formats or ['json']
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created_files = {}
        
        for format_type in formats:
            try:
                if format_type == 'json':
                    file_path = output_dir / f"rapport_genealogique_{timestamp}.json"
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
                    created_files['json'] = str(file_path)
                
                elif format_type == 'txt':
                    file_path = output_dir / f"rapport_genealogique_{timestamp}.txt"
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(self._format_report_as_text(report))
                    created_files['txt'] = str(file_path)
                
                elif format_type == 'gedcom':
                    # Placeholder pour export GEDCOM futur
                    self.logger.info("Export GEDCOM non encore implémenté")
                
            except Exception as e:
                self.logger.error(f"Erreur export {format_type}: {e}")
        
        return created_files
    
    def _format_report_as_text(self, report: Dict[str, Any]) -> str:
        """Formate le rapport en texte lisible"""
        
        lines = [
            "=" * 80,
            "RAPPORT D'ANALYSE GÉNÉALOGIQUE",
            "=" * 80,
            "",
            f"📅 Date: {report['processing_metadata'].get('start_time', 'N/A')}",
            f"📍 Source: {report['source_info'].get('lieu', 'N/A')}",
            f"⏱️ Temps traitement: {report['processing_metadata'].get('processing_time_seconds', 0):.2f}s",
            "",
            "🔍 RÉSULTATS D'EXTRACTION:",
            ""
        ]
        
        # Normalisation du texte
        if 'text_normalization' in report['results']:
            norm = report['results']['text_normalization']
            ocr_count = len(norm.get('ocr_corrections', []))
            abbrev_count = len(norm.get('abbreviations_expanded', []))
            
            lines.extend([
                f"   📝 Corrections OCR appliquées: {ocr_count}",
                f"   📖 Abréviations développées: {abbrev_count}",
                f"   📊 Ratio d'amélioration: {norm.get('improvement_ratio', 0):.2%}",
                ""
            ])
        
        # Extraction des noms
        if 'name_extraction' in report['results']:
            names = report['results']['name_extraction']
            total = names.get('total_names', 0)
            corrected = names.get('names_with_corrections', 0)
            
            lines.extend([
                f"   👥 Noms extraits: {total}",
                f"   ✅ Noms corrigés: {corrected}",
                ""
            ])
            
            # Échantillon de noms
            if names.get('sample_names'):
                lines.append("   📋 Échantillon de noms:")
                for name in names['sample_names']:
                    lines.append(f"      • {name}")
                lines.append("")
        
        # Statistiques
        if 'statistics' in report:
            stats = report['statistics']
            if 'global' in stats:
                glob_stats = stats['global']
                lines.extend([
                    "📊 STATISTIQUES:",
                    "",
                    f"   📄 Documents traités: {glob_stats.get('documents_processed', 0)}",
                    f"   👥 Personnes totales: {glob_stats.get('total_persons', 0)}",
                    f"   🔧 Corrections totales: {glob_stats.get('total_corrections', 0)}",
                    f"   ⚠️ Erreurs gérées: {glob_stats.get('errors_handled', 0)}",
                    ""
                ])
        
        # Erreurs
        if report.get('errors'):
            lines.extend([
                "⚠️ ERREURS RENCONTRÉES:",
                ""
            ])
            for error in report['errors']:
                lines.append(f"   • {error}")
            lines.append("")
        
        lines.extend([
            "=" * 80,
            "Fin du rapport",
            "=" * 80
        ])
        
        return '\n'.join(lines)

# === UTILITAIRES ===

class ProgressTracker:
    """Gestionnaire de progression pour les opérations longues"""
    
    def __init__(self, show_progress: bool = True):
        self.show_progress = show_progress
        self.start_time = time.time()
        self.last_update = 0
    
    def update(self, progress: int, message: str = ""):
        """Met à jour la progression"""
        if not self.show_progress:
            return
        
        # Limiter les mises à jour trop fréquentes
        current_time = time.time()
        if current_time - self.last_update < 0.5 and progress != 100:
            return
        
        self.last_update = current_time
        elapsed = current_time - self.start_time
        
        # Barre de progression simple
        bar_length = 30
        filled_length = int(bar_length * progress // 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        print(f'\r⏳ [{bar}] {progress:3d}% {message} ({elapsed:.1f}s)', end='', flush=True)
        
        if progress >= 100:
            print()  # Nouvelle ligne à la fin

@contextmanager
def safe_file_operation(file_path: Union[str, Path], operation: str = "operation"):
    """Context manager pour opérations fichier sécurisées"""
    try:
        yield
    except FileNotFoundError:
        print(f"❌ Fichier non trouvé pour {operation}: {file_path}")
    except PermissionError:
        print(f"❌ Permission refusée pour {operation}: {file_path}")
    except Exception as e:
        print(f"❌ Erreur {operation}: {e}")

# === FONCTION PRINCIPALE ===

def create_argument_parser() -> argparse.ArgumentParser:
    """Crée le parser d'arguments de ligne de commande"""
    
    parser = argparse.ArgumentParser(
        description='Parseur généalogique avancé pour registres paroissiaux',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python main.py document.pdf                           # Traitement PDF complet
  python main.py document.txt -o resultats/             # Fichier texte avec sortie personnalisée
  python main.py document.pdf --pdf-pages 50           # Limiter à 50 pages
  python main.py document.pdf --pdf-range 10-30        # Pages 10 à 30
  python main.py demo                                   # Mode démonstration
  python main.py --test                                 # Tests intégrés

Formats supportés: .pdf, .txt, .md, .rtf
        """
    )
    
    # Fichier d'entrée
    parser.add_argument(
        'input_file', 
        nargs='?',
        help='Fichier à analyser (PDF, TXT) ou "demo" pour démonstration'
    )
    
    # Options de sortie
    output_group = parser.add_argument_group('Options de sortie')
    output_group.add_argument(
        '-o', '--output', 
        type=str, 
        default='output',
        help='Répertoire de sortie (défaut: ./output)'
    )
    output_group.add_argument(
        '--formats', 
        nargs='+', 
        choices=['json', 'txt', 'gedcom'],
        default=['txt'],
        help='Formats d\'export (défaut: txt)'
    )
    
    # Options PDF
    pdf_group = parser.add_argument_group('Options PDF')
    pdf_group.add_argument(
        '--pdf-pages', 
        type=int, 
        help='Nombre maximum de pages PDF à traiter'
    )
    pdf_group.add_argument(
        '--pdf-range', 
        type=str, 
        help='Plage de pages PDF (ex: 10-50)'
    )
    pdf_group.add_argument(
        '--pdf-info', 
        action='store_true',
        help='Afficher uniquement les informations du PDF'
    )
    
    # Options de traitement
    processing_group = parser.add_argument_group('Options de traitement')
    processing_group.add_argument(
        '--no-ocr', 
        action='store_true',
        help='Désactiver les corrections OCR'
    )
    processing_group.add_argument(
        '--config', 
        type=str,
        help='Fichier de configuration personnalisé'
    )
    processing_group.add_argument(
        '--chunk-size', 
        type=int, 
        default=Config.CHUNK_SIZE,
        help=f'Taille des chunks de traitement (défaut: {Config.CHUNK_SIZE})'
    )
    
    # Options de logging
    logging_group = parser.add_argument_group('Options de logging')
    logging_group.add_argument(
        '-v', '--verbose', 
        action='store_true',
        help='Mode verbeux (debug)'
    )
    logging_group.add_argument(
        '--log-file', 
        type=str,
        help='Fichier de log personnalisé'
    )
    logging_group.add_argument(
        '--no-progress', 
        action='store_true',
        help='Désactiver l\'affichage du progrès'
    )
    
    # Options spéciales
    special_group = parser.add_argument_group('Options spéciales')
    special_group.add_argument(
        '--test', 
        action='store_true',
        help='Lancer les tests intégrés'
    )
    special_group.add_argument(
        '--check-deps', 
        action='store_true',
        help='Vérifier les dépendances'
    )
    
    return parser

def check_dependencies() -> Dict[str, bool]:
    """Vérifie les dépendances du système"""
    
    deps = {
        'PyMuPDF (PDF)': HAS_PYMUPDF,
        'Parsers Garméa': HAS_PARSERS
    }
    
    print("🔍 VÉRIFICATION DES DÉPENDANCES")
    print("=" * 40)
    
    all_ok = True
    for name, available in deps.items():
        status = "✅ Disponible" if available else "❌ Manquant"
        print(f"{name:20} : {status}")
        if not available:
            all_ok = False
    
    print()
    
    if not all_ok:
        print("⚠️  INSTRUCTIONS D'INSTALLATION:")
        if not HAS_PYMUPDF:
            print("   pip install PyMuPDF")
        if not HAS_PARSERS:
            print("   Vérifiez que les modules parsers sont dans le PYTHONPATH")
    else:
        print("✅ Toutes les dépendances sont disponibles!")
    
    return deps

def run_integrated_tests() -> bool:
    print("🧪 TESTS INTÉGRÉS")
    print("=" * 40)
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Configuration
    total_tests += 1
    try:
        config = Config()
        assert hasattr(config, 'MAX_PDF_PAGES')
        print("✅ Test configuration")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Test configuration: {e}")
    
    # Test 2: Logging
    total_tests += 1
    try:
        logger = LoggingSetup.setup_logging(verbose=False)
        logger.info("Test log")
        print("✅ Test logging")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Test logging: {e}")
    
    # Test 3: PDF Reader (si disponible)
    if HAS_PYMUPDF:
        total_tests += 1
        try:
            pdf_reader = EnhancedPDFReader()
            assert pdf_reader.can_read_pdf
            print("✅ Test PDF reader")
            tests_passed += 1
        except Exception as e:
            print(f"❌ Test PDF reader: {e}")
    
    # Test 4: Parser principal
    total_tests += 1
    try:
        parser = EnhancedGenealogyParser()
        assert hasattr(parser, 'process_document')
        print("✅ Test parser principal")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Test parser principal: {e}")
    
    print(f"\n📊 Résultats: {tests_passed}/{total_tests} tests réussis")
    return tests_passed == total_tests

def run_demo() -> Dict[str, Any]:
    """Lance une démonstration avec exemple de texte"""
    
    print("🎭 MODE DÉMONSTRATION")
    print("=" * 50)
    
    # Texte d'exemple enrichi
    sample_text = """
    1643-1687. — Registres de baptêmes, mariages et sépultures de Notre-Dame d'Esméville.
    
    « L'an de grâce 1643, le dimanche 8e jour de mars, moy, Charles Demontigny, prestre, 
    ay, au nom de Dieu, pris possession du bénéfice Notre-Dame d'Esméville, sans aucune opposition. »
    
    — 1646, 13 fév., décès de Jean Le Boucher, écuyer, sieur de Bréville. Le 14, inhumation 
    dans l'église.
    
    — 1651, 23 janv., inh., dans l'église, de Françoise Picot, épouse de Charles Le Boucher, 
    écuyer, sieur du Hausey, avocat du Roi au siège de Saint-Sylvain.
    
    — 24 oct. 1651, naissance et bapt. de Charlotte, fille de Jean Le Boucher, écuyer, 
    sieur de La Granville, et de Françoise Varin; marraine: Perrette Dupré; 
    parrain: Charles Le Boucher, écuyer, sieur du Hozey, conseiller et avocat du Roi.
    
    — 1655, 15 mars, mariage de Pierre Martin, fils de Jean Martin, laboureur, 
    avec Marie Durand, fille de Nicolas Durand, marchand.
    """
    
    print("Texte d'exemple:")
    print("-" * 50)
    print(sample_text[:300] + "..." if len(sample_text) > 300 else sample_text)
    print("-" * 50)
    
    try:
        parser = EnhancedGenealogyParser()
        
        source_info = {
            'lieu': 'Notre-Dame d\'Esméville',
            'type': 'demo',
            'periode': '1643-1687'
        }
        
        progress = ProgressTracker(show_progress=True)
        
        print("\nTraitement en cours...")
        report = parser.process_document(
            sample_text, 
            source_info,
            progress_callback=progress.update
        )
        
        print("\nRÉSULTATS:")
        print("=" * 30)
        
        if 'text_normalization' in report['results']:
            norm = report['results']['text_normalization']
            print(f"Corrections OCR: {len(norm.get('ocr_corrections', []))}")
            print(f"Abréviations: {len(norm.get('abbreviations_expanded', []))}")
        
        if 'name_extraction' in report['results']:
            names = report['results']['name_extraction']
            print(f"👥 Noms extraits: {names.get('total_names', 0)}")
            
            # Afficher quelques noms
            sample_names = names.get('sample_names', [])[:5]
            if sample_names:
                print("\nNoms trouvés:")
                for name in sample_names:
                    print(f"   • {name}")
        
        processing_time = report['processing_metadata'].get('processing_time_seconds', 0)
        print(f"\n⏱Temps de traitement: {processing_time:.2f}s")
        
        return report
        
    except Exception as e:
        print(f"Erreur démonstration: {e}")
        if '--verbose' in sys.argv:
            traceback.print_exc()
        return {'error': str(e)}

def main():
    parser = create_argument_parser()
    args = parser.parse_args()
    log_file = args.log_file or Config.DEFAULT_LOGS_DIR / "genealogy_parser.log"
    logger = LoggingSetup.setup_logging(args.verbose, log_file)
    
    if args.check_deps:
        check_dependencies()
        return
    
    if args.test:
        success = run_integrated_tests()
        sys.exit(0 if success else 1)
    
    if not args.input_file:
        print("Aucun fichier spécifié. Utilisez --help pour l'aide.")
        sys.exit(1)
    
    if args.input_file.lower() == 'demo':
        run_demo()
        return
    
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Fichier non trouvé: {input_path}")
        sys.exit(1)
    
    if input_path.suffix.lower() not in Config.get_all_supported_formats():
        print(f"❌ Format non supporté: {input_path.suffix}")
        print(f"Formats supportés: {', '.join(Config.get_all_supported_formats())}")
        sys.exit(1)
    
    # Création du répertoire de sortie
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"🚀 Démarrage traitement: {input_path.name}")
    
    try:
        # === LECTURE DU FICHIER ===
        
        text_content = ""
        source_info = {
            'fichier': input_path.name,
            'type': 'pdf' if input_path.suffix.lower() == '.pdf' else 'text',
            'taille_mb': input_path.stat().st_size / (1024 * 1024)
        }
        
        if input_path.suffix.lower() == '.pdf':
            # Traitement PDF
            pdf_reader = EnhancedPDFReader(logger)
            
            if not pdf_reader.can_read_pdf:
                print("❌ PyMuPDF non disponible pour lire les PDF")
                print("   Installation: pip install PyMuPDF")
                sys.exit(1)
            
            # Info PDF si demandé
            if args.pdf_info:
                info = pdf_reader.get_pdf_info(input_path)
                print("\n📋 INFORMATIONS PDF:")
                print("=" * 30)
                for key, value in info.items():
                    print(f"{key:20}: {value}")
                return
            
            # Options PDF
            pdf_options = {}
            if args.pdf_pages:
                pdf_options['max_pages'] = args.pdf_pages
            
            if args.pdf_range:
                try:
                    start, end = map(int, args.pdf_range.split('-'))
                    pdf_options['page_range'] = (start, end)
                except ValueError:
                    print(f"Format de plage invalide: {args.pdf_range}")
                    sys.exit(1)
            
            progress = ProgressTracker(not args.no_progress)
            print(f"Lecture PDF: {input_path.name}")
            text_content = pdf_reader.read_pdf_file(
                input_path, 
                progress_callback=progress.update,
                **pdf_options)
            
            pdf_stats = pdf_reader.get_statistics()
            logger.info(f"PDF traité: {pdf_stats['pages_processed']} pages")
            source_info.update(pdf_stats)
        
        else:
            print(f"Lecture fichier texte: {input_path.name}")
            with safe_file_operation(input_path, "lecture"):
                with open(input_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
        
        if not text_content.strip():
            print("Aucun contenu textuel extrait!")
            sys.exit(1)
        
        print(f"Contenu extrait: {len(text_content):,} caractères")
        config_overrides = {}
        if args.no_ocr:
            config_overrides['enable_ocr_corrections'] = False
        if args.chunk_size:
            config_overrides['chunk_size'] = args.chunk_size
        
        parser_instance = EnhancedGenealogyParser(args.config, logger)
        if config_overrides:
            parser_instance.config.update(config_overrides)
        progress = ProgressTracker(not args.no_progress)
        
        print(f"\n🔄 Traitement généalogique...")
        report = parser_instance.process_document(
            text_content,
            source_info,
            progress_callback=progress.update
        )
        
        print(f"\nExport des résultats...")
        created_files = parser_instance.export_results(
            report, 
            output_dir, 
            args.formats)
        
        print(f"\nRÉSULTATS:")
        print("=" * 50)
        
        if 'text_normalization' in report['results']:
            norm = report['results']['text_normalization']
            ocr_count = len(norm.get('ocr_corrections', []))
            abbrev_count = len(norm.get('abbreviations_expanded', []))
            print(f"Corrections OCR appliquées: {ocr_count}")
            print(f"Abréviations développées: {abbrev_count}")
        
        if 'name_extraction' in report['results']:
            names = report['results']['name_extraction']
            total_names = names.get('total_names', 0)
            corrected_names = names.get('names_with_corrections', 0)
            print(f"Noms extraits: {total_names}")
            print(f"Noms corrigés automatiquement: {corrected_names}")
        
        if 'person_creation' in report['results']:
            persons = report['results']['person_creation']
            total_persons = persons.get('total_persons', 0)
            print(f"Personnes créées: {total_persons}")
        
        processing_time = report['processing_metadata'].get('processing_time_seconds', 0)
        print(f"⏱Temps de traitement: {processing_time:.2f}s")
        
        if created_files:
            print(f"\nFichiers créés:")
            for format_type, file_path in created_files.items():
                print(f"   {format_type.upper()}: {file_path}")
        
        if report.get('errors'):
            print(f"\nErreurs rencontrées: {len(report['errors'])}")
            if args.verbose:
                for error in report['errors']:
                    print(f"   • {error}")
        
        if args.verbose:
            print(f"\nSTATISTIQUES DÉTAILLÉES:")
            print("-" * 30)
            stats = report.get('statistics', {})
            print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))
        
        print(f"\nTraitement terminé avec succès!")
        
    except KeyboardInterrupt:
        print(f"\n⏹Traitement interrompu par l'utilisateur")
        sys.exit(130)
    
    except Exception as e:
        logger.error(f"Erreur critique: {e}")
        print(f"\nErreur: {e}")
        
        if args.verbose:
            print("\n🔍 Détails de l'erreur:")
            traceback.print_exc()
        sys.exit(1)
if __name__ == "__main__":
    main()