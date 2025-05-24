import re
from typing import List, Dict, Set
from functools import lru_cache

from config.settings import ParserConfig

class NameExtractor:
    """Extracteur de noms optimisé avec cache"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.known_places = set(config.known_places)
        
        # Patterns compilés pour performance
        self._compile_patterns()
        
        # Caches
        self._false_positives_cache = set()
        self._extraction_cache = {}
    
    def _compile_patterns(self):  # CORRECTION: Supprimer @lru_cache ici
        """Compile les patterns regex une seule fois"""
        self.name_patterns = [
            # Noms avec particules
            re.compile(r'\b([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)\s+(de\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)*)'),
            
            # Noms "Le + Nom"
            re.compile(r'\b([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)\s+(Le\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)'),
            
            # Noms composés doubles
            re.compile(r'\b([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+é?)')
        ]
    
    @lru_cache(maxsize=1000)
    def extract_complete_names(self, text: str) -> List[Dict]:
        """Extraction optimisée avec cache"""
        # Vérifier le cache
        cache_key = hash(text[:200])  # Hash des premiers 200 caractères
        if cache_key in self._extraction_cache:
            return self._extraction_cache[cache_key]
        
        persons = []
        found_names = set()
        
        for pattern in self.name_patterns:
            for match in pattern.finditer(text):
                prenom = match.group(1).strip()
                nom = match.group(2).strip()
                full_name = f"{prenom} {nom}"
                
                # Optimisation: vérification rapide des doublons
                if full_name in found_names:
                    continue
                
                # Optimisation: cache des faux positifs
                if full_name in self._false_positives_cache:
                    continue
                
                if self._is_valid_name(prenom, nom, full_name):
                    found_names.add(full_name)
                    context = self._extract_context(text, match.start(), match.end())
                    
                    person_info = {
                        'nom_complet': full_name,
                        'prenom': prenom,
                        'nom': nom,
                        'context': context,
                        # Extraction parallèle des autres attributs
                        **self._extract_attributes_batch(context, full_name)
                    }
                    persons.append(person_info)
                else:
                    self._false_positives_cache.add(full_name)
        
        # Mise en cache du résultat
        self._extraction_cache[cache_key] = persons
        return persons
    
    def _is_valid_name(self, prenom: str, nom: str, full_name: str) -> bool:
        """Validation optimisée des noms"""
        return (
            len(prenom) > 2 and len(nom) > 2 and
            not any(lieu in full_name for lieu in self.known_places)
        )
    
    def _extract_context(self, text: str, start: int, end: int, context_size: int = 200) -> str:
        """Extraction de contexte optimisée"""
        context_start = max(0, start - context_size)
        context_end = min(len(text), end + context_size)
        return text[context_start:context_end]
    
    def _extract_attributes_batch(self, context: str, full_name: str) -> Dict:
        """Extraction en lot de tous les attributs pour éviter les re-parsing"""
        # CORRECTION: Éviter les imports circulaires en créant des instances légères
        from parsers.profession_parser import ProfessionParser
        from parsers.relationship_parser import RelationshipParser
        
        # Créer des instances légères pour éviter la récursion
        profession_parser = ProfessionParser(self.config)
        relationship_parser = RelationshipParser(self.config)
        
        return {
            'professions': profession_parser.extract_professions(context, full_name),
            'statut': profession_parser.extract_status(context, full_name),
            'terres': profession_parser.extract_lands(context, full_name),
            'notable': self._is_notable(context),
            'relationships': relationship_parser.extract_relationships(context)
        }
    
    @lru_cache(maxsize=500)
    def _is_notable(self, context: str) -> bool:
        """Détection de notabilité avec cache"""
        context_lower = context.lower()
        notable_patterns = [
            "dans l'église", "dans l'eglise", "dans la chapelle",
            "sous le chœur", "près de l'autel", "inhumé dans"
        ]
        # CORRECTION: Ligne complète
        return any(pattern in context_lower for pattern in notable_patterns)
