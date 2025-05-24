import re
import logging
from typing import Dict, List, Tuple, Optional
from functools import lru_cache
from dataclasses import dataclass

from config.settings import ParserConfig

@dataclass
class CorrectionSuggestion:
    """Suggestion de correction de transcription"""
    original: str
    corrected: str
    confidence: float
    rule_applied: str
    context: str

class TranscriptionCorrector:
    """Correcteur de transcription basé sur des patterns historiques"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Dictionnaire de corrections spécifiques aux registres français
        self.correction_patterns = self._load_correction_patterns()
        
        # Cache des corrections
        self._correction_cache = {}
    
    def _load_correction_patterns(self) -> Dict[str, List[Dict]]:
        """Charge les patterns de correction pour transcription historique"""
        return {
            'abbreviation_expansions': [
                {'pattern': r'\bsr\b', 'replacement': 'sieur', 'confidence': 0.95},
                {'pattern': r'\bsgr\b', 'replacement': 'seigneur', 'confidence': 0.95},
                {'pattern': r'\béc\.\b', 'replacement': 'écuyer', 'confidence': 0.90},
                {'pattern': r'\bBapt\.\b', 'replacement': 'baptême', 'confidence': 0.95},
                {'pattern': r'\bmar\.\b', 'replacement': 'mariage', 'confidence': 0.90},
                {'pattern': r'\binh\.\b', 'replacement': 'inhumation', 'confidence': 0.95},
                {'pattern': r'\bprestre\b', 'replacement': 'prêtre', 'confidence': 0.95},
                {'pattern': r'\bfév\.\b', 'replacement': 'février', 'confidence': 0.95},
                {'pattern': r'\bsept\.\b', 'replacement': 'septembre', 'confidence': 0.95},
                {'pattern': r'\boct\.\b', 'replacement': 'octobre', 'confidence': 0.95},
                {'pattern': r'\bnov\.\b', 'replacement': 'novembre', 'confidence': 0.95},
                {'pattern': r'\bdéc\.\b', 'replacement': 'décembre', 'confidence': 0.95},
            ],
            
            'orthographic_variations': [
                {'pattern': r'\by\b', 'replacement': 'i', 'confidence': 0.75, 'context': 'medieval_names'},
                {'pattern': r'([a-z])\1{2,}', 'replacement': r'\1\1', 'confidence': 0.70, 'context': 'double_letters'},
                {'pattern': r'ph', 'replacement': 'f', 'confidence': 0.60, 'context': 'greek_letters'},
                {'pattern': r'th', 'replacement': 't', 'confidence': 0.65, 'context': 'greek_letters'},
            ],
            
            'particule_corrections': [
                {'pattern': r'\bDe([A-Z][a-z]+)', 'replacement': r'de \1', 'confidence': 0.90},
                {'pattern': r'\bDu([A-Z][a-z]+)', 'replacement': r'du \1', 'confidence': 0.90},
                {'pattern': r'\bLe([A-Z][a-z]+)', 'replacement': r'Le \1', 'confidence': 0.85},
            ],
            
            'date_corrections': [
                {'pattern': r'(\d+)e\s+jour\s+de\s+(\w+)', 'replacement': r'\1 \2', 'confidence': 0.85},
                {'pattern': r'l\'an\s+de\s+grâce\s+(\d{4})', 'replacement': r'\1', 'confidence': 0.95},
            ],
            
            'common_mistakes': [
                {'pattern': r'\bmoy\b', 'replacement': 'moi', 'confidence': 0.80},
                {'pattern': r'\bay\b(?=\s+[a-z])', 'replacement': 'ai', 'confidence': 0.75},
                {'pattern': r'\blesd\.\b', 'replacement': 'lesdits', 'confidence': 0.90},
                {'pattern': r'\blad\.\b', 'replacement': 'ladite', 'confidence': 0.90},
                {'pattern': r'\bdesd\.\b', 'replacement': 'décédé', 'confidence': 0.85},
            ]
        }
    
    @lru_cache(maxsize=1000)
    def suggest_corrections(self, text: str, context: str = "") -> List[CorrectionSuggestion]:
        """Suggère des corrections pour un texte donné"""
        suggestions = []
        
        for category, patterns in self.correction_patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info['pattern']
                replacement = pattern_info['replacement']
                confidence = pattern_info['confidence']
                
                # Appliquer le pattern
                matches = list(re.finditer(pattern, text, re.IGNORECASE))
                
                for match in matches:
                    original = match.group(0)
                    
                    # Appliquer la correction
                    if pattern_info.get('context'):
                        # Vérifier si le contexte est approprié
                        if not self._is_context_appropriate(context, pattern_info['context']):
                            continue
                    
                    corrected = re.sub(pattern, replacement, original, flags=re.IGNORECASE)
                    
                    if original != corrected:
                        suggestion = CorrectionSuggestion(
                            original=original,
                            corrected=corrected,
                            confidence=confidence,
                            rule_applied=f"{category}:{pattern}",
                            context=context[:100] if context else ""
                        )
                        suggestions.append(suggestion)
        
        # Trier par confiance décroissante
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        
        return suggestions
    
    def apply_corrections(self, text: str, min_confidence: float = 0.8) -> Tuple[str, List[CorrectionSuggestion]]:
        """Applique automatiquement les corrections avec confiance élevée"""
        suggestions = self.suggest_corrections(text)
        
        corrected_text = text
        applied_corrections = []
        
        for suggestion in suggestions:
            if suggestion.confidence >= min_confidence:
                # Appliquer la correction
                corrected_text = corrected_text.replace(suggestion.original, suggestion.corrected)
                applied_corrections.append(suggestion)
        
        return corrected_text, applied_corrections
    
    def _is_context_appropriate(self, context: str, context_type: str) -> bool:
        """Vérifie si le contexte est approprié pour une correction"""
        context_lower = context.lower()
        
        context_indicators = {
            'medieval_names': ['sieur', 'seigneur', 'écuyer', 'noble'],
            'double_letters': ['ll', 'nn', 'mm', 'tt'],
            'greek_letters': ['philosophe', 'théologie', 'mathématiques'],
            'ecclesiastical': ['curé', 'prêtre', 'église', 'chapelle'],
            'legal': ['avocat', 'conseiller', 'notaire', 'roi']
        }
        
        indicators = context_indicators.get(context_type, [])
        return any(indicator in context_lower for indicator in indicators)
    
    def learn_from_corrections(self, original_text: str, corrected_text: str, 
                             confidence: float = 0.8):
        """Apprend de nouvelles corrections pour améliorer le modèle"""
        # Cette méthode pourrait être étendue pour l'apprentissage automatique
        if confidence >= 0.9:
            self.logger.info(f"Nouvelle correction apprise: '{original_text}' → '{corrected_text}'")
            
            # Ajouter au cache pour usage futur
            self._correction_cache[original_text.lower()] = {
                'corrected': corrected_text,
                'confidence': confidence,
                'learned': True
            }
    
    def validate_correction(self, original: str, corrected: str, context: str) -> float:
        """Valide une correction proposée et retourne un score de confiance"""
        # Analyse linguistique basique
        confidence = 0.5
        
        # Bonus si la correction suit des patterns connus
        for category, patterns in self.correction_patterns.items():
            for pattern_info in patterns:
                if re.search(pattern_info['pattern'], original, re.IGNORECASE):
                    expected_correction = re.sub(
                        pattern_info['pattern'], 
                        pattern_info['replacement'], 
                        original, 
                        flags=re.IGNORECASE
                    )
                    if expected_correction.lower() == corrected.lower():
                        confidence += 0.3
                        break
        
        # Bonus si le contexte supporte la correction
        if self._context_supports_correction(context, original, corrected):
            confidence += 0.2
        
        return min(1.0, confidence)
    
    def _context_supports_correction(self, context: str, original: str, corrected: str) -> bool:
        """Vérifie si le contexte supporte une correction"""
        context_lower = context.lower()
        
        # Vérifications spécifiques
        if 'prestre' in original and 'prêtre' in corrected:
            return any(word in context_lower for word in ['église', 'curé', 'bénéfice'])
        
        if 'sr' in original and 'sieur' in corrected:
            return any(word in context_lower for word in ['de', 'terre', 'seigneurie'])
        
        return True
    
    def get_correction_statistics(self) -> Dict:
        """Retourne les statistiques des corrections"""
        stats = {
            'total_patterns': sum(len(patterns) for patterns in self.correction_patterns.values()),
            'categories': list(self.correction_patterns.keys()),
            'cache_size': len(self._correction_cache),
            'learned_corrections': len([c for c in self._correction_cache.values() if c.get('learned')])
        }
        
        return stats