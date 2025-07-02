# parsers/modern_nlp_parser.py
import spacy
import re
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from functools import lru_cache
import logging

try:
    # Essayer d'importer spaCy
    nlp = spacy.load("fr_core_news_sm")
    HAS_SPACY = True
except (ImportError, OSError):
    HAS_SPACY = False
    nlp = None

@dataclass
class RelationshipMatch:
    """Résultat d'extraction de relation avec confiance"""
    type: str
    persons: Dict[str, str]
    confidence: float
    source_span: Tuple[int, int]
    context: str

class ModernNLPParser:
    """Parser NLP moderne pour remplacer les regex fragiles"""
    
    def __init__(self, fallback_to_regex: bool = True):
        self.logger = logging.getLogger(__name__)
        self.use_spacy = HAS_SPACY
        self.fallback_to_regex = fallback_to_regex
        
        if self.use_spacy:
            self.logger.info("Utilisation de spaCy pour NLP avancé")
            self._setup_spacy_patterns()
        else:
            self.logger.warning("spaCy non disponible, utilisation regex de fallback")
        
        # Patterns de fallback (vos regex existants optimisés)
        self._setup_fallback_patterns()
        
        # Cache pour les entités nommées
        self._entity_cache = {}
    
    def _setup_spacy_patterns(self):
        """Configure les patterns spaCy personnalisés"""
        if not self.use_spacy:
            return
            
        from spacy.matcher import Matcher
        self.matcher = Matcher(nlp.vocab)
        
        # Pattern pour filiation
        filiation_pattern = [
            {"LOWER": {"IN": ["fils", "fille", "filz"]}},
            {"LOWER": "de"},
            {"POS": "PROPN", "OP": "+"},  # Nom du père
            {"LOWER": {"IN": ["et", "de"]}, "OP": "?"},
            {"LOWER": "de", "OP": "?"},
            {"POS": "PROPN", "OP": "*"}   # Nom de la mère
        ]
        self.matcher.add("FILIATION", [filiation_pattern])
        
        # Pattern pour mariage
        mariage_pattern = [
            {"POS": "PROPN", "OP": "+"},  # Nom épouse
            {"LOWER": {"IN": ["épouse", "femme", "veuve"]}},
            {"LOWER": "de"},
            {"POS": "PROPN", "OP": "+"}   # Nom époux
        ]
        self.matcher.add("MARIAGE", [mariage_pattern])
        
        # Pattern pour parrainage
        parrain_pattern = [
            {"LOWER": {"IN": ["parr", "parrain"]}},
            {"IS_PUNCT": True, "OP": "?"},
            {"POS": "PROPN", "OP": "+"}
        ]
        self.matcher.add("PARRAIN", [parrain_pattern])
    
    def _setup_fallback_patterns(self):
        """Patterns regex optimisés pour fallback"""
        self.fallback_patterns = {
            'filiation': re.compile(
                r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+),?\s+'
                r'(?:fils|fille|filz)\s+de\s+'
                r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s,]+?)'
                r'(?:\s+et\s+(?:de\s+)?([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+))?',
                re.IGNORECASE
            ),
            'mariage': re.compile(
                r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+),?\s+'
                r'(?:épouse|femme|veuve)\s+de\s+'
                r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s,]+)',
                re.IGNORECASE
            )
        }
    
    def extract_relationships(self, text: str) -> List[RelationshipMatch]:
        """Extraction intelligente des relations avec NLP + fallback"""
        relationships = []
        
        if self.use_spacy:
            relationships.extend(self._extract_with_spacy(text))
        
        if self.fallback_to_regex:
            relationships.extend(self._extract_with_regex(text))
        
        # Déduplication et scoring
        return self._deduplicate_and_score(relationships)
    
    def _extract_with_spacy(self, text: str) -> List[RelationshipMatch]:
        """Extraction avec spaCy NLP"""
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
                    if rel:
                        relationships.append(rel)
                
                elif match_label == "MARIAGE":
                    rel = self._parse_mariage_spacy(span, text)
                    if rel:
                        relationships.append(rel)
                
                elif match_label == "PARRAIN":
                    rel = self._parse_parrain_spacy(span, text)
                    if rel:
                        relationships.append(rel)
            
            return relationships
            
        except Exception as e:
            self.logger.error(f"Erreur spaCy: {e}")
            return []
    
    def _parse_filiation_spacy(self, span, full_text: str) -> Optional[RelationshipMatch]:
        """Parse une filiation détectée par spaCy"""
        try:
            # Analyser les entités nommées dans le span
            entities = [ent for ent in span.ents if ent.label_ == "PER"]
            
            if len(entities) >= 2:
                # Premier = père, deuxième = mère (si présente)
                pere = entities[0].text
                mere = entities[1].text if len(entities) > 1 else None
                
                # Chercher l'enfant dans le contexte précédent
                enfant = self._find_child_in_context(span.start_char, full_text)
                
                if enfant:
                    return RelationshipMatch(
                        type="filiation",
                        persons={
                            "enfant": enfant,
                            "pere": pere,
                            "mere": mere
                        },
                        confidence=0.85,  # Confiance spaCy
                        source_span=(span.start_char, span.end_char),
                        context=span.text
                    )
            
        except Exception as e:
            self.logger.debug(f"Erreur parse filiation spaCy: {e}")
        
        return None
    
    def _parse_mariage_spacy(self, span, full_text: str) -> Optional[RelationshipMatch]:
        """Parse un mariage détecté par spaCy"""
        try:
            entities = [ent for ent in span.ents if ent.label_ == "PER"]
            
            if len(entities) >= 2:
                return RelationshipMatch(
                    type="mariage",
                    persons={
                        "epouse": entities[0].text,
                        "epoux": entities[1].text
                    },
                    confidence=0.82,
                    source_span=(span.start_char, span.end_char),
                    context=span.text
                )
        except Exception as e:
            self.logger.debug(f"Erreur parse mariage spaCy: {e}")
        
        return None
    
    def _parse_parrain_spacy(self, span, full_text: str) -> Optional[RelationshipMatch]:
        """Parse un parrainage détecté par spaCy"""
        try:
            entities = [ent for ent in span.ents if ent.label_ == "PER"]
            
            if entities:
                return RelationshipMatch(
                    type="parrainage",
                    persons={
                        "parrain": entities[0].text,
                        "filleul": self._find_child_in_context(span.start_char, full_text)
                    },
                    confidence=0.80,
                    source_span=(span.start_char, span.end_char),
                    context=span.text
                )
        except Exception as e:
            self.logger.debug(f"Erreur parse parrain spaCy: {e}")
        
        return None
    
    def _find_child_in_context(self, span_start: int, text: str, window: int = 100) -> Optional[str]:
        """Trouve l'enfant dans le contexte précédant la filiation"""
        # Chercher dans les 100 caractères précédents
        context_start = max(0, span_start - window)
        context = text[context_start:span_start]
        
        # Pattern simple pour nom d'enfant
        child_pattern = re.compile(r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)(?:,|\s)', re.IGNORECASE)
        matches = child_pattern.findall(context)
        
        return matches[-1] if matches else None
    
    def _extract_with_regex(self, text: str) -> List[RelationshipMatch]:
        """Extraction avec regex de fallback"""
        relationships = []
        
        for rel_type, pattern in self.fallback_patterns.items():
            for match in pattern.finditer(text):
                if rel_type == "filiation":
                    rel = RelationshipMatch(
                        type="filiation",
                        persons={
                            "enfant": match.group(1).strip(),
                            "pere": match.group(2).strip(),
                            "mere": match.group(3).strip() if match.group(3) else None
                        },
                        confidence=0.75,  # Confiance regex moindre
                        source_span=match.span(),
                        context=match.group(0)
                    )
                    relationships.append(rel)
                
                elif rel_type == "mariage":
                    rel = RelationshipMatch(
                        type="mariage",
                        persons={
                            "epouse": match.group(1).strip(),
                            "epoux": match.group(2).strip()
                        },
                        confidence=0.80,
                        source_span=match.span(),
                        context=match.group(0)
                    )
                    relationships.append(rel)
        
        return relationships
    
    def _deduplicate_and_score(self, relationships: List[RelationshipMatch]) -> List[RelationshipMatch]:
        """Déduplique et score les relations trouvées"""
        if not relationships:
            return []
        
        # Grouper par type et positions similaires
        unique_relations = {}
        
        for rel in relationships:
            # Créer une clé unique
            key = f"{rel.type}_{rel.persons.get('enfant', '')}_{rel.persons.get('epouse', '')}"
            
            if key not in unique_relations or rel.confidence > unique_relations[key].confidence:
                unique_relations[key] = rel
        
        # Trier par confiance
        return sorted(unique_relations.values(), key=lambda x: x.confidence, reverse=True)
    
    @lru_cache(maxsize=1000)
    def get_person_entities(self, text: str) -> List[str]:
        """Cache des entités personnes extraites"""
        if not self.use_spacy:
            # Fallback simple
            names = re.findall(r'\b[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)+', text)
            return list(set(names))
        
        try:
            doc = nlp(text)
            persons = [ent.text for ent in doc.ents if ent.label_ == "PER"]
            return list(set(persons))
        except Exception:
            return []
    
    def validate_relationship(self, relationship: RelationshipMatch, context: str = "") -> float:
        """Valide une relation avec scoring contextuel"""
        base_confidence = relationship.confidence
        
        # Bonifications contextuelles
        context_lower = context.lower()
        
        # Contexte paroissial augmente la confiance
        if any(word in context_lower for word in ['baptême', 'église', 'curé', 'paroisse']):
            base_confidence += 0.05
        
        # Présence de dates augmente la confiance
        if re.search(r'\d{4}|\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)', context_lower):
            base_confidence += 0.03
        
        # Titres de noblesse augmentent la confiance  
        if any(word in context_lower for word in ['sieur', 'écuyer', 'seigneur', 'comte', 'baron']):
            base_confidence += 0.02
        
        return min(base_confidence, 1.0)  # Cap à 1.0
    
    def get_parsing_stats(self) -> Dict:
        """Statistiques du parser"""
        return {
            'nlp_engine': 'spaCy' if self.use_spacy else 'regex_fallback',
            'spacy_available': HAS_SPACY,
            'entity_cache_size': len(self._entity_cache),
            'patterns_count': len(self.fallback_patterns) if hasattr(self, 'fallback_patterns') else 0
        }

