import re
import logging
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from functools import lru_cache

try:
    import spacy
    nlp = spacy.load("fr_core_news_sm")
    HAS_SPACY = True
except (ImportError, OSError):
    HAS_SPACY = False
    nlp = None

@dataclass
class EnhancedRelationshipMatch:
    type: str
    persons: Dict[str, str]
    confidence: float
    source_span: Tuple[int, int]
    context: str
    extraction_method: str = "basic"
    validation_score: float = 0.0
    contextual_indicators: List[str] = None

class AdvancedRelationshipParser:
    def __init__(self, config=None, fallback_to_basic: bool = True):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.fallback_to_basic = fallback_to_basic
        self.use_spacy = HAS_SPACY
        
        self.stats = {
            'total_processed': 0, 'spacy_extractions': 0, 'regex_extractions': 0,
            'fallback_used': 0, 'validation_passed': 0
        }
        
        if self.use_spacy:
            self.logger.info("Initialisation parser NLP avancé avec spaCy")
            self._setup_spacy_patterns()
        else:
            self.logger.warning("spaCy non disponible, mode regex uniquement")
        
        self._setup_regex_patterns()
        self._entity_cache = {}
    
    def _setup_spacy_patterns(self):
        if not self.use_spacy:
            return
        
        from spacy.matcher import Matcher
        self.matcher = Matcher(nlp.vocab)
        
        filiation_pattern = [
            {"LOWER": {"IN": ["fils", "fille", "filz"]}},
            {"LOWER": "de"},
            {"POS": "PROPN", "OP": "+"},
            {"LOWER": {"IN": ["et", "de"]}, "OP": "?"},
            {"LOWER": "de", "OP": "?"},
            {"POS": "PROPN", "OP": "*"}
        ]
        self.matcher.add("FILIATION", [filiation_pattern])
        
        mariage_pattern = [
            {"POS": "PROPN", "OP": "+"},
            {"LOWER": {"IN": ["épouse", "femme", "veuve"]}},
            {"LOWER": "de"},
            {"POS": "PROPN", "OP": "+"}
        ]
        self.matcher.add("MARIAGE", [mariage_pattern])
        
        parrain_pattern = [
            {"LOWER": {"IN": ["parr", "parrain", "marr", "marraine"]}},
            {"IS_PUNCT": True, "OP": "?"},
            {"POS": "PROPN", "OP": "+"}
        ]
        self.matcher.add("PARRAIN", [parrain_pattern])
    
    def _setup_regex_patterns(self):
        name_pattern = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+'
        
        self.regex_patterns = {
            'filiation': re.compile(
                rf'({name_pattern}),?\s*(?:fils|fille|filz)\s+de\s+({name_pattern})(?:\s+et\s+(?:de\s+)?({name_pattern}))?',
                re.IGNORECASE
            ),
            'marriage': re.compile(
                rf'({name_pattern}),?\s*(?:épouse|femme|veuve)\s+de\s+({name_pattern})',
                re.IGNORECASE
            ),
            'godparent': re.compile(
                rf'(?:parrain|marraine|parr|marr)\s*:?\s*({name_pattern})',
                re.IGNORECASE
            )
        }
    
    def extract_relationships(self, text: str) -> List[EnhancedRelationshipMatch]:
        if not text:
            return []
        
        self.stats['total_processed'] += 1
        
        relationships = []
        
        if self.use_spacy:
            spacy_results = self._extract_with_spacy(text)
            relationships.extend(spacy_results)
            self.stats['spacy_extractions'] += len(spacy_results)
        
        regex_results = self._extract_with_regex(text)
        relationships.extend(regex_results)
        self.stats['regex_extractions'] += len(regex_results)
        
        if self.fallback_to_basic and not relationships:
            try:
                from .basic_relationship_parser import BasicRelationshipParser
                basic_parser = BasicRelationshipParser(self.config)
                basic_results = basic_parser.extract_relationships(text)
                
                relationships = [
                    EnhancedRelationshipMatch(
                        type=r.type,
                        persons=r.entities,
                        confidence=r.confidence * 0.8,
                        source_span=r.position,
                        context=r.source_text,
                        extraction_method="fallback_basic"
                    )
                    for r in basic_results
                ]
                self.stats['fallback_used'] += 1
            except ImportError:
                self.logger.warning("Fallback parser non disponible")
        
        return self._deduplicate_and_enhance(relationships)
    
    def _extract_with_spacy(self, text: str) -> List[EnhancedRelationshipMatch]:
        if not self.use_spacy:
            return []
        
        try:
            doc = nlp(text)
            matches = self.matcher(doc)
            relationships = []
            
            for match_id, start, end in matches:
                span = doc[start:end]
                match_label = nlp.vocab.strings[match_id]
                
                if match_label == "FILIATION":
                    rel = self._parse_filiation_spacy(span, text)
                elif match_label == "MARIAGE":
                    rel = self._parse_marriage_spacy(span, text)
                elif match_label == "PARRAIN":
                    rel = self._parse_godparent_spacy(span, text)
                else:
                    continue
                
                if rel:
                    relationships.append(rel)
            
            return relationships
            
        except Exception as e:
            self.logger.error(f"Erreur extraction spaCy: {e}")
            return []
    
    def _extract_with_regex(self, text: str) -> List[EnhancedRelationshipMatch]:
        relationships = []
        
        for rel_type, pattern in self.regex_patterns.items():
            for match in pattern.finditer(text):
                if rel_type == "filiation":
                    rel = EnhancedRelationshipMatch(
                        type="filiation",
                        persons={
                            "child": match.group(1).strip(),
                            "father": match.group(2).strip(),
                            "mother": match.group(3).strip() if match.group(3) else None
                        },
                        confidence=0.75,
                        source_span=match.span(),
                        context=match.group(0),
                        extraction_method="regex"
                    )
                elif rel_type == "marriage":
                    rel = EnhancedRelationshipMatch(
                        type="marriage",
                        persons={
                            "wife": match.group(1).strip(),
                            "husband": match.group(2).strip()
                        },
                        confidence=0.80,
                        source_span=match.span(),
                        context=match.group(0),
                        extraction_method="regex"
                    )
                elif rel_type == "godparent":
                    rel = EnhancedRelationshipMatch(
                        type="godparent",
                        persons={
                            "godparent": match.group(1).strip()
                        },
                        confidence=0.70,
                        source_span=match.span(),
                        context=match.group(0),
                        extraction_method="regex"
                    )
                else:
                    continue
                
                if rel:
                    relationships.append(rel)
        
        return relationships
    
    def _parse_filiation_spacy(self, span, full_text: str) -> Optional[EnhancedRelationshipMatch]:
        try:
            entities = [ent for ent in span.ents if ent.label_ == "PER"]
            
            if len(entities) >= 2:
                father = entities[0].text
                mother = entities[1].text if len(entities) > 1 else None
                child = self._find_child_in_context(span.start_char, full_text)
                
                if child:
                    return EnhancedRelationshipMatch(
                        type="filiation",
                        persons={
                            "child": child,
                            "father": father,
                            "mother": mother
                        },
                        confidence=0.85,
                        source_span=(span.start_char, span.end_char),
                        context=span.text,
                        extraction_method="spacy"
                    )
            
        except Exception as e:
            self.logger.debug(f"Erreur parse filiation spaCy: {e}")
        
        return None
    
    def _parse_marriage_spacy(self, span, full_text: str) -> Optional[EnhancedRelationshipMatch]:
        try:
            entities = [ent for ent in span.ents if ent.label_ == "PER"]
            
            if len(entities) >= 2:
                return EnhancedRelationshipMatch(
                    type="marriage",
                    persons={
                        "wife": entities[0].text,
                        "husband": entities[1].text
                    },
                    confidence=0.82,
                    source_span=(span.start_char, span.end_char),
                    context=span.text,
                    extraction_method="spacy"
                )
        except Exception as e:
            self.logger.debug(f"Erreur parse mariage spaCy: {e}")
        
        return None
    
    def _parse_godparent_spacy(self, span, full_text: str) -> Optional[EnhancedRelationshipMatch]:
        try:
            entities = [ent for ent in span.ents if ent.label_ == "PER"]
            
            if entities:
                return EnhancedRelationshipMatch(
                    type="godparent",
                    persons={
                        "godparent": entities[0].text,
                        "godchild": self._find_child_in_context(span.start_char, full_text)
                    },
                    confidence=0.80,
                    source_span=(span.start_char, span.end_char),
                    context=span.text,
                    extraction_method="spacy"
                )
        except Exception as e:
            self.logger.debug(f"Erreur parse parrain spaCy: {e}")
        
        return None
    
    def _find_child_in_context(self, span_start: int, text: str, window: int = 100) -> Optional[str]:
        context_start = max(0, span_start - window)
        context = text[context_start:span_start]
        
        child_pattern = re.compile(r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)(?:,|\s)', re.IGNORECASE)
        matches = child_pattern.findall(context)
        
        return matches[-1] if matches else None
    
    def _deduplicate_and_enhance(self, relationships: List[EnhancedRelationshipMatch]) -> List[EnhancedRelationshipMatch]:
        if not relationships:
            return []
        
        unique_relations = {}
        
        for rel in relationships:
            key = f"{rel.type}_{rel.persons.get('child', '')}_{rel.persons.get('wife', '')}"
            
            if key not in unique_relations or rel.confidence > unique_relations[key].confidence:
                enhanced_rel = self._enhance_relationship(rel)
                unique_relations[key] = enhanced_rel
        
        return sorted(unique_relations.values(), key=lambda x: x.confidence, reverse=True)
    
    def _enhance_relationship(self, rel: EnhancedRelationshipMatch) -> EnhancedRelationshipMatch:
        validation_score = self._validate_relationship_context(rel)
        rel.validation_score = validation_score
        
        if validation_score > 0.8:
            rel.confidence = min(rel.confidence + 0.1, 1.0)
        
        rel.contextual_indicators = self._extract_contextual_indicators(rel.context)
        
        if rel.validation_score > 0.5:
            self.stats['validation_passed'] += 1
        
        return rel
    
    def _validate_relationship_context(self, rel: EnhancedRelationshipMatch) -> float:
        context_lower = rel.context.lower()
        score = 0.5
        
        genealogical_terms = ['baptême', 'église', 'curé', 'paroisse', 'mariage', 'inhumation']
        for term in genealogical_terms:
            if term in context_lower:
                score += 0.1
        
        if re.search(r'\d{4}', rel.context):
            score += 0.2
        
        noble_titles = ['sieur', 'écuyer', 'seigneur', 'comte', 'baron', 'dame']
        for title in noble_titles:
            if title in context_lower:
                score += 0.1
        
        return min(score, 1.0)
    
    def _extract_contextual_indicators(self, context: str) -> List[str]:
        indicators = []
        context_lower = context.lower()
        
        if 'baptême' in context_lower or 'bapt' in context_lower:
            indicators.append('baptism_context')
        if 'mariage' in context_lower:
            indicators.append('marriage_context')
        if 'curé' in context_lower or 'prêtre' in context_lower:
            indicators.append('clerical_context')
        if re.search(r'\d{4}', context):
            indicators.append('dated_context')
        
        return indicators
    
    @lru_cache(maxsize=1000)
    def get_person_entities(self, text: str) -> List[str]:
        if not self.use_spacy:
            names = re.findall(r'\b[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)+', text)
            return list(set(names))
        
        try:
            doc = nlp(text)
            persons = [ent.text for ent in doc.ents if ent.label_ == "PER"]
            return list(set(persons))
        except Exception:
            return []
    
    def get_stats(self) -> Dict:
        return {
            **self.stats,
            'spacy_available': HAS_SPACY,
            'extraction_methods': {
                'spacy': self.stats['spacy_extractions'],
                'regex': self.stats['regex_extractions'],
                'fallback': self.stats['fallback_used']
            }
        }