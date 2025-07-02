from typing import Dict, List, Set, Tuple
from dataclasses import dataclass

@dataclass
class OCRConfig:
    name_corrections: Dict[str, str]
    systematic_corrections: Dict[str, str]
    ligature_corrections: Dict[str, str]
    punctuation_corrections: Dict[str, str]
    context_corrections: Dict[str, str]
    rejection_patterns: List[str]
    
    @classmethod
    def get_default_config(cls) -> 'OCRConfig':
        return cls(
            name_corrections={
                'Aiicelle': 'Ancelle', 'Aiiber': 'Auber', 'Aiigotin': 'Antigotin',
                'Aiimont': 'Aumont', 'Aiivray': 'Auvray', 'Aii-': 'Anne',
                'Aiil': 'Anil', 'Aiine-': 'Anne-', 'Aiieelle': 'Ancelle',
                'Jaeques': 'Jacques', 'Franteois': 'François', 'Catlierhie': 'Catherine',
                'Guillaïune': 'Guillaume', 'Nicollas': 'Nicolas', 'Muiiie': 'Marie',
                'Cliarles': 'Charles', 'Jeau': 'Jean', 'Vietoire': 'Victoire',
                'Iagdeleine': 'Madeleine', 'Pi-ançois': 'François', 'Toussaiut': 'Toussaint',
                'Jlagdeleiue': 'Madeleine', 'Marie- An': 'Marie-Anne', 'Ade-': 'Adeline',
                'Alexandre-': 'Alexandre', 'Adrienne-': 'Adrienne', 'Agnès-': 'Agnès'
            },
            
            systematic_corrections={
                'Aii': 'Ann', 'Jae': 'Jac', 'Muii': 'Mari', 'Cliar': 'Char',
                'Viet': 'Vict', 'Iagd': 'Magd', 'Jlag': 'Mag', 'Touss': 'Touss',
                'rn': 'm', 'cl': 'cl', 'ri': 'n'
            },
            
            ligature_corrections={
                'ﬁ': 'fi', 'ﬂ': 'fl', 'œ': 'oe', 'æ': 'ae',
                'ß': 'ss', 'ſ': 's'
            },
            
            punctuation_corrections={
                'épous de': 'épouse de', 'fils d ': 'fils de ', 'fille d ': 'fille de ',
                'parr ain': 'parrain', 'marr aine': 'marraine', 'mar riage': 'mariage',
                'bapt ême': 'baptême', 'inhum ation': 'inhumation'
            },
            
            context_corrections={
                'sieur d e': 'sieur de', 'seigneur d e': 'seigneur de',
                'écuyer d e': 'écuyer de', 'fils d e': 'fils de',
                'fille d e': 'fille de', 'épouse d e': 'épouse de'
            },
            
            rejection_patterns=[
                r'archives\s+du\s+calvados',
                r'registre\s+paroissial',
                r'page\s+\d+',
                r'folio\s+\d+',
                r'\d{3,}',
                r'[<>@#$%^&*()]',
                r'^[^A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ]'
            ]
        )
    
    @classmethod
    def get_strict_config(cls) -> 'OCRConfig':
        default = cls.get_default_config()
        
        default.rejection_patterns.extend([
            r'^.{1,3}$',
            r'^.{50,}$',
            r'[0-9]{2,}',
            r'[^a-zA-ZÀ-ÿ\s\-\']{2,}'
        ])
        
        return default
    
    @classmethod
    def get_tolerant_config(cls) -> 'OCRConfig':
        default = cls.get_default_config()
        
        default.systematic_corrections.update({
            'rn': 'm', 'cl': 'cl', 'ri': 'n', 'ii': 'n',
            'vv': 'w', 'nn': 'n', 'rr': 'r'
        })
        
        default.name_corrections.update({
            'Mar ie': 'Marie', 'Jean ne': 'Jeanne', 'Pier re': 'Pierre',
            'Jac ques': 'Jacques', 'Fran çois': 'François', 'Char les': 'Charles',
            'Guil laume': 'Guillaume', 'Nico las': 'Nicolas'
        })
        
        return default
    
    def get_all_corrections(self) -> Dict[str, str]:
        all_corrections = {}
        all_corrections.update(self.name_corrections)
        all_corrections.update(self.systematic_corrections)
        all_corrections.update(self.ligature_corrections)
        all_corrections.update(self.punctuation_corrections)
        all_corrections.update(self.context_corrections)
        return all_corrections
    
    def get_rejection_patterns_compiled(self):
        import re
        return [re.compile(pattern, re.IGNORECASE) for pattern in self.rejection_patterns]

