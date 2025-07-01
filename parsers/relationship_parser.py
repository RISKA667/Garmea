# parsers/robust_relationship_parser.py - VERSION AMÉLIORÉE
"""
Parser de relations robuste avec corrections OCR intégrées
Intègre directement les corrections découvertes dans le processus de parsing
"""

import re
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import logging
from functools import lru_cache

@dataclass
class RelationMatch:
    """Match de relation avec métadonnées enrichies"""
    type: str
    persons: Dict[str, str]
    confidence: float
    source_text: str
    position: Tuple[int, int]
    ocr_corrections_applied: List[str] = None

class RelationshipParser:
    """Parser de relations robuste avec corrections OCR intégrées"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Statistiques enrichies
        self.stats = {
            'total_processed': 0,
            'relations_found': 0,
            'ocr_corrections_applied': 0,
            'pattern_successes': {},
            'text_cleaning_improvements': 0
        }
        
        # Dictionnaire de corrections OCR intégrées
        self.corrections_ocr_genealogiques = {
            # === ERREURS "Aii" SYSTÉMATIQUES ===
            'Aiicelle': 'Ancelle',
            'Aiigotin': 'Antigotin',
            'Aiimont': 'Aumont',
            'Aiiber': 'Auber',
            'Aiivray': 'Auvray',
            'Aii-': 'Anne',
            
            # === ERREURS TRANSCRIPTION RELATIONS ===
            'Jaeques': 'Jacques',
            'Franteois': 'François',
            'Catlierhie': 'Catherine',
            'Guillaïune': 'Guillaume',
            'Nicollas': 'Nicolas',
            'Muiiie': 'Marie',
            
            # === NOMS TRONQUÉS DANS RELATIONS ===
            'Marie- An': 'Marie-Anne',
            'An-': 'Anne',
            'Ade-': 'Adeline',
            'Alexandre-': 'Alexandre',
            
            # === ERREURS CONTEXTUELLES RELATIONS ===
            'épous de': 'épouse de',
            'fils d ': 'fils de ',
            'fille d ': 'fille de ',
            'parr ain': 'parrain',
            'marr aine': 'marraine'
        }
        
        # Configuration des patterns améliorés
        self._setup_enhanced_patterns()
        
        # Vocabulaires de relations avec variantes OCR
        self._setup_relation_vocabularies()
        
        # Cache pour performance
        self._cache = {}
        self._cleaning_cache = {}
    
    def _setup_enhanced_patterns(self):
        """Configure des patterns améliorés pour OCR dégradé"""
        
        # Pattern de nom très tolérant aux erreurs OCR
        nom_pattern = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß\d][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-\.\s]{1,40}'
        
        self.patterns = {
            # === FILIATION ROBUSTE ===
            'filiation_basic_robust': re.compile(
                rf'({nom_pattern})\s*[,\.;:]?\s*(?:fils?|filles?|filz|f1ls|flls)\s+[deoû]+\s+({nom_pattern})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            'filiation_with_mother_robust': re.compile(
                rf'({nom_pattern})\s*[,\.;:]?\s*(?:fils?|filles?|filz)\s+[deoû]+\s+({nom_pattern})\s+(?:et|&)\s+(?:[deoû]+\s+)?({nom_pattern})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # === MARIAGE ROBUSTE ===
            'marriage_robust': re.compile(
                rf'({nom_pattern})\s*[,\.;:]?\s*(?:épouse?|femme|espouse|epouse)\s+[deoû]+\s+({nom_pattern})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            'widowhood_robust': re.compile(
                rf'({nom_pattern})\s*[,\.;:]?\s*(?:veuve?|vve?|veuf)\s+[deoû]+\s+({nom_pattern})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # === PARRAINAGE ROBUSTE ===
            'godfather_robust': re.compile(
                rf'(?:parr?[aâ]?in?[es]?|parr?\.?|parr?:)\s*[\.;:,]?\s*({nom_pattern})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            'godmother_robust': re.compile(
                rf'(?:marr?[aâ]?ines?|marr?\.?|marr?:|marrines?)\s*[\.;:,]?\s*({nom_pattern})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # === PATTERNS CONTEXTUELS AMÉLIORÉS ===
            'marriage_ceremony': re.compile(
                rf'(?:mariage|mar\.|épous[ée])\s+.*?(?:de|entre)\s+({nom_pattern})\s+(?:et|avec|&)\s+({nom_pattern})',
                re.IGNORECASE | re.DOTALL
            ),
            
            'baptism_context': re.compile(
                rf'(?:bapt[êe]?me?|baptisé[e]?|ondoyé[e]?)\s+.*?({nom_pattern})\s*[,\.;]?\s*(?:fils?|filles?)\s+[deoû]+\s+({nom_pattern})',
                re.IGNORECASE | re.DOTALL
            ),
            
            # === RELATIONS MULTIPLES ===
            'family_group': re.compile(
                rf'({nom_pattern})\s+et\s+({nom_pattern})\s*[,\.;]?\s*(?:ses\s+)?(?:père\s+et\s+mère|parents)',
                re.IGNORECASE
            )
        }
    
    def _setup_relation_vocabularies(self):
        """Configure les vocabulaires de relations avec variantes OCR"""
        
        self.relation_vocabularies = {
            'filiation': {
                'fils': ['fils', 'filz', 'f1ls', 'flls', 'fïls'],
                'fille': ['fille', 'fïlle', 'f1lle', 'fllle'],
                'de': ['de', 'du', 'dû', 'cl', 'cl0']
            },
            'mariage': {
                'épouse': ['épouse', 'espouse', 'epouse', 'femme'],
                'époux': ['époux', 'espoux', 'epoux', 'mari'],
                'veuve': ['veuve', 'vve', 'weuve'],
                'veuf': ['veuf', 'vf', 'weuf']
            },
            'parrainage': {
                'parrain': ['parrain', 'parrin', 'parrein', 'parr', 'parr.', 'parr:', 'parrair'],
                'marraine': ['marraine', 'marrine', 'marrirre', 'marr', 'marr.', 'marr:']
            }
        }
    
    @lru_cache(maxsize=500)
    def _clean_text_for_parsing(self, text: str) -> Tuple[str, List[str]]:
        """
        Nettoyage spécialisé avec corrections OCR intégrées
        
        Returns:
            Tuple[str, List[str]]: (texte_nettoyé, corrections_appliquées)
        """
        if not text:
            return text, []
        
        corrections_appliquees = []
        cleaned = text
        
        # 1. Corrections OCR spécifiques aux généalogies
        for erreur, correction in self.corrections_ocr_genealogiques.items():
            if erreur in cleaned:
                cleaned = cleaned.replace(erreur, correction)
                corrections_appliquees.append(f"{erreur} → {correction}")
                self.stats['ocr_corrections_applied'] += 1
        
        # 2. Corrections OCR courantes (existantes)
        corrections_ocr_base = {
            r'\bl\b(?=[A-Z])': 'I',  # l -> I devant majuscule
            r'\b1(?=[a-z])': 'l',    # 1 -> l devant minuscule
            r'\b0(?=[a-z])': 'o',    # 0 -> o
            r'(?<=[a-z])1(?=[a-z])': 'l',  # 1 -> l entre lettres
            r'(?<=[a-z])0(?=[a-z])': 'o',  # 0 -> o entre lettres
            r'rn(?=[aeiou])': 'm',   # rn -> m devant voyelle
            r'cl(?=[aeiou])': 'd',   # cl -> d devant voyelle
            r'ii(?=[bcdfghjklmnpqrstvwxyz])': 'n',  # ii -> n devant consonne
        }
        
        for pattern, replacement in corrections_ocr_base.items():
            nouvelle_version = re.sub(pattern, replacement, cleaned)
            if nouvelle_version != cleaned:
                corrections_appliquees.append(f"Pattern OCR: {pattern}")
                cleaned = nouvelle_version
        
        # 3. Normalisation de la ponctuation pour relations
        ponctuation_fixes = {
            r'[,;\.]{2,}': ',',      # Ponctuation multiple
            r'\s*[,;\.]\s*de\s+': ' de ',  # "., de" -> " de "
            r'\s*[,;\.]\s*et\s+': ' et ',  # "., et" -> " et "
            r'(\w)\s*-\s*(\w)': r'\1-\2',  # Espaces autour tirets
        }
        
        for pattern, replacement in ponctuation_fixes.items():
            nouvelle_version = re.sub(pattern, replacement, cleaned)
            if nouvelle_version != cleaned:
                corrections_appliquees.append(f"Ponctuation: {pattern}")
                cleaned = nouvelle_version
        
        # 4. Normaliser les espaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        if corrections_appliquees:
            self.stats['text_cleaning_improvements'] += 1
        
        return cleaned, corrections_appliquees
    
    def extract_relationships(self, text: str, strict_mode: bool = False) -> List[RelationMatch]:
        """Extraction principale avec corrections OCR intégrées"""
        
        if not text or len(text.strip()) < 20:
            return []
        
        self.stats['total_processed'] += 1
        
        # Nettoyer le texte avec corrections OCR
        cleaned_text, corrections_appliquees = self._clean_text_for_parsing(text)
        
        relationships = []
        used_positions = set()
        
        # Appliquer les patterns dans l'ordre de priorité
        pattern_order = self._get_pattern_order(strict_mode)
        
        for pattern_name in pattern_order:
            pattern = self.patterns[pattern_name]
            
            matches = self._find_non_overlapping_matches(
                pattern, cleaned_text, used_positions
            )
            
            for match in matches:
                relation = self._parse_match(pattern_name, match, cleaned_text)
                if relation:
                    # Ajouter les informations de correction OCR
                    relation.ocr_corrections_applied = corrections_appliquees
                    relationships.append(relation)
                    used_positions.update(range(match.start(), match.end()))
                    
                    # Statistiques
                    if pattern_name not in self.stats['pattern_successes']:
                        self.stats['pattern_successes'][pattern_name] = 0
                    self.stats['pattern_successes'][pattern_name] += 1
        
        # Post-traitement et validation
        relationships = self._validate_relationships(relationships, cleaned_text)
        
        self.stats['relations_found'] += len(relationships)
        
        return relationships
    
    def _get_pattern_order(self, strict_mode: bool) -> List[str]:
        """Ordre d'application des patterns selon le mode"""
        
        if strict_mode:
            return [
                'filiation_basic_robust',
                'marriage_robust',
                'godfather_robust',
                'godmother_robust'
            ]
        else:
            return [
                'filiation_with_mother_robust',
                'filiation_basic_robust', 
                'marriage_ceremony',
                'marriage_robust',
                'widowhood_robust',
                'baptism_context',
                'family_group',
                'godfather_robust',
                'godmother_robust'
            ]
    
    def _find_non_overlapping_matches(self, pattern, text: str, used_positions: Set[int]):
        """Trouve les matches non-chevauchants"""
        
        matches = []
        for match in pattern.finditer(text):
            match_range = range(match.start(), match.end())
            if not any(pos in used_positions for pos in match_range):
                matches.append(match)
        
        return matches
    
    def _parse_match(self, pattern_name: str, match, text: str) -> Optional[RelationMatch]:
        """Parse un match spécifique selon le pattern avec corrections OCR"""
        
        try:
            groups = match.groups()
            confidence = 0.8  # Base confidence
            
            if 'filiation' in pattern_name:
                enfant = self._clean_person_name(groups[0]) if groups[0] else ""
                pere = self._clean_person_name(groups[1]) if len(groups) > 1 and groups[1] else ""
                mere = self._clean_person_name(groups[2]) if len(groups) > 2 and groups[2] else ""
                
                persons = {'enfant': enfant, 'pere': pere}
                if mere:
                    persons['mere'] = mere
                    confidence += 0.1  # Bonus pour relation complète
                
                return RelationMatch(
                    type='filiation',
                    persons=persons,
                    confidence=confidence,
                    source_text=match.group(0),
                    position=(match.start(), match.end())
                )
            
            elif 'marriage' in pattern_name or 'widowhood' in pattern_name:
                personne1 = self._clean_person_name(groups[0]) if groups[0] else ""
                personne2 = self._clean_person_name(groups[1]) if len(groups) > 1 and groups[1] else ""
                
                # Déterminer époux/épouse selon le contexte
                context = match.group(0).lower()
                if 'épouse' in context or 'femme' in context:
                    persons = {'epouse': personne1, 'epoux': personne2}
                else:
                    persons = {'epoux': personne1, 'epouse': personne2}
                
                rel_type = 'veuvage' if 'widow' in pattern_name else 'mariage'
                
                return RelationMatch(
                    type=rel_type,
                    persons=persons,
                    confidence=confidence,
                    source_text=match.group(0),
                    position=(match.start(), match.end())
                )
            
            elif 'god' in pattern_name:
                personne = self._clean_person_name(groups[0]) if groups[0] else ""
                rel_type = 'parrain' if 'father' in pattern_name else 'marraine'
                
                return RelationMatch(
                    type=rel_type,
                    persons={'personne': personne},
                    confidence=confidence - 0.1,  # Moins précis sans contexte enfant
                    source_text=match.group(0),
                    position=(match.start(), match.end())
                )
            
            elif 'family_group' in pattern_name:
                pere = self._clean_person_name(groups[0]) if groups[0] else ""
                mere = self._clean_person_name(groups[1]) if len(groups) > 1 and groups[1] else ""
                
                return RelationMatch(
                    type='parents',
                    persons={'pere': pere, 'mere': mere},
                    confidence=confidence,
                    source_text=match.group(0),
                    position=(match.start(), match.end())
                )
        
        except Exception as e:
            self.logger.warning(f"Erreur parsing match {pattern_name}: {e}")
            return None
        
        return None
    
    @lru_cache(maxsize=1000)
    def _clean_person_name(self, name: str) -> str:
        """Nettoyage amélioré des noms de personnes avec corrections OCR"""
        
        if not name:
            return ""
        
        original_name = name
        
        # 1. Corrections OCR spécifiques
        for erreur, correction in self.corrections_ocr_genealogiques.items():
            if erreur in name:
                name = name.replace(erreur, correction)
        
        # 2. Nettoyage standard
        # Supprimer titres en préfixe
        name = re.sub(r'^(?:messire|damoiselle|sieur?|sr\.?|éc\.?|monsieur|madame)\s+', '', name, flags=re.IGNORECASE)
        
        # Supprimer professions et titres en suffixe
        name = re.sub(r',\s*(?:écuyer|seigneur|prêtre|curé|marchand|laboureur).*$', '', name, flags=re.IGNORECASE)
        
        # Nettoyer ponctuation
        name = re.sub(r'[,;\.]+$', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Validation
        if len(name) < 2 or len(name) > 60:
            return ""
        
        return name
    
    def _validate_relationships(self, relationships: List[RelationMatch], text: str) -> List[RelationMatch]:
        """Validation des relations avec prise en compte des corrections OCR"""
        
        validated = []
        
        for rel in relationships:
            # Validation de base
            if not any(rel.persons.values()):
                continue
            
            # Vérifier que les noms ne sont pas des artifacts OCR
            valid_persons = {}
            for role, nom in rel.persons.items():
                if nom and self._is_valid_person_name(nom):
                    valid_persons[role] = nom
            
            if valid_persons:
                rel.persons = valid_persons
                # Ajuster la confiance selon la qualité des corrections OCR
                if rel.ocr_corrections_applied:
                    rel.confidence = min(rel.confidence + 0.05, 0.95)  # Bonus léger
                validated.append(rel)
        
        return validated
    
    def _is_valid_person_name(self, name: str) -> bool:
        """Validation améliorée des noms de personnes"""
        
        if not name or len(name) < 2:
            return False
        
        # Rejeter les mots courants non-noms
        mots_exclus = {'le', 'la', 'de', 'du', 'et', 'dans', 'pour', 'avec', 'sur'}
        if name.lower() in mots_exclus:
            return False
        
        # Doit contenir au moins une lettre
        if not re.search(r'[a-zA-ZÀ-ÿ]', name):
            return False
        
        # Pas uniquement de la ponctuation
        if re.match(r'^[^a-zA-ZÀ-ÿ]+$', name):
            return False
        
        return True
    
    def get_enhanced_statistics(self) -> Dict:
        """Statistiques enrichies avec informations OCR"""
        
        return {
            **self.stats,
            'correction_rate': (
                self.stats['ocr_corrections_applied'] / max(self.stats['total_processed'], 1)
            ) * 100,
            'success_rate': (
                self.stats['relations_found'] / max(self.stats['total_processed'], 1)
            ) * 100
        }
    
    def debug_on_text(self, text: str) -> Dict:
        """Debug enrichi avec informations de correction OCR"""
        
        print(f"🔧 DEBUG PARSER ROBUSTE AVEC OCR")
        print("=" * 50)
        
        # Nettoyage du texte
        cleaned, corrections = self._clean_text_for_parsing(text)
        
        print(f"📝 Corrections OCR appliquées: {len(corrections)}")
        for correction in corrections[:5]:  # Afficher les 5 premières
            print(f"   ✅ {correction}")
        
        if cleaned != text:
            print(f"\n📋 Texte après nettoyage (premier 200 chars):")
            print(f"   {cleaned[:200]}...")
        
        # Test des patterns
        print(f"\n🔍 Test des patterns:")
        pattern_results = {}
        
        for pattern_name, pattern in self.patterns.items():
            matches = list(pattern.finditer(cleaned))
            pattern_results[pattern_name] = matches
            
            if matches:
                print(f"   ✅ {pattern_name}: {len(matches)} matches")
                print(f"      Exemple: '{matches[0].group(0)[:60]}...'")
            else:
                print(f"   ❌ {pattern_name}: 0 matches")
        
        # Extraction complète
        print(f"\n🔗 Extraction complète:")
        relations = self.extract_relationships(text, strict_mode=False)
        
        print(f"   Relations trouvées: {len(relations)}")
        for rel in relations:
            print(f"   - {rel.type}: {rel.persons} (confiance: {rel.confidence:.2f})")
            if rel.ocr_corrections_applied:
                print(f"     Corrections OCR: {len(rel.ocr_corrections_applied)}")
        
        return {
            'original_text': text,
            'cleaned_text': cleaned,
            'ocr_corrections': corrections,
            'pattern_results': pattern_results,
            'final_relations': relations,
            'statistics': self.get_enhanced_statistics()
        }

# === TEST ET VALIDATION ===

if __name__ == "__main__":
    # Test du parser amélioré
    parser = RobustRelationshipParser()
    
    # Texte de test avec erreurs OCR simulées
    test_text = """
    Jean Aiicelle, fils de Pierre Aiicelle et Catlierhie Aiimont.
    Mariage de Franteois Guillaïune avec Marie- An.
    Jaeques- Roch Adam, épous de Marguerite Ade-.
    Parr ain: Charles Le Boucher. Marr aine: Perrette Dupré.
    """
    
    print("=== TEST PARSER ROBUSTE AMÉLIORÉ ===\n")
    
    # Debug complet
    result = parser.debug_on_text(test_text)
    
    # Statistiques finales
    print(f"\n📊 Statistiques finales:")
    stats = parser.get_enhanced_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   - {key}: {value:.1f}%")
        else:
            print(f"   - {key}: {value}")