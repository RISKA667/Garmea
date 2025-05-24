import re
from typing import List, Optional, Dict, Set
from functools import lru_cache
from config.settings import ParserConfig
from core.models import PersonStatus

class ProfessionParser:
    """Parser optimisé pour professions, statuts et terres"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        
        # Dictionnaires de professions (extensibles via config)
        self.professions_dict = {
            'curé': ['curé', 'curés'],
            'prêtre': ['prestre', 'prestres', 'prêtre', 'prêtres'],
            'avocat': ['avocat'],
            'avocat du Roi': ['avocat du roi'],
            'conseiller': ['conseiller', 'conseillers'],
            'trésorier': ['trésorier', 'trésoriers'],
            'notaire': ['notaire', 'notaires'],
            'marchand': ['marchand', 'marchands'],
            'laboureur': ['laboureur', 'laboureurs']
        }
        
        self.statuts_dict = {
            'seigneur': ['seigneur', 'sgr'],
            'sieur': ['sieur', 'sr'],
            'écuyer': ['écuyer', 'éc.', 'ecuyer'],
            'noble': ['noble', 'nob.'],
            'bourgeois': ['bourgeois', 'bourg.']
        }
        
        # Compilation des patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile les patterns pour performance"""
        # Patterns pour terres (sr de [lieu])
        self.terre_patterns = [
            re.compile(r'(?:sr|sieur)\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)*)', re.IGNORECASE),
            re.compile(r'(?:sgr|seigneur)\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)*)', re.IGNORECASE)
        ]
    
    @lru_cache(maxsize=500)
    def extract_professions(self, context: str, person_name: str) -> List[str]:
        """Extraction des professions avec cache"""
        if not context or not person_name:
            return []
        
        context_lower = context.lower()
        person_lower = person_name.lower()
        
        # Localiser la personne dans le contexte
        person_pos = context_lower.find(person_lower)
        if person_pos == -1:
            return []
        
        # Contexte immédiat (±60 caractères)
        start = max(0, person_pos - 60)
        end = min(len(context), person_pos + len(person_name) + 60)
        immediate_context = context_lower[start:end]
        
        professions_found = []
        
        # Recherche des professions
        for profession, variants in self.professions_dict.items():
            for variant in variants:
                if variant in immediate_context:
                    # CORRECTION: Garder le terme exact utilisé
                    if variant in ['prestre', 'prestres']:
                        if 'prêtre' not in professions_found:
                            professions_found.append('prêtre')
                    elif profession not in professions_found:
                        professions_found.append(profession)
        
        # Gestion spéciale "conseiller ET avocat du Roi"
        if 'conseiller et avocat du roi' in immediate_context:
            professions_found = ['conseiller', 'avocat du Roi']
        
        return professions_found
    
    @lru_cache(maxsize=500)
    def extract_status(self, context: str, person_name: str) -> Optional[PersonStatus]:
        """Extraction du statut social avec cache"""
        if not context or not person_name:
            return None
        
        context_lower = context.lower()
        person_lower = person_name.lower()
        
        person_pos = context_lower.find(person_lower)
        if person_pos == -1:
            return None
        
        # Contexte immédiat
        start = max(0, person_pos - 60)
        end = min(len(context), person_pos + len(person_name) + 60)
        immediate_context = context_lower[start:end]
        
        # Hiérarchie des statuts (du plus élevé au moins élevé)
        status_hierarchy = [
            (PersonStatus.SEIGNEUR, ['seigneur', 'sgr']),
            (PersonStatus.ECUYER, ['écuyer', 'éc.', 'ecuyer']),
            (PersonStatus.SIEUR, ['sieur', 'sr'])
        ]
        
        # Prendre le statut le plus élevé trouvé
        for status, variants in status_hierarchy:
            for variant in variants:
                if variant in immediate_context:
                    return status
        
        return None
    
    @lru_cache(maxsize=300)
    def extract_lands(self, context: str, person_name: str) -> List[str]:
        """Extraction des terres possédées avec cache"""
        if not context:
            return []
        
        terres = []
        
        for pattern in self.terre_patterns:
            for match in pattern.finditer(context):
                terre = match.group(1).strip()
                if terre and terre not in terres:
                    terres.append(terre)
        
        return terres
    
    def is_ecclesiastical_profession(self, professions: List[str]) -> bool:
        """Vérifie si la personne a une profession ecclésiastique"""
        ecclesiastical = {'curé', 'prêtre', 'vicaire', 'chapelain', 'abbé'}
        return any(prof in ecclesiastical for prof in professions)