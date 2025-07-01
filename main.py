#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py - Parseur généalogique principal pour registres paroissiaux
Version complètement corrigée et optimisée avec intégration OCR

Usage:
    python main.py [fichier] [options]
    python main.py demo  # Mode démonstration
    python main.py --help  # Aide complète

Auteur: Système Garméa - Parser Généalogique Avancé
Version: 3.0.0
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
from typing import Dict, List, Optional, Union, Any, Tuple
import warnings

# Configuration des warnings
warnings.filterwarnings('ignore', category=UserWarning)

# === IMPORTS CONDITIONNELS ===

# PyMuPDF pour PDF
try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

# Parsers Garméa (avec fallbacks si modules manquants)
try:
    from parsers.text_parser import TextParser
    from parsers.name_extractor import NameExtractor  
    from database.person_manager import PersonManager
    HAS_PARSERS = True
except ImportError as e:
    print(f"⚠️  Modules parsers manquants: {e}")
    HAS_PARSERS = False

# === CONFIGURATION ET CONSTANTES ===

class Config:
    """Configuration centralisée de l'application"""
    
    # Paths par défaut
    DEFAULT_OUTPUT_DIR = Path("output")
    DEFAULT_LOGS_DIR = Path("logs")
    DEFAULT_CONFIG_FILE = Path("config/settings.json")
    
    # Limites de traitement
    MAX_PDF_PAGES = 500
    MAX_TEXT_LENGTH = 1_000_000  # 1M caractères
    CHUNK_SIZE = 100_000  # Taille des chunks
    
    # Performance
    CACHE_SIZE = 5000
    ENABLE_OCR_CORRECTIONS = True
    ENABLE_VALIDATION = True
    
    # Formats supportés
    SUPPORTED_TEXT_FORMATS = {'.txt', '.md', '.rtf'}
    SUPPORTED_PDF_FORMATS = {'.pdf'}
    
    @classmethod
    def get_all_supported_formats(cls) -> set:
        """Retourne tous les formats supportés"""
        return cls.SUPPORTED_TEXT_FORMATS | cls.SUPPORTED_PDF_FORMATS

# === GESTION DU LOGGING ===

class LoggingSetup:
    """Configuration centralisée du logging"""
    
    @staticmethod
    def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> logging.Logger:
        """Configure le système de logging"""
        
        # Créer le répertoire de logs
        Config.DEFAULT_LOGS_DIR.mkdir(exist_ok=True)
        
        # Configuration du niveau
        level = logging.DEBUG if verbose else logging.INFO
        
        # Format des messages
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Logger principal
        logger = logging.getLogger('garmeae_parser')
        logger.setLevel(level)
        
        # Éviter la duplication des handlers
        if logger.handlers:
            logger.handlers.clear()
        
        # Handler console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Handler fichier
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger

# === LECTEUR PDF AMÉLIORÉ ===

