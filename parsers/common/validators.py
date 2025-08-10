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
    details: Dict[str, any] = None

class NameValidator:
    def __init__(self):
        self.valid_first_names = {
            'Jean', 'Pierre', 'Jacques', 'Nicolas', 'François', 'Louis', 'Antoine',
            'Michel', 'Guillaume', 'Charles', 'Philippe', 'Gabriel', 'Thomas',
            'André', 'Claude', 'Henri', 'Paul', 'Denis', 'Étienne', 'Martin',
            'Barthélemy', 'Laurent', 'Julien', 'Gilles', 'Robert', 'Christophe',
            'Marie', 'Jeanne', 'Catherine', 'Marguerite', 'Anne', 'Françoise',
            'Madeleine', 'Louise', 'Élisabeth', 'Marthe', 'Agnès', 'Nicole',
            'Barbe', 'Suzanne', 'Michelle', 'Jacqueline', 'Antoinette',
            
            # Variantes anciennes ajoutées
            'Jehan', 'Michiel', 'Guillemette', 'Mahieu', 'Anthoine', 'Robinet',
            'Pérot', 'Perrin', 'Colin', 'Robin', 'Noël', 'Mathieu', 'Mathurin',
            'Raoul', 'Renaud', 'Regnault', 'Thibault', 'Arnaud', 'Bertrand',
            'Germain', 'Sébastien', 'Vincent', 'Yves', 'Yvon'
        }
        
        self.valid_family_names = {
            'Le Roy', 'Le Comte', 'Le Baron', 'Le Boucher', 'Le Barbier', 'Le Charpentier',
            'Martin', 'Bernard', 'Thomas', 'Petit', 'Robert', 'Richard', 'Durand',
            'Dubois', 'Moreau', 'Laurent', 'Simon', 'Michel', 'Lefebvre', 'Leroy',
            'Roux', 'David', 'Bertrand', 'Morel', 'Fournier', 'Girard', 'Bonnet',
            'Dupont', 'Lambert', 'Fontaine', 'Rousseau', 'Vincent', 'Muller',
            'Mercier', 'Boyer', 'Blanc', 'Guerin', 'Boucher', 'Fernandez'
        }
        
        self.religious_titles = {'dom', 'père', 'abbé', 'prieur', 'frère', 'sœur', 'mère'}
        self.noble_titles = {'sieur', 'sr', 'seigneur', 'sgr', 'écuyer', 'éc', 'noble', 'damoiselle', 'dame'}
        self.particles = {'de', 'du', 'des', 'le', 'la', 'les', "d'", 'von', 'van'}
        
        self.forbidden_words = {
            'archives', 'calvados', 'registre', 'paroisse', 'page', 'folio',
            'acte', 'baptême', 'mariage', 'décès', 'inhumation', 'témoin',
            'inventaire', 'sommaire', 'table', 'index', 'document', 'fichier'
        }
        
        self.location_indicators = {
            'paroisse', 'église', 'chapelle', 'cathédrale', 'abbaye',
            'clos', 'champ', 'pré', 'jardin', 'verger', 'rue', 'place'
        }
        
        self.forbidden_patterns = [
            re.compile(r'\d{3,}'),  # Séquences de 3+ chiffres
            re.compile(r'^[^A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß]'),  # Ne commence pas par majuscule
            re.compile(r'[<>@#$%^&*()]'),  # Caractères spéciaux
            re.compile(r'^.{1,2}$'),  # Trop court
            re.compile(r'^.{80,}$'),  # Trop long
            re.compile(r'^[A-Z]{3,}$'),  # Que des majuscules
            re.compile(r'^\d+$'),  # Que des chiffres
        ]
    
    @cached("name_validation")
    def validate_name(self, name: str, context: str = "") -> ValidationResult:
        errors = []
        warnings = []
        score = 0.0
        details = {}
        
        if not name or not name.strip():
            return ValidationResult(False, 0.0, ["Nom vide"], [], 0.0)
        
        name_clean = name.strip()
        words = name_clean.split()
        
        # Vérification des patterns interdits
        for pattern in self.forbidden_patterns:
            if pattern.search(name_clean):
                errors.append(f"Pattern interdit détecté: {pattern.pattern}")
        
        # Vérification des mots interdits
        for word in words:
            word_lower = word.lower()
            if word_lower in self.forbidden_words:
                errors.append(f"Mot interdit: {word}")
            if word_lower in self.location_indicators:
                errors.append(f"Indicateur de lieu: {word}")
        
        # Analyse de la structure
        structure_analysis = self._analyze_name_structure(words)
        details.update(structure_analysis)
        
        # Score pour le prénom
        if structure_analysis['first_names']:
            first_name = structure_analysis['first_names'][0]
            if first_name in self.valid_first_names:
                score += 0.4
                details['known_first_name'] = True
            elif self._is_plausible_first_name(first_name):
                score += 0.2
                warnings.append(f"Prénom non reconnu mais plausible: {first_name}")
                details['plausible_first_name'] = True
            else:
                score += 0.1
                warnings.append(f"Prénom non reconnu: {first_name}")
        
        # Score pour le nom de famille
        if structure_analysis['family_name']:
            family_name = structure_analysis['family_name']
            full_family = ' '.join(structure_analysis['particles'] + [family_name])
            if full_family in self.valid_family_names:
                score += 0.3
                details['known_family_name'] = True
            elif self._is_plausible_family_name(family_name):
                score += 0.2
                details['plausible_family_name'] = True
            else:
                score += 0.1
        
        # Bonus pour structure complexe
        if len(words) >= 2:
            score += 0.2
        if structure_analysis['title']:
            score += 0.1
        if structure_analysis['particles']:
            score += 0.1
        
        # Analyse contextuelle
        if context:
            context_analysis = self._analyze_context(context, name_clean)
            score += context_analysis['context_bonus']
            details['context_analysis'] = context_analysis
            if context_analysis['warnings']:
                warnings.extend(context_analysis['warnings'])
        
        # Vérifications supplémentaires
        if any(char.isupper() for char in name_clean):
            score += 0.05
        
        if re.search(r'[àáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]', name_clean.lower()):
            score += 0.05
        
        if '-' in name_clean:
            score += 0.05
        
        # Pénalités
        digit_ratio = sum(1 for c in name_clean if c.isdigit()) / len(name_clean)
        if digit_ratio > 0.1:
            score -= 0.3
            warnings.append(f"Ratio de chiffres élevé: {digit_ratio:.2f}")
        
        confidence = min(score, 1.0)
        is_valid = len(errors) == 0 and confidence > 0.3
        
        return ValidationResult(is_valid, confidence, errors, warnings, score, details)
    
    def _analyze_name_structure(self, words: List[str]) -> Dict[str, any]:
        """Analyse la structure d'un nom complet"""
        structure = {
            'title': '',
            'first_names': [],
            'particles': [],
            'family_name': '',
            'word_count': len(words)
        }
        
        if not words:
            return structure
        
        current_index = 0
        
        # Vérification du titre
        if words[0].lower() in self.religious_titles or words[0].lower() in self.noble_titles:
            structure['title'] = words[0]
            current_index = 1
        
        # Traitement des mots restants
        remaining_words = words[current_index:]
        
        if not remaining_words:
            return structure
        
        # Si un seul mot restant, c'est le nom de famille
        if len(remaining_words) == 1:
            structure['family_name'] = remaining_words[0]
            return structure
        
        # Recherche des particules
        for i, word in enumerate(remaining_words):
            if word.lower() in self.particles:
                # La particule et tout ce qui suit forment le nom de famille
                structure['particles'] = remaining_words[i:i+1]
                structure['family_name'] = ' '.join(remaining_words[i+1:]) if i+1 < len(remaining_words) else ''
                structure['first_names'] = remaining_words[:i]
                return structure
        
        # Pas de particule trouvée : dernier mot = nom de famille
        structure['first_names'] = remaining_words[:-1]
        structure['family_name'] = remaining_words[-1]
        
        return structure
    
    def _is_plausible_first_name(self, name: str) -> bool:
        """Vérifie si un nom pourrait être un prénom plausible"""
        if len(name) < 2:
            return False
        
        # Doit commencer par une majuscule
        if not name[0].isupper():
            return False
        
        # Terminaisons typiques de prénoms féminins
        feminine_endings = ['e', 'ette', 'ine', 'elle', 'ienne']
        if any(name.lower().endswith(ending) for ending in feminine_endings):
            return True
        
        # Terminaisons typiques de prénoms masculins
        masculine_endings = ['ard', 'bert', 'mund', 'ric', 'ulf']
        if any(name.lower().endswith(ending) for ending in masculine_endings):
            return True
        
        # Longueur raisonnable
        if 3 <= len(name) <= 15:
            return True
        
        return False
    
    def _is_plausible_family_name(self, name: str) -> bool:
        """Vérifie si un nom pourrait être un nom de famille plausible"""
        if len(name) < 2:
            return False
        
        # Doit commencer par une majuscule
        if not name[0].isupper():
            return False
        
        # Préfixes typiques de noms de famille
        prefixes = ['Mc', 'Mac', 'O\'', 'De', 'Du', 'Le', 'La']
        if any(name.startswith(prefix) for prefix in prefixes):
            return True
        
        # Suffixes typiques
        suffixes = ['son', 'sen', 'ez', 'ez', 'oux', 'ard', 'ot', 'et', 'in', 'on']
        if any(name.lower().endswith(suffix) for suffix in suffixes):
            return True
        
        return True  # Par défaut, on accepte
    
    def _analyze_context(self, context: str, name: str) -> Dict[str, any]:
        """Analyse le contexte pour valider un nom"""
        context_lower = context.lower()
        analysis = {
            'context_bonus': 0.0,
            'genealogical_context': False,
            'location_context': False,
            'religious_context': False,
            'warnings': []
        }
        
        # Contexte généalogique
        genealogical_terms = ['fils', 'fille', 'épouse', 'mari', 'père', 'mère', 'baptême', 'mariage', 'décès']
        if any(term in context_lower for term in genealogical_terms):
            analysis['genealogical_context'] = True
            analysis['context_bonus'] += 0.15
        
        # Contexte religieux
        religious_terms = ['curé', 'prêtre', 'vicaire', 'abbé', 'église', 'paroisse']
        if any(term in context_lower for term in religious_terms):
            analysis['religious_context'] = True
            analysis['context_bonus'] += 0.1
        
        # Contexte de lieu (suspect pour un nom de personne)
        location_terms = ['rue', 'place', 'chemin', 'clos', 'champ']
        if any(term in context_lower for term in location_terms):
            analysis['location_context'] = True
            analysis['context_bonus'] -= 0.2
            analysis['warnings'].append("Contexte géographique détecté")
        
        # Présence de dates
        if re.search(r'\b\d{4}\b', context):
            analysis['context_bonus'] += 0.05
        
        return analysis

