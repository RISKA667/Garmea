import re
from typing import List, Dict, Optional, Tuple
from functools import lru_cache
from config.settings import ParserConfig

class RelationshipParser:
    """Parser optimisé pour relations familiales"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        
        # Compilation des patterns de relations
        self._compile_relationship_patterns()
    
    def _compile_relationship_patterns(self):
        """Compile les patterns de relations familiales"""
        # Pattern pour noms (réutilisable)
        name_pattern = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)*'
        
        self.relationship_patterns = {
            'marriage': re.compile(
                rf'({name_pattern}),?\s+épouse\s+de\s+({name_pattern})', 
                re.IGNORECASE
            ),
            
            'filiation_fille': re.compile(
                rf'({name_pattern}),?\s+fille\s+de\s+({name_pattern})(?:\s+et\s+de\s+({name_pattern}))?', 
                re.IGNORECASE
            ),
            
            'filiation_fils': re.compile(
                rf'({name_pattern}),?\s+fils\s+de\s+({name_pattern})(?:\s+et\s+de\s+({name_pattern}))?', 
                re.IGNORECASE
            ),
            
            'parrain': re.compile(
                rf'parrain\s*:\s*({name_pattern})', 
                re.IGNORECASE
            ),
            
            'marraine': re.compile(
                rf'marraine\s*:\s*({name_pattern})', 
                re.IGNORECASE
            ),
            
            'veuve': re.compile(
                rf'({name_pattern}),?\s+veuve\s+de\s+({name_pattern})', 
                re.IGNORECASE
            )
        }
    
    @lru_cache(maxsize=300)
    def extract_relationships(self, text: str) -> List[Dict]:
        """Extraction de toutes les relations avec cache"""
        relationships = []
        
        for rel_type, pattern in self.relationship_patterns.items():
            for match in pattern.finditer(text):
                relationship = self._parse_relationship(rel_type, match)
                if relationship:
                    relationships.append(relationship)
        
        return relationships
    
    def _parse_relationship(self, rel_type: str, match: re.Match) -> Optional[Dict]:
        """Parse une relation spécifique"""
        groups = match.groups()
        
        try:
            if rel_type == 'marriage':
                personne1 = self._clean_person_name(groups[0])
                personne2 = self._clean_person_name(groups[1])
                
                if personne1 and personne2:
                    return {
                        'type': 'épouse',
                        'personne1': personne1,
                        'personne2': personne2,
                        'position': (match.start(), match.end())
                    }
            
            elif rel_type in ['filiation_fille', 'filiation_fils']:
                enfant = self._clean_person_name(groups[0])
                pere = self._clean_person_name(groups[1]) if groups[1] else None
                mere = self._clean_person_name(groups[2]) if len(groups) > 2 and groups[2] else None
                
                if enfant:
                    return {
                        'type': 'filiation',
                        'enfant': enfant,
                        'pere': pere,
                        'mere': mere,
                        'genre': 'F' if rel_type == 'filiation_fille' else 'M',
                        'position': (match.start(), match.end())
                    }
            
            elif rel_type in ['parrain', 'marraine']:
                personne = self._clean_person_name(groups[0])
                if personne:
                    return {
                        'type': rel_type,
                        'personne': personne,
                        'position': (match.start(), match.end())
                    }
            
            elif rel_type == 'veuve':
                veuve = self._clean_person_name(groups[0])
                defunt = self._clean_person_name(groups[1])
                
                if veuve and defunt:
                    return {
                        'type': 'veuvage',
                        'veuve': veuve,
                        'défunt': defunt,
                        'position': (match.start(), match.end())
                    }
            
        except (IndexError, AttributeError):
            return None
        
        return None
    
    def _clean_person_name(self, name: str) -> Optional[str]:
        """Nettoie les noms extraits"""
        if not name:
            return None
        
        name = name.strip()
        
        # Supprimer les mots parasites en début
        parasites = ['de', 'du', 'la', 'le', 'des', 'et', 'ou', 'dans', 'avec']
        words = name.split()
        
        while words and words[0].lower() in parasites and len(words[0]) <= 3:
            words = words[1:]
        
        if not words:
            return None
        
        clean_name = ' '.join(words)
        
        # Vérifier que le nom nettoyé est valide
        if len(clean_name) < 3 or not re.match(r'^[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß]', clean_name):
            return None
        
        return clean_name
    
    def extract_godparents(self, text: str) -> Dict[str, Optional[str]]:
        """Extraction spécialisée des parrains/marraines"""
        godparents = {'parrain': None, 'marraine': None}
        
        relationships = self.extract_relationships(text)
        
        for rel in relationships:
            if rel['type'] in ['parrain', 'marraine']:
                godparents[rel['type']] = rel['personne']
        
        return godparents
    
    def find_parents(self, text: str, child_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Trouve les parents d'un enfant spécifique"""
        relationships = self.extract_relationships(text)
        
        for rel in relationships:
            if (rel['type'] == 'filiation' and 
                rel['enfant'].lower() == child_name.lower()):
                return rel.get('pere'), rel.get('mere')
        
        return None, None