class EnhancedPDFReader:
    """Lecteur PDF optimisé pour documents généalogiques"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.stats = {
            'pages_processed': 0,
            'total_chars': 0,
            'processing_time': 0.0,
            'errors': 0,
            'warnings': 0
        }
    
    @property
    def can_read_pdf(self) -> bool:
        """Vérifie si la lecture PDF est disponible"""
        return HAS_PYMUPDF
    
    def get_pdf_info(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        """Récupère les informations du PDF"""
        
        pdf_path = Path(pdf_path)
        
        basic_info = {
            'file_name': pdf_path.name,
            'file_size_mb': pdf_path.stat().st_size / (1024 * 1024),
            'can_process': False,
            'estimated_time_minutes': 0.0
        }
        
        if not self.can_read_pdf:
            basic_info['error'] = 'PyMuPDF non disponible'
            return basic_info
        
        try:
            with fitz.open(str(pdf_path)) as doc:
                basic_info.update({
                    'pages': len(doc),
                    'can_process': True,
                    'metadata': doc.metadata,
                    'estimated_time_minutes': len(doc) * 0.05  # 3 secondes par page
                })
                
                # Vérifier si le PDF contient du texte
                sample_page = doc[0] if len(doc) > 0 else None
                if sample_page:
                    sample_text = sample_page.get_text()
                    basic_info['has_text'] = len(sample_text.strip()) > 100
                    basic_info['sample_text_length'] = len(sample_text)
                
        except Exception as e:
            basic_info['error'] = str(e)
            self.logger.error(f"Erreur lecture info PDF: {e}")
        
        return basic_info
    
    def read_pdf_file(self, pdf_path: Union[str, Path], 
                     max_pages: Optional[int] = None,
                     page_range: Optional[Tuple[int, int]] = None,
                     progress_callback: Optional[callable] = None) -> str:
        """
        Lit un fichier PDF avec options avancées
        
        Args:
            pdf_path: Chemin vers le PDF
            max_pages: Nombre maximum de pages
            page_range: Tuple (début, fin) 1-indexé
            progress_callback: Fonction appelée pour le progrès
            
        Returns:
            str: Contenu textuel extrait
            
        Raises:
            FileNotFoundError: Fichier non trouvé
            ImportError: PyMuPDF non disponible
            ValueError: Paramètres invalides
        """
        
        start_time = time.time()
        pdf_path = Path(pdf_path)
        
        # Validations
        if not pdf_path.exists():
            raise FileNotFoundError(f"Fichier PDF introuvable: {pdf_path}")
        
        if not self.can_read_pdf:
            raise ImportError("PyMuPDF requis mais non disponible. Installez avec: pip install PyMuPDF")
        
        self.logger.info(f"📖 Lecture PDF: {pdf_path.name}")
        
        try:
            with fitz.open(str(pdf_path)) as doc:
                total_pages = len(doc)
                self.logger.info(f"📄 Document: {total_pages} pages")
                
                # Calculer la plage de pages
                start_page, end_page = self._calculate_page_range(
                    total_pages, max_pages, page_range
                )
                
                self.logger.info(f"📊 Traitement pages {start_page + 1} à {end_page}")
                
                # Extraction du texte
                text_parts = []
                pages_processed = 0
                
                for page_num in range(start_page, end_page):
                    try:
                        page = doc[page_num]
                        page_text = page.get_text()
                        
                        if page_text.strip():
                            # Ajouter séparateur de page
                            text_parts.append(f"\n--- PAGE {page_num + 1} ---\n")
                            text_parts.append(page_text)
                        else:
                            self.logger.warning(f"Page {page_num + 1} sans texte")
                            self.stats['warnings'] += 1
                        
                        pages_processed += 1
                        
                        # Callback de progrès
                        if progress_callback:
                            progress = (pages_processed / (end_page - start_page)) * 100
                            progress_callback(progress, page_num + 1, end_page)
                        
                        # Log de progression
                        if pages_processed % 25 == 0:
                            self.logger.info(f"⏳ Progression: {pages_processed}/{end_page - start_page} pages")
                        
                    except Exception as e:
                        self.logger.error(f"Erreur page {page_num + 1}: {e}")
                        self.stats['errors'] += 1
                        continue
                
                # Assemblage final
                full_text = '\n'.join(text_parts)
                
                # Mise à jour des statistiques
                self.stats.update({
                    'pages_processed': pages_processed,
                    'total_chars': len(full_text),
                    'processing_time': time.time() - start_time
                })
                
                self.logger.info(
                    f"✅ PDF lu avec succès: {pages_processed} pages, "
                    f"{len(full_text):,} caractères, "
                    f"{self.stats['processing_time']:.2f}s"
                )
                
                return full_text
                
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Erreur lecture PDF: {e}")
            raise
    
    def _calculate_page_range(self, total_pages: int, 
                            max_pages: Optional[int],
                            page_range: Optional[Tuple[int, int]]) -> Tuple[int, int]:
        """Calcule la plage de pages à traiter (0-indexé)"""
        
        if page_range:
            start, end = page_range
            # Convertir en 0-indexé et valider
            start_page = max(0, start - 1)
            end_page = min(total_pages, end)
        else:
            start_page = 0
            end_page = min(total_pages, max_pages) if max_pages else total_pages
        
        if start_page >= end_page:
            raise ValueError(f"Plage de pages invalide: {start_page + 1}-{end_page}")
        
        return start_page, end_page
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques de traitement"""
        stats = self.stats.copy()
        
        if stats['processing_time'] > 0:
            stats['pages_per_second'] = stats['pages_processed'] / stats['processing_time']
            stats['chars_per_second'] = stats['total_chars'] / stats['processing_time']
        
        return stats