class RelationshipValidator:
    def __init__(self):
        self.relationship_types = {'filiation', 'marriage', 'godparent'}
        self.required_fields = {
            'filiation': {'child', 'father'},
            'marriage': {'spouse1', 'spouse2'},
            'godparent': {'godchild', 'godparent'}
        }
        
        self.suspicious_combinations = [
            # Mêmes noms pour différents rôles
            lambda rel: rel.get('child', '').lower() == rel.get('father', '').lower(),
            lambda rel: rel.get('child', '').lower() == rel.get('mother', '').lower(),
            lambda rel: rel.get('spouse1', '').lower() == rel.get('spouse2', '').lower(),
        ]
    
    @cached("relationship_validation")
    def validate_relationship(self, rel_type: str, entities: Dict[str, str], context: str = "") -> ValidationResult:
        errors = []
        warnings = []
        score = 0.0
        details = {}
        
        if rel_type not in self.relationship_types:
            errors.append(f"Type de relation invalide: {rel_type}")
        
        # Vérification des champs requis
        required = self.required_fields.get(rel_type, set())
        for field in required:
            if field not in entities or not entities[field]:
                errors.append(f"Champ requis manquant: {field}")
        
        # Validation des noms individuels
        name_validator = NameValidator()
        valid_names = 0
        total_names = 0
        
        for role, name in entities.items():
            if name:
                total_names += 1
                validation = name_validator.validate_name(name, context)
                if validation.is_valid:
                    valid_names += 1
                    score += validation.score * 0.3
                else:
                    warnings.extend([f"{role}: {error}" for error in validation.errors])
        
        # Vérifications de cohérence
        for check in self.suspicious_combinations:
            if check(entities):
                warnings.append("Noms identiques détectés dans des rôles différents")
                score -= 0.3
        
        # Bonus selon le type de relation
        if rel_type == 'filiation':
            if 'mother' in entities and entities['mother']:
                score += 0.2
                details['has_mother'] = True
            if 'father' in entities and entities['father']:
                details['has_father'] = True
        elif rel_type == 'marriage':
            score += 0.1
        
        # Analyse contextuelle
        if context:
            context_analysis = self._analyze_relationship_context(context, rel_type)
            score += context_analysis['bonus']
            details['context_analysis'] = context_analysis
        
        # Calcul final
        if total_names > 0:
            name_validity_ratio = valid_names / total_names
            score += name_validity_ratio * 0.4
        
        confidence = min(score, 1.0)
        is_valid = len(errors) == 0 and confidence > 0.5
        
        return ValidationResult(is_valid, confidence, errors, warnings, score, details)
    
    def _analyze_relationship_context(self, context: str, rel_type: str) -> Dict[str, any]:
        """Analyse le contexte d'une relation"""
        context_lower = context.lower()
        analysis = {'bonus': 0.0, 'indicators': []}
        
        type_indicators = {
            'filiation': ['fils', 'fille', 'enfant', 'née', 'baptême'],
            'marriage': ['épouse', 'mari', 'époux', 'femme', 'mariage', 'mariée'],
            'godparent': ['parrain', 'marraine', 'filleul', 'filleule']
        }
        
        if rel_type in type_indicators:
            for indicator in type_indicators[rel_type]:
                if indicator in context_lower:
                    analysis['bonus'] += 0.1
                    analysis['indicators'].append(indicator)
        
        # Présence de dates
        if re.search(r'\b\d{4}\b', context):
            analysis['bonus'] += 0.05
        
        # Contexte religieux
        religious_terms = ['curé', 'prêtre', 'église', 'paroisse', 'baptême']
        if any(term in context_lower for term in religious_terms):
            analysis['bonus'] += 0.05
        
        return analysis

