import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from ..common import pattern_compiler, get_cache
from ..base import TextParser, NameExtractor, DateParser
from ..relationship import RelationshipFactory

class HistoricalPeriod(Enum):
    ANCIEN_REGIME = "ancien_regime"
    REVOLUTION = "revolution"
    ETAT_CIVIL_ANCIEN = "etat_civil_ancien"
    MODERNE = "moderne"

@dataclass
class PeriodDetection:
    period: HistoricalPeriod
    confidence: float
    indicators: List[str]
    estimated_date_range: Tuple[int, int]
    vocabulary_matches: Dict[str, int]

class PeriodParser:
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.cache = get_cache("period_parser", max_size=500)
        
        self.stats = {
            'documents_processed': 0, 'period_detections': 0,
            'successful_parses': 0, 'fallback_used': 0
        }
        
        self.period_indicators = self._setup_period_indicators()
        self.period_parsers = self._initialize_specialized_parsers()
        self.patterns = pattern_compiler.get_all_patterns()
    
    def _setup_period_indicators(self) -> Dict[HistoricalPeriod, Dict]:
        return {
            HistoricalPeriod.ANCIEN_REGIME: {
                'vocabulary': [
                    'bapt.', 'inh.', 'curé', 'prestre', 'chapelle', 'paroisse',
                    'sieur', 'escuyer', 'conseiller du roi', 'sr de', 'sgr de',
                    'pris possession', 'bénéfice', 'cure', 'filz', 'feu',
                    'défunt', 'grâce', 'nostre seigneur'
                ],
                'date_patterns': [
                    r"l'an\s+(?:de\s+)?(?:grâce\s+)?\d{4}",
                    r"(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}",
                    r"\d{4}(?:[-–]\d{4})?"
                ],
                'format_indicators': [
                    'ay,? au nom de Dieu', 'moy,? .+? prestre',
                    'registre de baptesmes', 'livre de raison'
                ],
                'date_range': (1500, 1789),
                'characteristic_phrases': [
                    'registre des baptesmes et inhumations',
                    'paroisse de nostre dame',
                    'en présence de'
                ]
            },
            
            HistoricalPeriod.REVOLUTION: {
                'vocabulary': [
                    'vendémiaire', 'brumaire', 'frimaire', 'nivôse', 'pluviôse', 'ventôse',
                    'germinal', 'floréal', 'prairial', 'messidor', 'thermidor', 'fructidor',
                    'citoyen', 'citoyenne', 'commune', 'république', 'directoire',
                    'an', 'liberté', 'égalité', 'déclaration'
                ],
                'date_patterns': [
                    r"l'an\s+[IVX]+\s+de\s+la\s+république",
                    r"\d{1,2}\s+(vendémiaire|brumaire|frimaire|nivôse|pluviôse|ventôse|germinal|floréal|prairial|messidor|thermidor|fructidor)\s+an\s+[IVX]+",
                    r"(?:le\s+)?\d{1,2}\s+\w+\s+(?:de\s+)?l'an\s+[IVX]+"
                ],
                'format_indicators': [
                    'acte de naissance', 'acte de mariage', 'acte de décès',
                    'état civil', 'officier public'
                ],
                'date_range': (1789, 1815),
                'characteristic_phrases': [
                    'registre des actes de naissance',
                    'commune de',
                    'république française'
                ]
            },
            
            HistoricalPeriod.ETAT_CIVIL_ANCIEN: {
                'vocabulary': [
                    'maire', 'adjoint', 'officier d\'état civil', 'commune',
                    'arrondissement', 'département', 'préfecture', 'sous-préfecture',
                    'légitimé', 'reconnu', 'naturel', 'adoption'
                ],
                'date_patterns': [
                    r"\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(?:18|19)\d{2}",
                    r"(?:18|19)\d{2}[-/]\d{1,2}[-/]\d{1,2}"
                ],
                'format_indicators': [
                    'extrait des registres', 'acte de naissance n°',
                    'transcription', 'mention marginale'
                ],
                'date_range': (1815, 1900),
                'characteristic_phrases': [
                    'registres de l\'état civil',
                    'mairie de',
                    'en présence des témoins'
                ]
            },
            
            HistoricalPeriod.MODERNE: {
                'vocabulary': [
                    'prénom', 'nom de famille', 'profession', 'domicile',
                    'nationalité', 'carte d\'identité', 'passeport',
                    'code civil', 'livret de famille'
                ],
                'date_patterns': [
                    r"(?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}",
                    r"\d{1,2}[-/]\d{1,2}[-/](?:19|20)\d{2}"
                ],
                'format_indicators': [
                    'code insee', 'numéro de sécurité sociale',
                    'forme dactylographiée', 'informatisé'
                ],
                'date_range': (1900, 2000),
                'characteristic_phrases': [
                    'service de l\'état civil',
                    'code de la famille',
                    'convention internationale'
                ]
            }
        }
    
    def _initialize_specialized_parsers(self) -> Dict[HistoricalPeriod, 'SpecializedPeriodParser']:
        return {
            HistoricalPeriod.ANCIEN_REGIME: AncienRegimeParser(self.config),
            HistoricalPeriod.REVOLUTION: RevolutionParser(self.config),
            HistoricalPeriod.ETAT_CIVIL_ANCIEN: EtatCivilAncienParser(self.config),
            HistoricalPeriod.MODERNE: ModerneParser(self.config)
        }
    
    @get_cache("period_parser").cached_method()
    def detect_period(self, text: str) -> PeriodDetection:
        if not text:
            return PeriodDetection(
                HistoricalPeriod.ANCIEN_REGIME, 0.0, [], (1500, 1789), {}
            )
        
        text_lower = text.lower()
        period_scores = {}
        
        for period, indicators in self.period_indicators.items():
            score = 0.0
            found_indicators = []
            vocabulary_matches = {}
            
            for vocab_word in indicators['vocabulary']:
                count = text_lower.count(vocab_word.lower())
                if count > 0:
                    vocabulary_matches[vocab_word] = count
                    score += count * 2
                    found_indicators.append(vocab_word)
            
            for pattern_str in indicators['date_patterns']:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                matches = len(pattern.findall(text))
                if matches > 0:
                    score += matches * 3
                    found_indicators.append(f"date_pattern: {matches} matches")
            
            for phrase in indicators.get('characteristic_phrases', []):
                if phrase.lower() in text_lower:
                    score += 5
                    found_indicators.append(phrase)
            
            period_scores[period] = {
                'score': score,
                'indicators': found_indicators,
                'vocabulary_matches': vocabulary_matches
            }
        
        if not any(data['score'] > 0 for data in period_scores.values()):
            return PeriodDetection(
                HistoricalPeriod.ANCIEN_REGIME, 0.3, ['default'], (1500, 1789), {}
            )
        
        best_period = max(period_scores.keys(), key=lambda p: period_scores[p]['score'])
        best_score = period_scores[best_period]['score']
        
        total_possible_score = len(self.period_indicators[best_period]['vocabulary']) * 2 + 30
        confidence = min(best_score / total_possible_score, 1.0)
        
        date_range = self.period_indicators[best_period]['date_range']
        
        return PeriodDetection(
            period=best_period,
            confidence=confidence,
            indicators=period_scores[best_period]['indicators'],
            estimated_date_range=date_range,
            vocabulary_matches=period_scores[best_period]['vocabulary_matches']
        )
    
    def parse_document(self, text: str, forced_period: Optional[HistoricalPeriod] = None) -> Dict:
        if not text:
            return {'error': 'Texte vide', 'period_info': None}
        
        self.stats['documents_processed'] += 1
        
        if forced_period:
            period = forced_period
            detection_info = {"forced": True, "period": period.value}
        else:
            detection = self.detect_period(text)
            period = detection.period
            detection_info = {
                "detected": True,
                "confidence": detection.confidence,
                "indicators": detection.indicators,
                "estimated_dates": detection.estimated_date_range,
                "vocabulary_matches": detection.vocabulary_matches
            }
            self.stats['period_detections'] += 1
        
        specialized_parser = self.period_parsers[period]
        
        try:
            result = specialized_parser.parse(text)
            
            result['period_info'] = {
                'period': period.value,
                'detection': detection_info,
                'parser_used': specialized_parser.__class__.__name__
            }
            
            self.stats['successful_parses'] += 1
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur parsing période {period.value}: {e}")
            
            if period != HistoricalPeriod.ANCIEN_REGIME:
                self.logger.info("Fallback vers parser Ancien Régime")
                self.stats['fallback_used'] += 1
                fallback_result = self.period_parsers[HistoricalPeriod.ANCIEN_REGIME].parse(text)
                fallback_result['period_info'] = {
                    'period': HistoricalPeriod.ANCIEN_REGIME.value,
                    'detection': {'fallback': True, 'original_period': period.value},
                    'parser_used': 'AncienRegimeParser (fallback)'
                }
                return fallback_result
            else:
                raise
    
    def get_stats(self) -> Dict:
        cache_stats = self.cache.get_stats()
        return {
            **self.stats,
            'cache_hit_rate': cache_stats['hit_rate_percent'],
            'cache_size': cache_stats['size']
        }

