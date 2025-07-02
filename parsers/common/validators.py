import re
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from .cache_manager import cached

@dataclass
class ValidationResult:
    is_valid: bool
    confidence: float
    errors: List[str]
    warnings: List[str]
    score: float

class NameValidator:
    def __init__(self):
        self.valid_first_names = {
            'Jean', 'Pierre', 'Jacques', 'Nicolas', 'François', 'Louis', 'Antoine',
            'Michel', 'Guillaume', 'Charles', 'Philippe', 'Gabriel', 'Thomas',
            'André', 'Claude', 'Henri', 'Paul', 'Denis', 'Étienne', 'Martin',
            'Barthélemy', 'Laurent', 'Julien', 'Gilles', 'Robert', 'Christophe',
            'Marie', 'Jeanne', 'Catherine', 'Marguerite', 'Anne', 'Françoise',
            'Madeleine', 'Louise', 'Élisabeth', 'Marthe', 'Agnès', 'Nicole',
            'Barbe', 'Suzanne', 'Michelle', 'Jacqueline', 'Antoinette'
        }
        
        self.forbidden_words = {
            'archives', 'calvados', 'registre', 'paroisse', 'page', 'folio',
            'acte', 'baptême', 'mariage', 'décès', 'inhumation', 'témoin'
        }
        
        self.forbidden_patterns = [
            re.compile(r'\d{3,}'),
            re.compile(r'^[^A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß]'),
            re.compile(r'[<>@#$%^&*()]'),
            re.compile(r'^.{1,2}$'),
            re.compile(r'^.{50,}$')
        ]
    
    @cached("name_validation")
    def validate_name(self, name: str) -> ValidationResult:
        errors = []
        warnings = []
        score = 0.0
        
        if not name or not name.strip():
            return ValidationResult(False, 0.0, ["Nom vide"], [], 0.0)
        
        name_clean = name.strip()
        words = name_clean.split()
        
        for pattern in self.forbidden_patterns:
            if pattern.search(name_clean):
                errors.append(f"Pattern interdit détecté: {pattern.pattern}")
        
        for word in words:
            if word.lower() in self.forbidden_words:
                errors.append(f"Mot interdit: {word}")
        
        if len(words) > 0:
            first_word = words[0]
            if first_word in self.valid_first_names:
                score += 0.4
            elif first_word.endswith('e') and len(first_word) > 3:
                score += 0.2
                warnings.append("Prénom possiblement féminin non reconnu")
            elif len(first_word) > 3:
                score += 0.1
                warnings.append("Prénom non reconnu")
        
        if len(words) >= 2:
            score += 0.3
        
        if len(words) == 1:
            warnings.append("Nom composé d'un seul mot")
        
        if any(char.isupper() for char in name_clean):
            score += 0.1
        
        if re.search(r'[àáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]', name_clean.lower()):
            score += 0.1
        
        if '-' in name_clean:
            score += 0.1
        
        confidence = min(score, 1.0)
        is_valid = len(errors) == 0 and confidence > 0.3
        
        return ValidationResult(is_valid, confidence, errors, warnings, score)

class RelationshipValidator:
    def __init__(self):
        self.relationship_types = {'filiation', 'marriage', 'godparent'}
        self.required_fields = {
            'filiation': {'child', 'father'},
            'marriage': {'spouse1', 'spouse2'},
            'godparent': {'godchild', 'godparent'}
        }
    
    @cached("relationship_validation")
    def validate_relationship(self, rel_type: str, entities: Dict[str, str]) -> ValidationResult:
        errors = []
        warnings = []
        score = 0.0
        
        if rel_type not in self.relationship_types:
            errors.append(f"Type de relation invalide: {rel_type}")
        
        required = self.required_fields.get(rel_type, set())
        for field in required:
            if field not in entities or not entities[field]:
                errors.append(f"Champ requis manquant: {field}")
        
        name_validator = NameValidator()
        valid_names = 0
        total_names = 0
        
        for role, name in entities.items():
            if name:
                total_names += 1
                validation = name_validator.validate_name(name)
                if validation.is_valid:
                    valid_names += 1
                    score += validation.score * 0.3
                else:
                    warnings.extend([f"{role}: {error}" for error in validation.errors])
        
        if total_names > 0:
            name_validity_ratio = valid_names / total_names
            score += name_validity_ratio * 0.4
        
        if rel_type == 'filiation':
            if 'mother' in entities and entities['mother']:
                score += 0.2
        elif rel_type == 'marriage':
            score += 0.1
        
        confidence = min(score, 1.0)
        is_valid = len(errors) == 0 and confidence > 0.5
        
        return ValidationResult(is_valid, confidence, errors, warnings, score)

class DateValidator:
    def __init__(self):
        self.valid_year_range = (1500, 1950)
        self.months = {
            'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6,
            'juillet': 7, 'août': 8, 'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
        }
    
    @cached("date_validation")
    def validate_date(self, year: Optional[int], month: Optional[int], day: Optional[int]) -> ValidationResult:
        errors = []
        warnings = []
        score = 0.0
        
        if year is not None:
            if self.valid_year_range[0] <= year <= self.valid_year_range[1]:
                score += 0.5
            else:
                errors.append(f"Année hors de la plage valide: {year}")
        
        if month is not None:
            if 1 <= month <= 12:
                score += 0.25
            else:
                errors.append(f"Mois invalide: {month}")
        
        if day is not None:
            if 1 <= day <= 31:
                score += 0.25
                if month in [4, 6, 9, 11] and day > 30:
                    warnings.append("Jour potentiellement invalide pour ce mois")
                elif month == 2 and day > 29:
                    warnings.append("Jour invalide pour février")
            else:
                errors.append(f"Jour invalide: {day}")
        
        confidence = min(score, 1.0)
        is_valid = len(errors) == 0
        
        return ValidationResult(is_valid, confidence, errors, warnings, score)

class TextQualityValidator:
    def __init__(self):
        self.min_length = 10
        self.max_length = 100000
        self.quality_indicators = {
            'proper_names': re.compile(r'\b[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+\b'),
            'dates': re.compile(r'\b\d{4}\b'),
            'genealogical_terms': re.compile(r'\b(fils|fille|épouse|mari|parrain|marraine|baptême|mariage|décès)\b', re.IGNORECASE)
        }
    
    @cached("text_quality")
    def validate_text_quality(self, text: str) -> ValidationResult:
        errors = []
        warnings = []
        score = 0.0
        
        if len(text) < self.min_length:
            errors.append(f"Texte trop court: {len(text)} caractères")
        elif len(text) > self.max_length:
            warnings.append(f"Texte très long: {len(text)} caractères")
        else:
            score += 0.2
        
        for indicator_name, pattern in self.quality_indicators.items():
            matches = len(pattern.findall(text))
            if matches > 0:
                score += min(matches * 0.1, 0.3)
        
        char_variety = len(set(text.lower())) / max(len(text), 1)
        if char_variety > 0.05:
            score += 0.2
        else:
            warnings.append("Faible variété de caractères")
        
        confidence = min(score, 1.0)
        is_valid = len(errors) == 0
        
        return ValidationResult(is_valid, confidence, errors, warnings, score)

name_validator = NameValidator()
relationship_validator = RelationshipValidator()
date_validator = DateValidator()
text_quality_validator = TextQualityValidator()