class DateValidator:
    def __init__(self):
        self.valid_year_range = (1500, 1950)
        self.months = {
            'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6,
            'juillet': 7, 'août': 8, 'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12,
            'janv': 1, 'fév': 2, 'sept': 9, 'oct': 10, 'nov': 11, 'déc': 12
        }
        
        self.republican_months = {
            'vendémiaire': 1, 'brumaire': 2, 'frimaire': 3, 'nivôse': 4,
            'pluviôse': 5, 'ventôse': 6, 'germinal': 7, 'floréal': 8,
            'prairial': 9, 'messidor': 10, 'thermidor': 11, 'fructidor': 12
        }
    
    @cached("date_validation")
    def validate_date(self, year: Optional[int], month: Optional[int], day: Optional[int], 
                     date_type: str = "standard") -> ValidationResult:
        errors = []
        warnings = []
        score = 0.0
        details = {'date_type': date_type}
        
        # Validation de l'année
        if year is not None:
            if self.valid_year_range[0] <= year <= self.valid_year_range[1]:
                score += 0.5
                details['year_valid'] = True
            else:
                errors.append(f"Année hors de la plage valide: {year}")
                details['year_valid'] = False
        
        # Validation du mois
        if month is not None:
            if date_type == "republican":
                if 1 <= month <= 12:
                    score += 0.25
                    details['month_valid'] = True
                else:
                    errors.append(f"Mois républicain invalide: {month}")
            else:
                if 1 <= month <= 12:
                    score += 0.25
                    details['month_valid'] = True
                else:
                    errors.append(f"Mois invalide: {month}")
        
        # Validation du jour
        if day is not None:
            if 1 <= day <= 31:
                score += 0.25
                details['day_valid'] = True
                # Vérifications spécifiques par mois
                if month in [4, 6, 9, 11] and day > 30:
                    warnings.append("Jour potentiellement invalide pour ce mois")
                elif month == 2 and day > 29:
                    warnings.append("Jour invalide pour février")
                elif month == 2 and day == 29 and year and not self._is_leap_year(year):
                    warnings.append("29 février dans une année non bissextile")
            else:
                errors.append(f"Jour invalide: {day}")
                details['day_valid'] = False
        
        confidence = min(score, 1.0)
        is_valid = len(errors) == 0
        
        return ValidationResult(is_valid, confidence, errors, warnings, score, details)
    
    def _is_leap_year(self, year: int) -> bool:
        """Vérifie si une année est bissextile"""
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

