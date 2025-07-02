import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from ..common import ocr_corrector, pattern_compiler, relationship_validator, get_cache

@dataclass
class RelationshipMatch:
    type: str
    entities: Dict[str, str]
    confidence: float
    source_text: str
    position: Tuple[int, int]
    ocr_corrections_applied: List[str] = None

class BasicRelationshipParser:
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.cache = get_cache("basic_relationships", max_size=1000)
        
        self.stats = {
            'total_processed': 0, 'relations_found': 0, 'ocr_corrections_applied': 0,
            'filiations': 0, 'marriages': 0, 'godparents': 0
        }
        
        self.patterns = pattern_compiler.get_all_patterns()
        self._setup_additional_patterns()
        
        self.parasitic_words = {
            'archives', 'calvados', 'registre', 'paroisse', 'page', 'folio',
            'acte', 'vue', 'document', 'témoin', 'présent'
        }
    
    def _setup_additional_patterns(self):
        self.additional_patterns = {
            'filiation_extended': re.compile(
                r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-\s]{2,40})\s*[,\.;:]?\s*'
                r'(?:fils|fille|filz)\s+de\s+'
                r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-\s,]{2,50})'
                r'(?:\s+et\s+(?:de\s+)?([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-\s]{2,40}))?',
                re.IGNORECASE
            ),
            
            'marriage_extended': re.compile(
                r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-\s]{2,40})\s*[,\.;:]?\s*'
                r'(?:épouse|femme|veuve|mariée|mari|époux)\s+(?:de\s+)?'
                r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-\s,]{2,50})',
                re.IGNORECASE
            ),
            
            'godparent_extended': re.compile(
                r'(?:parr\.|parrain)\s*:?\s*([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-\s,]{2,50})',
                re.IGNORECASE
            ),
            
            'godmother_extended': re.compile(
                r'(?:marr\.|marraine)\s*:?\s*([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-\s,]{2,50})',
                re.IGNORECASE
            )
        }
    
    @get_cache("basic_relationships").cached_method()
    def extract_relationships(self, text: str) -> List[RelationshipMatch]:
        if not text:
            return []
        
        self.stats['total_processed'] += 1
        
        cleaned_text, corrections_applied = self._clean_text_for_parsing(text)
        
        relationships = []
        used_positions = set()
        
        extraction_order = [
            ('filiation_strict', self.patterns['filiation_strict']),
            ('filiation_tolerant', self.patterns['filiation_tolerant']),
            ('filiation_extended', self.additional_patterns['filiation_extended']),
            ('marriage_basic', self.patterns['marriage_basic']),
            ('marriage_tolerant', self.patterns['marriage_tolerant']),
            ('marriage_extended', self.additional_patterns['marriage_extended']),
            ('godparent_basic', self.patterns['godparent_basic']),
            ('godparent_tolerant', self.patterns['godparent_tolerant']),
            ('godparent_extended', self.additional_patterns['godparent_extended']),
            ('godmother_extended', self.additional_patterns['godmother_extended'])
        ]
        
        for pattern_name, pattern in extraction_order:
            for match in pattern.finditer(cleaned_text):
                start, end = match.span()
                if not any(pos in used_positions for pos in range(start, end)):
                    relation = self._parse_relationship_match(match, pattern_name, corrections_applied)
                    if relation and self._validate_relationship_quality(relation):
                        relationships.append(relation)
                        used_positions.update(range(start, end))
                        self._update_stats(relation.type)
        
        return self._deduplicate_and_rank_relationships(relationships)
    
    def _clean_text_for_parsing(self, text: str) -> Tuple[str, List[str]]:
        corrected_text = ocr_corrector.correct_text(text)
        corrections_applied = []
        
        if corrected_text != text:
            corrections_applied.append("OCR corrections applied")
            self.stats['ocr_corrections_applied'] += 1
        
        words = corrected_text.split()
        filtered_words = []
        
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word).lower()
            if word_clean not in self.parasitic_words and len(word_clean) > 1:
                filtered_words.append(word)
        
        return ' '.join(filtered_words), corrections_applied
    
    def _parse_relationship_match(self, match, pattern_name: str, corrections: List[str]) -> Optional[RelationshipMatch]:
        try:
            if 'filiation' in pattern_name:
                return self._parse_filiation_match(match, pattern_name, corrections)
            elif 'marriage' in pattern_name:
                return self._parse_marriage_match(match, pattern_name, corrections)
            elif 'godparent' in pattern_name or 'godmother' in pattern_name:
                return self._parse_godparent_match(match, pattern_name, corrections)
        except Exception as e:
            self.logger.debug(f"Erreur parsing relation {pattern_name}: {e}")
        
        return None
    
    def _parse_filiation_match(self, match, pattern_name: str, corrections: List[str]) -> Optional[RelationshipMatch]:
        child = match.group(1).strip()
        father_text = match.group(2).strip()
        mother = match.group(3).strip() if len(match.groups()) > 2 and match.group(3) else None
        
        father = self._extract_father_name(father_text)
        
        entities = {'child': child, 'father': father}
        if mother:
            entities['mother'] = mother
        
        confidence = self._calculate_filiation_confidence(child, father, mother, pattern_name)
        
        return RelationshipMatch(
            type='filiation',
            entities=entities,
            confidence=confidence,
            source_text=match.group(0),
            position=match.span(),
            ocr_corrections_applied=corrections
        )
    
    def _parse_marriage_match(self, match, pattern_name: str, corrections: List[str]) -> Optional[RelationshipMatch]:
        spouse1 = match.group(1).strip()
        spouse2 = match.group(2).strip()
        
        if 'épouse' in match.group(0).lower() or 'femme' in match.group(0).lower():
            entities = {'wife': spouse1, 'husband': spouse2}
        else:
            entities = {'spouse1': spouse1, 'spouse2': spouse2}
        
        confidence = self._calculate_marriage_confidence(spouse1, spouse2, pattern_name)
        
        return RelationshipMatch(
            type='marriage',
            entities=entities,
            confidence=confidence,
            source_text=match.group(0),
            position=match.span(),
            ocr_corrections_applied=corrections
        )
    
    def _parse_godparent_match(self, match, pattern_name: str, corrections: List[str]) -> Optional[RelationshipMatch]:
        godparent = match.group(1).strip()
        
        if 'godmother' in pattern_name or 'marr' in pattern_name.lower():
            role = 'godmother'
        else:
            role = 'godfather'
        
        entities = {role: godparent}
        confidence = self._calculate_godparent_confidence(godparent, role, pattern_name)
        
        return RelationshipMatch(
            type='godparent',
            entities=entities,
            confidence=confidence,
            source_text=match.group(0),
            position=match.span(),
            ocr_corrections_applied=corrections
        )
    
    def _extract_father_name(self, father_text: str) -> str:
        father_text = re.sub(r'^(feu\s+|défunt\s+)', '', father_text, flags=re.IGNORECASE)
        
        if ' et ' in father_text.lower():
            parts = re.split(r'\s+et\s+', father_text, flags=re.IGNORECASE)
            return parts[0].strip()
        
        return father_text.strip()
    
    def _calculate_filiation_confidence(self, child: str, father: str, mother: Optional[str], pattern_name: str) -> float:
        base_confidence = 0.6
        
        pattern_bonuses = {
            'filiation_strict': 0.2,
            'filiation_tolerant': 0.1,
            'filiation_extended': 0.05
        }
        base_confidence += pattern_bonuses.get(pattern_name, 0.0)
        
        if len(child.split()) >= 2:
            base_confidence += 0.1
        if len(father.split()) >= 2:
            base_confidence += 0.1
        if mother and len(mother.split()) >= 2:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _calculate_marriage_confidence(self, spouse1: str, spouse2: str, pattern_name: str) -> float:
        base_confidence = 0.7
        
        pattern_bonuses = {
            'marriage_basic': 0.15,
            'marriage_tolerant': 0.1,
            'marriage_extended': 0.05
        }
        base_confidence += pattern_bonuses.get(pattern_name, 0.0)
        
        if len(spouse1.split()) >= 2 and len(spouse2.split()) >= 2:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _calculate_godparent_confidence(self, godparent: str, role: str, pattern_name: str) -> float:
        base_confidence = 0.5
        
        if len(godparent.split()) >= 2:
            base_confidence += 0.2
        
        if 'extended' in pattern_name:
            base_confidence += 0.1
        else:
            base_confidence += 0.15
        
        return min(base_confidence, 1.0)
    
    def _validate_relationship_quality(self, relation: RelationshipMatch) -> bool:
        validation = relationship_validator.validate_relationship(relation.type, relation.entities)
        return validation.is_valid and validation.confidence > 0.4
    
    def _update_stats(self, relation_type: str):
        self.stats['relations_found'] += 1
        if relation_type == 'filiation':
            self.stats['filiations'] += 1
        elif relation_type == 'marriage':
            self.stats['marriages'] += 1
        elif relation_type == 'godparent':
            self.stats['godparents'] += 1
    
    def _deduplicate_and_rank_relationships(self, relationships: List[RelationshipMatch]) -> List[RelationshipMatch]:
        if not relationships:
            return []
        
        unique_relations = {}
        for relation in relationships:
            key = self._generate_relation_key(relation)
            
            if key not in unique_relations or relation.confidence > unique_relations[key].confidence:
                unique_relations[key] = relation
        
        return sorted(unique_relations.values(), key=lambda x: x.confidence, reverse=True)
    
    def _generate_relation_key(self, relation: RelationshipMatch) -> str:
        entity_values = list(relation.entities.values())
        entity_key = '_'.join(name.lower().strip() for name in entity_values if name)
        return f"{relation.type}_{entity_key}"
    
    def get_relationship_statistics(self, relationships: List[RelationshipMatch]) -> Dict:
        if not relationships:
            return {'total': 0, 'by_type': {}, 'confidence_distribution': {}}
        
        by_type = {}
        confidence_ranges = {'high': 0, 'medium': 0, 'low': 0}
        
        for relation in relationships:
            by_type[relation.type] = by_type.get(relation.type, 0) + 1
            
            if relation.confidence >= 0.8:
                confidence_ranges['high'] += 1
            elif relation.confidence >= 0.6:
                confidence_ranges['medium'] += 1
            else:
                confidence_ranges['low'] += 1
        
        return {
            'total': len(relationships),
            'by_type': by_type,
            'confidence_distribution': confidence_ranges,
            'average_confidence': sum(r.confidence for r in relationships) / len(relationships),
            'ocr_correction_rate': sum(1 for r in relationships if r.ocr_corrections_applied) / len(relationships)
        }
    
    def get_stats(self) -> Dict:
        cache_stats = self.cache.get_stats()
        return {
            **self.stats,
            'cache_hit_rate': cache_stats['hit_rate_percent'],
            'cache_size': cache_stats['size']
        }