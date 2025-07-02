import logging
from typing import Union, Dict, Any, Optional
from .basic_relationship_parser import BasicRelationshipParser
from .advanced_relationship_parser import AdvancedRelationshipParser, HAS_SPACY

class RelationshipFactory:
    @staticmethod
    def get_optimal_parser(config=None, prefer_advanced: bool = True, 
                          fallback_enabled: bool = True) -> Union[AdvancedRelationshipParser, BasicRelationshipParser]:
        logger = logging.getLogger(__name__)
        
        if prefer_advanced and HAS_SPACY:
            logger.info("Création du parser de relations avancé (spaCy)")
            return AdvancedRelationshipParser(config, fallback_to_basic=fallback_enabled)
        
        elif fallback_enabled:
            logger.info("Création du parser de relations de base (fallback)")
            return BasicRelationshipParser(config)
        
        else:
            logger.warning("spaCy non disponible et fallback désactivé")
            raise ImportError("Parser de relations avancé non disponible et fallback désactivé")
    
    @staticmethod
    def get_basic_parser(config=None) -> BasicRelationshipParser:
        return BasicRelationshipParser(config)
    
    @staticmethod
    def get_advanced_parser(config=None, fallback_enabled: bool = True) -> AdvancedRelationshipParser:
        if not HAS_SPACY:
            raise ImportError("spaCy non disponible pour le parser avancé")
        return AdvancedRelationshipParser(config, fallback_to_basic=fallback_enabled)
    
    @staticmethod
    def get_capabilities() -> Dict[str, Any]:
        return {
            'spacy_available': HAS_SPACY,
            'basic_parser': True,
            'advanced_parser': HAS_SPACY,
            'fallback_support': True,
            'recommended_parser': 'advanced' if HAS_SPACY else 'basic'
        }
    
    @staticmethod
    def create_from_config(config_dict: Dict[str, Any]) -> Union[AdvancedRelationshipParser, BasicRelationshipParser]:
        parser_type = config_dict.get('parser_type', 'optimal')
        prefer_advanced = config_dict.get('prefer_advanced', True)
        fallback_enabled = config_dict.get('fallback_enabled', True)
        
        if parser_type == 'basic':
            return RelationshipFactory.get_basic_parser(config_dict.get('config'))
        elif parser_type == 'advanced':
            return RelationshipFactory.get_advanced_parser(
                config_dict.get('config'), 
                fallback_enabled
            )
        else:
            return RelationshipFactory.get_optimal_parser(
                config_dict.get('config'), 
                prefer_advanced, 
                fallback_enabled
            )