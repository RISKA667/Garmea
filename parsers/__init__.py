import logging
from typing import Dict, Any, Optional, Union

from .base import TextParser, NameExtractor, DateParser, ProfessionParser
from .relationship import RelationshipFactory, BasicRelationshipParser
from .specialized import PeriodParser, StrictParser
from .common import get_cache, global_cache_manager
from .config import patterns_config, ocr_config

try:
    from .relationship import AdvancedRelationshipParser, EnhancedRelationshipMatch
    ADVANCED_RELATIONSHIP_AVAILABLE = True
except ImportError:
    ADVANCED_RELATIONSHIP_AVAILABLE = False
    AdvancedRelationshipParser = None
    EnhancedRelationshipMatch = None

try:
    from .specialized import PDFAnalyzer
    PDF_ANALYZER_AVAILABLE = True
except ImportError:
    PDF_ANALYZER_AVAILABLE = False
    PDFAnalyzer = None

__version__ = "3.0.0"
__author__ = "Garméa Parser Team"
__license__ = "MIT"

__all__ = [
    'TextParser', 'NameExtractor', 'DateParser', 'ProfessionParser',
    'BasicRelationshipParser', 'RelationshipFactory',
    'PeriodParser', 'StrictParser',
    'create_parser_suite', 'get_optimal_parser', 'get_capabilities',
    'ParserManager'
]

if ADVANCED_RELATIONSHIP_AVAILABLE:
    __all__.extend(['AdvancedRelationshipParser', 'EnhancedRelationshipMatch'])

if PDF_ANALYZER_AVAILABLE:
    __all__.append('PDFAnalyzer')

