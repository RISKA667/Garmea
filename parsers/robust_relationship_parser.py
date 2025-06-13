# parsers/robust_relationship_parser.py
import re
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import logging
from functools import lru_cache

@dataclass
class RelationMatch:
    """Match de relation avec métadonnées"""
    type: str
    persons: Dict[str, str]
    confidence: float
    source_text: str
    position: Tuple[int, int]

class RobustRelationshipParser:
    """Parser de relations robuste et tolérant aux erreurs OCR"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Patterns progressifs : du plus simple au plus complexe
        self._setup_flexible_patterns()
        
        # Mots de relation avec variantes OCR
        self._setup_relation_vocabularies()
        
        # Cache pour performance
        self._cache = {}
        
        # Statistiques
        self.stats = {
            'total_processed': 0,
            'relations_found': 0,
            'pattern_successes': {}
        }
    
    def _setup_flexible_patterns(self):
        """Configure des patterns progressivement plus tolérants"""
        
        # Nom très permissif pour OCR dégradé
        nom_pattern = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß\d][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-\.\s]*'
        
        self.patterns = {
            # === NIVEAU 1: PATTERNS TRÈS SIMPLES ===
            
            # Filiation basique
            'filiation_basic': re.compile(
                rf'({nom_pattern})\s*,?\s*(?:fils?|filles?|filz)\s+de\s+({nom_pattern})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # Filiation avec mère
            'filiation_with_mother': re.compile(
                rf'({nom_pattern})\s*,?\s*(?:fils?|filles?|filz)\s+de\s+({nom_pattern})\s+et\s+(?:de\s+)?({nom_pattern})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # Mariage basique
            'marriage_basic': re.compile(
                rf'({nom_pattern})\s*,?\s*(?:épouse|femme|espouse)\s+de\s+({nom_pattern})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # Veuvage
            'widowhood': re.compile(
                rf'({nom_pattern})\s*,?\s*veuve?\s+de\s+({nom_pattern})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # === NIVEAU 2: PATTERNS AVEC TOLÉRANCE OCR ===
            
            # Filiation avec variantes OCR
            'filiation_ocr_tolerant': re.compile(
                rf'({nom_pattern})\s*[,\.;:]?\s*(?:fils?|filles?|filz|flls|f1ls)\s+[deo]+\s+({nom_pattern})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # Parrainage simplifié
            'godfather_simple': re.compile(
                rf'(?:parr?ain?|parr?\.?|parr?:)\s*[\.:\-]?\s*({nom_pattern})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            'godmother_simple': re.compile(
                rf'(?:marr?aine?|marr?\.?|marr?:)\s*[\.:\-]?\s*({nom_pattern})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # === NIVEAU 3: PATTERNS CONTEXTUELS ===
            
            # Relations dans contexte baptême
            'baptism_context': re.compile(
                rf'(?:bapt[êe]?me?|bapt\.?|baptisé[e]?)\s+.*?de\s+({nom_pattern}).*?'
                rf'(?:parr?[\.:]?\s*({nom_pattern}))?.*?'
                rf'(?:marr?[\.:]?\s*({nom_pattern}))?',
                re.IGNORECASE | re.MULTILINE | re.DOTALL
            ),
            
            # Relations dans contexte mariage
            'marriage_context': re.compile(
                rf'(?:mariage|mar\.?|union)\s+.*?(?:de|entre)\s+({nom_pattern})\s+(?:et|avec)\s+({nom_pattern})',
                re.IGNORECASE | re.MULTILINE | re.DOTALL
            ),
            
            # === NIVEAU 4: PATTERNS TRÈS PERMISSIFS ===
            
            # Détection "X et Y" comme couple potentiel
            'potential_couple': re.compile(
                rf'({nom_pattern})\s+et\s+({nom_pattern})',
                re.IGNORECASE
            )
        }
    
    def _setup_relation_vocabularies(self):
        """Configure les vocabulaires avec variantes OCR"""
        
        self.relation_words = {
            'parent_child': {
                'fils': ['fils', 'filz', 'fls', 'f1ls', 'flls'],
                'fille': ['fille', 'filles', 'flle', 'f1lle'],
                'enfant': ['enfant', 'enfans', 'enfanr'],
                'de': ['de', 'du', 'des', 'dé', 'dc', 'do']
            },
            'marriage': {
                'épouse': ['épouse', 'espouse', 'cpouse', 'époufe'],
                'femme': ['femme', 'fame', 'fcmme'],
                'mari': ['mari', 'mary', 'man'],
                'époux': ['époux', 'espoux', 'cpoux']
            },
            'widowhood': {
                'veuve': ['veuve', 'veve', 'vcuve'],
                'veuf': ['veuf', 'vcuf', 'vef']
            },
            'godparentage': {
                'parrain': ['parrain', 'parrin', 'parr', 'parr.', 'parr:', 'parrair'],
                'marraine': ['marraine', 'marrine', 'marr', 'marr.', 'marr:', 'marrirre']
            }
        }
    
    def extract_relationships(self, text: str, strict_mode: bool = False) -> List[RelationMatch]:
        """Extraction principale avec mode strict/permissif"""
        
        if not text or len(text.strip()) < 20:
            return []
        
        self.stats['total_processed'] += 1
        
        # Nettoyer le texte d'abord
        cleaned_text = self._clean_text_for_parsing(text)
        
        relationships = []
        used_positions = set()
        
        # Appliquer les patterns dans l'ordre de confiance
        pattern_order = self._get_pattern_order(strict_mode)
        
        for pattern_name in pattern_order:
            pattern = self.patterns[pattern_name]
            
            matches = self._find_non_overlapping_matches(
                pattern, cleaned_text, used_positions
            )
            
            for match in matches:
                relation = self._parse_match(pattern_name, match, cleaned_text)
                if relation:
                    relationships.append(relation)
                    used_positions.update(range(match.start(), match.end()))
                    
                    # Statistiques
                    if pattern_name not in self.stats['pattern_successes']:
                        self.stats['pattern_successes'][pattern_name] = 0
                    self.stats['pattern_successes'][pattern_name] += 1
        
        # Post-traitement et validation
        relationships = self._validate_relationships(relationships, text)
        
        self.stats['relations_found'] += len(relationships)
        
        return relationships
    
    def _clean_text_for_parsing(self, text: str) -> str:
        """Nettoyage spécialisé pour améliorer le parsing"""
        
        # 1. Corrections OCR courantes
        corrections = {
            r'\bl\b(?=[A-Z])': 'I',  # l -> I devant majuscule
            r'\b1(?=[a-z])': 'l',    # 1 -> l devant minuscule
            r'\b0(?=[a-z])': 'o',    # 0 -> o
            r'(?<=[a-z])1(?=[a-z])': 'l',  # 1 -> l entre lettres
            r'(?<=[a-z])0(?=[a-z])': 'o',  # 0 -> o entre lettres
            r'rn': 'm',              # rn -> m (erreur OCR fréquente)
            r'cl(?=[aeiou])': 'd',   # cl -> d devant voyelle
        }
        
        cleaned = text
        for pattern, replacement in corrections.items():
            cleaned = re.sub(pattern, replacement, cleaned)
        
        # 2. Normaliser la ponctuation
        cleaned = re.sub(r'[,;\.]{2,}', ', ', cleaned)  # Ponctuation multiple
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Espaces multiples
        cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)  # Mots collés
        
        return cleaned
    
    def _get_pattern_order(self, strict_mode: bool) -> List[str]:
        """Ordre d'application des patterns selon le mode"""
        
        if strict_mode:
            # Mode strict : patterns précis seulement
            return [
                'filiation_basic',
                'filiation_with_mother', 
                'marriage_basic',
                'widowhood',
                'godfather_simple',
                'godmother_simple'
            ]
        else:
            # Mode permissif : tous les patterns
            return [
                'filiation_basic',
                'filiation_with_mother',
                'marriage_basic',
                'widowhood',
                'godfather_simple',
                'godmother_simple',
                'filiation_ocr_tolerant',
                'baptism_context',
                'marriage_context',
                'potential_couple'
            ]
    
    def _find_non_overlapping_matches(self, pattern: re.Pattern, text: str, 
                                     used_positions: Set[int]) -> List[re.Match]:
        """Trouve les matches qui ne chevauchent pas avec les positions déjà utilisées"""
        
        matches = []
        for match in pattern.finditer(text):
            # Vérifier si ce match chevauche avec une position déjà utilisée
            match_range = set(range(match.start(), match.end()))
            if not match_range.intersection(used_positions):
                matches.append(match)
        
        return matches
    
    def _parse_match(self, pattern_name: str, match: re.Match, text: str) -> Optional[RelationMatch]:
        """Parse un match spécifique selon son type"""
        
        groups = match.groups()
        confidence = self._calculate_confidence(pattern_name, match, text)
        
        try:
            if pattern_name in ['filiation_basic', 'filiation_ocr_tolerant']:
                child = self._clean_name(groups[0])
                father = self._clean_name(groups[1])
                
                if child and father:
                    return RelationMatch(
                        type='filiation',
                        persons={'enfant': child, 'pere': father},
                        confidence=confidence,
                        source_text=match.group(0)[:100],
                        position=match.span()
                    )
            
            elif pattern_name == 'filiation_with_mother':
                child = self._clean_name(groups[0])
                father = self._clean_name(groups[1])
                mother = self._clean_name(groups[2]) if len(groups) > 2 else None
                
                if child and father:
                    persons = {'enfant': child, 'pere': father}
                    if mother:
                        persons['mere'] = mother
                    
                    return RelationMatch(
                        type='filiation',
                        persons=persons,
                        confidence=confidence,
                        source_text=match.group(0)[:100],
                        position=match.span()
                    )
            
            elif pattern_name in ['marriage_basic', 'widowhood']:
                wife = self._clean_name(groups[0])
                husband = self._clean_name(groups[1])
                
                if wife and husband:
                    rel_type = 'mariage' if pattern_name == 'marriage_basic' else 'veuvage'
                    return RelationMatch(
                        type=rel_type,
                        persons={'epouse': wife, 'epoux': husband},
                        confidence=confidence,
                        source_text=match.group(0)[:100],
                        position=match.span()
                    )
            
            elif pattern_name == 'godfather_simple':
                godfather = self._clean_name(groups[0])
                
                if godfather:
                    return RelationMatch(
                        type='parrain',
                        persons={'parrain': godfather},
                        confidence=confidence,
                        source_text=match.group(0)[:50],
                        position=match.span()
                    )
            
            elif pattern_name == 'godmother_simple':
                godmother = self._clean_name(groups[0])
                
                if godmother:
                    return RelationMatch(
                        type='marraine',
                        persons={'marraine': godmother},
                        confidence=confidence,
                        source_text=match.group(0)[:50],
                        position=match.span()
                    )
            
            elif pattern_name == 'potential_couple':
                person1 = self._clean_name(groups[0])
                person2 = self._clean_name(groups[1])
                
                if person1 and person2:
                    return RelationMatch(
                        type='couple_potentiel',
                        persons={'personne1': person1, 'personne2': person2},
                        confidence=confidence * 0.5,  # Confiance réduite
                        source_text=match.group(0)[:50],
                        position=match.span()
                    )
        
        except Exception as e:
            self.logger.debug(f"Erreur parsing match {pattern_name}: {e}")
        
        return None
    
    def _clean_name(self, name: str) -> Optional[str]:
        """Nettoyage intelligent des noms"""
        
        if not name:
            return None
        
        # Supprimer les titres et suffixes courants
        name = re.sub(r',?\s*(?:éc\.|écuyer|sr|seigneur|sieur|conseiller|avocat|curé|prêtre).*$', '', name, flags=re.IGNORECASE)
        
        # Supprimer les particules en début si isolées
        name = re.sub(r'^(?:de|du|des|le|la|les)\s+', '', name, flags=re.IGNORECASE)
        
        # Nettoyer la ponctuation
        name = re.sub(r'[,;:\.]+$', '', name)
        name = re.sub(r'\s+', ' ', name)
        name = name.strip()
        
        # Validation
        if len(name) < 2 or len(name) > 50:
            return None
        
        # Doit commencer par une lettre
        if not re.match(r'^[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß]', name):
            return None
        
        # Capitalisation
        words = name.split()
        capitalized = []
        
        for word in words:
            if word.lower() in ['de', 'du', 'des', 'le', 'la', 'les']:
                capitalized.append(word.lower())
            else:
                capitalized.append(word.capitalize())
        
        return ' '.join(capitalized)
    
    def _calculate_confidence(self, pattern_name: str, match: re.Match, text: str) -> float:
        """Calcule la confiance d'un match"""
        
        base_confidence = {
            'filiation_basic': 0.90,
            'filiation_with_mother': 0.95,
            'marriage_basic': 0.85,
            'widowhood': 0.80,
            'godfather_simple': 0.75,
            'godmother_simple': 0.75,
            'filiation_ocr_tolerant': 0.70,
            'baptism_context': 0.65,
            'marriage_context': 0.60,
            'potential_couple': 0.30
        }.get(pattern_name, 0.50)
        
        # Bonifications
        match_text = match.group(0).lower()
        
        # Contexte religieux augmente la confiance
        if any(word in text.lower() for word in ['église', 'curé', 'baptême', 'paroisse']):
            base_confidence += 0.05
        
        # Dates présentes augmentent la confiance
        if re.search(r'\d{4}', match_text):
            base_confidence += 0.03
        
        # Titres de noblesse augmentent la confiance
        if any(word in match_text for word in ['sieur', 'écuyer', 'seigneur']):
            base_confidence += 0.02
        
        return min(base_confidence, 1.0)
    
    def _validate_relationships(self, relationships: List[RelationMatch], text: str) -> List[RelationMatch]:
        """Validation et nettoyage final"""
        
        if not relationships:
            return []
        
        validated = []
        seen_signatures = set()
        
        for rel in relationships:
            # Créer une signature unique
            persons_str = '_'.join(sorted(rel.persons.values()))
            signature = f"{rel.type}_{persons_str}"
            
            # Éviter les doublons
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                validated.append(rel)
        
        # Trier par confiance décroissante
        validated.sort(key=lambda x: x.confidence, reverse=True)
        
        return validated
    
    def get_statistics(self) -> Dict:
        """Statistiques du parser"""
        
        total_found = self.stats['relations_found']
        total_processed = max(1, self.stats['total_processed'])
        
        return {
            'total_documents_processed': self.stats['total_processed'],
            'total_relations_found': total_found,
            'average_relations_per_document': total_found / total_processed,
            'pattern_successes': self.stats['pattern_successes'],
            'most_successful_pattern': max(
                self.stats['pattern_successes'].items(),
                key=lambda x: x[1],
                default=('none', 0)
            )[0] if self.stats['pattern_successes'] else 'none'
        }
    
    def debug_on_text(self, text: str, show_details: bool = True) -> Dict:
        """Debug détaillé sur un texte"""
        
        print("🔧 DEBUG PARSER ROBUSTE")
        print("=" * 40)
        
        # Test nettoyage
        cleaned = self._clean_text_for_parsing(text)
        print(f"📝 Texte nettoyé ({len(cleaned)} chars):")
        print(cleaned[:200] + "..." if len(cleaned) > 200 else cleaned)
        
        # Test patterns
        print(f"\n🎯 Test des patterns:")
        
        pattern_results = {}
        for pattern_name, pattern in self.patterns.items():
            matches = list(pattern.finditer(cleaned))
            pattern_results[pattern_name] = matches
            
            if matches:
                print(f"   ✅ {pattern_name}: {len(matches)} matches")
                if show_details:
                    for i, match in enumerate(matches[:2]):  # Max 2 exemples
                        print(f"      {i+1}. '{match.group(0)[:60]}...'")
            else:
                print(f"   ❌ {pattern_name}: 0 matches")
        
        # Test extraction complète
        print(f"\n🔗 Extraction complète:")
        relations = self.extract_relationships(text, strict_mode=False)
        
        print(f"   Relations trouvées: {len(relations)}")
        for rel in relations:
            print(f"   - {rel.type}: {rel.persons} (confiance: {rel.confidence:.2f})")
        
        return {
            'cleaned_text': cleaned,
            'pattern_results': pattern_results,
            'final_relations': relations
        }

# Test rapide
if __name__ == "__main__":
    # Créer le parser
    parser = RobustRelationshipParser()
    
    # Texte de test avec problèmes OCR simulés
    test_text = """
    1651, 23 janv., inh., dans l'église, de Françoise Picot, épouse de Charles Le Boucher, 
    éc., sr du Hausey; 24 oct., naissance, bapt. de Charlotte, fille de Jean Le Boucher 
    et de Françoise Varin; marr.: Perrette Dupré; parr.: Charles Le Boucher.
    Pierre Martin, fils de Jean Martln et Marie Duponr.
    """
    
    print("=== TEST PARSER ROBUSTE ===\n")
    
    # Debug complet
    result = parser.debug_on_text(test_text)
    
    # Statistiques
    stats = parser.get_statistics()
    print(f"\n📊 Statistiques:")
    for key, value in stats.items():
        print(f"   - {key}: {value}")