# FIX: Parser de base pour compatibilité
class FallbackRelationshipParser:
    """Parser de base compatible avec l'interface existante"""
    
    def __init__(self, config=None):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def extract_relationships(self, text: str) -> List[Dict]:
        """Interface compatible avec l'ancien parser"""
        modern_parser = ModernNLPParser()
        relationships = modern_parser.extract_relationships(text)
        
        # Convertir au format attendu
        return [
            {
                'type': rel.type,
                'persons': rel.persons,
                'confidence': rel.confidence,
                'context': rel.context
            }
            for rel in relationships
        ]

# Factory function corrigée
def create_relationship_parser(prefer_nlp: bool = True) -> Union[ModernNLPParser, FallbackRelationshipParser]:
    """Factory pour créer le parser optimal selon l'environnement"""
    
    if prefer_nlp and HAS_SPACY:
        return ModernNLPParser(fallback_to_regex=True)
    else:
        # FIX: Utiliser le parser de fallback intégré
        try:
            from config.settings import ParserConfig
            from parsers.relationship.basic_relationship_parser import RelationshipParser
            return RelationshipParser(ParserConfig())
        except ImportError:
            # Si l'import échoue, utiliser notre fallback
            return FallbackRelationshipParser()

# Instructions d'installation pour améliorer les performances
INSTALL_INSTRUCTIONS = """
Pour activer le parsing NLP avancé, installez spaCy :

pip install spacy
python -m spacy download fr_core_news_sm

Cela améliorera significativement la précision et robustesse du parsing !
"""

