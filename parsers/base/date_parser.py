import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging
from ..common import pattern_compiler, date_validator, get_cache

class DateParser:
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.cache = get_cache("date_parser", max_size=1000)
        self.stats = {'dates_parsed': 0, 'successful_parses': 0, 'republican_dates': 0}
        
        self.month_names = {
            'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6,
            'juillet': 7, 'août': 8, 'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12,
            'janv': 1, 'fév': 2, 'sept': 9, 'oct': 10, 'nov': 11, 'déc': 12
        }
        
        self.republican_months = {
            'vendémiaire': 1, 'brumaire': 2, 'frimaire': 3, 'nivôse': 4, 'pluviôse': 5, 'ventôse': 6,
            'germinal': 7, 'floréal': 8, 'prairial': 9, 'messidor': 10, 'thermidor': 11, 'fructidor': 12
        }
        
        self.patterns = pattern_compiler.get_all_patterns()
    
    @get_cache("date_parser").cached_method()
    def extract_dates(self, text: str) -> List[Dict]:
        if not text:
            return []
        
        self.stats['dates_parsed'] += 1
        dates = []
        used_positions = set()
        
        date_patterns = [
            ('republican', self.patterns['date_republican']),
            ('standard', self.patterns['date_standard']),
            ('year_first', self.patterns['date_year_first']),
            ('year_only', self.patterns['date_year_only'])
        ]
        
        for pattern_name, pattern in date_patterns:
            for match in pattern.finditer(text):
                start, end = match.span()
                if not any(pos in used_positions for pos in range(start, end)):
                    date_info = self._parse_date_match(match, pattern_name)
                    if date_info:
                        dates.append(date_info)
                        used_positions.update(range(start, end))
                        self.stats['successful_parses'] += 1
                        
                        if pattern_name == 'republican':
                            self.stats['republican_dates'] += 1
        
        return self._deduplicate_and_rank_dates(dates)
    
    def _parse_date_match(self, match, pattern_name: str) -> Optional[Dict]:
        try:
            if pattern_name == 'standard':
                day, month_name, year = match.groups()
                month = self.month_names.get(month_name.lower())
                if month:
                    return self._create_date_info(int(day), month, int(year), match, 'standard')
            
            elif pattern_name == 'year_first':
                year, day, month_name = match.groups()
                month = self.month_names.get(month_name.lower())
                if month:
                    return self._create_date_info(int(day), month, int(year), match, 'year_first')
            
            elif pattern_name == 'republican':
                day, month_name, year_roman = match.groups()
                month = self.republican_months.get(month_name.lower())
                year = self._roman_to_int(year_roman) + 1792
                if month and year:
                    return self._create_date_info(int(day), month, year, match, 'republican')
            
            elif pattern_name == 'year_only':
                year = int(match.group(1))
                return self._create_date_info(None, None, year, match, 'year_only')
        
        except (ValueError, TypeError, AttributeError) as e:
            self.logger.debug(f"Erreur parsing date {match.group(0)}: {e}")
        
        return None
    
    def _create_date_info(self, day: Optional[int], month: Optional[int], year: int, 
                         match, date_type: str = 'standard') -> Dict:
        
        validation = date_validator.validate_date(year, month, day)
        
        date_obj = None
        if day and month and validation.is_valid:
            try:
                date_obj = datetime(year, month, day)
            except ValueError:
                pass
        
        confidence = self._calculate_date_confidence(day, month, year, date_type, validation)
        
        return {
            'original_text': match.group(0),
            'day': day,
            'month': month,
            'year': year,
            'date_object': date_obj,
            'position': match.span(),
            'type': date_type,
            'confidence': confidence,
            'validation': validation,
            'is_complete': day is not None and month is not None,
            'era': self._determine_era(year)
        }
    
    def _calculate_date_confidence(self, day: Optional[int], month: Optional[int], 
                                 year: int, date_type: str, validation) -> float:
        base_confidence = validation.confidence
        
        type_bonuses = {
            'republican': 0.1,
            'standard': 0.05,
            'year_first': 0.05,
            'year_only': -0.3
        }
        
        base_confidence += type_bonuses.get(date_type, 0.0)
        
        if day and month:
            base_confidence += 0.2
        elif month:
            base_confidence += 0.1
        
        if 1600 <= year <= 1800:
            base_confidence += 0.1
        
        return max(0.0, min(base_confidence, 1.0))
    
    def _roman_to_int(self, roman: str) -> int:
        values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
        total = 0
        prev_value = 0
        
        for char in reversed(roman.upper()):
            value = values.get(char, 0)
            if value < prev_value:
                total -= value
            else:
                total += value
            prev_value = value
        
        return total
    
    def _determine_era(self, year: int) -> str:
        if year < 1789:
            return 'ancien_regime'
        elif year < 1815:
            return 'revolution_empire'
        elif year < 1870:
            return 'monarchie_juillet'
        elif year < 1940:
            return 'republique'
        else:
            return 'moderne'
    
    def _deduplicate_and_rank_dates(self, dates: List[Dict]) -> List[Dict]:
        if not dates:
            return []
        
        unique_dates = {}
        for date in dates:
            key = (date['year'], date['month'], date['day'], date['type'])
            
            if key not in unique_dates or date['confidence'] > unique_dates[key]['confidence']:
                unique_dates[key] = date
        
        return sorted(unique_dates.values(), key=lambda x: x['confidence'], reverse=True)
    
    @get_cache("date_parser").cached_method()
    def extract_date_ranges(self, text: str) -> List[Dict]:
        dates = self.extract_dates(text)
        ranges = []
        
        for i, date1 in enumerate(dates):
            for j, date2 in enumerate(dates[i+1:], i+1):
                if self._could_be_range(date1, date2):
                    range_info = {
                        'start_date': date1,
                        'end_date': date2,
                        'span_years': abs(date2['year'] - date1['year']),
                        'confidence': min(date1['confidence'], date2['confidence']) * 0.8
                    }
                    ranges.append(range_info)
        
        return sorted(ranges, key=lambda x: x['confidence'], reverse=True)
    
    def _could_be_range(self, date1: Dict, date2: Dict) -> bool:
        year_diff = abs(date2['year'] - date1['year'])
        return 1 <= year_diff <= 100 and date1['confidence'] > 0.5 and date2['confidence'] > 0.5
    
    def get_date_statistics(self, dates: List[Dict]) -> Dict:
        if not dates:
            return {'total': 0, 'by_type': {}, 'by_era': {}, 'completeness': {}}
        
        by_type = {}
        by_era = {}
        completeness = {'complete': 0, 'partial': 0, 'year_only': 0}
        
        for date in dates:
            date_type = date['type']
            by_type[date_type] = by_type.get(date_type, 0) + 1
            
            era = date['era']
            by_era[era] = by_era.get(era, 0) + 1
            
            if date['is_complete']:
                completeness['complete'] += 1
            elif date['month']:
                completeness['partial'] += 1
            else:
                completeness['year_only'] += 1
        
        return {
            'total': len(dates),
            'by_type': by_type,
            'by_era': by_era,
            'completeness': completeness,
            'average_confidence': sum(d['confidence'] for d in dates) / len(dates),
            'year_range': (min(d['year'] for d in dates), max(d['year'] for d in dates))
        }
    
    def get_stats(self) -> Dict:
        cache_stats = self.cache.get_stats()
        return {
            **self.stats,
            'cache_hit_rate': cache_stats['hit_rate_percent'],
            'cache_size': cache_stats['size'],
            'success_rate': self.stats['successful_parses'] / max(self.stats['dates_parsed'], 1)
        }