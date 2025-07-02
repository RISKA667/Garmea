import re
import unicodedata
from typing import Dict, List, Tuple
from functools import lru_cache

class OCRCorrector:
    def __init__(self):
        self.corrections_map = {
            'Aiicelle': 'Ancelle', 'Aiiber': 'Auber', 'Aiigotin': 'Antigotin',
            'Aiimont': 'Aumont', 'Aiivray': 'Auvray', 'Aii-': 'Anne',
            'Aiil': 'Anil', 'Aiine-': 'Anne-', 'Aiieelle': 'Ancelle',
            'Jaeques': 'Jacques', 'Franteois': 'François', 'Catlierhie': 'Catherine',
            'Guillaïune': 'Guillaume', 'Nicollas': 'Nicolas', 'Muiiie': 'Marie',
            'Cliarles': 'Charles', 'Jeau': 'Jean', 'Vietoire': 'Victoire',
            'Iagdeleine': 'Madeleine', 'Pi-ançois': 'François', 'Toussaiut': 'Toussaint',
            'Jlagdeleiue': 'Madeleine', 'Marie- An': 'Marie-Anne', 'Ade-': 'Adeline',
            'Alexandre-': 'Alexandre', 'Adrienne-': 'Adrienne', 'Agnès-': 'Agnès',
            'épous de': 'épouse de', 'fils d ': 'fils de ', 'fille d ': 'fille de ',
            'parr ain': 'parrain', 'marr aine': 'marraine'
        }
        
        self.ligature_corrections = {
            'ﬁ': 'fi', 'ﬂ': 'fl', 'œ': 'oe', 'æ': 'ae'
        }
        
        self.punctuation_fixes = {
            r'[,;\.]{2,}': ',', r'(\w)\s*-\s*(\w)': r'\1-\2',
            r'(\w)\s*\.\s*(\w)': r'\1.\2', r'\s+': ' '
        }
        
        self.compiled_patterns = {
            pattern: re.compile(pattern) for pattern in self.punctuation_fixes.keys()
        }
        
        self.stats = {'corrections_applied': 0, 'texts_processed': 0}
    
    @lru_cache(maxsize=2000)
    def correct_text(self, text: str) -> str:
        if not text:
            return ""
        
        self.stats['texts_processed'] += 1
        original_text = text
        
        text = unicodedata.normalize('NFKD', text)
        
        for incorrect, correct in self.corrections_map.items():
            if incorrect in text:
                text = text.replace(incorrect, correct)
                self.stats['corrections_applied'] += 1
        
        for ligature, replacement in self.ligature_corrections.items():
            text = text.replace(ligature, replacement)
        
        for pattern, replacement in self.punctuation_fixes.items():
            text = self.compiled_patterns[pattern].sub(replacement, text)
        
        return text.strip()
    
    @lru_cache(maxsize=1000)
    def correct_name(self, name: str) -> str:
        corrected = self.correct_text(name)
        
        words = corrected.split()
        corrected_words = []
        
        for word in words:
            if word in self.corrections_map:
                corrected_words.append(self.corrections_map[word])
            elif word.endswith('-') and len(word) > 2:
                base = word[:-1]
                if any(full_name.startswith(base) for full_name in ['Adeline', 'Alexandre', 'Adrienne', 'Agnès']):
                    corrected_words.append(base)
                else:
                    corrected_words.append(word)
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()
    
    def add_correction(self, incorrect: str, correct: str):
        self.corrections_map[incorrect] = correct
        self.correct_text.cache_clear()
        self.correct_name.cache_clear()

ocr_corrector = OCRCorrector()