class ParserManager:
    """Gestionnaire centralisé pour tous les parsers"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self._parsers = {}
        self._initialized = False
        
        self.stats = {
            'parsers_created': 0,
            'documents_processed': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def initialize(self, force_reinit: bool = False):
        """Initialise tous les parsers de manière paresseuse"""
        if self._initialized and not force_reinit:
            return
        
        self.logger.info(f"Initialisation ParserManager v{__version__}")
        
        try:
            self._parsers = {
                'text': TextParser(self.config),
                'name': NameExtractor(self.config),
                'date': DateParser(self.config),
                'profession': ProfessionParser(self.config),
                'relationship': RelationshipFactory.get_optimal_parser(self.config),
                'period': PeriodParser(self.config),
                'strict': StrictParser(self.config)
            }
            
            if PDF_ANALYZER_AVAILABLE:
                self._parsers['pdf'] = PDFAnalyzer(self.config)
            
            self.stats['parsers_created'] = len(self._parsers)
            self._initialized = True
            
            self.logger.info(f"✅ {len(self._parsers)} parsers initialisés")
            
        except Exception as e:
            self.logger.error(f"Erreur initialisation parsers: {e}")
            raise
    
    def get_parser(self, parser_type: str):
        """Récupère un parser spécifique"""
        if not self._initialized:
            self.initialize()
        
        if parser_type not in self._parsers:
            available = list(self._parsers.keys())
            raise ValueError(f"Parser '{parser_type}' non disponible. Disponibles: {available}")
        
        return self._parsers[parser_type]
    
    def process_document(self, text: str, parser_types: Optional[list] = None) -> Dict[str, Any]:
        """Traite un document avec plusieurs parsers"""
        if not self._initialized:
            self.initialize()
        
        if parser_types is None:
            parser_types = ['text', 'name', 'date', 'relationship']
        
        self.stats['documents_processed'] += 1
        
        results = {}
        processing_stats = {}
        
        for parser_type in parser_types:
            if parser_type not in self._parsers:
                self.logger.warning(f"Parser '{parser_type}' non disponible, ignoré")
                continue
            
            try:
                import time
                start_time = time.time()
                
                parser = self._parsers[parser_type]
                
                if parser_type == 'text':
                    result = parser.normalize_text(text)
                elif parser_type == 'name':
                    result = parser.extract_names(text)
                elif parser_type == 'date':
                    result = parser.extract_dates(text)
                elif parser_type == 'profession':
                    result = parser.extract_professions_and_titles(text)
                elif parser_type == 'relationship':
                    result = parser.extract_relationships(text)
                elif parser_type == 'period':
                    result = parser.parse_document(text)
                elif parser_type == 'strict':
                    result = parser.extract_ultra_strict_filiations(text)
                elif parser_type == 'pdf':
                    self.logger.warning("PDF parser nécessite un fichier, pas un texte")
                    result = None
                else:
                    result = None
                
                processing_time = time.time() - start_time
                
                results[parser_type] = result
                processing_stats[parser_type] = {
                    'processing_time': processing_time,
                    'success': result is not None
                }
                
            except Exception as e:
                self.logger.error(f"Erreur parser '{parser_type}': {e}")
                results[parser_type] = None
                processing_stats[parser_type] = {
                    'processing_time': 0,
                    'success': False,
                    'error': str(e)
                }
        
        return {
            'results': results,
            'processing_stats': processing_stats,
            'document_stats': {
                'text_length': len(text),
                'parsers_used': len(parser_types),
                'successful_parsers': sum(1 for stats in processing_stats.values() if stats['success'])
            }
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Retourne les capacités disponibles"""
        if not self._initialized:
            self.initialize()
        
        return {
            'version': __version__,
            'parsers_available': list(self._parsers.keys()),
            'advanced_features': {
                'advanced_relationships': ADVANCED_RELATIONSHIP_AVAILABLE,
                'pdf_analysis': PDF_ANALYZER_AVAILABLE,
                'period_detection': True,
                'strict_validation': True,
                'ocr_corrections': True,
                'vectorized_processing': True
            },
            'cache_system': {
                'enabled': True,
                'global_stats': global_cache_manager.get_global_stats()
            }
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Statistiques globales du système"""
        parser_stats = {}
        
        for name, parser in self._parsers.items():
            if hasattr(parser, 'get_stats'):
                parser_stats[name] = parser.get_stats()
        
        cache_stats = global_cache_manager.get_global_stats()
        
        return {
            'manager_stats': self.stats,
            'parser_stats': parser_stats,
            'cache_stats': cache_stats,
            'system_info': {
                'version': __version__,
                'parsers_count': len(self._parsers),
                'initialized': self._initialized
            }
        }
    
    def cleanup_caches(self) -> Dict[str, int]:
        """Nettoie tous les caches"""
        cleaned = global_cache_manager.cleanup_all()
        self.logger.info(f"Nettoyage caches: {cleaned} entrées supprimées")
        return {'cleaned_entries': cleaned}

def create_parser_suite(config=None) -> ParserManager:
    """Crée une suite complète de parsers"""
    return ParserManager(config)

def get_optimal_parser(parser_type: str, config=None):
    """Factory pour obtenir le parser optimal pour un type donné"""
    manager = ParserManager(config)
    manager.initialize()
    return manager.get_parser(parser_type)

def get_capabilities() -> Dict[str, Any]:
    """Retourne les capacités du système de parsing"""
    return {
        'version': __version__,
        'base_parsers': {
            'text_parser': True,
            'name_extractor': True,
            'date_parser': True,
            'profession_parser': True
        },
        'relationship_parsers': {
            'basic': True,
            'advanced': ADVANCED_RELATIONSHIP_AVAILABLE
        },
        'specialized_parsers': {
            'period_parser': True,
            'strict_parser': True,
            'pdf_analyzer': PDF_ANALYZER_AVAILABLE
        },
        'features': {
            'ocr_corrections': True,
            'pattern_compilation': True,
            'cache_system': True,
            'vectorized_processing': True,
            'parallel_processing': PDF_ANALYZER_AVAILABLE
        }
    }

def install_dependencies_guide():
    """Guide d'installation des dépendances optionnelles"""
    guide = [
        "=== GUIDE D'INSTALLATION PARSERS ===",
        "",
        "Dépendances de base (incluses) :",
        "✅ re, typing, dataclasses, functools, logging",
        "",
        "Dépendances optionnelles pour fonctionnalités avancées :",
        ""
    ]
    
    if not ADVANCED_RELATIONSHIP_AVAILABLE:
        guide.extend([
            "📦 Pour parsing NLP avancé :",
            "   pip install spacy",
            "   python -m spacy download fr_core_news_sm",
            "   → Améliore précision et robustesse relations",
            ""
        ])
    else:
        guide.append("✅ spaCy disponible - Parsing NLP avancé activé")
    
    if not PDF_ANALYZER_AVAILABLE:
        guide.extend([
            "📦 Pour analyse PDF :",
            "   pip install PyMuPDF",
            "   → Permet traitement direct des fichiers PDF",
            ""
        ])
    else:
        guide.append("✅ PyMuPDF disponible - Analyse PDF activée")
    
    guide.extend([
        "🚀 Installation complète recommandée :",
        "   pip install spacy PyMuPDF",
        "   python -m spacy download fr_core_news_sm",
        "",
        f"Version actuelle: {__version__}",
        "Documentation: Voir fichiers README du projet"
    ])
    
    return "\n".join(guide)

_default_manager = None

def get_default_manager() -> ParserManager:
    """Retourne l'instance par défaut du gestionnaire de parsers"""
    global _default_manager
    if _default_manager is None:
        _default_manager = ParserManager()
        _default_manager.initialize()
    return _default_manager

if __name__ == "__main__":
    print(install_dependencies_guide())
    print("\n" + "="*50)
    print("Test des capacités du système :")
    capabilities = get_capabilities()
    for category, features in capabilities.items():
        print(f"\n{category.upper()}:")
        if isinstance(features, dict):
            for feature, available in features.items():
                status = "✅" if available else "❌"
                print(f"  {status} {feature}")
        else:
            print(f"  {features}")