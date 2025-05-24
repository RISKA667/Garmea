import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from functools import lru_cache

from core.models import Person, ActeParoissial, ValidationResult
from config.settings import ParserConfig
from parsers.date_parser import DateParser

class ChronologyValidator:
    """Validateur chronologique optimisé"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.date_parser = DateParser(config)
        self.logger = logging.getLogger(__name__)
        
        # Cache des validations pour éviter les recalculs
        self._validation_cache = {}
    
    def validate_person_chronology(self, person: Person) -> ValidationResult:
        """Validation chronologique complète d'une personne"""
        errors = []
        warnings = []
        confidence = 1.0
        
        # Vérification naissance/décès
        if person.date_naissance and person.date_deces:
            birth_year = self._extract_year(person.date_naissance)
            death_year = self._extract_year(person.date_deces)
            
            if birth_year and death_year:
                if death_year <= birth_year:
                    errors.append(f"Date de décès ({death_year}) antérieure à la naissance ({birth_year})")
                    confidence -= 0.4
                
                # Vérifier espérance de vie plausible
                age_at_death = death_year - birth_year
                if age_at_death > 100:
                    warnings.append(f"Âge au décès très élevé ({age_at_death} ans)")
                    confidence -= 0.1
        
        # Vérification cohérence mariage/naissance
        if person.date_naissance and person.date_mariage:
            birth_year = self._extract_year(person.date_naissance)
            marriage_year = self._extract_year(person.date_mariage)
            
            if birth_year and marriage_year:
                age_at_marriage = marriage_year - birth_year
                if age_at_marriage < 12:
                    errors.append(f"Âge au mariage trop jeune ({age_at_marriage} ans)")
                    confidence -= 0.3
                elif age_at_marriage > 60:
                    warnings.append(f"Âge au mariage tardif ({age_at_marriage} ans)")
                    confidence -= 0.1
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            confidence_score=max(0.0, confidence)
        )
    
    def validate_parent_child_coherence(self, parent: Person, child_birth_year: int) -> bool:
        """Valide qu'un parent peut avoir un enfant à une date donnée"""
        # Si le parent est décédé avant la naissance de l'enfant
        if parent.date_deces:
            parent_death_year = self._extract_year(parent.date_deces)
            if parent_death_year and parent_death_year < child_birth_year:
                return False
        
        # Si on connaît la naissance du parent, vérifier l'âge
        if parent.date_naissance:
            parent_birth_year = self._extract_year(parent.date_naissance)
            if parent_birth_year:
                age_at_child_birth = child_birth_year - parent_birth_year
                # Âge plausible pour avoir un enfant : 15-65 ans
                if not (15 <= age_at_child_birth <= 65):
                    return False
        
        return True
    
    def validate_and_correct_chronology(self, persons: List[Person], actes: List[ActeParoissial]) -> List[str]:
        """Validation et correction automatique des erreurs chronologiques"""
        corrections = []
        
        # 1. Valider les relations parent-enfant
        for acte in actes:
            if acte.pere_id and acte.year:
                pere = next((p for p in persons if p.id == acte.pere_id), None)
                if pere and not self.validate_parent_child_coherence(pere, acte.year):
                    correction = self._fix_parent_child_error(pere, acte, persons)
                    if correction:
                        corrections.append(correction)
        
        # 2. Valider les personnes individuellement
        for person in persons:
            result = self.validate_person_chronology(person)
            if not result.is_valid:
                for error in result.errors:
                    corrections.append(f"ERREUR {person.full_name}: {error}")
        
        return corrections
    
    def _fix_parent_child_error(self, wrong_parent: Person, acte: ActeParoissial, 
                              all_persons: List[Person]) -> Optional[str]:
        """Tente de corriger une erreur de filiation chronologique"""
        # Chercher un homonyme vivant à la date de l'acte
        homonym = self._find_living_homonym(wrong_parent, acte.year, all_persons)
        
        if homonym:
            # Rediriger vers l'homonyme
            old_id = acte.pere_id
            acte.pere_id = homonym.id
            
            return (f"CORRECTION: Père de l'acte {acte.id} redirigé de "
                   f"{wrong_parent.full_name} (†{wrong_parent.date_deces}) vers "
                   f"homonyme vivant {homonym.full_name} (ID: {homonym.id})")
        
        return f"ERREUR NON CORRIGÉE: {wrong_parent.full_name} décédé avant naissance enfant ({acte.year})"
    
    def _find_living_homonym(self, deceased_person: Person, target_year: int, 
                           all_persons: List[Person]) -> Optional[Person]:
        """Trouve un homonyme vivant à la date cible"""
        for person in all_persons:
            if (person.id != deceased_person.id and
                person.nom == deceased_person.nom and
                person.prenom == deceased_person.prenom):
                
                # Vérifier que cet homonyme pourrait être vivant à target_year
                if self._could_be_alive_at_year(person, target_year):
                    return person
        
        return None
    
    def _could_be_alive_at_year(self, person: Person, year: int) -> bool:
        """Vérifie si une personne pourrait être vivante à une année donnée"""
        # Si date de décès connue et postérieure à l'année cible
        if person.date_deces:
            death_year = self._extract_year(person.date_deces)
            if death_year and death_year <= year:
                return False
        
        # Si date de naissance connue et cohérente
        if person.date_naissance:
            birth_year = self._extract_year(person.date_naissance)
            if birth_year:
                age_at_year = year - birth_year
                # Âge plausible (pas plus de 100 ans)
                if age_at_year < 0 or age_at_year > 100:
                    return False
        
        return True
    
    @lru_cache(maxsize=1000)
    def _extract_year(self, date_str: str) -> Optional[int]:
        """Extraction d'année avec cache"""
        if not date_str:
            return None
        
        return self.date_parser.get_year_from_text(date_str)
    
    def generate_chronology_report(self, persons: List[Person], actes: List[ActeParoissial]) -> Dict:
        """Génère un rapport détaillé de cohérence chronologique"""
        issues = []
        
        for person in persons:
            person_issues = []
            result = self.validate_person_chronology(person)
            
            if result.errors:
                person_issues.extend(result.errors)
            
            if result.warnings:
                person_issues.extend([f"AVERTISSEMENT: {w}" for w in result.warnings])
            
            # Vérifier cohérence avec les actes
            person_actes = [a for a in actes if 
                          a.personne_principale_id == person.id or 
                          a.pere_id == person.id or 
                          a.mere_id == person.id]
            
            for acte in person_actes:
                if acte.year and person.date_deces:
                    death_year = self._extract_year(person.date_deces)
                    if death_year and acte.year > death_year:
                        person_issues.append(f"Présent dans acte {acte.year} après décès {death_year}")
            
            if person_issues:
                issues.append({
                    'person': person.full_name,
                    'person_id': person.id,
                    'issues': person_issues,
                    'confidence': result.confidence_score
                })
        
        return {
            'total_issues': len(issues),
            'persons_with_issues': issues,
            'validation_date': datetime.now().isoformat(),
            'total_persons_validated': len(persons),
            'total_actes_validated': len(actes)
        }
