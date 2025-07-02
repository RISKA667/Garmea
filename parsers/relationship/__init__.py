from .basic_relationship_parser import BasicRelationshipParser, RelationshipMatch
from .relationship_factory import RelationshipFactory

try:
    from .advanced_relationship_parser import AdvancedRelationshipParser, EnhancedRelationshipMatch, HAS_SPACY
    ADVANCED_AVAILABLE = True
except ImportError:
    ADVANCED_AVAILABLE = False
    AdvancedRelationshipParser = None
    EnhancedRelationshipMatch = None
    HAS_SPACY = False

__all__ = [
    'BasicRelationshipParser',
    'RelationshipMatch',
    'RelationshipFactory'
]

if ADVANCED_AVAILABLE:
    __all__.extend([
        'AdvancedRelationshipParser',
        'EnhancedRelationshipMatch'
    ])

def create_relationship_parser(config=None, prefer_advanced: bool = True):
    return RelationshipFactory.get_optimal_parser(config, prefer_advanced)

def get_relationship_capabilities():
    return RelationshipFactory.get_capabilities()