import logging
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict
from dataclasses import dataclass

from core.models import Person
from config.settings import ParserConfig
from ml.similarity_engine import SimilarityEngine

@dataclass
class HomonymGroup:
    """Groupe d'homonymes détectés"""
    name: str
    persons: List[Person]
    confidence: float
    distinguishing_factors: List[str]

class HomonymDetector:
    """Détecteur d'homonymes avancé avec analyse contextuelle"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.similarity_engine = SimilarityEngine(config)
        
        # Seuils de détection
        self.name_similarity_threshold = 0.95
        self.context_difference_threshold = 0.3
    
    def detect_homonyms(self, persons: List[Person]) -> List[HomonymGroup]:
        """Détecte tous les groupes d'homonymes"""
        self.logger.info(f"Début détection d'homonymes sur {len(persons)} personnes")
        
        # Regrouper par nom similaire
        name_groups = self._group_by_similar_names(persons)
        
        # Analyser chaque groupe pour détecter les vrais homonymes
        homonym_groups = []
        for name, group_persons in name_groups.items():
            if len(group_persons) > 1:
                homonym_group = self._analyze_potential_homonyms(name, group_persons)
                if homonym_group:
                    homonym_groups.append(homonym_group)
        
        self.logger.info(f"Détecté {len(homonym_groups)} groupes d'homonymes")
        return homonym_groups
    
    def _group_by_similar_names(self, persons: List[Person]) -> Dict[str, List[Person]]:
        """Regroupe les personnes par noms similaires"""
        name_groups = defaultdict(list)
        
        for person in persons:
            # Utiliser le nom complet normalisé comme clé
            normalized_name = self._normalize_name_for_grouping(person.full_name)
            name_groups[normalized_name].append(person)
        
        # Fusionner les groupes avec des noms très similaires
        merged_groups = self._merge_similar_name_groups(name_groups)
        
        return merged_groups
    
    def _normalize_name_for_grouping(self, full_name: str) -> str:
        """Normalise un nom pour le regroupement"""
        import unicodedata
        
        # Supprimer les accents et normaliser
        normalized = unicodedata.normalize('NFD', full_name.lower())
        normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        
        # Supprimer les espaces multiples et caractères spéciaux
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _merge_similar_name_groups(self, name_groups: Dict[str, List[Person]]) -> Dict[str, List[Person]]:
        """Fusionne les groupes de noms très similaires"""
        merged_groups = {}
        processed_names = set()
        
        for name1, persons1 in name_groups.items():
            if name1 in processed_names:
                continue
            
            # Créer un nouveau groupe
            merged_group = persons1.copy()
            group_key = name1
            processed_names.add(name1)
            
            # Chercher des noms similaires à fusionner
            for name2, persons2 in name_groups.items():
                if name2 in processed_names or name1 == name2:
                    continue
                
                # Calculer la similarité entre les noms
                if self._are_names_similar_enough(name1, name2):
                    merged_group.extend(persons2)
                    processed_names.add(name2)
            
            if merged_group:
                merged_groups[group_key] = merged_group
        
        return merged_groups
    
    def _are_names_similar_enough(self, name1: str, name2: str) -> bool:
        """Détermine si deux noms sont suffisamment similaires pour être fusionnés"""
        # Utiliser le moteur de similarité pour calculer la distance
        parts1 = name1.split(' ', 1)
        parts2 = name2.split(' ', 1)
        
        if len(parts1) == 2 and len(parts2) == 2:
            result = self.similarity_engine.calculate_name_similarity(
                parts1[1], parts1[0], parts2[1], parts2[0]  # nom, prénom
            )
            return result.similarity_score >= self.name_similarity_threshold
        
        return False
    
    def _analyze_potential_homonyms(self, name: str, persons: List[Person]) -> Optional[HomonymGroup]:
        """Analyse un groupe de personnes pour détecter les vrais homonymes"""
        if len(persons) < 2:
            return None
        
        # Analyser les facteurs de distinction
        distinguishing_factors = self._find_distinguishing_factors(persons)
        
        # Calculer la confiance dans la détection d'homonymes
        confidence = self._calculate_homonym_confidence(persons, distinguishing_factors)
        
        # Seulement retourner si confiance suffisante qu'il s'agit d'homonymes distincts
        if confidence >= 0.7:
            return HomonymGroup(
                name=name,
                persons=persons,
                confidence=confidence,
                distinguishing_factors=distinguishing_factors
            )
        
        return None
    
    def _find_distinguishing_factors(self, persons: List[Person]) -> List[str]:
        """Trouve les facteurs qui distinguent les personnes d'un groupe"""
        factors = []
        
        # Terres différentes
        all_terres = [set(p.terres) for p in persons if p.terres]
        if len(all_terres) > 1:
            # Vérifier s'il y a des terres complètement disjointes
            terres_overlap = any(
                t1.intersection(t2) 
                for i, t1 in enumerate(all_terres) 
                for j, t2 in enumerate(all_terres) 
                if i != j
            )
            if not terres_overlap:
                factors.append("terres_distinctes")
        
        # Dates de vie non chevauchantes
        death_years = [self._extract_year(p.date_deces) for p in persons if p.date_deces]
        birth_years = [self._extract_year(p.date_naissance) for p in persons if p.date_naissance]
        
        if len(death_years) >= 2:
            # Si une personne meurt avant qu'une autre naisse
            min_death = min(death_years)
            max_birth = max(birth_years) if birth_years else None
            
            if max_birth and min_death < max_birth:
                factors.append("chronologie_distincte")
        
        # Professions incompatibles
        all_professions = [set(p.profession) for p in persons if p.profession]
        if len(all_professions) > 1:
            ecclesiastical = {'curé', 'prêtre', 'vicaire'}
            secular = {'avocat', 'marchand', 'laboureur'}
            
            has_ecclesiastical = any(profs.intersection(ecclesiastical) for profs in all_professions)
            has_secular = any(profs.intersection(secular) for profs in all_professions)
            
            if has_ecclesiastical and has_secular:
                factors.append("professions_incompatibles")
        
        # Statuts sociaux très différents
        statuts = [p.statut for p in persons if p.statut]
        if len(set(statuts)) > 1:
            factors.append("statuts_differents")
        
        return factors
    
    def _calculate_homonym_confidence(self, persons: List[Person], 
                                    distinguishing_factors: List[str]) -> float:
        """Calcule la confiance dans la détection d'homonymes"""
        base_confidence = 0.5  # Confiance de base pour des noms identiques
        
        # Bonus par facteur de distinction
        factor_bonuses = {
            "terres_distinctes": 0.3,
            "chronologie_distincte": 0.4,
            "professions_incompatibles": 0.3,
            "statuts_differents": 0.1
        }
        
        for factor in distinguishing_factors:
            base_confidence += factor_bonuses.get(factor, 0.1)
        
        # Malus si trop peu d'informations distinctives
        total_info = sum(
            len(p.profession) + len(p.terres) + (1 if p.date_naissance else 0) + 
            (1 if p.date_deces else 0) + (1 if p.statut else 0)
            for p in persons
        )
        
        if total_info < len(persons) * 2:  # Moins de 2 infos par personne en moyenne
            base_confidence -= 0.2
        
        return max(0.0, min(1.0, base_confidence))
    
    def _extract_year(self, date_str: Optional[str]) -> Optional[int]:
        """Extrait l'année d'une chaîne de date"""
        if not date_str:
            return None
        
        import re
        match = re.search(r'\b(\d{4})\b', date_str)
        return int(match.group(1)) if match else None
    
    def resolve_homonym_conflicts(self, persons: List[Person], 
                                actes_context: Dict) -> List[Tuple[Person, str]]:
        """Résout les conflits d'homonymes en proposant des corrections"""
        resolutions = []
        
        homonym_groups = self.detect_homonyms(persons)
        
        for group in homonym_groups:
            for person in group.persons:
                # Proposer des résolutions basées sur les facteurs de distinction
                resolution_strategy = self._suggest_resolution_strategy(person, group)
                resolutions.append((person, resolution_strategy))
        
        return resolutions
    
    def _suggest_resolution_strategy(self, person: Person, group: HomonymGroup) -> str:
        """Suggère une stratégie de résolution pour un homonyme"""
        strategies = []
        
        if "terres_distinctes" in group.distinguishing_factors:
            if person.terres:
                strategies.append(f"Distinguer par terres: sr de {', '.join(person.terres)}")
        
        if "chronologie_distincte" in group.distinguishing_factors:
            if person.date_deces:
                strategies.append(f"Distinguer par chronologie: †{person.date_deces}")
            elif person.date_naissance:
                strategies.append(f"Distinguer par chronologie: *{person.date_naissance}")
        
        if "professions_incompatibles" in group.distinguishing_factors:
            if person.profession:
                strategies.append(f"Distinguer par profession: {', '.join(person.profession)}")
        
        if not strategies:
            strategies.append("Ajouter un identifiant numérique (ex: Jean Le Boucher I, II)")
        
        return " | ".join(strategies)