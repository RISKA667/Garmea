import difflib
import unicodedata
from typing import Dict, List, Tuple, Optional
from functools import lru_cache
from dataclasses import dataclass

from config.settings import ParserConfig

@dataclass
class SimilarityResult:
    """Résultat de calcul de similarité"""
    similarity_score: float
    confidence: float
    applied_rules: List[str]
    details: Dict

class SimilarityEngine:
    """Moteur de calcul de similarité optimisé avec ML patterns"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        
        # Patterns ML pour erreurs de transcription
        self.transcription_patterns = {
            'particule_errors': [
                {'pattern': r'de\s+(\w+)', 'error': r'De\1', 'confidence': 0.95},
                {'pattern': r'du\s+(\w+)', 'error': r'Du\1', 'confidence': 0.93},
            ],
            'accent_errors': [
                {'pattern': 'é', 'error': 'e', 'confidence': 0.85},
                {'pattern': 'è', 'error': 'e', 'confidence': 0.85},
                {'pattern': 'ç', 'error': 'c', 'confidence': 0.90},
            ],
            'consonant_variations': [
                {'pattern': 'y', 'error': 'i', 'confidence': 0.75},
                {'pattern': 'll', 'error': 'l', 'confidence': 0.70},
                {'pattern': 'nn', 'error': 'n', 'confidence': 0.70},
            ]
        }
        
        # Cache pour éviter les recalculs
        self._similarity_cache = {}
    
    @lru_cache(maxsize=2000)
    def calculate_name_similarity(self, nom1: str, prenom1: str, 
                                nom2: str, prenom2: str) -> SimilarityResult:
        """Calcul de similarité optimisé avec cache"""
        
        applied_rules = []
        details = {}
        
        # Similarité de base (Levenshtein)
        nom_sim = difflib.SequenceMatcher(None, nom1.lower(), nom2.lower()).ratio()
        prenom_sim = difflib.SequenceMatcher(None, prenom1.lower(), prenom2.lower()).ratio()
        
        details['base_nom_similarity'] = nom_sim
        details['base_prenom_similarity'] = prenom_sim
        
        # Application des patterns ML
        ml_boost = 0.0
        if self.config.ml_patterns_enabled:
            ml_boost, ml_rules = self._apply_ml_patterns(nom1, nom2)
            applied_rules.extend(ml_rules)
            details['ml_boost'] = ml_boost
        
        # Règles spécifiques historiques
        historical_boost, hist_rules = self._apply_historical_rules(nom1, nom2, prenom1, prenom2)
        applied_rules.extend(hist_rules)
        details['historical_boost'] = historical_boost
        
        # Score final pondéré
        nom_final = max(nom_sim, ml_boost, historical_boost)
        similarity_score = (nom_final * 0.6 + prenom_sim * 0.4)
        
        # Calcul de confiance
        confidence = self._calculate_confidence(similarity_score, applied_rules, details)
        
        return SimilarityResult(
            similarity_score=similarity_score,
            confidence=confidence,
            applied_rules=applied_rules,
            details=details
        )
    
    def _apply_ml_patterns(self, nom1: str, nom2: str) -> Tuple[float, List[str]]:
        """Application des patterns ML de transcription"""
        max_confidence = 0.0
        applied_rules = []
        
        for category, patterns in self.transcription_patterns.items():
            for pattern_info in patterns:
                if self._matches_pattern(nom1, nom2, pattern_info):
                    confidence = pattern_info['confidence']
                    if confidence > max_confidence:
                        max_confidence = confidence
                        applied_rules.append(f"ML_{category}_{pattern_info['pattern']}")
        
        return max_confidence, applied_rules
    
    def _matches_pattern(self, nom1: str, nom2: str, pattern_info: Dict) -> bool:
        """Vérifie si deux noms correspondent à un pattern d'erreur"""
        pattern = pattern_info['pattern']
        error = pattern_info['error']
        
        try:
            # Test bidirectionnel
            test1 = nom1.replace(pattern, error).lower() == nom2.lower()
            test2 = nom2.replace(pattern, error).lower() == nom1.lower()
            return test1 or test2
        except Exception:
            return False
    
    def _apply_historical_rules(self, nom1: str, nom2: str, 
                              prenom1: str, prenom2: str) -> Tuple[float, List[str]]:
        """Application des règles spécifiques aux noms historiques français"""
        max_boost = 0.0
        applied_rules = []
        
        # Règle 1: Erreurs de particules (de Montigny vs Demontigny)
        if self._check_de_prefix_error(nom1, nom2):
            max_boost = max(max_boost, 0.95)
            applied_rules.append("de_prefix_correction")
        
        # Règle 2: Variations y/i
        if self._check_y_i_variation(nom1, nom2):
            max_boost = max(max_boost, 0.90)
            applied_rules.append("y_i_variation")
        
        # Règle 3: Perte d'accents
        if self._check_accent_loss(nom1, nom2):
            max_boost = max(max_boost, 0.92)
            applied_rules.append("accent_loss")
        
        # Règle 4: Consonnes doubles/simples
        if self._check_consonant_variation(nom1, nom2):
            max_boost = max(max_boost, 0.88)
            applied_rules.append("consonant_variation")
        
        # Règle 5: Variantes de prénoms (Charles/Carl, Guillaume/William)
        if self._check_firstname_variants(prenom1, prenom2):
            max_boost = max(max_boost, 0.85)
            applied_rules.append("firstname_variant")
        
        return max_boost, applied_rules
    
    @lru_cache(maxsize=500)
    def _check_de_prefix_error(self, nom1: str, nom2: str) -> bool:
        """Détecte les erreurs de particules avec cache"""
        nom1_clean = nom1.replace(' ', '').lower()
        nom2_clean = nom2.replace(' ', '').lower()
        
        return (
            (nom1_clean.startswith('de') and nom2_clean == nom1_clean) or
            (nom2_clean.startswith('de') and nom1_clean == nom2_clean) or
            (nom1.replace('de ', '').lower() == nom2.lower()) or
            (nom2.replace('de ', '').lower() == nom1.lower())
        )
    
    @lru_cache(maxsize=500)
    def _check_y_i_variation(self, nom1: str, nom2: str) -> bool:
        """Détecte les variations y/i avec cache"""
        def normalize_y_i(text):
            text = unicodedata.normalize('NFD', text)
            return text.replace('y', 'i').replace('Y', 'I').lower()
        
        return normalize_y_i(nom1) == normalize_y_i(nom2)
    
    @lru_cache(maxsize=500)
    def _check_accent_loss(self, nom1: str, nom2: str) -> bool:
        """Détecte la perte d'accents avec cache"""
        def remove_accents(text):
            return ''.join(c for c in unicodedata.normalize('NFD', text)
                          if unicodedata.category(c) != 'Mn')
        
        return remove_accents(nom1.lower()) == remove_accents(nom2.lower())
    
    @lru_cache(maxsize=500)
    def _check_consonant_variation(self, nom1: str, nom2: str) -> bool:
        """Détecte les variations de consonnes doubles avec cache"""
        def normalize_doubles(text):
            doubles = ['ll', 'nn', 'mm', 'tt', 'ss', 'rr']
            result = text.lower()
            for double in doubles:
                result = result.replace(double, double[0])
            return result
        
        return normalize_doubles(nom1) == normalize_doubles(nom2)
    
    @lru_cache(maxsize=200)
    def _check_firstname_variants(self, prenom1: str, prenom2: str) -> bool:
        """Détecte les variantes de prénoms avec cache"""
        variants = {
            'charles': ['carl', 'karol'],
            'guillaume': ['william', 'willem'],
            'jacques': ['jacob', 'james'],
            'jean': ['john', 'johan'],
            'françois': ['francis', 'francisco'],
            'marie': ['maria', 'mary']
        }
        
        p1_lower = prenom1.lower()
        p2_lower = prenom2.lower()
        
        for main_name, variant_list in variants.items():
            if ((p1_lower == main_name and p2_lower in variant_list) or
                (p2_lower == main_name and p1_lower in variant_list)):
                return True
        
        return False
    
    def _calculate_confidence(self, similarity_score: float, 
                            applied_rules: List[str], details: Dict) -> float:
        """Calcule la confiance dans le résultat de similarité"""
        base_confidence = similarity_score
        
        # Bonus pour les règles appliquées
        rule_bonus = len(applied_rules) * 0.05
        
        # Malus si trop de différences détectées
        if details.get('base_nom_similarity', 0) < 0.3:
            base_confidence -= 0.2
        
        # Bonus si plusieurs règles convergent
        if len(applied_rules) >= 2:
            base_confidence += 0.1
        
        return max(0.0, min(1.0, base_confidence + rule_bonus))
    
    def batch_similarity_calculation(self, names_list: List[Tuple[str, str, str, str]]) -> List[SimilarityResult]:
        """Calcul en lot pour optimiser les performances"""
        results = []
        
        for nom1, prenom1, nom2, prenom2 in names_list:
            result = self.calculate_name_similarity(nom1, prenom1, nom2, prenom2)
            results.append(result)
        
        return results
    
    def find_best_matches(self, target_name: Tuple[str, str], 
                         candidate_names: List[Tuple[str, str, int]], 
                         threshold: float = None) -> List[Tuple[int, float]]:
        """Trouve les meilleures correspondances pour un nom cible"""
        if threshold is None:
            threshold = self.config.similarity_threshold
        
        matches = []
        target_nom, target_prenom = target_name
        
        for candidate_nom, candidate_prenom, candidate_id in candidate_names:
            result = self.calculate_name_similarity(
                target_nom, target_prenom, 
                candidate_nom, candidate_prenom
            )
            
            if result.similarity_score >= threshold:
                matches.append((candidate_id, result.similarity_score))
        
        # Trier par score décroissant
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches