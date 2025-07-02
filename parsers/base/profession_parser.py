import re
from typing import List, Dict, Optional, Set
import logging
from collections import Counter
from ..common import pattern_compiler, get_cache

class ProfessionParser:
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.cache = get_cache("profession_parser", max_size=800)
        self.stats = {'professions_found': 0, 'titles_found': 0, 'lands_found': 0}
        
        self.professions = {
            'curé': ['curé', 'curés', 'cure'],
            'prêtre': ['prestre', 'prestres', 'prêtre', 'prêtres'],
            'avocat': ['avocat', 'avocats'],
            'avocat du roi': ['avocat du roi', 'avocat du roy'],
            'conseiller': ['conseiller', 'conseillers', 'conseiller du roi'],
            'trésorier': ['trésorier', 'trésoriers'],
            'notaire': ['notaire', 'notaires', 'tabellion'],
            'marchand': ['marchand', 'marchands', 'marchant'],
            'laboureur': ['laboureur', 'laboureurs'],
            'chirurgien': ['chirurgien', 'chirurgiens'],
            'maître': ['maître', 'maîtres', 'maistre'],
            'procureur': ['procureur', 'procureurs'],
            'greffier': ['greffier', 'greffiers'],
            'sergent': ['sergent', 'sergents'],
            'huissier': ['huissier', 'huissiers']
        }
        
        self.titles = {
            'seigneur': ['seigneur', 'sgr', 'seigneurs'],
            'sieur': ['sieur', 'sr', 'sieurs'],
            'écuyer': ['écuyer', 'éc', 'ecuyer', 'escuyer'],
            'noble': ['noble', 'nob', 'nobles'],
            'bourgeois': ['bourgeois', 'bourg'],
            'damoiselle': ['damoiselle', 'demoiselle'],
            'dame': ['dame', 'dames']
        }
        
        self.patterns = pattern_compiler.get_all_patterns()
        self._compile_profession_patterns()
    
    def _compile_profession_patterns(self):
        all_professions = [var for variants in self.professions.values() for var in variants]
        all_titles = [var for variants in self.titles.values() for var in variants]
        
        prof_pattern = '|'.join(re.escape(p) for p in all_professions)
        title_pattern = '|'.join(re.escape(t) for t in all_titles)
        
        self.custom_patterns = {
            'profession_basic': re.compile(rf'\b({prof_pattern})\b', re.IGNORECASE),
            'title_basic': re.compile(rf'\b({title_pattern})\b', re.IGNORECASE),
            'royal_office_extended': re.compile(
                r'\b(conseiller|trésorier|avocat|procureur|greffier)\s+du\s+(roi|roy)\b', re.IGNORECASE
            ),
            'ecclesiastical': re.compile(
                r'\b(curé|prestre|prêtre|vicaire|chapelain)\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+)\b',
                re.IGNORECASE
            ),
            'master_craftsman': re.compile(
                r'\b(maître|maistre)\s+(charpentier|maçon|tailleur|cordonnier|boulanger)\b', re.IGNORECASE
            )
        }
    
    @get_cache("profession_parser").cached_method()
    def extract_professions_and_titles(self, text: str) -> List[Dict]:
        if not text:
            return []
        
        results = []
        used_positions = set()
        
        extraction_patterns = [
            ('royal_office', self.custom_patterns['royal_office_extended']),
            ('ecclesiastical', self.custom_patterns['ecclesiastical']),
            ('master_craftsman', self.custom_patterns['master_craftsman']),
            ('title_with_land', self.patterns['title_land']),
            ('profession_basic', self.custom_patterns['profession_basic']),
            ('title_basic', self.custom_patterns['title_basic'])
        ]
        
        for pattern_name, pattern in extraction_patterns:
            for match in pattern.finditer(text):
                start, end = match.span()
                if not any(pos in used_positions for pos in range(start, end)):
                    result = self._parse_profession_title_match(match, pattern_name)
                    if result:
                        results.append(result)
                        used_positions.update(range(start, end))
                        
                        if result['category'] == 'profession':
                            self.stats['professions_found'] += 1
                        elif result['category'] == 'title':
                            self.stats['titles_found'] += 1
                        elif result['category'] == 'land':
                            self.stats['lands_found'] += 1
        
        return self._deduplicate_and_rank_results(results)
    
    def _parse_profession_title_match(self, match, pattern_name: str) -> Optional[Dict]:
        if pattern_name == 'royal_office':
            office, monarch = match.groups()
            return {
                'type': f"{office} du {monarch}",
                'category': 'profession',
                'subcategory': 'royal_office',
                'office': office,
                'authority': monarch,
                'original_text': match.group(0),
                'position': match.span(),
                'confidence': 0.9
            }
        
        elif pattern_name == 'ecclesiastical':
            position, place = match.groups()
            return {
                'type': position,
                'category': 'profession',
                'subcategory': 'ecclesiastical',
                'place': place.strip(),
                'original_text': match.group(0),
                'position': match.span(),
                'confidence': 0.85
            }
        
        elif pattern_name == 'master_craftsman':
            title, craft = match.groups()
            return {
                'type': f"{title} {craft}",
                'category': 'profession',
                'subcategory': 'craftsman',
                'craft': craft,
                'original_text': match.group(0),
                'position': match.span(),
                'confidence': 0.8
            }
        
        elif pattern_name == 'title_with_land':
            land = match.group(1)
            title_match = re.search(r'\b(sieur|sr|seigneur|sgr|écuyer|éc)\b', match.group(0), re.IGNORECASE)
            title = title_match.group(1) if title_match else 'seigneur'
            
            return {
                'type': title,
                'category': 'title',
                'subcategory': 'landed',
                'land': land.strip(),
                'original_text': match.group(0),
                'position': match.span(),
                'confidence': 0.85
            }
        
        elif pattern_name in ['profession_basic', 'title_basic']:
            profession_or_title = match.group(1).lower()
            
            category = 'profession' if pattern_name == 'profession_basic' else 'title'
            standardized_type = self._standardize_profession_title(profession_or_title, category)
            
            return {
                'type': standardized_type,
                'category': category,
                'subcategory': 'basic',
                'original_text': match.group(0),
                'position': match.span(),
                'confidence': 0.7
            }
        
        return None
    
    def _standardize_profession_title(self, term: str, category: str) -> str:
        term_lower = term.lower()
        
        reference_dict = self.professions if category == 'profession' else self.titles
        
        for standard, variants in reference_dict.items():
            if term_lower in [v.lower() for v in variants]:
                return standard
        
        return term
    
    def _deduplicate_and_rank_results(self, results: List[Dict]) -> List[Dict]:
        if not results:
            return []
        
        unique_results = {}
        for result in results:
            key = f"{result['category']}_{result['type'].lower()}_{result.get('place', '').lower()}"
            
            if key not in unique_results or result['confidence'] > unique_results[key]['confidence']:
                unique_results[key] = result
        
        return sorted(unique_results.values(), key=lambda x: x['confidence'], reverse=True)
    
    @get_cache("profession_parser").cached_method()
    def extract_with_context(self, text: str, context_window: int = 30) -> List[Dict]:
        results = self.extract_professions_and_titles(text)
        
        for result in results:
            start, end = result['position']
            context_start = max(0, start - context_window)
            context_end = min(len(text), end + context_window)
            
            context = text[context_start:context_end].strip()
            result['context'] = context
            result['context_analysis'] = self._analyze_context(context, result)
        
        return results
    
    def _analyze_context(self, context: str, result: Dict) -> Dict:
        context_lower = context.lower()
        
        name_matches = len(re.findall(r'\b[A-Z][a-z]+\b', context))
        date_matches = len(re.findall(r'\b\d{4}\b', context))
        
        relationship_indicators = {
            'family': len(re.findall(r'\b(fils|fille|épouse|mari|père|mère)\b', context_lower)),
            'professional': len(re.findall(r'\b(maître|apprenti|compagnon|associé)\b', context_lower)),
            'location': len(re.findall(r'\b(de|du|des)\s+[A-Z][a-z]+\b', context))
        }
        
        return {
            'name_density': name_matches / max(len(context.split()), 1),
            'has_dates': date_matches > 0,
            'relationship_indicators': relationship_indicators,
            'context_length': len(context),
            'prominence_score': context.count(result['type']) / max(len(context.split()), 1)
        }
    
    def get_profession_statistics(self, results: List[Dict]) -> Dict:
        if not results:
            return {'total': 0, 'by_category': {}, 'by_subcategory': {}, 'confidence_distribution': {}}
        
        by_category = Counter(r['category'] for r in results)
        by_subcategory = Counter(r['subcategory'] for r in results)
        
        confidence_ranges = {'high': 0, 'medium': 0, 'low': 0}
        for result in results:
            conf = result['confidence']
            if conf >= 0.8:
                confidence_ranges['high'] += 1
            elif conf >= 0.6:
                confidence_ranges['medium'] += 1
            else:
                confidence_ranges['low'] += 1
        
        most_common_professions = Counter(
            r['type'] for r in results if r['category'] == 'profession'
        ).most_common(5)
        
        most_common_titles = Counter(
            r['type'] for r in results if r['category'] == 'title'
        ).most_common(5)
        
        return {
            'total': len(results),
            'by_category': dict(by_category),
            'by_subcategory': dict(by_subcategory),
            'confidence_distribution': confidence_ranges,
            'most_common_professions': most_common_professions,
            'most_common_titles': most_common_titles,
            'average_confidence': sum(r['confidence'] for r in results) / len(results)
        }
    
    def get_stats(self) -> Dict:
        cache_stats = self.cache.get_stats()
        return {
            **self.stats,
            'cache_hit_rate': cache_stats['hit_rate_percent'],
            'cache_size': cache_stats['size']
        }