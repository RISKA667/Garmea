import re
import logging
from typing import Dict, List, Optional, Tuple
import unicodedata
from ..common import ocr_corrector, pattern_compiler, get_cache

class TextParser:
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.cache = get_cache("text_parser", max_size=2000)
        self.stats = {'texts_processed': 0, 'corrections_applied': 0, 'normalizations': 0}
        
        self.abbreviations = {
            'bapt.': 'baptême', 'mar.': 'mariage', 'inh.': 'inhumation',
            'sr': 'sieur', 'sgr': 'seigneur', 'éc.': 'écuyer', 'ec.': 'écuyer',
            'fév.': 'février', 'sept.': 'septembre', 'oct.': 'octobre',
            'nov.': 'novembre', 'déc.': 'décembre', 'janv.': 'janvier',
            'parr.': 'parrain', 'marr.': 'marraine', 'épse': 'épouse'
        }
        
        self.parasitic_words = {
            'archives', 'calvados', 'registre', 'paroisse', 'page', 'folio',
            'acte', 'vue', 'image', 'scan', 'document', 'fichier'
        }
        
        self.patterns = pattern_compiler.get_all_patterns()
    
    @get_cache("text_parser").cached_method()
    def normalize_text(self, text: str) -> Dict[str, any]:
        if not text:
            return {'normalized': '', 'corrections': [], 'abbreviations_expanded': []}
        
        self.stats['texts_processed'] += 1
        original_text = text
        
        text = unicodedata.normalize('NFKD', text)
        
        corrected_text = ocr_corrector.correct_text(text)
        corrections_applied = corrected_text != text
        
        expanded_text, abbreviations_expanded = self._expand_abbreviations(corrected_text)
        
        normalized_text = self._normalize_spacing_and_punctuation(expanded_text)
        
        cleaned_text = self._remove_parasitic_elements(normalized_text)
        
        if corrections_applied:
            self.stats['corrections_applied'] += 1
        
        self.stats['normalizations'] += 1
        
        return {
            'normalized': cleaned_text,
            'corrections': [f"OCR: {len(ocr_corrector.corrections_map)} corrections"] if corrections_applied else [],
            'abbreviations_expanded': abbreviations_expanded,
            'original_length': len(original_text),
            'final_length': len(cleaned_text),
            'compression_ratio': len(cleaned_text) / max(len(original_text), 1)
        }
    
    def _expand_abbreviations(self, text: str) -> Tuple[str, List[str]]:
        expanded_words = []
        abbreviations_expanded = []
        
        words = text.split()
        for word in words:
            original_word = word
            word_clean = re.sub(r'[^\w\.]', '', word).strip().lower()
            
            if word_clean in self.abbreviations:
                expanded_word = word.replace(word_clean, self.abbreviations[word_clean])
                expanded_words.append(expanded_word)
                abbreviations_expanded.append(f"{original_word} → {expanded_word}")
            else:
                expanded_words.append(word)
        
        return ' '.join(expanded_words), abbreviations_expanded
    
    def _normalize_spacing_and_punctuation(self, text: str) -> str:
        text = self.patterns['cleanup_spaces'].sub(' ', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r'([.,;:])([A-Za-z])', r'\1 \2', text)
        text = re.sub(r'\s+([.,;:])', r'\1', text)
        text = self.patterns['cleanup_punctuation'].sub(',', text)
        text = self.patterns['cleanup_dashes'].sub(r'\1-\2', text)
        return text.strip()
    
    def _remove_parasitic_elements(self, text: str) -> str:
        words = text.split()
        filtered_words = []
        
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word).lower()
            if word_clean not in self.parasitic_words and len(word_clean) > 1:
                if not re.search(r'^[^A-Za-zÀ-ÿ]*$', word):
                    filtered_words.append(word)
        
        return ' '.join(filtered_words)
    
    @get_cache("text_parser").cached_method()
    def extract_segments(self, text: str) -> List[Dict]:
        normalized_result = self.normalize_text(text)
        normalized_text = normalized_result['normalized']
        
        segments = []
        sentences = re.split(r'[.;]\s+', normalized_text)
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) > 10:
                segment_type = self._classify_segment(sentence)
                segments.append({
                    'index': i,
                    'text': sentence,
                    'length': len(sentence),
                    'type': segment_type,
                    'word_count': len(sentence.split()),
                    'quality_score': self._calculate_segment_quality(sentence)
                })
        
        return segments
    
    def _classify_segment(self, text: str) -> str:
        text_lower = text.lower()
        
        baptism_keywords = ['bapt', 'baptême', 'naissance', 'né', 'née']
        marriage_keywords = ['mariage', 'épouse', 'mari', 'époux', 'mariée']
        death_keywords = ['inh', 'inhumation', 'décès', 'mort', 'décédé', 'défunt']
        
        if any(keyword in text_lower for keyword in baptism_keywords):
            return 'bapteme'
        elif any(keyword in text_lower for keyword in marriage_keywords):
            return 'mariage'
        elif any(keyword in text_lower for keyword in death_keywords):
            return 'deces'
        
        return 'general'
    
    def _calculate_segment_quality(self, segment: str) -> float:
        score = 0.0
        
        if len(segment) > 20:
            score += 0.2
        
        proper_names = len(self.patterns['name_basic'].findall(segment))
        if proper_names > 0:
            score += min(proper_names * 0.15, 0.4)
        
        dates = len(self.patterns['date_year_only'].findall(segment))
        if dates > 0:
            score += min(dates * 0.2, 0.3)
        
        genealogical_terms = len(re.findall(r'\b(fils|fille|épouse|mari|parrain|marraine)\b', segment, re.IGNORECASE))
        if genealogical_terms > 0:
            score += min(genealogical_terms * 0.1, 0.2)
        
        return min(score, 1.0)
    
    def get_stats(self) -> Dict:
        cache_stats = self.cache.get_stats()
        return {
            **self.stats,
            'cache_hit_rate': cache_stats['hit_rate_percent'],
            'cache_size': cache_stats['size']
        }