import re
from typing import Dict, List, Optional
from functools import lru_cache

# Import corrigé
from config.settings import ParserConfig

class TextParser:
    """Parser de texte optimisé pour registres paroissiaux"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.abbreviations = config.abbreviations
        
        # Compilation des regex pour performance
        self._compile_normalization_patterns()
    
    def _compile_normalization_patterns(self):
        """Compile les patterns de normalisation une seule fois"""
        self.abbrev_patterns = {}
        for abbrev, full in self.abbreviations.items():
            # Échapper les caractères spéciaux et créer le pattern
            escaped_abbrev = re.escape(abbrev)
            self.abbrev_patterns[abbrev] = re.compile(
                r'\b' + escaped_abbrev, re.IGNORECASE
            )
    
    @lru_cache(maxsize=500)
    def normalize_text(self, text: str) -> str:
        """Normalisation rapide du texte avec cache"""
        if not text:
            return ""
        
        normalized = text
        
        # Remplacement des abréviations (optimisé)
        for abbrev, pattern in self.abbrev_patterns.items():
            full_form = self.abbreviations[abbrev] 
            normalized = pattern.sub(full_form, normalized)
        
        # Nettoyage supplémentaire
        normalized = self._clean_text(normalized)
        
        return normalized
    
    def _clean_text(self, text: str) -> str:
        """Nettoyage du texte (caractères parasites, espaces multiples)"""
        # Supprimer caractères de contrôle
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', text)
        
        # Normaliser les espaces
        text = re.sub(r'\s+', ' ', text)
        
        # Nettoyer la ponctuation problématique
        text = re.sub(r'[""''`]', '"', text)  # Unifier les guillemets
        text = re.sub(r'…', '...', text)       # Points de suspension
        
        return text.strip()
    
    def extract_segments(self, text: str) -> List[Dict]:
        """Extraction des segments (chaque — = acte distinct)"""
        segments = []
        
        # Découper par "—" selon spécification
        raw_segments = re.split(r'\s*—\s*', text)
        
        for i, segment in enumerate(raw_segments):
            segment = segment.strip()
            if len(segment) < 20:  # Ignorer segments trop courts
                continue
            
            # Premier segment = période (ex: "1643-1687")
            if i == 0 and re.match(r'\d{4}-\d{4}', segment):
                segments.append({
                    'type': 'period',
                    'content': segment,
                    'index': i
                })
                continue
            
            # Segments d'actes
            segments.append({
                'type': 'acte',
                'content': segment,
                'index': i,
                'length': len(segment)
            })
        
        return segments