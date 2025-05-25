import re
from typing import Dict, List, Optional
import hashlib
from functools import lru_cache
from config.settings import ParserConfig

class TextParser:
    """Parser de texte optimisé pour registres paroissiaux"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.abbreviations = config.abbreviations
        self._normalize_cache = {}
        self._cache_max_size = 500
        
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
    
    def _create_cache_key(self, text: str) -> str:
        """Crée une clé de cache pour le texte"""
        try:
            return hashlib.md5(text.encode('utf-8')).hexdigest()
        except Exception:
            return str(hash(text))
    
    def _manage_cache_size(self):
        """Gère la taille du cache pour éviter une croissance excessive"""
        if len(self._normalize_cache) > self._cache_max_size:
            # Supprimer les 100 entrées les plus anciennes (approximation)
            keys_to_remove = list(self._normalize_cache.keys())[:100]
            for key in keys_to_remove:
                self._normalize_cache.pop(key, None)
    
    def normalize_text(self, text: str) -> str:
        """Normalisation rapide du texte avec cache manuel"""
        if not text:
            return ""
        
        # Vérifier le cache
        cache_key = self._create_cache_key(text)
        if cache_key in self._normalize_cache:
            return self._normalize_cache[cache_key]
        
        normalized = text
        
        # Remplacement des abréviations (optimisé)
        for abbrev, pattern in self.abbrev_patterns.items():
            full_form = self.abbreviations[abbrev] 
            normalized = pattern.sub(full_form, normalized)
        
        # Nettoyage supplémentaire
        normalized = self._clean_text(normalized)
        
        # Mettre en cache
        self._manage_cache_size()
        self._normalize_cache[cache_key] = normalized
        
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
            
            segments.append({
                'type': 'acte',
                'content': segment,
                'index': i,
                'length': len(segment)})
        return segments
    
    def clear_cache(self):
        """Vide le cache pour libérer la mémoire"""
        self._normalize_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Retourne les statistiques du cache"""
        return {
            'cache_size': len(self._normalize_cache),
            'cache_max_size': self._cache_max_size,
            'abbreviations_count': len(self.abbreviations)
        }
    
    def preprocess_large_text(self, text: str, chunk_size: int = 10000) -> List[str]:
        """Préprocesse de gros textes par chunks pour éviter les problèmes de mémoire"""
        if len(text) <= chunk_size:
            return [self.normalize_text(text)]
        
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            # Éviter de couper au milieu des mots
            if i + chunk_size < len(text):
                last_space = chunk.rfind(' ')
                if last_space > chunk_size * 0.8:  # Si on trouve un espace dans les 20% finaux
                    chunk = chunk[:last_space]
            
            normalized_chunk = self.normalize_text(chunk)
            chunks.append(normalized_chunk)
        return chunks