import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from collections import Counter
from ..common import ocr_corrector, pattern_compiler, name_validator, get_cache

class NameExtractor:
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.cache = get_cache("name_extractor", max_size=1500)
        self.stats = {'names_extracted': 0, 'valid_names': 0, 'ocr_corrections': 0}
        
        self.particles = {'de', 'du', 'des', 'le', 'la', 'les', "d'", 'von', 'van'}
        self.titles = {'sieur', 'sr', 'seigneur', 'sgr', 'écuyer', 'éc', 'noble', 'damoiselle', 'dame'}
        
        self.patterns = pattern_compiler.get_all_patterns()
        
        self.name_quality_thresholds = {
            'minimum': 0.3,
            'good': 0.6,
            'excellent': 0.8
        }
    
    @get_cache("name_extractor").cached_method()
    def extract_names(self, text: str) -> List[Dict]:
        if not text:
            return []
        
        corrected_text = ocr_corrector.correct_text(text)
        names = []
        used_positions = set()
        
        extraction_patterns = [
            ('name_with_title', self.patterns['name_with_title']),
            ('name_with_particle', self.patterns['name_with_particle']),
            ('compound_name', self.patterns['compound_name']),
            ('name_full', self.patterns['name_full']),
            ('name_basic', self.patterns['name_basic'])
        ]
        
        for pattern_name, pattern in extraction_patterns:
            for match in pattern.finditer(corrected_text):
                start, end = match.span()
                if not any(pos in used_positions for pos in range(start, end)):
                    
                    if pattern_name == 'name_with_title':
                        name_text = match.group(1)
                    else:
                        name_text = match.group(0)
                    
                    name_info = self._parse_and_validate_name(name_text, start, end, pattern_name)
                    
                    if name_info and name_info['confidence'] > self.name_quality_thresholds['minimum']:
                        names.append(name_info)
                        used_positions.update(range(start, end))
                        self.stats['names_extracted'] += 1
                        
                        if name_info['confidence'] > self.name_quality_thresholds['good']:
                            self.stats['valid_names'] += 1
        
        return self._deduplicate_and_rank_names(names)
    
    def _parse_and_validate_name(self, name_text: str, start: int, end: int, source_pattern: str) -> Optional[Dict]:
        name_text = name_text.strip()
        
        corrected_name = ocr_corrector.correct_name(name_text)
        if corrected_name != name_text:
            self.stats['ocr_corrections'] += 1
        
        validation = name_validator.validate_name(corrected_name)
        if not validation.is_valid:
            return None
        
        parts = corrected_name.split()
        first_names = []
        particles = []
        family_name = ""
        
        i = 0
        while i < len(parts):
            part = parts[i]
            part_lower = part.lower()
            
            if part_lower in self.particles:
                particles.append(part)
            elif part_lower in self.titles:
                pass
            elif not family_name and i == len(parts) - 1:
                family_name = part
            else:
                first_names.append(part)
            i += 1
        
        if not family_name and first_names:
            family_name = first_names.pop()
        
        confidence = self._calculate_extraction_confidence(corrected_name, source_pattern, validation)
        
        return {
            'full_name': corrected_name,
            'first_names': first_names,
            'particles': particles,
            'family_name': family_name,
            'position': (start, end),
            'source_pattern': source_pattern,
            'confidence': confidence,
            'validation_score': validation.score,
            'ocr_corrected': corrected_name != name_text,
            'word_count': len(parts)
        }
    
    def _calculate_extraction_confidence(self, name: str, source_pattern: str, validation) -> float:
        base_confidence = validation.confidence
        
        pattern_bonuses = {
            'name_with_title': 0.15,
            'name_with_particle': 0.1,
            'compound_name': 0.1,
            'name_full': 0.05,
            'name_basic': 0.0
        }
        
        base_confidence += pattern_bonuses.get(source_pattern, 0.0)
        
        if '-' in name:
            base_confidence += 0.05
        
        word_count = len(name.split())
        if word_count == 2:
            base_confidence += 0.1
        elif word_count == 3:
            base_confidence += 0.05
        elif word_count > 4:
            base_confidence -= 0.05
        
        return min(base_confidence, 1.0)
    
    def _deduplicate_and_rank_names(self, names: List[Dict]) -> List[Dict]:
        if not names:
            return []
        
        unique_names = {}
        for name in names:
            family_key = name['family_name'].lower().strip()
            full_key = name['full_name'].lower().strip()
            
            key = f"{family_key}_{full_key}"
            
            if key not in unique_names or name['confidence'] > unique_names[key]['confidence']:
                unique_names[key] = name
        
        sorted_names = sorted(unique_names.values(), key=lambda x: x['confidence'], reverse=True)
        
        return sorted_names
    
    @get_cache("name_extractor").cached_method()
    def extract_names_with_context(self, text: str, context_window: int = 50) -> List[Dict]:
        names = self.extract_names(text)
        
        for name in names:
            start, end = name['position']
            context_start = max(0, start - context_window)
            context_end = min(len(text), end + context_window)
            
            context = text[context_start:context_end].strip()
            name['context'] = context
            name['context_analysis'] = self._analyze_name_context(context, name['full_name'])
        
        return names
    
    def _analyze_name_context(self, context: str, name: str) -> Dict:
        context_lower = context.lower()
        
        relationship_indicators = {
            'filiation': len(re.findall(r'\b(fils|fille|filz)\b', context_lower)),
            'marriage': len(re.findall(r'\b(épouse|mari|époux|femme|veuve)\b', context_lower)),
            'godparent': len(re.findall(r'\b(parrain|marraine)\b', context_lower)),
            'profession': len(re.findall(r'\b(curé|prêtre|avocat|notaire|marchand)\b', context_lower))
        }
        
        date_mentions = len(re.findall(r'\b\d{4}\b', context))
        place_mentions = len(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', context))
        
        return {
            'relationship_indicators': relationship_indicators,
            'date_mentions': date_mentions,
            'place_mentions': place_mentions,
            'context_length': len(context),
            'name_prominence': context.count(name)
        }
    
    def get_name_statistics(self, names: List[Dict]) -> Dict:
        if not names:
            return {'total': 0, 'quality_distribution': {}, 'pattern_distribution': {}}
        
        quality_distribution = {'excellent': 0, 'good': 0, 'minimum': 0}
        pattern_distribution = Counter()
        
        for name in names:
            confidence = name['confidence']
            if confidence >= self.name_quality_thresholds['excellent']:
                quality_distribution['excellent'] += 1
            elif confidence >= self.name_quality_thresholds['good']:
                quality_distribution['good'] += 1
            else:
                quality_distribution['minimum'] += 1
            
            pattern_distribution[name['source_pattern']] += 1
        
        return {
            'total': len(names),
            'quality_distribution': quality_distribution,
            'pattern_distribution': dict(pattern_distribution),
            'average_confidence': sum(n['confidence'] for n in names) / len(names),
            'ocr_correction_rate': sum(1 for n in names if n['ocr_corrected']) / len(names)
        }
    
    def get_stats(self) -> Dict:
        cache_stats = self.cache.get_stats()
        return {
            **self.stats,
            'cache_hit_rate': cache_stats['hit_rate_percent'],
            'cache_size': cache_stats['size'],
            'validation_rate': self.stats['valid_names'] / max(self.stats['names_extracted'], 1)
        }