import re
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
from ..common import get_cache

@dataclass
class Person:
    id: str
    full_name: str
    first_names: List[str]
    family_name: str
    birth_date: Optional[datetime] = None
    death_date: Optional[datetime] = None
    birth_place: str = ""
    death_place: str = ""
    gender: Optional[str] = None
    confidence: float = 0.0
    sources: List[str] = None

@dataclass
class Relationship:
    person1_id: str
    person2_id: str
    relationship_type: str
    confidence: float
    source_text: str
    estimated: bool = False

@dataclass
class FamilyGroup:
    family_id: str
    father: Optional[Person] = None
    mother: Optional[Person] = None
    children: List[Person] = None
    marriage_date: Optional[datetime] = None
    marriage_place: str = ""

class GenealogyCalculator:
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.cache = get_cache("genealogy_calculator", max_size=500)
        
        self.persons = {}
        self.relationships = []
        self.family_groups = {}
        
        self.stats = {
            'persons_processed': 0, 'families_created': 0, 'relationships_validated': 0,
            'dates_estimated': 0, 'duplicates_merged': 0, 'inconsistencies_found': 0
        }
        
        self.age_patterns = {
            'marriage_min': 16, 'marriage_max': 50, 'marriage_typical': 25,
            'first_child_min': 17, 'first_child_max': 45, 'first_child_typical': 22,
            'child_spacing_min': 1, 'child_spacing_max': 15, 'child_spacing_typical': 2.5,
            'generation_gap_min': 15, 'generation_gap_max': 50, 'generation_gap_typical': 25
        }
    
    def add_person(self, name: str, birth_date: Optional[datetime] = None, 
                   death_date: Optional[datetime] = None, **kwargs) -> str:
        """Ajoute une personne et retourne son ID"""
        person_id = self._generate_person_id(name)
        
        existing_person = self._find_similar_person(name, birth_date)
        if existing_person:
            return self._merge_person_data(existing_person.id, name, birth_date, death_date, **kwargs)
        
        names = name.split()
        first_names = names[:-1] if len(names) > 1 else [names[0]] if names else []
        family_name = names[-1] if names else ""
        
        person = Person(
            id=person_id,
            full_name=name,
            first_names=first_names,
            family_name=family_name,
            birth_date=birth_date,
            death_date=death_date,
            sources=[]
        )
        
        for key, value in kwargs.items():
            if hasattr(person, key):
                setattr(person, key, value)
        
        self.persons[person_id] = person
        self.stats['persons_processed'] += 1
        
        return person_id
    
    def add_relationship(self, person1_name: str, person2_name: str, 
                        relationship_type: str, confidence: float = 0.8, 
                        source_text: str = "") -> bool:
        """Ajoute une relation entre deux personnes"""
        person1_id = self.add_person(person1_name)
        person2_id = self.add_person(person2_name)
        
        if person1_id == person2_id:
            self.logger.warning(f"Tentative de relation avec soi-même: {person1_name}")
            return False
        
        relationship = Relationship(
            person1_id=person1_id,
            person2_id=person2_id,
            relationship_type=relationship_type,
            confidence=confidence,
            source_text=source_text
        )
        
        if self._validate_relationship(relationship):
            self.relationships.append(relationship)
            self.stats['relationships_validated'] += 1
            return True
        
        return False
    
    def calculate_birth_from_age(self, death_date: datetime, age: int) -> datetime:
        """Calcule la date de naissance approximative à partir de l'âge au décès"""
        birth_year = death_date.year - age
        birth_date = datetime(birth_year, 6, 15)  # 15 juin par défaut
        self.stats['dates_estimated'] += 1
        return birth_date
    
    def estimate_marriage_date(self, child_birth: datetime, is_first_child: bool = True) -> datetime:
        """Estime la date de mariage à partir de la naissance d'un enfant"""
        if is_first_child:
            marriage_year = child_birth.year - 1
        else:
            marriage_year = child_birth.year - 2
        
        marriage_date = datetime(marriage_year, 5, 1)  # 1er mai par défaut
        self.stats['dates_estimated'] += 1
        return marriage_date
    
    def validate_family_chronology(self, family: FamilyGroup) -> Dict[str, any]:
        """Valide la chronologie d'une famille"""
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'estimated_dates': []
        }
        
        if not family.father and not family.mother:
            validation['errors'].append("Famille sans parents")
            validation['is_valid'] = False
            return validation
        
        # Vérification des âges des parents
        if family.father and family.father.birth_date:
            father_age_checks = self._validate_parent_ages(family.father, family.children or [])
            validation['warnings'].extend(father_age_checks)
        
        if family.mother and family.mother.birth_date:
            mother_age_checks = self._validate_parent_ages(family.mother, family.children or [])
            validation['warnings'].extend(mother_age_checks)
        
        # Vérification de l'espacement entre enfants
        if family.children and len(family.children) > 1:
            spacing_checks = self._validate_child_spacing(family.children)
            validation['warnings'].extend(spacing_checks)
        
        # Estimation des dates manquantes
        estimated = self._estimate_missing_dates(family)
        validation['estimated_dates'] = estimated
        
        return validation
    
    def build_family_trees(self, persons: List[Dict]) -> List[FamilyGroup]:
        """Construit les arbres généalogiques à partir des personnes et relations"""
        families = []
        
        # Grouper les relations par famille
        family_relationships = defaultdict(list)
        
        for rel in self.relationships:
            if rel.relationship_type in ['father', 'mother', 'child']:
                family_key = self._get_family_key(rel)
                family_relationships[family_key].append(rel)
        
        # Créer les groupes familiaux
        for family_key, rels in family_relationships.items():
            family = self._build_family_group(rels)
            if family:
                families.append(family)
                self.stats['families_created'] += 1
        
        return families
    
    def resolve_name_variants(self, names: List[str]) -> str:
        """Résout les variantes de noms pour identifier la forme canonique"""
        if not names:
            return ""
        
        # Normalisation des noms
        normalized_names = []
        for name in names:
            normalized = self._normalize_name(name)
            normalized_names.append(normalized)
        
        # Trouver le nom le plus complet
        longest_name = max(normalized_names, key=len)
        
        # Vérifier si c'est un nom connu
        canonical = self._find_canonical_form(longest_name)
        
        return canonical or longest_name
    
    def detect_duplicates(self) -> List[Tuple[str, str, float]]:
        """Détecte les doublons potentiels dans les personnes"""
        duplicates = []
        persons_list = list(self.persons.values())
        
        for i, person1 in enumerate(persons_list):
            for person2 in persons_list[i+1:]:
                similarity = self._calculate_person_similarity(person1, person2)
                if similarity > 0.8:
                    duplicates.append((person1.id, person2.id, similarity))
        
        return duplicates
    
    def merge_duplicate_persons(self, person1_id: str, person2_id: str) -> str:
        """Fusionne deux personnes identifiées comme doublons"""
        if person1_id not in self.persons or person2_id not in self.persons:
            return person1_id
        
        person1 = self.persons[person1_id]
        person2 = self.persons[person2_id]
        
        # Merge des données
        merged_person = self._merge_person_objects(person1, person2)
        
        # Mise à jour des relations
        for rel in self.relationships:
            if rel.person1_id == person2_id:
                rel.person1_id = person1_id
            if rel.person2_id == person2_id:
                rel.person2_id = person1_id
        
        # Suppression du doublon
        del self.persons[person2_id]
        self.persons[person1_id] = merged_person
        
        self.stats['duplicates_merged'] += 1
        return person1_id
    
    def _generate_person_id(self, name: str) -> str:
        """Génère un ID unique pour une personne"""
        base_id = re.sub(r'[^a-zA-Z0-9]', '', name.replace(' ', '_')).lower()
        counter = 1
        while f"{base_id}_{counter}" in self.persons:
            counter += 1
        return f"{base_id}_{counter}"
    
    def _find_similar_person(self, name: str, birth_date: Optional[datetime]) -> Optional[Person]:
        """Trouve une personne similaire existante"""
        normalized_name = self._normalize_name(name)
        
        for person in self.persons.values():
            person_normalized = self._normalize_name(person.full_name)
            
            name_similarity = self._calculate_name_similarity(normalized_name, person_normalized)
            
            if name_similarity > 0.9:
                if birth_date and person.birth_date:
                    date_diff = abs((birth_date - person.birth_date).days)
                    if date_diff <= 365:  # Moins d'un an de différence
                        return person
                elif not birth_date and not person.birth_date:
                    return person
        
        return None
    
    def _normalize_name(self, name: str) -> str:
        """Normalise un nom pour la comparaison"""
        normalized = name.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = normalized.replace('dom ', '').replace('père ', '')
        return normalized
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calcule la similarité entre deux noms"""
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _validate_relationship(self, relationship: Relationship) -> bool:
        """Valide la cohérence d'une relation"""
        person1 = self.persons.get(relationship.person1_id)
        person2 = self.persons.get(relationship.person2_id)
        
        if not person1 or not person2:
            return False
        
        # Vérifications chronologiques
        if relationship.relationship_type in ['father', 'mother']:
            if person1.birth_date and person2.birth_date:
                age_diff = (person2.birth_date - person1.birth_date).days / 365.25
                if age_diff < self.age_patterns['generation_gap_min'] or age_diff > self.age_patterns['generation_gap_max']:
                    self.stats['inconsistencies_found'] += 1
                    self.logger.warning(f"Écart d'âge suspect parent-enfant: {age_diff:.1f} ans")
                    return False
        
        return True
    
    def _validate_parent_ages(self, parent: Person, children: List[Person]) -> List[str]:
        """Valide les âges d'un parent par rapport à ses enfants"""
        warnings = []
        
        if not parent.birth_date or not children:
            return warnings
        
        for child in children:
            if child.birth_date:
                age_at_birth = (child.birth_date - parent.birth_date).days / 365.25
                
                if age_at_birth < self.age_patterns['first_child_min']:
                    warnings.append(f"Parent très jeune: {age_at_birth:.1f} ans à la naissance de {child.full_name}")
                elif age_at_birth > self.age_patterns['first_child_max']:
                    warnings.append(f"Parent âgé: {age_at_birth:.1f} ans à la naissance de {child.full_name}")
        
        return warnings
    
    def _validate_child_spacing(self, children: List[Person]) -> List[str]:
        """Valide l'espacement entre les naissances des enfants"""
        warnings = []
        
        children_with_dates = [c for c in children if c.birth_date]
        children_with_dates.sort(key=lambda x: x.birth_date)
        
        for i in range(1, len(children_with_dates)):
            prev_child = children_with_dates[i-1]
            curr_child = children_with_dates[i]
            
            spacing = (curr_child.birth_date - prev_child.birth_date).days / 365.25
            
            if spacing < self.age_patterns['child_spacing_min']:
                warnings.append(f"Espacement très court entre {prev_child.full_name} et {curr_child.full_name}: {spacing:.1f} ans")
            elif spacing > self.age_patterns['child_spacing_max']:
                warnings.append(f"Espacement très long entre {prev_child.full_name} et {curr_child.full_name}: {spacing:.1f} ans")
        
        return warnings
    
    def _estimate_missing_dates(self, family: FamilyGroup) -> List[Dict]:
        """Estime les dates manquantes dans une famille"""
        estimates = []
        
        # Estimation des dates de naissance des parents
        if family.children:
            oldest_child = min(family.children, key=lambda c: c.birth_date or datetime.max)
            
            if oldest_child.birth_date:
                if family.father and not family.father.birth_date:
                    estimated_birth = oldest_child.birth_date - timedelta(days=25*365)
                    estimates.append({
                        'person': family.father.full_name,
                        'type': 'birth_date',
                        'estimated_date': estimated_birth,
                        'confidence': 0.6
                    })
                
                if family.mother and not family.mother.birth_date:
                    estimated_birth = oldest_child.birth_date - timedelta(days=22*365)
                    estimates.append({
                        'person': family.mother.full_name,
                        'type': 'birth_date',
                        'estimated_date': estimated_birth,
                        'confidence': 0.6
                    })
        
        return estimates
    
    def _merge_person_data(self, person_id: str, name: str, birth_date: Optional[datetime], 
                          death_date: Optional[datetime], **kwargs) -> str:
        """Fusionne les données d'une personne existante"""
        person = self.persons[person_id]
        
        # Mise à jour des dates si plus précises
        if birth_date and not person.birth_date:
            person.birth_date = birth_date
        if death_date and not person.death_date:
            person.death_date = death_date
        
        # Mise à jour des autres attributs
        for key, value in kwargs.items():
            if hasattr(person, key) and value and not getattr(person, key):
                setattr(person, key, value)
        
        return person_id
    
    def get_statistics(self) -> Dict:
        """Retourne les statistiques du calculateur"""
        return {
            **self.stats,
            'total_persons': len(self.persons),
            'total_relationships': len(self.relationships),
            'families_identified': len(self.family_groups)
        }
    
    def export_gedcom(self, filename: str) -> bool:
        """Exporte les données au format GEDCOM"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("0 HEAD\n")
                f.write("1 SOUR GenealogyCalculator\n")
                f.write("1 GEDC\n")
                f.write("2 VERS 5.5.1\n")
                f.write("2 FORM LINEAGE-LINKED\n")
                f.write("1 CHAR UTF-8\n")
                
                # Export des individus
                for person in self.persons.values():
                    f.write(f"0 @{person.id}@ INDI\n")
                    f.write(f"1 NAME {person.full_name}\n")
                    if person.birth_date:
                        f.write(f"1 BIRT\n")
                        f.write(f"2 DATE {person.birth_date.strftime('%d %b %Y')}\n")
                    if person.death_date:
                        f.write(f"1 DEAT\n")
                        f.write(f"2 DATE {person.death_date.strftime('%d %b %Y')}\n")
                
                f.write("0 TRLR\n")
            
            return True
        except Exception as e:
            self.logger.error(f"Erreur export GEDCOM: {e}")
            return False