class TextQualityValidator:
    def __init__(self):
        self.min_length = 10
        self.max_length = 100000
        self.quality_indicators = {
            'proper_names': re.compile(r'\b[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+\b'),
            'dates': re.compile(r'\b\d{4}\b'),
            'genealogical_terms': re.compile(r'\b(fils|fille|épouse|mari|parrain|marraine|baptême|mariage|décès)\b', re.IGNORECASE),
            'religious_terms': re.compile(r'\b(curé|prêtre|église|paroisse|dom|abbé)\b', re.IGNORECASE),
            'noble_terms': re.compile(r'\b(sieur|seigneur|écuyer|dame|comte|baron)\b', re.IGNORECASE)
        }
    
    @cached("text_quality")
    def validate_text_quality(self, text: str) -> ValidationResult:
        errors = []
        warnings = []
        score = 0.0
        details = {}
        
        text_length = len(text)
        details['length'] = text_length
        
        # Validation de la longueur
        if text_length < self.min_length:
            errors.append(f"Texte trop court: {text_length} caractères")
        elif text_length > self.max_length:
            warnings.append(f"Texte très long: {text_length} caractères")
        else:
            score += 0.2
        
        # Analyse des indicateurs de qualité
        indicator_scores = {}
        for indicator_name, pattern in self.quality_indicators.items():
            matches = len(pattern.findall(text))
            indicator_scores[indicator_name] = matches
            if matches > 0:
                score += min(matches * 0.1, 0.3)
        
        details['indicators'] = indicator_scores
        
        # Analyse de la variété des caractères
        char_variety = len(set(text.lower())) / max(len(text), 1)
        details['char_variety'] = char_variety
        if char_variety > 0.05:
            score += 0.2
        else:
            warnings.append("Faible variété de caractères")
        
        # Analyse de la structure
        sentences = text.split('.')
        details['sentence_count'] = len(sentences)
        if len(sentences) > 1:
            score += 0.1
        
        # Détection d'erreurs OCR
        ocr_error_patterns = [r'[il1]{3,}', r'rn[a-z]', r'cl[aeiou]', r'\d+[a-z]']
        ocr_errors = sum(len(re.findall(pattern, text)) for pattern in ocr_error_patterns)
        details['ocr_errors'] = ocr_errors
        if ocr_errors > text_length * 0.02:  # Plus de 2% d'erreurs OCR
            warnings.append(f"Nombreuses erreurs OCR détectées: {ocr_errors}")
            score -= 0.1
        
        confidence = min(score, 1.0)
        is_valid = len(errors) == 0
        
        return ValidationResult(is_valid, confidence, errors, warnings, score, details)

# Instances globales
name_validator = NameValidator()
relationship_validator = RelationshipValidator()
date_validator = DateValidator()
text_quality_validator = TextQualityValidator()