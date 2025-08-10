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
        self.stats = {'names_extracted': 0, 'valid_names': 0, 'ocr_corrections': 0, 'false_positives_filtered': 0}
        
        self.religious_titles = {'dom', 'père', 'abbé', 'prieur', 'frère', 'sœur', 'mère'}
        self.noble_titles = {'sieur', 'sr', 'seigneur', 'sgr', 'écuyer', 'éc', 'noble', 'damoiselle', 'dame', 'comte', 'baron', 'duc'}
        self.particles = {'de', 'du', 'des', 'le', 'la', 'les', "d'", 'von', 'van'}
        
        self.location_patterns = [
            re.compile(r'^(paroisse|église|chapelle|cathédrale|abbaye)\s+', re.IGNORECASE),
            re.compile(r'^(clos|champ|pré|jardin|verger)\s+', re.IGNORECASE),
            re.compile(r'^(la|le)\s+[a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+ière?$', re.IGNORECASE),
            re.compile(r'^familles?\s+', re.IGNORECASE),
            re.compile(r'^(rue|place|chemin|route)\s+', re.IGNORECASE)
        ]
        
        self.incomplete_name_patterns = [
            re.compile(r'^[a-z]{1,2}$', re.IGNORECASE),
            re.compile(r'\s[a-z]{1,2}$', re.IGNORECASE),
            re.compile(r'^(dom|père|abbé)\s+[a-z]{1,2}$', re.IGNORECASE)
        ]
        
        self.patterns = pattern_compiler.get_all_patterns()
        
        self.name_quality_thresholds = {
            'minimum': 0.4,
            'good': 0.7,
            'excellent': 0.85
        }
    
    @get_cache("name_extractor").cached_method()
    def extract_names(self, text: str) -> List[Dict]:
        if not text:
            return []
        
        corrected_text = ocr_corrector.correct_text(text)
        names = []
        used_positions = set()
        
        extraction_patterns = [
            ('name_with_religious_title', self._get_religious_title_pattern()),
            ('name_with_noble_title', self._get_noble_title_pattern()),
            ('name_with_particle', self.patterns['name_with_particle']),
            ('compound_name', self.patterns['compound_name']),
            ('name_full', self.patterns['name_full']),
            ('name_basic', self.patterns['name_basic'])
        ]
        
        for pattern_name, pattern in extraction_patterns:
            for match in pattern.finditer(corrected_text):
                start, end = match.span()
                if not any(pos in used_positions for pos in range(start, end)):
                    
                    name_info = self._parse_and_validate_name(match, start, end, pattern_name, corrected_text)
                    
                    if name_info and self._is_valid_person_name(name_info):
                        names.append(name_info)
                        used_positions.update(range(start, end))
                        self.stats['names_extracted'] += 1
                        
                        if name_info['confidence'] > self.name_quality_thresholds['good']:
                            self.stats['valid_names'] += 1
        
        return self._deduplicate_and_rank_names(names)
    
    def _get_religious_title_pattern(self):
        titles = '|'.join(self.religious_titles)
        name_pattern = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-]{2,25}'
        return re.compile(rf'\b({titles})\s+({name_pattern}(?:\s+{name_pattern})*)', re.IGNORECASE)
    
    def _get_noble_title_pattern(self):
        titles = '|'.join(self.noble_titles)
        name_pattern = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-]{2,25}'
        return re.compile(rf'\b({titles})\s+(?:de\s+)?({name_pattern}(?:\s+{name_pattern})*)', re.IGNORECASE)
    
    def _parse_and_validate_name(self, match, start: int, end: int, source_pattern: str, full_text: str) -> Optional[Dict]:
        if source_pattern in ['name_with_religious_title', 'name_with_noble_title']:
            title = match.group(1).strip()
            name_text = match.group(2).strip()
        else:
            title = ""
            if source_pattern == 'name_with_title':
                name_text = match.group(1).strip()
            else:
                name_text = match.group(0).strip()
        
        corrected_name = ocr_corrector.correct_name(name_text)
        if corrected_name != name_text:
            self.stats['ocr_corrections'] += 1
        
        if self._is_location_or_false_positive(corrected_name):
            self.stats['false_positives_filtered'] += 1
            return None
        
        if self._is_incomplete_name(corrected_name):
            return None
        
        validation = name_validator.validate_name(corrected_name)
        if not validation.is_valid:
            return None
        
        parsed_name = self._parse_name_components(corrected_name, title)
        
        context_start = max(0, start - 30)
        context_end = min(len(full_text), end + 30)
        context = full_text[context_start:context_end].strip()
        
        confidence = self._calculate_extraction_confidence(corrected_name, source_pattern, validation, context)
        
        return {
            'full_name': corrected_name,
            'title': parsed_name['title'],
            'first_names': parsed_name['first_names'],
            'particles': parsed_name['particles'],
            'family_name': parsed_name['family_name'],
            'position': (start, end),
            'source_pattern': source_pattern,
            'confidence': confidence,
            'validation_score': validation.score,
            'ocr_corrected': corrected_name != name_text,
            'word_count': len(corrected_name.split()),
            'context': context
        }
    
    def _parse_name_components(self, name: str, title: str = "") -> Dict[str, any]:
        parts = name.split()
        
        first_names = []
        particles = []
        family_name = ""
        
        i = 0
        while i < len(parts):
            part = parts[i]
            part_lower = part.lower()
            
            if part_lower in self.particles:
                particles.append(part)
                if i + 1 < len(parts):
                    remaining_parts = parts[i:]
                    family_name = ' '.join(remaining_parts)
                    break
            elif i == len(parts) - 1:
                family_name = part
            else:
                first_names.append(part)
            i += 1
        
        if not family_name and first_names:
            family_name = first_names.pop()
        
        return {
            'title': title,
            'first_names': first_names,
            'particles': particles,
            'family_name': family_name
        }
    
    def _is_location_or_false_positive(self, name: str) -> bool:
        for pattern in self.location_patterns:
            if pattern.match(name):
                return True
        
        false_positive_keywords = {
            'archives', 'registre', 'folio', 'page', 'acte', 'document',
            'inventaire', 'sommaire', 'table', 'index'
        }
        
        name_lower = name.lower()
        if any(keyword in name_lower for keyword in false_positive_keywords):
            return True
        
        if re.match(r'^[A-Z]{2,}$', name):
            return True
        
        return False
    
    def _is_incomplete_name(self, name: str) -> bool:
        for pattern in self.incomplete_name_patterns:
            if pattern.match(name):
                return True
        
        if len(name.strip()) < 3:
            return True
        
        words = name.split()
        if len(words) == 1 and len(words[0]) < 3:
            return True
        
        return False
    
    def _is_valid_person_name(self, name_info: Dict) -> bool:
        if name_info['confidence'] < self.name_quality_thresholds['minimum']:
            return False
        
        full_name = name_info['full_name']
        
        if not name_info['family_name'] and not name_info['title']:
            return False
        
        if len(full_name) > 80:
            return False
        
        digit_ratio = sum(1 for c in full_name if c.isdigit()) / len(full_name)
        if digit_ratio > 0.2:
            return False
        
        return True
    
    def _calculate_extraction_confidence(self, name: str, source_pattern: str, validation, context: str) -> float:
        base_confidence = validation.confidence
        
        pattern_bonuses = {
            'name_with_religious_title': 0.2,
            'name_with_noble_title': 0.15,
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
        
        genealogical_context = any(term in context.lower() for term in [
            'fils', 'fille', 'épouse', 'mari', 'père', 'mère', 'baptême', 'mariage', 'décès'
        ])
        if genealogical_context:
            base_confidence += 0.1
        
        ocr_error_indicators = any(indicator in name.lower() for indicator in [
            'ii', 'rn', 'cl', 'vv', 'nn'
        ])
        if ocr_error_indicators:
            base_confidence -= 0.1
        
        return max(0.0, min(base_confidence, 1.0))
    
    def _deduplicate_and_rank_names(self, names: List[Dict]) -> List[Dict]:
        if not names:
            return []
        
        unique_names = {}
        for name in names:
            normalized_key = self._normalize_name_for_dedup(name['full_name'])
            
            if normalized_key not in unique_names or name['confidence'] > unique_names[normalized_key]['confidence']:
                unique_names[normalized_key] = name
        
        sorted_names = sorted(unique_names.values(), key=lambda x: x['confidence'], reverse=True)
        
        return sorted_names
    
    def _normalize_name_for_dedup(self, name: str) -> str:
        normalized = name.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = normalized.replace('dom ', '').replace('père ', '')
        return normalized
    
    @get_cache("name_extractor").cached_method()
    def extract_names_with_context(self, text: str, context_window: int = 50) -> List[Dict]:
        names = self.extract_names(text)
        
        for name in names:
            start, end = name['position']
            context_start = max(0, start - context_window)
            context_end = min(len(text), end + context_window)
            
            extended_context = text[context_start:context_end].strip()
            name['extended_context'] = extended_context
            name['context_analysis'] = self._analyze_name_context(extended_context, name['full_name'])
        
        return names
    
    def _analyze_name_context(self, context: str, name: str) -> Dict:
        context_lower = context.lower()
        
        relationship_indicators = {
            'filiation': len(re.findall(r'\b(fils|fille|filz)\b', context_lower)),
            'marriage': len(re.findall(r'\b(épouse|mari|époux|femme|veuve)\b', context_lower)),
            'godparent': len(re.findall(r'\b(parrain|marraine)\b', context_lower)),
            'clerical': len(re.findall(r'\b(curé|prêtre|vicaire|abbé)\b', context_lower))
        }
        
        date_mentions = len(re.findall(r'\b\d{4}\b', context))
        place_mentions = len(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', context))
        
        return {
            'relationship_indicators': relationship_indicators,
            'date_mentions': date_mentions,
            'place_mentions': place_mentions,
            'context_length': len(context),
            'name_prominence': context.count(name),
            'confidence_boost': sum(relationship_indicators.values()) * 0.05
        }
    
    def get_name_statistics(self, names: List[Dict]) -> Dict:
        if not names:
            return {'total': 0, 'quality_distribution': {}, 'pattern_distribution': {}}
        
        quality_distribution = {'excellent': 0, 'good': 0, 'minimum': 0}
        pattern_distribution = Counter()
        title_distribution = Counter()
        
        for name in names:
            confidence = name['confidence']
            if confidence >= self.name_quality_thresholds['excellent']:
                quality_distribution['excellent'] += 1
            elif confidence >= self.name_quality_thresholds['good']:
                quality_distribution['good'] += 1
            else:
                quality_distribution['minimum'] += 1
            
            pattern_distribution[name['source_pattern']] += 1
            
            if name['title']:
                title_distribution[name['title']] += 1
        
        return {
            'total': len(names),
            'quality_distribution': quality_distribution,
            'pattern_distribution': dict(pattern_distribution),
            'title_distribution': dict(title_distribution),
            'average_confidence': sum(n['confidence'] for n in names) / len(names),
            'ocr_correction_rate': sum(1 for n in names if n['ocr_corrected']) / len(names),
            'with_particles': sum(1 for n in names if n['particles']) / len(names),
            'with_titles': sum(1 for n in names if n['title']) / len(names)
        }
    
    def get_stats(self) -> Dict:
        cache_stats = self.cache.get_stats()
        return {
            **self.stats,
            'cache_hit_rate': cache_stats['hit_rate_percent'],
            'cache_size': cache_stats['size'],
            'validation_rate': self.stats['valid_names'] / max(self.stats['names_extracted'], 1),
            'false_positive_filter_rate': self.stats['false_positives_filtered'] / max(self.stats['names_extracted'] + self.stats['false_positives_filtered'], 1)
        }