import re
import unicodedata
from typing import List, Optional, Set, Dict
from functools import lru_cache

class TextNormalizer:
    """Utilitaires de normalisation de texte optimisés"""
    
    def __init__(self):
        # Patterns compilés pour performance
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile les patterns regex une seule fois"""
        self.patterns = {
            'control_chars': re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]'),
            'multiple_spaces': re.compile(r'\s+'),
            'quotes': re.compile(r'[""''`]'),
            'ellipsis': re.compile(r'…'),
            'word_boundaries': re.compile(r'\b'),
            'french_accents': re.compile(r'[àáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]', re.IGNORECASE)
        }
    
    @lru_cache(maxsize=1000)
    def clean_text(self, text: str) -> str:
        """Nettoyage complet de texte avec cache"""
        if not text:
            return ""
        
        # Supprimer caractères de contrôle
        text = self.patterns['control_chars'].sub('', text)
        
        # Normaliser les espaces
        text = self.patterns['multiple_spaces'].sub(' ', text)
        
        # Unifier la ponctuation
        text = self.patterns['quotes'].sub('"', text)
        text = self.patterns['ellipsis'].sub('...', text)
        
        return text.strip()
    
    @lru_cache(maxsize=500)
    def remove_accents(self, text: str) -> str:
        """Suppression des accents avec cache"""
        if not text:
            return ""
        
        # Décomposition Unicode puis suppression des marques diacritiques
        nfd = unicodedata.normalize('NFD', text)
        return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    
    @lru_cache(maxsize=500)
    def normalize_for_comparison(self, text: str) -> str:
        """Normalisation pour comparaison (minuscules, sans accents, sans espaces)"""
        if not text:
            return ""
        
        # Pipeline de normalisation
        normalized = text.lower()
        normalized = self.remove_accents(normalized)
        normalized = re.sub(r'[^\w]', '', normalized)  # Garder seulement lettres/chiffres
        
        return normalized
    
    def extract_words(self, text: str, min_length: int = 3) -> Set[str]:
        """Extraction des mots avec filtrage par longueur"""
        if not text:
            return set()
        
        words = re.findall(r'\b[A-ZÀ-ÿ][a-zà-ÿ]+\b', text)
        return {word for word in words if len(word) >= min_length}
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calcul de similarité basique entre deux textes"""
        if not text1 or not text2:
            return 0.0
        
        words1 = self.extract_words(text1)
        words2 = self.extract_words(text2)
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0

class NameUtils:
    """Utilitaires spécialisés pour les noms de personnes"""
    
    @staticmethod
    @lru_cache(maxsize=500)
    def split_full_name(full_name: str) -> tuple:
        """Sépare un nom complet en prénom et nom"""
        if not full_name:
            return "", ""
        
        parts = full_name.strip().split()
        if len(parts) == 1:
            return parts[0], ""
        elif len(parts) == 2:
            return parts[0], parts[1]
        else:
            # Plus de 2 parties : prendre le premier comme prénom, le reste comme nom
            return parts[0], " ".join(parts[1:])
    
    @staticmethod
    @lru_cache(maxsize=300)
    def normalize_particle(name: str) -> str:
        """Normalise les particules dans les noms (de, du, Le)"""
        if not name:
            return ""
        
        # Patterns de particules
        particles = {
            'de': r'\bde\s+',
            'du': r'\bdu\s+',
            'des': r'\bdes\s+',
            'Le': r'\bLe\s+',
            'La': r'\bLa\s+'
        }
        
        normalized = name
        for particle, pattern in particles.items():
            # Uniformiser la casse des particules
            normalized = re.sub(pattern, f'{particle} ', normalized, flags=re.IGNORECASE)
        
        return normalized
    
    @staticmethod
    def detect_name_gender_clues(name: str) -> Optional[str]:
        if not name:
            return None
        
        name_lower = name.lower()
        feminine_endings = ['ette', 'elle', 'oise', 'ine', 'anne', 'ette']
        masculine_endings = ['ard', 'ert', 'aud', 'oux']
        
        for ending in feminine_endings:
            if name_lower.endswith(ending):
                return 'F'
        
        for ending in masculine_endings:
            if name_lower.endswith(ending):
                return 'M'
        return None