class SpecializedPeriodParser:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def parse(self, text: str) -> Dict:
        raise NotImplementedError

class AncienRegimeParser(SpecializedPeriodParser):
    def __init__(self, config):
        super().__init__(config)
        self.text_parser = TextParser(config)
        self.name_extractor = NameExtractor(config)
        self.date_parser = DateParser(config)
        self.relationship_parser = RelationshipFactory.get_optimal_parser(config)
    
    def parse(self, text: str) -> Dict:
        normalized = self.text_parser.normalize_text(text)
        names = self.name_extractor.extract_names(normalized['normalized'])
        dates = self.date_parser.extract_dates(normalized['normalized'])
        relationships = self.relationship_parser.extract_relationships(normalized['normalized'])
        
        return {
            'period': 'ancien_regime',
            'names': names,
            'dates': dates,
            'relationships': relationships,
            'text_analysis': normalized,
            'statistics': {
                'names_count': len(names),
                'dates_count': len(dates),
                'relationships_count': len(relationships)
            }
        }

class RevolutionParser(SpecializedPeriodParser):
    def __init__(self, config):
        super().__init__(config)
        self.text_parser = TextParser(config)
        self.name_extractor = NameExtractor(config)
        self.date_parser = DateParser(config)
        self.relationship_parser = RelationshipFactory.get_optimal_parser(config)
        
        self.republican_corrections = {
            'citoyen': 'citizen',
            'citoyenne': 'citizen_female',
            'commune': 'municipality'
        }
    
    def parse(self, text: str) -> Dict:
        text = self._apply_republican_preprocessing(text)
        
        normalized = self.text_parser.normalize_text(text)
        names = self.name_extractor.extract_names(normalized['normalized'])
        dates = self.date_parser.extract_dates(normalized['normalized'])
        relationships = self.relationship_parser.extract_relationships(normalized['normalized'])
        
        republican_dates = [d for d in dates if d.get('type') == 'republican']
        
        return {
            'period': 'revolution',
            'names': names,
            'dates': dates,
            'republican_dates': republican_dates,
            'relationships': relationships,
            'text_analysis': normalized,
            'statistics': {
                'names_count': len(names),
                'dates_count': len(dates),
                'republican_dates_count': len(republican_dates),
                'relationships_count': len(relationships)
            }
        }
    
    def _apply_republican_preprocessing(self, text: str) -> str:
        for old, new in self.republican_corrections.items():
            text = re.sub(rf'\b{old}\b', new, text, flags=re.IGNORECASE)
        return text

