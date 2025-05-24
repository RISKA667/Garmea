import re
from datetime import datetime, date
from typing import Optional, List, Tuple
from functools import lru_cache

class DateUtils:
    """Utilitaires de manipulation de dates historiques"""
    
    # Calendriers et conversions
    FRENCH_MONTHS = {
        'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
        'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
    }
    
    MONTH_ABBREVIATIONS = {
        'janv': 'janvier', 'fév': 'février', 'sept': 'septembre',
        'oct': 'octobre', 'nov': 'novembre', 'déc': 'décembre'
    }
    
    @staticmethod
    @lru_cache(maxsize=1000)
    def extract_year(date_str: str) -> Optional[int]:
        """Extraction rapide d'année avec validation"""
        if not date_str:
            return None
        
        # Chercher un nombre à 4 chiffres
        year_match = re.search(r'\b(\d{4})\b', date_str)
        if year_match:
            year = int(year_match.group(1))
            # Validation pour registres paroissiaux (1400-1900)
            if 1400 <= year <= 1900:
                return year
        
        return None
    
    @staticmethod
    @lru_cache(maxsize=500)
    def parse_french_date(date_str: str) -> Optional[datetime]:
        """Parse une date en français vers datetime"""
        if not date_str:
            return None
        
        date_str = date_str.lower().strip()
        
        # Patterns de dates françaises
        patterns = [
            # "13 février 1646"
            r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})',
            # "1646, 13 fév."
            r'(\d{4}),?\s+(\d{1,2})\s+(janv\.?|fév\.?|mars|avr\.?|mai|juin|juil\.?|août|sept\.?|oct\.?|nov\.?|déc\.?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if len(match.groups()) == 3:
                        if match.group(1).isdigit() and len(match.group(1)) == 4:
                            # Format: année, jour, mois
                            year, day, month_str = int(match.group(1)), int(match.group(2)), match.group(3)
                        else:
                            # Format: jour, mois, année
                            day, month_str, year = int(match.group(1)), match.group(2), int(match.group(3))
                        
                        # Conversion du mois
                        month_str = month_str.rstrip('.')
                        if month_str in DateUtils.MONTH_ABBREVIATIONS:
                            month_str = DateUtils.MONTH_ABBREVIATIONS[month_str]
                        
                        month = DateUtils.FRENCH_MONTHS.get(month_str)
                        if month:
                            return datetime(year, month, day)
                
                except (ValueError, KeyError):
                    continue
        
        return None
    
    @staticmethod
    def calculate_age_at_date(birth_date: str, target_date: str) -> Optional[int]:
        """Calcule l'âge d'une personne à une date donnée"""
        birth_year = DateUtils.extract_year(birth_date)
        target_year = DateUtils.extract_year(target_date)
        
        if birth_year and target_year:
            return target_year - birth_year
        
        return None
    
    @staticmethod
    def is_chronologically_coherent(earlier_date: str, later_date: str) -> bool:
        """Vérifie que deux dates sont dans l'ordre chronologique"""
        earlier_year = DateUtils.extract_year(earlier_date)
        later_year = DateUtils.extract_year(later_date)
        
        if earlier_year and later_year:
            return earlier_year <= later_year
        
        # Si on ne peut pas déterminer, on considère comme cohérent
        return True
    
    @staticmethod
    def format_date_range(start_date: str, end_date: str) -> str:
        """Formate une période de dates"""
        start_year = DateUtils.extract_year(start_date)
        end_year = DateUtils.extract_year(end_date)
        
        if start_year and end_year:
            if start_year == end_year:
                return str(start_year)
            else:
                return f"{start_year}-{end_year}"
        elif start_year:
            return f"{start_year}-?"
        elif end_year:
            return f"?-{end_year}"
        else:
            return "période inconnue"
    
    @staticmethod
    def infer_birth_year_from_events(events: List[Tuple[str, int]]) -> Optional[int]:
        """Infère une année de naissance basée sur des événements"""
        # events = [(type_event, year), ...]
        # ex: [("mariage", 1650), ("premier_enfant", 1652)]
        
        min_birth_year = None
        max_birth_year = None
        
        for event_type, year in events:
            if event_type == "mariage":
                # Âge au mariage: 16-40 ans typiquement
                min_birth_year = max(min_birth_year or 0, year - 40)
                max_birth_year = min(max_birth_year or 9999, year - 16)
            elif event_type == "premier_enfant":
                # Âge au premier enfant: 18-45 ans
                min_birth_year = max(min_birth_year or 0, year - 45)
                max_birth_year = min(max_birth_year or 9999, year - 18)
            elif event_type == "deces":
                # Espérance de vie: 30-80 ans
                min_birth_year = max(min_birth_year or 0, year - 80)
                max_birth_year = min(max_birth_year or 9999, year - 30)
        
        if min_birth_year and max_birth_year:
            # Prendre le milieu de la fourchette
            return (min_birth_year + max_birth_year) // 2
        
        return None