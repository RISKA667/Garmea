import re
import logging
from typing import Dict, List, Tuple, Set, Optional, Any
from dataclasses import dataclass, field
from collections import Counter
from ..common import ocr_corrector, name_validator, get_cache

@dataclass
class ValidatedRelation:
    type: str
    entities: Dict[str, str]
    source_text: str
    position: Tuple[int, int]
    confidence: float
    validation_score: float
    rejection_reason: Optional[str] = None

class StrictParser:
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.cache = get_cache("strict_parser", max_size=800)
        
        self.stats = {
            'candidates_examined': 0, 'relations_validated': 0,
            'rejections_absolute_pattern': 0, 'rejections_forbidden_word': 0,
            'rejections_invalid_name': 0, 'rejections_length': 0,
            'rejections_validation': 0, 'ocr_corrections_applied': 0
        }
        
        self.valid_first_names_male = {
            'Jean', 'Pierre', 'Jacques', 'Nicolas', 'François', 'Louis', 'Antoine',
            'Michel', 'Guillaume', 'Charles', 'Philippe', 'Gabriel', 'Thomas',
            'André', 'Claude', 'Henri', 'Paul', 'Denis', 'Étienne', 'Martin',
            'Barthélemy', 'Laurent', 'Julien', 'Gilles', 'Robert', 'Christophe',
            'Mathieu', 'Simon', 'Alexis', 'Blaise', 'Sébastien', 'Vincent'
        }
        
        self.valid_first_names_female = {
            'Marie', 'Jeanne', 'Catherine', 'Marguerite', 'Anne', 'Françoise',
            'Madeleine', 'Louise', 'Élisabeth', 'Marthe', 'Agnès', 'Nicole',
            'Barbe', 'Suzanne', 'Michelle', 'Jacqueline', 'Antoinette',
            'Geneviève', 'Hélène', 'Isabelle', 'Claudine', 'Renée'
        }
        
        self.valid_family_names = {
            'Boucher', 'Dupré', 'Martin', 'Bernard', 'Thomas', 'Petit',
            'Robert', 'Richard', 'Durand', 'Dubois', 'Moreau', 'Laurent',
            'Simon', 'Michel', 'Lefebvre', 'Leroy', 'Roux', 'David',
            'Bertrand', 'Morel', 'Fournier', 'Girard', 'Bonnet', 'Dupont'
        }
        
        self.strict_ocr_corrections = {
            'Aiicelle': 'Ancelle', 'Aiigotin': 'Antigotin', 'Aiimont': 'Aumont',
            'Aiiber': 'Auber', 'Aiivray': 'Auvray', 'Aii-': 'Anne',
            'Jaeques': 'Jacques', 'Franteois': 'François', 'Catlierhie': 'Catherine',
            'Guillaïune': 'Guillaume', 'Nicollas': 'Nicolas', 'Muiiie': 'Marie',
            'Cliarles': 'Charles', 'Jeau': 'Jean', 'Vietoire': 'Victoire',
            'Iagdeleine': 'Madeleine', 'Pi-ançois': 'François', 'Toussaiut': 'Toussaint'
        }
        
        self.absolute_rejection_patterns = [
            re.compile(r'archives\s+du\s+calvados', re.IGNORECASE),
            re.compile(r'registre\s+paroissial', re.IGNORECASE),
            re.compile(r'page\s+\d+', re.IGNORECASE),
            re.compile(r'folio\s+\d+', re.IGNORECASE),
            re.compile(r'\d{3,}'),
            re.compile(r'[<>@#$%^&*()]'),
            re.compile(r'^[^A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ]')
        ]
        
        self.forbidden_words = {
            'archives', 'calvados', 'registre', 'paroisse', 'page', 'folio',
            'acte', 'baptême', 'mariage', 'décès', 'vue', 'document'
        }
        
        self.forbidden_prefixes = {
            'arch', 'reg', 'par', 'doc', 'img', 'scan', 'pdf'
        }
        
        self._compile_strict_patterns()
    
    def _compile_strict_patterns(self):
        strict_name = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]{2,}'
        strict_person = rf'{strict_name}(?:\s+{strict_name})*'
        
        self.compiled_patterns = {
            'ultra_strict_filiation': re.compile(
                rf'({strict_person}),?\s+(?:fils|fille)\s+de\s+({strict_name}(?:\s+et\s+(?:de\s+)?{strict_name})?)',
                re.IGNORECASE | re.MULTILINE
            ),
            'valid_first_name': re.compile(rf'^{strict_name}$'),
            'valid_family_name': re.compile(rf'^{strict_name}$')
        }
    
    @get_cache("strict_parser").cached_method()
    def extract_ultra_strict_filiations(self, text: str) -> List[ValidatedRelation]:
        if not text:
            return []
        
        cleaned_text = self._pre_clean_text(text)
        filiations = []
        
        pattern = self.compiled_patterns['ultra_strict_filiation']
        
        for match in pattern.finditer(cleaned_text):
            self.stats['candidates_examined'] += 1
            
            child_raw = match.group(1).strip()
            parents_raw = match.group(2).strip()
            
            child_validation = self._validate_child_ultra_strict(child_raw)
            
            if not child_validation['valid']:
                self._categorize_rejection(child_validation['reason'])
                continue
            
            child_clean = self._apply_strict_ocr_corrections(child_raw)
            parents = self._parse_parents_ultra_strict(parents_raw)
            
            if not self._final_validation(child_clean, parents):
                self.stats['rejections_validation'] += 1
                continue
            
            confidence = self._calculate_strict_confidence(child_clean, parents)
            
            relation = ValidatedRelation(
                type='filiation',
                entities={
                    'child': child_clean,
                    'father': parents.get('father', ''),
                    'mother': parents.get('mother', '')
                },
                source_text=match.group(0),
                position=match.span(),
                confidence=confidence,
                validation_score=child_validation['score']
            )
            
            filiations.append(relation)
            self.stats['relations_validated'] += 1
        
        return filiations
    
    def _pre_clean_text(self, text: str) -> str:
        text = re.sub(r'ARCHIVES\s+DU\s+CALVADOS[^,]*,\s*', '', text, flags=re.IGNORECASE)
        
        for error, correction in self.strict_ocr_corrections.items():
            if error in text:
                text = text.replace(error, correction)
                self.stats['ocr_corrections_applied'] += 1
        
        return text
    
    def _validate_child_ultra_strict(self, child: str) -> Dict[str, Any]:
        cache_key = child.lower().strip()
        
        result = {'valid': False, 'reason': '', 'score': 0.0}
        
        if len(child.strip()) < 4:
            result['reason'] = 'Trop court (< 4 caractères)'
            return result
        
        for pattern in self.absolute_rejection_patterns:
            if pattern.search(child):
                result['reason'] = f'Pattern rejeté: {pattern.pattern[:30]}...'
                return result
        
        words = child.split()
        if not words:
            result['reason'] = 'Aucun mot valide'
            return result
        
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word).lower()
            if word_clean in self.forbidden_words:
                result['reason'] = f'Mot interdit: {word}'
                return result
            
            if any(word_clean.startswith(prefix) for prefix in self.forbidden_prefixes):
                result['reason'] = f'Préfixe interdit: {word}'
                return result
        
        first_word = words[0]
        corrected_first = self.strict_ocr_corrections.get(first_word, first_word)
        
        if not self._is_valid_first_name(corrected_first):
            result['reason'] = f'Premier mot invalide comme prénom: {first_word}'
            return result
        
        if not self._validate_name_structure(child):
            result['reason'] = 'Structure de nom invalide'
            return result
        
        score = self._calculate_name_quality_score(child, words)
        
        if score < 0.5:
            result['reason'] = f'Score qualité insuffisant: {score:.2f}'
            return result
        
        result['valid'] = True
        result['score'] = score
        return result
    
    def _is_valid_first_name(self, name: str) -> bool:
        return (name in self.valid_first_names_male or 
                name in self.valid_first_names_female)
    
    def _validate_name_structure(self, name: str) -> bool:
        corrected = self._apply_strict_ocr_corrections(name)
        
        if not re.match(r'^[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]{2,}', corrected):
            return False
        
        return True
    
    def _calculate_name_quality_score(self, child: str, words: List[str]) -> float:
        score = 0.2
        
        if 2 <= len(words) <= 4:
            score += 0.2
        
        first_word = words[0] if words else ''
        corrected_first = self.strict_ocr_corrections.get(first_word, first_word)
        
        if corrected_first in self.valid_first_names_male or corrected_first in self.valid_first_names_female:
            score += 0.4
        
        if len(words) >= 2:
            last_word = words[-1]
            if last_word in self.valid_family_names:
                score += 0.2
        
        if re.search(r'[0-9]', child):
            score -= 0.3
        
        if re.search(r'[^a-zA-ZÀ-ÿ\s\-\']', child):
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _apply_strict_ocr_corrections(self, name: str) -> str:
        corrected = name
        for error, correction in self.strict_ocr_corrections.items():
            if error in corrected:
                corrected = corrected.replace(error, correction)
        
        corrected = ' '.join(corrected.split())
        return corrected
    
    def _parse_parents_ultra_strict(self, parents_str: str) -> Dict[str, str]:
        parents = {'father': '', 'mother': ''}
        
        cleaned = re.sub(r'^(feu\s+|défunt\s+|défunte\s+)', '', parents_str, flags=re.IGNORECASE)
        cleaned = self._apply_strict_ocr_corrections(cleaned)
        
        if ' et ' in cleaned.lower():
            parts = re.split(r'\s+et\s+(?:de\s+)?', cleaned, flags=re.IGNORECASE)
            if len(parts) >= 2:
                parents['father'] = parts[0].strip()
                parents['mother'] = parts[1].strip()
        else:
            parents['father'] = cleaned.strip()
        
        return parents
    
    def _final_validation(self, child: str, parents: Dict[str, str]) -> bool:
        if not child or len(child.strip()) < 4:
            return False
        
        if not parents.get('father') and not parents.get('mother'):
            return False
        
        if child.lower() == parents.get('father', '').lower():
            return False
        
        if child.lower() == parents.get('mother', '').lower():
            return False
        
        return True
    
    def _calculate_strict_confidence(self, child: str, parents: Dict[str, str]) -> float:
        confidence = 0.4
        
        words_child = child.split()
        if len(words_child) >= 2:
            confidence += 0.2
        
        first_word = words_child[0] if words_child else ''
        if first_word in self.valid_first_names_male or first_word in self.valid_first_names_female:
            confidence += 0.2
        
        father = parents.get('father', '')
        mother = parents.get('mother', '')
        
        if father and len(father.split()) >= 2:
            confidence += 0.1
        
        if mother and len(mother.split()) >= 2:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _categorize_rejection(self, reason: str):
        reason_lower = reason.lower()
        if 'pattern rejeté' in reason_lower:
            self.stats['rejections_absolute_pattern'] += 1
        elif 'mot interdit' in reason_lower:
            self.stats['rejections_forbidden_word'] += 1
        elif 'premier mot invalide' in reason_lower:
            self.stats['rejections_invalid_name'] += 1
        elif 'trop court' in reason_lower:
            self.stats['rejections_length'] += 1
        else:
            self.stats['rejections_validation'] += 1
    
    def export_to_legacy_format(self, relations: List[ValidatedRelation]) -> List[Dict[str, Any]]:
        filiations_csv = []
        
        for i, relation in enumerate(relations, 1):
            filiations_csv.append({
                'ID': i,
                'Child': relation.entities.get('child', ''),
                'Father': relation.entities.get('father', ''),
                'Mother': relation.entities.get('mother', ''),
                'Source_Text': relation.source_text,
                'Position_Start': relation.position[0],
                'Position_End': relation.position[1],
                'Confidence': round(relation.confidence, 2),
                'Validation_Score': round(relation.validation_score, 2)
            })
        
        return filiations_csv
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        total_examined = self.stats['candidates_examined']
        
        return {
            'candidates_examined': total_examined,
            'relations_validated': self.stats['relations_validated'],
            'validation_rate': (self.stats['relations_validated'] / max(total_examined, 1)) * 100,
            'rejection_details': {
                'absolute_pattern': self.stats['rejections_absolute_pattern'],
                'forbidden_word': self.stats['rejections_forbidden_word'],
                'invalid_name': self.stats['rejections_invalid_name'],
                'length': self.stats['rejections_length'],
                'final_validation': self.stats['rejections_validation']
            },
            'ocr_corrections': self.stats['ocr_corrections_applied'],
            'quality_assessment': self._assess_quality()
        }
    
    def _assess_quality(self) -> str:
        if self.stats['candidates_examined'] == 0:
            return 'No data'
        
        validation_rate = (self.stats['relations_validated'] / self.stats['candidates_examined']) * 100
        
        if validation_rate > 80:
            return 'Excellent'
        elif validation_rate > 60:
            return 'Good'
        elif validation_rate > 40:
            return 'Average'
        else:
            return 'Poor'
    
    def process_text_ultra_strict(self, text: str) -> Dict[str, Any]:
        relations = self.extract_ultra_strict_filiations(text)
        filiations_csv = self.export_to_legacy_format(relations)
        stats = self.get_processing_statistics()
        
        return {
            'filiations': filiations_csv,
            'statistics': stats,
            'quality_estimate': stats['quality_assessment']
        }
    
    def get_stats(self) -> Dict:
        cache_stats = self.cache.get_stats()
        return {
            **self.stats,
            'cache_hit_rate': cache_stats['hit_rate_percent'],
            'cache_size': cache_stats['size']
        }