# === PARSEUR PRINCIPAL AMÉLIORÉ ===

class EnhancedGenealogyParser:
    """Parseur généalogique principal avec intégration OCR complète"""
    
    def __init__(self, config_path: Optional[str] = None, 
                 logger: Optional[logging.Logger] = None):
        """
        Initialise le parseur avec configuration avancée
        
        Args:
            config_path: Chemin vers fichier de configuration
            logger: Logger personnalisé
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
        # Initialisation des composants (lazy loading)
        self._text_parser = None
        self._name_extractor = None  
        self._person_manager = None
        
        # Statistiques globales
        self.stats = {
            'documents_processed': 0,
            'total_persons': 0,
            'total_corrections': 0,
            'processing_time': 0.0,
            'errors_handled': 0
        }
        
        self.logger.info("🔧 Parseur généalogique initialisé")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Charge la configuration depuis un fichier ou utilise les défauts"""
        
        default_config = {
            'enable_ocr_corrections': Config.ENABLE_OCR_CORRECTIONS,
            'enable_validation': Config.ENABLE_VALIDATION,
            'cache_size': Config.CACHE_SIZE,
            'max_text_length': Config.MAX_TEXT_LENGTH,
            'chunk_size': Config.CHUNK_SIZE
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                default_config.update(file_config)
                self.logger.info(f"📋 Configuration chargée: {config_path}")
            except Exception as e:
                self.logger.warning(f"Erreur chargement config: {e}")
        
        return default_config
    
    @property
    def text_parser(self) -> 'TextParser':
        """Parser de texte (lazy loading)"""
        if not HAS_PARSERS:
            raise ImportError("Modules parsers non disponibles")
        
        if self._text_parser is None:
            self._text_parser = TextParser(self.config)
            self.logger.debug("📝 TextParser initialisé")
        
        return self._text_parser
    
    @property
    def name_extractor(self) -> 'NameExtractor':
        """Extracteur de noms (lazy loading)"""
        if not HAS_PARSERS:
            raise ImportError("Modules parsers non disponibles")
        
        if self._name_extractor is None:
            self._name_extractor = NameExtractor(self.config)
            self.logger.debug("👤 NameExtractor initialisé")
        
        return self._name_extractor
    
    @property  
    def person_manager(self) -> 'PersonManager':
        """Gestionnaire de personnes (lazy loading)"""
        if not HAS_PARSERS:
            raise ImportError("Modules parsers non disponibles")
        
        if self._person_manager is None:
            self._person_manager = PersonManager(self.config.get('cache_size', Config.CACHE_SIZE))
            self.logger.debug("🏛️ PersonManager initialisé")
        
        return self._person_manager
    
    def process_document(self, text: str, 
                        source_info: Optional[Dict[str, Any]] = None,
                        progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Traite un document complet avec toutes les améliorations
        
        Args:
            text: Texte à analyser
            source_info: Informations sur la source
            progress_callback: Fonction de progression
            
        Returns:
            Dict: Rapport structuré complet
        """
        start_time = time.time()
        
        # Informations par défaut
        source_info = source_info or {
            'lieu': 'Document généalogique',
            'type': 'registre_paroissial',
            'date_traitement': datetime.now().isoformat()
        }
        
        self.logger.info(f"🚀 Début traitement: {source_info.get('lieu', 'Source inconnue')}")
        
        try:
            # Validation initiale
            if len(text) > self.config['max_text_length']:
                self.logger.warning(f"Texte tronqué: {len(text)} → {self.config['max_text_length']} caractères")
                text = text[:self.config['max_text_length']]
            
            report = {
                'source_info': source_info,
                'processing_metadata': {
                    'start_time': datetime.now().isoformat(),
                    'text_length': len(text),
                    'enable_ocr': self.config['enable_ocr_corrections']
                },
                'results': {},
                'statistics': {},
                'errors': []
            }
            
            # === ÉTAPE 1: NORMALISATION DU TEXTE ===
            self._update_progress(progress_callback, 10, "Normalisation du texte...")
            
            try:
                if HAS_PARSERS:
                    norm_result = self.text_parser.normalize_text(text, apply_ocr_corrections=True)
                    normalized_text = norm_result['normalized']
                    
                    report['results']['text_normalization'] = {
                        'ocr_corrections': norm_result.get('ocr_corrections', []),
                        'abbreviations_expanded': norm_result.get('abbreviations_expanded', []),
                        'improvement_ratio': norm_result.get('improvement_ratio', 0.0)
                    }
                    
                    self.stats['total_corrections'] += len(norm_result.get('ocr_corrections', []))
                else:
                    normalized_text = text
                    report['results']['text_normalization'] = {'status': 'parsers_unavailable'}
                
            except Exception as e:
                self.logger.error(f"Erreur normalisation: {e}")
                normalized_text = text
                report['errors'].append(f"Normalisation: {str(e)}")
            
            # === ÉTAPE 2: SEGMENTATION ===
            self._update_progress(progress_callback, 25, "Segmentation du document...")
            
            try:
                if HAS_PARSERS:
                    segments = self.text_parser.extract_segments(normalized_text, normalize_segments=True)
                    report['results']['segmentation'] = {
                        'total_segments': len(segments),
                        'segments_by_type': self._count_segments_by_type(segments)
                    }
                else:
                    segments = [{'type': 'text', 'content': normalized_text}]
                    report['results']['segmentation'] = {'status': 'basic_segmentation'}
                
            except Exception as e:
                self.logger.error(f"Erreur segmentation: {e}")
                segments = [{'type': 'text', 'content': normalized_text}]
                report['errors'].append(f"Segmentation: {str(e)}")
            
            # === ÉTAPE 3: EXTRACTION DES NOMS ===
            self._update_progress(progress_callback, 50, "Extraction des noms...")
            
            try:
                if HAS_PARSERS:
                    persons_data = self.name_extractor.extract_complete_names_with_sources(
                        normalized_text, 
                        source_info.get('lieu', 'Source'),
                        1
                    )
                    
                    report['results']['name_extraction'] = {
                        'total_names': len(persons_data),
                        'names_with_corrections': sum(1 for p in persons_data if p.get('correction_ocr_appliquee')),
                        'sample_names': [p['nom_complet'] for p in persons_data[:10]]
                    }
                else:
                    persons_data = []
                    report['results']['name_extraction'] = {'status': 'parsers_unavailable'}
                
            except Exception as e:
                self.logger.error(f"Erreur extraction noms: {e}")
                persons_data = []
                report['errors'].append(f"Extraction noms: {str(e)}")
            
            # === ÉTAPE 4: CRÉATION DES PERSONNES ===
            self._update_progress(progress_callback, 75, "Création des personnes...")
            
            created_persons = []
            try:
                if HAS_PARSERS and persons_data:
                    for person_data in persons_data:
                        try:
                            person = self.person_manager.find_or_create_person(
                                person_data['nom_complet'],
                                {
                                    'source': source_info.get('lieu', 'Source'),
                                    'extraction_data': person_data
                                }
                            )
                            created_persons.append(person)
                        except Exception as e:
                            self.logger.warning(f"Erreur création personne: {e}")
                            continue
                    
                    report['results']['person_creation'] = {
                        'total_persons': len(created_persons),
                        'cache_statistics': self.person_manager.get_enhanced_statistics()
                    }
                else:
                    report['results']['person_creation'] = {'status': 'no_data_or_parsers_unavailable'}
                
            except Exception as e:
                self.logger.error(f"Erreur création personnes: {e}")
                report['errors'].append(f"Création personnes: {str(e)}")
            
            # === ÉTAPE 5: FINALISATION ===
            self._update_progress(progress_callback, 90, "Finalisation...")
            
            # Statistiques finales
            processing_time = time.time() - start_time
            self.stats.update({
                'documents_processed': self.stats['documents_processed'] + 1,
                'total_persons': len(created_persons),
                'processing_time': self.stats['processing_time'] + processing_time
            })
            
            report['processing_metadata'].update({
                'end_time': datetime.now().isoformat(),
                'processing_time_seconds': processing_time,
                'errors_count': len(report['errors'])
            })
            
            report['statistics'] = self._generate_processing_statistics()
            
            self._update_progress(progress_callback, 100, "Traitement terminé!")
            
            self.logger.info(f"✅ Traitement terminé en {processing_time:.2f}s")
            return report
            
        except Exception as e:
            self.stats['errors_handled'] += 1
            self.logger.error(f"Erreur critique traitement: {e}")
            raise
    
    def _count_segments_by_type(self, segments: List[Dict]) -> Dict[str, int]:
        """Compte les segments par type"""
        counts = {}
        for segment in segments:
            seg_type = segment.get('type', 'unknown')
            counts[seg_type] = counts.get(seg_type, 0) + 1
        return counts
    
    def _update_progress(self, callback: Optional[callable], 
                        progress: int, message: str):
        """Met à jour le progrès si callback fourni"""
        if callback:
            callback(progress, message)
    
    def _generate_processing_statistics(self) -> Dict[str, Any]:
        """Génère des statistiques détaillées"""
        
        base_stats = {
            'global': self.stats.copy(),
            'performance': {
                'avg_processing_time': (
                    self.stats['processing_time'] / max(self.stats['documents_processed'], 1)
                ),
                'corrections_per_document': (
                    self.stats['total_corrections'] / max(self.stats['documents_processed'], 1)
                )
            }
        }
        
        # Ajouter stats des parsers si disponibles
        if HAS_PARSERS:
            try:
                if self._text_parser:
                    base_stats['text_parser'] = self._text_parser.get_enhanced_statistics()
                if self._person_manager:
                    base_stats['person_manager'] = self._person_manager.get_enhanced_statistics()
            except Exception as e:
                self.logger.debug(f"Erreur récupération stats parsers: {e}")
        
        return base_stats
    
    def export_results(self, report: Dict[str, Any], 
                      output_dir: Path, 
                      formats: List[str] = None) -> Dict[str, str]:
        """
        Exporte les résultats dans différents formats
        
        Args:
            report: Rapport à exporter
            output_dir: Répertoire de sortie
            formats: Liste des formats ('json', 'txt', 'gedcom')
            
        Returns:
            Dict: Chemins des fichiers créés
        """
        
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
    """Lance les tests intégrés"""
    
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
    
    print("📄 Texte d'exemple:")
    print("-" * 50)
    print(sample_text[:300] + "..." if len(sample_text) > 300 else sample_text)
    print("-" * 50)
    
    # Traitement
    try:
        parser = EnhancedGenealogyParser()
        
        source_info = {
            'lieu': 'Notre-Dame d\'Esméville',
            'type': 'demo',
            'periode': '1643-1687'
        }
        
        progress = ProgressTracker(show_progress=True)
        
        print("\n🔄 Traitement en cours...")
        report = parser.process_document(
            sample_text, 
            source_info,
            progress_callback=progress.update
        )
        
        print("\n📊 RÉSULTATS:")
        print("=" * 30)
        
        # Affichage simplifié des résultats
        if 'text_normalization' in report['results']:
            norm = report['results']['text_normalization']
            print(f"📝 Corrections OCR: {len(norm.get('ocr_corrections', []))}")
            print(f"📖 Abréviations: {len(norm.get('abbreviations_expanded', []))}")
        
        if 'name_extraction' in report['results']:
            names = report['results']['name_extraction']
            print(f"👥 Noms extraits: {names.get('total_names', 0)}")
            
            # Afficher quelques noms
            sample_names = names.get('sample_names', [])[:5]
            if sample_names:
                print("\n🏷️ Noms trouvés:")
                for name in sample_names:
                    print(f"   • {name}")
        
        processing_time = report['processing_metadata'].get('processing_time_seconds', 0)
        print(f"\n⏱️ Temps de traitement: {processing_time:.2f}s")
        
        return report
        
    except Exception as e:
        print(f"❌ Erreur démonstration: {e}")
        if '--verbose' in sys.argv:
            traceback.print_exc()
        return {'error': str(e)}

def main():
    """Fonction principale"""
    
    # Parser d'arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Configuration du logging
    log_file = args.log_file or Config.DEFAULT_LOGS_DIR / "genealogy_parser.log"
    logger = LoggingSetup.setup_logging(args.verbose, log_file)
    
    # Actions spéciales
    if args.check_deps:
        check_dependencies()
        return
    
    if args.test:
        success = run_integrated_tests()
        sys.exit(0 if success else 1)
    
    if not args.input_file:
        print("❌ Aucun fichier spécifié. Utilisez --help pour l'aide.")
        sys.exit(1)
    
    if args.input_file.lower() == 'demo':
        run_demo()
        return
    
    # Validation du fichier d'entrée
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ Fichier non trouvé: {input_path}")
        sys.exit(1)
    
    # Vérification du format
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
                    print(f"❌ Format de plage invalide: {args.pdf_range}")
                    sys.exit(1)
            
            # Lecture PDF avec progression
            progress = ProgressTracker(not args.no_progress)
            
            print(f"📖 Lecture PDF: {input_path.name}")
            text_content = pdf_reader.read_pdf_file(
                input_path, 
                progress_callback=progress.update,
                **pdf_options
            )
            
            # Stats PDF
            pdf_stats = pdf_reader.get_statistics()
            logger.info(f"PDF traité: {pdf_stats['pages_processed']} pages")
            source_info.update(pdf_stats)
        
        else:
            # Lecture fichier texte
            print(f"📄 Lecture fichier texte: {input_path.name}")
            
            with safe_file_operation(input_path, "lecture"):
                with open(input_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
        
        # Validation du contenu
        if not text_content.strip():
            print("❌ Aucun contenu textuel extrait!")
            sys.exit(1)
        
        print(f"✅ Contenu extrait: {len(text_content):,} caractères")
        
        # === TRAITEMENT GÉNÉALOGIQUE ===
        
        # Configuration personnalisée
        config_overrides = {}
        if args.no_ocr:
            config_overrides['enable_ocr_corrections'] = False
        if args.chunk_size:
            config_overrides['chunk_size'] = args.chunk_size
        
        # Création du parseur
        parser_instance = EnhancedGenealogyParser(args.config, logger)
        if config_overrides:
            parser_instance.config.update(config_overrides)
        
        # Traitement avec progression
        progress = ProgressTracker(not args.no_progress)
        
        print(f"\n🔄 Traitement généalogique...")
        report = parser_instance.process_document(
            text_content,
            source_info,
            progress_callback=progress.update
        )
        
        # === EXPORT DES RÉSULTATS ===
        
        print(f"\n💾 Export des résultats...")
        created_files = parser_instance.export_results(
            report, 
            output_dir, 
            args.formats
        )
        
        # === AFFICHAGE DES RÉSULTATS ===
        
        print(f"\n📊 RÉSULTATS:")
        print("=" * 50)
        
        # Résumé principal
        if 'text_normalization' in report['results']:
            norm = report['results']['text_normalization']
            ocr_count = len(norm.get('ocr_corrections', []))
            abbrev_count = len(norm.get('abbreviations_expanded', []))
            print(f"📝 Corrections OCR appliquées: {ocr_count}")
            print(f"📖 Abréviations développées: {abbrev_count}")
        
        if 'name_extraction' in report['results']:
            names = report['results']['name_extraction']
            total_names = names.get('total_names', 0)
            corrected_names = names.get('names_with_corrections', 0)
            print(f"👥 Noms extraits: {total_names}")
            print(f"✅ Noms corrigés automatiquement: {corrected_names}")
        
        if 'person_creation' in report['results']:
            persons = report['results']['person_creation']
            total_persons = persons.get('total_persons', 0)
            print(f"🏛️ Personnes créées: {total_persons}")
        
        # Temps de traitement
        processing_time = report['processing_metadata'].get('processing_time_seconds', 0)
        print(f"⏱️ Temps de traitement: {processing_time:.2f}s")
        
        # Fichiers créés
        if created_files:
            print(f"\n📁 Fichiers créés:")
            for format_type, file_path in created_files.items():
                print(f"   {format_type.upper()}: {file_path}")
        
        # Erreurs
        if report.get('errors'):
            print(f"\n⚠️ Erreurs rencontrées: {len(report['errors'])}")
            if args.verbose:
                for error in report['errors']:
                    print(f"   • {error}")
        
        # Statistiques détaillées si demandé
        if args.verbose:
            print(f"\n📈 STATISTIQUES DÉTAILLÉES:")
            print("-" * 30)
            stats = report.get('statistics', {})
            print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))
        
        print(f"\n✅ Traitement terminé avec succès!")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Traitement interrompu par l'utilisateur")
        sys.exit(130)
    
    except Exception as e:
        logger.error(f"Erreur critique: {e}")
        print(f"\n❌ Erreur: {e}")
        
        if args.verbose:
            print("\n🔍 Détails de l'erreur:")
            traceback.print_exc()
        
        sys.exit(1)

if __name__ == "__main__":
    main()