class EtatCivilAncienParser(SpecializedPeriodParser):
    def __init__(self, config):
        super().__init__(config)
        self.text_parser = TextParser(config)
        self.name_extractor = NameExtractor(config)
        self.date_parser = DateParser(config)
        self.relationship_parser = RelationshipFactory.get_optimal_parser(config)
    
    def parse(self, text: str) -> Dict:
        normalized = self.text_parser.normalize_text(text)
        names = self.name_extractor.extract_names(normalized['normalized'])
        dates = self.date_parser.extract_dates(normalized['normalized'])
        relationships = self.relationship_parser.extract_relationships(normalized['normalized'])
        
        civil_acts = self._extract_civil_acts(normalized['normalized'])
        
        return {
            'period': 'etat_civil_ancien',
            'names': names,
            'dates': dates,
            'relationships': relationships,
            'civil_acts': civil_acts,
            'text_analysis': normalized,
            'statistics': {
                'names_count': len(names),
                'dates_count': len(dates),
                'relationships_count': len(relationships),
                'civil_acts_count': len(civil_acts)
            }
        }
    
    def _extract_civil_acts(self, text: str) -> List[Dict]:
        acts = []
        act_pattern = re.compile(
            r'acte\s+de\s+(naissance|mariage|décès)\s+n°\s*(\d+)',
            re.IGNORECASE
        )
        
        for match in act_pattern.finditer(text):
            acts.append({
                'type': match.group(1),
                'number': match.group(2),
                'position': match.span(),
                'text': match.group(0)
            })
        
        return acts

class ModerneParser(SpecializedPeriodParser):
    def __init__(self, config):
        super().__init__(config)
        self.text_parser = TextParser(config)
        self.name_extractor = NameExtractor(config)
        self.date_parser = DateParser(config)
        self.relationship_parser = RelationshipFactory.get_optimal_parser(config)
    
    def parse(self, text: str) -> Dict:
        normalized = self.text_parser.normalize_text(text)
        names = self.name_extractor.extract_names(normalized['normalized'])
        dates = self.date_parser.extract_dates(normalized['normalized'])
        relationships = self.relationship_parser.extract_relationships(normalized['normalized'])
        
        modern_features = self._extract_modern_features(normalized['normalized'])
        
        return {
            'period': 'moderne',
            'names': names,
            'dates': dates,
            'relationships': relationships,
            'modern_features': modern_features,
            'text_analysis': normalized,
            'statistics': {
                'names_count': len(names),
                'dates_count': len(dates),
                'relationships_count': len(relationships),
                'modern_features_count': len(modern_features)
            }
        }
    
    def _extract_modern_features(self, text: str) -> List[Dict]:
        features = []
        
        insee_pattern = re.compile(r'\b\d{5}\b')
        for match in insee_pattern.finditer(text):
            features.append({
                'type': 'code_insee',
                'value': match.group(0),
                'position': match.span()
            })
        
        return features