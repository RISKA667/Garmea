import re
from typing import List, Optional, Dict
from functools import lru_cache
from core.models import Person, PersonStatus, ValidationResult
from config.settings import ParserConfig

class GenderValidator:    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.feminine_indicators = [
            'épouse de', 'femme de', 'veuve de', 'fille de',
            'marraine', 'dame', 'demoiselle', 'madame'
        ]
        
        self.masculine_indicators = [
            'époux de', 'mari de', 'veuf de', 'fils de',
            'parrain', 'sieur', 'seigneur', 'monsieur'
        ]
        
        self.masculine_titles = {PersonStatus.SIEUR, PersonStatus.SEIGNEUR, PersonStatus.ECUYER}
        self.feminine_titles = set() 
        self.masculine_professions = {
            'curé', 'prêtre', 'avocat', 'conseiller', 'notaire',
            'marchand', 'laboureur', 'écuyer'
        }
        
        self.feminine_professions = {
            'sage-femme', 'servante', 'couturière'
        }
    
    @lru_cache(maxsize=1000)
    def detect_gender_from_context(self, text: str, person_name: str) -> Optional[str]:
        if not text or not person_name:
            return None
        
        text_lower = text.lower()
        person_lower = person_name.lower()
        person_pos = text_lower.find(person_lower)
        if person_pos == -1:
            return None
        
        start = max(0, person_pos - 100)
        end = min(len(text), person_pos + len(person_name) + 100)
        context = text_lower[start:end]
        feminine_count = sum(1 for indicator in self.feminine_indicators 
                           if indicator in context)
        masculine_count = sum(1 for indicator in self.masculine_indicators 
                            if indicator in context)
        
        if feminine_count > masculine_count:
            return 'F'
        elif masculine_count > feminine_count:
            return 'M'
        
        return None
    
    def validate_person_gender(self, person: Person, context: str = "") -> ValidationResult:
        errors = []
        warnings = []
        confidence = 1.0
        detected_gender = self.detect_gender_from_context(context, person.full_name)
        
        # Vérifier cohérence titre/genre
        if person.statut in self.masculine_titles and detected_gender == 'F':
            errors.append(f"Titre masculin '{person.statut.value}' attribué à une femme")
            confidence -= 0.4
        
        # Vérifier cohérence profession/genre (avec tolérance historique)
        for profession in person.profession:
            if (profession in self.masculine_professions and 
                detected_gender == 'F' and 
                profession in ['curé', 'prêtre']):  # Professions strictement masculines
                errors.append(f"Profession masculine '{profession}' attribuée à une femme")
                confidence -= 0.3
        
        # Vérifications spécifiques aux femmes mariées
        if detected_gender == 'F':
            if person.statut in self.masculine_titles:
                # Les femmes peuvent porter le titre de leur mari, mais c'est inhabituel
                warnings.append(f"Femme avec titre masculin '{person.statut.value}' (hérité du mari ?)")
                confidence -= 0.1
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            confidence_score=max(0.0, confidence)
        )
    
    def correct_gender_inconsistencies(self, persons: List[Person], 
                                     contexts: Dict[int, str]) -> List[str]:
        """Corrige automatiquement les incohérences de genre"""
        corrections = []
        
        for person in persons:
            context = contexts.get(person.id, "")
            result = self.validate_person_gender(person, context)
            
            if not result.is_valid:
                for error in result.errors:
                    if "Titre masculin" in error and "femme" in error:
                        # Supprimer le titre masculin
                        old_status = person.statut
                        person.statut = None
                        corrections.append(
                            f"CORRECTION: Titre '{old_status.value}' supprimé pour "
                            f"{person.full_name} (femme)"
                        )
        
        return corrections
    
    def infer_gender_from_relations(self, person: Person, all_persons: List[Person], 
                                  relationships: List[Dict]) -> Optional[str]:
        """Infère le genre depuis les relations familiales"""
        for rel in relationships:
            if rel['type'] == 'épouse' and rel['personne1'] == person.full_name:
                return 'F'  # C'est l'épouse
            elif rel['type'] == 'épouse' and rel['personne2'] == person.full_name:
                return 'M'  # C'est l'époux
            elif rel['type'] == 'filiation':
                if rel['enfant'] == person.full_name:
                    return rel.get('genre', None)
                elif rel['pere'] == person.full_name:
                    return 'M'
                elif rel['mere'] == person.full_name:
                    return 'F'
            elif rel['type'] == 'parrain' and rel['personne'] == person.full_name:
                return 'M'
            elif rel['type'] == 'marraine' and rel['personne'] == person.full_name:
                return 'F'
        
        return None