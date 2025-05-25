import re
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
import hashlib
from config.settings import ParserConfig

@dataclass
class ParsedDate:
    """Date parsée avec métadonnées"""
    original_text: str
    parsed_date: Optional[datetime]
    year: Optional[int]
    month: Optional[int]
    day: Optional[int]
    confidence: float
    position: tuple  # (start, end) dans le texte

class DateParser:
    """Parser de dates optimisé pour textes historiques français"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        
        # Cache manuel pour remplacer @lru_cache
        self._extract_dates_cache = {}
        self._year_cache = {}
        self._cache_max_size = 1000
        
        # Mappings français
        self.month_names = {
            'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
            'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
            'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
        }
        
        self.month_abbreviations = {
            'janv': 'janvier', 'fév': 'février', 'sept': 'septembre',
            'oct': 'octobre', 'nov': 'novembre', 'déc': 'décembre'
        }
        
        # Compilation des patterns
        self._compile_date_patterns()
    
    def _compile_date_patterns(self):
        """Compile les patterns de dates une seule fois"""
        # Mois complets
        months_full = '|'.join(self.month_names.keys())
        
        # Abréviations
        months_abbrev = '|'.join(self.month_abbreviations.keys())
        
        self.patterns = [
            # Format: "13 février 1646"
            re.compile(rf'(\d{{1,2}})\s+({months_full})\s+(\d{{4}})', re.IGNORECASE),
            
            # Format: "1646, 13 fév."
            re.compile(rf'(\d{{4}}),?\s+(\d{{1,2}})\s+({months_abbrev})\.?', re.IGNORECASE),
            
            # Format: "13 fév. 1646"
            re.compile(rf'(\d{{1,2}})\s+({months_abbrev})\.?\s+(\d{{4}})', re.IGNORECASE),
            
            # Année seule: "1643"
            re.compile(r'\b(\d{4})\b'),
            
            # Format ordinal: "8e jour de mars"
            re.compile(rf'(\d{{1,2}})e?\s+jour\s+de\s+({months_full})', re.IGNORECASE)
        ]
    
    def _create_cache_key(self, text: str) -> str:
        """Crée une clé de cache pour le texte"""
        try:
            return hashlib.md5(text.encode('utf-8')).hexdigest()
        except Exception:
            return str(hash(text))
    
    def _manage_cache_size(self, cache_dict: Dict):
        """Gère la taille du cache pour éviter une croissance excessive"""
        if len(cache_dict) > self._cache_max_size:
            # Supprimer les 200 entrées les plus anciennes (approximation)
            keys_to_remove = list(cache_dict.keys())[:200]
            for key in keys_to_remove:
                cache_dict.pop(key, None)
    
    def extract_all_dates(self, text: str) -> List[ParsedDate]:
        """Extraction de toutes les dates avec cache manuel"""
        if not text:
            return []
        
        # Vérifier le cache
        cache_key = self._create_cache_key(text)
        if cache_key in self._extract_dates_cache:
            return self._extract_dates_cache[cache_key]
        
        dates = []
        found_positions = set()  # Éviter les doublons de position
        
        for pattern_idx, pattern in enumerate(self.patterns):
            for match in pattern.finditer(text):
                # Éviter les chevauchements
                if any(pos in found_positions for pos in range(match.start(), match.end())):
                    continue
                
                parsed_date = self._parse_match(match, pattern_idx)
                if parsed_date:
                    dates.append(parsed_date)
                    found_positions.update(range(match.start(), match.end()))
        
        # Trier par position dans le texte
        dates.sort(key=lambda d: d.position[0])
        
        # Mettre en cache
        self._manage_cache_size(self._extract_dates_cache)
        self._extract_dates_cache[cache_key] = dates
        
        return dates
    
    def _parse_match(self, match: re.Match, pattern_idx: int) -> Optional[ParsedDate]:
        """Parse un match regex en ParsedDate"""
        groups = match.groups()
        original_text = match.group(0)
        confidence = 1.0
        
        try:
            if pattern_idx == 0:  # "13 février 1646"
                day, month_name, year = int(groups[0]), groups[1].lower(), int(groups[2])
                month = self.month_names[month_name]
                
            elif pattern_idx == 1:  # "1646, 13 fév."
                year, day, month_abbrev = int(groups[0]), int(groups[1]), groups[2].lower()
                month_name = self.month_abbreviations.get(month_abbrev, month_abbrev)
                month = self.month_names.get(month_name)
                if not month:
                    return None
                
            elif pattern_idx == 2:  # "13 fév. 1646"
                day, month_abbrev, year = int(groups[0]), groups[1].lower(), int(groups[2])
                month_name = self.month_abbreviations.get(month_abbrev, month_abbrev)
                month = self.month_names.get(month_name)
                if not month:
                    return None
                
            elif pattern_idx == 3:  # Année seule "1643"
                year = int(groups[0])
                # Vérifier que c'est une année plausible (1400-1900)
                if not (1400 <= year <= 1900):
                    return None
                day, month = None, None
                confidence = 0.7  # Moins de confiance pour année seule
                
            elif pattern_idx == 4:  # "8e jour de mars"
                day, month_name = int(groups[0]), groups[1].lower()
                month = self.month_names[month_name]
                year = None
                confidence = 0.8  # Pas d'année = moins de confiance
            
            else:
                return None
            
            # Création de l'objet datetime si possible
            parsed_datetime = None
            if year and month and day:
                try:
                    parsed_datetime = datetime(year, month, day)
                    confidence = min(confidence, 1.0)
                except ValueError:
                    # Date invalide (ex: 31 février)
                    confidence = 0.3
            
            return ParsedDate(
                original_text=original_text,
                parsed_date=parsed_datetime,
                year=year,
                month=month,
                day=day,
                confidence=confidence,
                position=(match.start(), match.end())
            )
            
        except (ValueError, KeyError) as e:
            # Erreur de parsing
            return None
    
    def get_earliest_date(self, dates: List[ParsedDate]) -> Optional[ParsedDate]:
        """Récupère la date la plus ancienne"""
        valid_dates = [d for d in dates if d.parsed_date and d.confidence > 0.5]
        if not valid_dates:
            return None
        return min(valid_dates, key=lambda d: d.parsed_date)
    
    def get_year_from_text(self, text: str) -> Optional[int]:
        """Extraction rapide d'année pour validation chronologique avec cache manuel"""
        if not text:
            return None
        
        # Vérifier le cache
        cache_key = self._create_cache_key(text)
        if cache_key in self._year_cache:
            return self._year_cache[cache_key]
        
        dates = self.extract_all_dates(text)
        years = [d.year for d in dates if d.year and d.confidence > 0.6]
        result = years[0] if years else None
        
        # Mettre en cache
        self._manage_cache_size(self._year_cache)
        self._year_cache[cache_key] = result
        
        return result
    
    def clear_cache(self):
        """Vide les caches pour libérer la mémoire"""
        self._extract_dates_cache.clear()
        self._year_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Retourne les statistiques des caches"""
        return {
            'extract_dates_cache_size': len(self._extract_dates_cache),
            'year_cache_size': len(self._year_cache),
            'total_cache_entries': len(self._extract_dates_cache) + len(self._year_cache)
        }