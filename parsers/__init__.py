from .text_parser import TextParser
from .name_extractor import NameExtractor
from .date_parser import DateParser
from .profession_parser import ProfessionParser
from .relationship_parser import RelationshipParser

from .modern_nlp_parser import (
    ModernNLPParser,
    RelationshipMatch,
    create_relationship_parser,
    HAS_SPACY,
    INSTALL_INSTRUCTIONS
)

# Imports conditionnels pour les parsers avancés
try:
    from smart_pdf_analyzer import SmartPDFAnalyzer
    HAS_PDF_ANALYZER = True
except ImportError:
    HAS_PDF_ANALYZER = False
    SmartPDFAnalyzer = None

# Export principal
__all__ = [
    # Parsers de base
    'TextParser',
    'NameExtractor', 
    'DateParser',
    'ProfessionParser',
    'RelationshipParser',
    
    # Parsers NLP avancés
    'ModernNLPParser',
    'RelationshipMatch',
    'create_relationship_parser',
    
    # Utilitaires
    'get_optimal_parser',
    'get_parser_capabilities',
    'install_nlp_dependencies',
    
    # Flags de fonctionnalités
    'HAS_SPACY',
    'HAS_PDF_ANALYZER'
]

# Ajout conditionnel des parsers avancés
if HAS_PDF_ANALYZER:
    __all__.append('SmartPDFAnalyzer')

def get_optimal_parser(parser_type: str = "relationship", prefer_nlp: bool = True):
    """
    Factory pour obtenir le meilleur parser disponible selon l'environnement
    
    Args:
        parser_type: Type de parser ('relationship', 'text', 'name', etc.)
        prefer_nlp: Préférer les parsers NLP quand disponibles
        
    Returns:
        Instance du parser optimal
        
    Examples:
        >>> parser = get_optimal_parser("relationship", prefer_nlp=True)
        >>> # Retourne ModernNLPParser si spaCy disponible, sinon RelationshipParser
    """
    
    if parser_type == "relationship":
        return create_relationship_parser(prefer_nlp=prefer_nlp)
    
    elif parser_type == "text":
        return TextParser()
    
    elif parser_type == "name":
        return NameExtractor()
    
    elif parser_type == "date":
        return DateParser()
    
    elif parser_type == "profession":
        return ProfessionParser()
    
    elif parser_type == "pdf" and HAS_PDF_ANALYZER:
        return SmartPDFAnalyzer()
    
    else:
        raise ValueError(f"Parser type '{parser_type}' non supporté ou non disponible")

def get_parser_capabilities() -> dict:
    """
    Retourne les capacités de parsing disponibles dans l'environnement
    
    Returns:
        Dict avec les fonctionnalités disponibles
    """
    capabilities = {
        'base_parsers': {
            'text': True,
            'name': True,
            'date': True,
            'profession': True,
            'relationship_basic': True
        },
        'advanced_features': {
            'nlp_spacy': HAS_SPACY,
            'pdf_analyzer': HAS_PDF_ANALYZER,
            'relationship_advanced': HAS_SPACY,
            'entity_recognition': HAS_SPACY,
            'confidence_scoring': HAS_SPACY
        },
        'performance': {
            'caching': True,
            'batch_processing': HAS_SPACY,
            'parallel_processing': HAS_PDF_ANALYZER
        }
    }
    
    return capabilities

def install_nlp_dependencies():
    """
    Guide d'installation des dépendances NLP pour améliorer les performances
    """
    if not HAS_SPACY:
        print("=== AMÉLIORATION DES PERFORMANCES ===")
        print(INSTALL_INSTRUCTIONS)
        print("\nFonctionnalités débloquées avec spaCy :")
        print("✅ Reconnaissance d'entités nommées avancée")
        print("✅ Scoring de confiance automatique")
        print("✅ Validation contextuelle")
        print("✅ Performance 3x supérieure sur gros volumes")
        print("✅ Support des variantes orthographiques anciennes")
    else:
        print("✅ spaCy détecté - Fonctionnalités NLP avancées activées")
    
    if not HAS_PDF_ANALYZER:
        print("\nPour l'analyse PDF avancée, installez :")
        print("pip install PyMuPDF python-magic")
    else:
        print("✅ Analyseur PDF avancé disponible")

# Configuration par défaut recommandée
DEFAULT_CONFIG = {
    'prefer_nlp': True,
    'fallback_to_basic': True,
    'enable_caching': True,
    'confidence_threshold': 0.7,
    'batch_size': 100
}

def create_parser_suite(config: dict = None) -> dict:
    """
    Crée une suite complète de parsers avec configuration optimale
    
    Args:
        config: Configuration personnalisée (optionnel)
        
    Returns:
        Dict avec tous les parsers configurés
    """
    if config is None:
        config = DEFAULT_CONFIG.copy()
    
    suite = {
        'text': TextParser(),
        'name': NameExtractor(),
        'date': DateParser(),
        'profession': ProfessionParser(),
        'relationship': get_optimal_parser("relationship", config.get('prefer_nlp', True))
    }
    
    # Ajouter parsers avancés si disponibles
    if HAS_PDF_ANALYZER:
        suite['pdf'] = SmartPDFAnalyzer()
    
    return suite

# Version et compatibilité
__version__ = "2.0.0"
__compatibility__ = {
    'python': ">=3.8",
    'spacy': ">=3.4.0",  # Optionnel mais recommandé
    'required': ['re', 'typing', 'dataclasses', 'functools'],
    'optional': ['spacy', 'PyMuPDF', 'python-magic']
}

# Message d'initialisation
def _show_init_info():
    """Affiche les informations d'initialisation (mode debug)"""
    import os
    if os.getenv('GARMEA_DEBUG'):
        print(f"🔧 Parsers Garméa v{__version__} initialisés")
        caps = get_parser_capabilities()
        advanced_count = sum(caps['advanced_features'].values())
        print(f"   📊 Fonctionnalités avancées: {advanced_count}/4 disponibles")
        if not HAS_SPACY:
            print("   ⚠️  spaCy non disponible - performances limitées")

# Exécuter à l'import si mode debug
_show_init_info()