if __name__ == "__main__":
    # Test de démonstration
    parser = create_relationship_parser()
    
    sample_text = """
    1651, 24 oct., naissance, bapt. de Charlotte, fille de Jean Le Boucher, 
    éc., sr de La Granville, et de Françoise Varin; marr.: Perrette Dupré; 
    parr.: Charles Le Boucher, éc., sr du Hozey.
    """
    
    print("=== TEST PARSER MODERNE ===")
    print(f"Engine: {parser.__class__.__name__}")
    
    if hasattr(parser, 'extract_relationships'):
        # Parser moderne
        relationships = parser.extract_relationships(sample_text)
        
        if isinstance(relationships, list) and len(relationships) > 0:
            if isinstance(relationships[0], RelationshipMatch):
                # Format ModernNLPParser
                for rel in relationships:
                    print(f"\nType: {rel.type}")
                    print(f"Personnes: {rel.persons}")
                    print(f"Confiance: {rel.confidence:.2f}")
                    print(f"Contexte: {rel.context[:80]}...")
            else:
                # Format dict
                for rel in relationships:
                    print(f"\nType: {rel.get('type')}")
                    print(f"Personnes: {rel.get('persons')}")
                    print(f"Confiance: {rel.get('confidence', 0):.2f}")
    
    if not HAS_SPACY:
        print("\n" + INSTALL_INSTRUCTIONS)