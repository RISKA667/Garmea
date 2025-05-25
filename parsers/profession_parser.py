import re
import hashlib
from typing import List, Optional, Dict, Set
from config.settings import ParserConfig
from core.models import PersonStatus
from functools import lru_cache

class ProfessionParser:
    """Parser optimisé pour professions, statuts et terres"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        
        # Caches manuels
        self._profession_cache = {}
        self._status_cache = {}
        self._lands_cache = {}
        self._cache_max_size = 500
        
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
    
    def _create_cache_key(self, context: str, person_name: str) -> str:
        """Crée une clé de cache"""
        try:
            return hashlib.md5(f"{context[:200]}_{person_name}".encode('utf-8')).hexdigest()
        except Exception:
            return str(hash(f"{context[:200]}_{person_name}"))
    
    def _manage_cache_size(self, cache_dict: Dict):
        """Gère la taille du cache"""
        if len(cache_dict) > self._cache_max_size:
            keys_to_remove = list(cache_dict.keys())[:100]
            for key in keys_to_remove:
                cache_dict.pop(key, None)
    
    def extract_professions(self, context: str, person_name: str) -> List[str]:
        """Extraction des professions avec cache manuel"""
        if not context or not person_name:
            return []
        
        # Vérifier le cache
        cache_key = self._create_cache_key(context, person_name)
        if cache_key in self._profession_cache:
            return self._profession_cache[cache_key]
        
        context_lower = context.lower()
        person_lower = person_name.lower()
        
        # Localiser la personne dans le contexte
        person_pos = context_lower.find(person_lower)
        if person_pos == -1:
            self._profession_cache[cache_key] = []
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
        
        # Mettre en cache
        self._manage_cache_size(self._profession_cache)
        self._profession_cache[cache_key] = professions_found
        
        return professions_found
    
    def extract_status(self, context: str, person_name: str) -> Optional[PersonStatus]:
        """Extraction du statut social avec cache manuel"""
        if not context or not person_name:
            return None
        
        # Vérifier le cache
        cache_key = self._create_cache_key(context, person_name)
        if cache_key in self._status_cache:
            return self._status_cache[cache_key]
        
        context_lower = context.lower()
        person_lower = person_name.lower()
        
        person_pos = context_lower.find(person_lower)
        if person_pos == -1:
            self._status_cache[cache_key] = None
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
        
        result = None
        # Prendre le statut le plus élevé trouvé
        for status, variants in status_hierarchy:
            for variant in variants:
                if variant in immediate_context:
                    result = status
                    break
            if result:
                break
        
        # Mettre en cache
        self._manage_cache_size(self._status_cache)
        self._status_cache[cache_key] = result
        
        return result
    
    def extract_lands(self, context: str, person_name: str) -> List[str]:
        """Extraction des terres possédées avec cache manuel"""
        if not context:
            return []
        
        # Vérifier le cache
        cache_key = self._create_cache_key(context, person_name)
        if cache_key in self._lands_cache:
            return self._lands_cache[cache_key]
        
        terres = []
        
        for pattern in self.terre_patterns:
            for match in pattern.finditer(context):
                terre = match.group(1).strip()
                if terre and terre not in terres:
                    terres.append(terre)
        
        # Mettre en cache
        self._manage_cache_size(self._lands_cache)
        self._lands_cache[cache_key] = terres
        
        return terres
    
    def is_ecclesiastical_profession(self, professions: List[str]) -> bool:
        """Vérifie si la personne a une profession ecclésiastique"""
        ecclesiastical = {'curé', 'prêtre', 'vicaire', 'chapelain', 'abbé'}
        return any(prof in ecclesiastical for prof in professions)
    
    def clear_cache(self):
        """Vide tous les caches"""
        self._profession_cache.clear()
        self._status_cache.clear()
        self._lands_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Retourne les statistiques des caches"""
        return {
            'profession_cache_size': len(self._profession_cache),
            'status_cache_size': len(self._status_cache),
            'lands_cache_size': len(self._lands_cache),
            'total_cache_entries': len(self._profession_cache) + len(self._status_cache) + len(self._lands_cache)
        }