@dataclass
class OCRQualityMetrics:
    correction_confidence_threshold: float = 0.8
    word_length_threshold: Tuple[int, int] = (2, 30)
    character_ratio_threshold: float = 0.1
    numeric_content_threshold: float = 0.3
    
    @classmethod
    def get_strict_metrics(cls) -> 'OCRQualityMetrics':
        return cls(
            correction_confidence_threshold=0.9,
            word_length_threshold=(3, 25),
            character_ratio_threshold=0.05,
            numeric_content_threshold=0.1
        )
    
    @classmethod
    def get_tolerant_metrics(cls) -> 'OCRQualityMetrics':
        return cls(
            correction_confidence_threshold=0.6,
            word_length_threshold=(1, 40),
            character_ratio_threshold=0.2,
            numeric_content_threshold=0.5
        )

class OCRPreprocessor:
    def __init__(self, config: OCRConfig, metrics: OCRQualityMetrics):
        self.config = config
        self.metrics = metrics
        self.all_corrections = config.get_all_corrections()
        self.rejection_patterns = config.get_rejection_patterns_compiled()
        
        self.stats = {
            'texts_processed': 0,
            'corrections_applied': 0,
            'words_rejected': 0,
            'characters_corrected': 0
        }
    
    def preprocess_text(self, text: str) -> Dict[str, any]:
        if not text:
            return {'corrected': '', 'corrections': [], 'rejected_words': [], 'quality_score': 0.0}
        
        self.stats['texts_processed'] += 1
        
        original_text = text
        corrected_text = text
        corrections_applied = []
        rejected_words = []
        
        for incorrect, correct in self.all_corrections.items():
            if incorrect in corrected_text:
                corrected_text = corrected_text.replace(incorrect, correct)
                corrections_applied.append(f"{incorrect} → {correct}")
                self.stats['corrections_applied'] += 1
                self.stats['characters_corrected'] += len(incorrect)
        
        words = corrected_text.split()
        filtered_words = []
        
        for word in words:
            if self._should_reject_word(word):
                rejected_words.append(word)
                self.stats['words_rejected'] += 1
            else:
                filtered_words.append(word)
        
        final_text = ' '.join(filtered_words)
        quality_score = self._calculate_quality_score(original_text, final_text)
        
        return {
            'corrected': final_text,
            'corrections': corrections_applied,
            'rejected_words': rejected_words,
            'quality_score': quality_score,
            'compression_ratio': len(final_text) / max(len(original_text), 1),
            'stats': {
                'original_length': len(original_text),
                'final_length': len(final_text),
                'corrections_count': len(corrections_applied),
                'rejected_words_count': len(rejected_words)
            }
        }
    
    def _should_reject_word(self, word: str) -> bool:
        word_clean = word.strip()
        
        if not word_clean:
            return True
        
        word_length = len(word_clean)
        min_len, max_len = self.metrics.word_length_threshold
        if word_length < min_len or word_length > max_len:
            return True
        
        for pattern in self.rejection_patterns:
            if pattern.search(word_clean):
                return True
        
        numeric_chars = sum(1 for char in word_clean if char.isdigit())
        numeric_ratio = numeric_chars / len(word_clean)
        if numeric_ratio > self.metrics.numeric_content_threshold:
            return True
        
        return False
    
    def _calculate_quality_score(self, original: str, corrected: str) -> float:
        if not original or not corrected:
            return 0.0
        
        score = 0.5
        
        length_ratio = len(corrected) / len(original)
        if 0.7 <= length_ratio <= 1.1:
            score += 0.2
        
        word_count_original = len(original.split())
        word_count_corrected = len(corrected.split())
        if word_count_corrected >= word_count_original * 0.8:
            score += 0.2
        
        if self.stats['corrections_applied'] > 0:
            score += 0.1
        
        return min(score, 1.0)
    
    def get_stats(self) -> Dict[str, any]:
        return self.stats.copy()

ocr_config = OCRConfig.get_default_config()
strict_ocr_config = OCRConfig.get_strict_config()
tolerant_ocr_config = OCRConfig.get_tolerant_config()

quality_metrics = OCRQualityMetrics()
strict_quality_metrics = OCRQualityMetrics.get_strict_metrics()
tolerant_quality_metrics = OCRQualityMetrics.get_tolerant_metrics()