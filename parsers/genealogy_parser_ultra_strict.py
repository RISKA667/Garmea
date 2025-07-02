import re
import numpy as np
from typing import Dict, List, Tuple, Set, Optional, Any
from functools import lru_cache
from collections import defaultdict, Counter
from dataclasses import dataclass, field
import unicodedata

@dataclass
class ValidatedRelation:
    type: str
    entities: Dict[str, str]
    source_text: str
    position: Tuple[int, int]
    confidence: float
    validation_score: float
    rejection_reason: Optional[str] = None

class UltraStrictGenealogyParser:
    def __init__(self, text_parser=None, config=None):
        self.text_parser = text_parser
        self.config = config or {}
        self.prenoms_masculins = self._init_prenoms_masculins()
        self.prenoms_feminins = self._init_prenoms_feminins()
        self.noms_famille_valides = self._init_noms_famille()
        self.corrections_ocr_strictes = self._init_corrections_ocr_strictes()
        self.patterns_rejet_absolu = self._init_patterns_rejet_absolu()
        self.mots_interdits = self._init_mots_interdits()
        self.prefixes_interdits = self._init_prefixes_interdits()
        self.patterns_compiled = self._compile_ultra_strict_patterns()
        self.cache_validation = {}
        self.stats = self._init_stats()
        
    def _init_prenoms_masculins(self) -> Set[str]:
        return {
            'Jean', 'Pierre', 'Jacques', 'Nicolas', 'François', 'Louis', 'Antoine',
            'Michel', 'Guillaume', 'Charles', 'Philippe', 'Gabriel', 'Thomas',
            'André', 'Claude', 'Henri', 'Paul', 'Denis', 'Étienne', 'Martin',
            'Barthélemy', 'Laurent', 'Julien', 'Gilles', 'Robert', 'Christophe',
            'Mathurin', 'Noël', 'Olivier', 'Simon', 'Vincent', 'Yves', 'Alain',
            'Bernard', 'Gérard', 'Marcel', 'Maurice', 'Roger', 'Alexandre',
            'Adrien', 'Alexis', 'Georges', 'Joseph', 'Marin', 'Daniel', 'Léonard',
            'Gaspard', 'Augustin', 'Dominique', 'Sébastien', 'Mathieu', 'Luc',
            'Marc', 'Matthieu', 'Roch', 'Tanneguy', 'Richard', 'Pascal'
        }
    
    def _init_prenoms_feminins(self) -> Set[str]:
        return {
            'Anne', 'Marie', 'Françoise', 'Catherine', 'Marguerite', 'Jeanne',
            'Elisabeth', 'Louise', 'Madeleine', 'Antoinette', 'Geneviève',
            'Suzanne', 'Renée', 'Nicole', 'Monique', 'Brigitte', 'Sylvie',
            'Charlotte', 'Isabelle', 'Henriette', 'Victoire', 'Gabrielle',
            'Hélène', 'Jacqueline', 'Ursule', 'Thérèse', 'Angélique',
            'Eulalie', 'Barbe', 'Perrine', 'Robine', 'Colombe', 'Perrette'
        }
    
    def _init_noms_famille(self) -> Set[str]:
        return {
            'Dupont', 'Martin', 'Bernard', 'Thomas', 'Petit', 'Robert', 'Richard',
            'Durand', 'Dubois', 'Moreau', 'Laurent', 'Simon', 'Michel', 'Lefebvre',
            'Le Boucher', 'Le Chevallier', 'Le Cordier', 'Costart', 'Georges',
            'Denis', 'Colin', 'Bénard', 'Auvray', 'Bazire', 'Bouvet', 'Bouet',
            'Morin', 'Fouques', 'Ancellé', 'Banquet', 'Patey', 'Chéron'
        }
    
    def _init_corrections_ocr_strictes(self) -> Dict[str, str]:
        return {
            'Jacquess': 'Jacques',
            'Gilless': 'Gilles', 
            'Cilles': 'Gilles',
            'atherine': 'Catherine',
            'Cathe rine': 'Catherine',
            'arie': 'Marie',
            'arie Franeoise': 'Marie Françoise',
            'arie Françoise': 'Marie Françoise',
            'ilarguerite': 'Marguerite',
            'ilesnage': 'Mesnage',
            'ilares cot': 'Marescot',
            'Phi lippe': 'Philippe',
            'Pier re': 'Pierre',
            'Jac ques': 'Jacques',
            'Chai les': 'Charles',
            'Bé rot': 'Bérot',
            'Bo rel': 'Borel',
            'Bou vet': 'Bouvet',
            'Béuédic': 'Bénédic',
            'Coliu': 'Colin',
            'Duce lier': 'Ducelier',
            'LechevaUier': 'Le Chevallier',
            'dessusd': 'dessus',
            'bapL': 'baptême',
            'bapt': 'baptême'
        }
    
    def _init_patterns_rejet_absolu(self) -> List[re.Pattern]:
        return [
            re.compile(r'^ARCHIVES\s+DU\s+CALVADOS', re.IGNORECASE),
            re.compile(r'^archives\s+', re.IGNORECASE),
            re.compile(r'^bapt\s+de?\s+', re.IGNORECASE),
            re.compile(r'^baptême\s+de?\s+', re.IGNORECASE),
            re.compile(r'^cérémonies\s+de?\s+', re.IGNORECASE),
            re.compile(r'^contrat\s+', re.IGNORECASE),
            re.compile(r'^autre\s+contrat', re.IGNORECASE),
            re.compile(r'^adjugé\s+à\s+', re.IGNORECASE),
            re.compile(r'^assistée?\s+de?\s+', re.IGNORECASE),
            re.compile(r'^avec\s+', re.IGNORECASE),
            re.compile(r'^(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)$', re.IGNORECASE),
            re.compile(r'^(janv|févr|mars|avr|mai|juin|juil|août|sept|oct|nov|déc)\.?$', re.IGNORECASE),
            re.compile(r'^[a-zA-Z]{1,3}$'),
            re.compile(r'^ans\s+[A-Z]', re.IGNORECASE),
            re.compile(r'^ar\s+', re.IGNORECASE),
            re.compile(r'^ard$', re.IGNORECASE)
        ]
    
    def _init_mots_interdits(self) -> Set[str]:
        return {
            'adjugé', 'aiorel', 'ans', 'août', 'ard', 'assistée', 'aumerey',
            'archives', 'bapt', 'baptême', 'contrat', 'autre', 'avec',
            'de', 'du', 'des', 'le', 'la', 'les', 'et', 'ou', 'à', 'au',
            'ce', 'ci', 'ar', 'va', 'vz'
        }
    
    def _init_prefixes_interdits(self) -> List[str]:
        return [
            'ARCHIVES DU CALVADOS',
            'bapt de',
            'baptême de', 
            'contrat de',
            'autre contrat',
            'adjugé à',
            'assistée de',
            'avec ',
            'cérémonies de'
        ]
    
    def _compile_ultra_strict_patterns(self) -> Dict[str, re.Pattern]:
        prenom_strict = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]{2,15}'
        nom_strict = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ\s\-]{2,25}'
        personne_stricte = rf'(?:{prenom_strict}(?:\s+{prenom_strict})*\s+{nom_strict})'
        
        return {
            'filiation_ultra_stricte': re.compile(
                rf'({personne_stricte}),?\s+(?:fils|fille)\s+de\s+({nom_strict}(?:\s+et\s+(?:de\s+)?{nom_strict})?)',
                re.IGNORECASE | re.MULTILINE
            ),
            'prenom_valide': re.compile(rf'^{prenom_strict}$'),
            'nom_valide': re.compile(rf'^{nom_strict}$')
        }
    
    def _init_stats(self) -> Dict[str, int]:
        return {
            'candidats_examines': 0,
            'rejets_pattern_absolu': 0,
            'rejets_mot_interdit': 0,
            'rejets_prenom_invalide': 0,
            'rejets_longueur': 0,
            'rejets_validation': 0,
            'relations_validees': 0,
            'corrections_ocr_appliquees': 0
        }
    
    def extract_filiations_ultra_strict(self, text: str) -> List[ValidatedRelation]:
        if not text:
            return []
        
        text_cleaned = self._pre_clean_text(text)
        
        filiations = []
        pattern = self.patterns_compiled['filiation_ultra_stricte']
        
        for match in pattern.finditer(text_cleaned):
            self.stats['candidats_examines'] += 1
            
            enfant_raw = match.group(1).strip()
            parents_raw = match.group(2).strip()
            
            validation_enfant = self._validate_child_ultra_strict(enfant_raw)
            
            if not validation_enfant['valid']:
                self._categorize_rejection(validation_enfant['reason'])
                continue
            
            enfant_clean = self._apply_strict_ocr_corrections(enfant_raw)
            parents = self._parse_parents_ultra_strict(parents_raw)
            
            if not self._final_validation(enfant_clean, parents):
                self.stats['rejets_validation'] += 1
                continue
            
            confidence = self._calculate_strict_confidence(enfant_clean, parents)
            
            relation = ValidatedRelation(
                type='filiation',
                entities={
                    'enfant': enfant_clean,
                    'pere': parents.get('pere', ''),
                    'mere': parents.get('mere', '')
                },
                source_text=match.group(0),
                position=match.span(),
                confidence=confidence,
                validation_score=validation_enfant['score']
            )
            
            filiations.append(relation)
            self.stats['relations_validees'] += 1
        
        return filiations
    
    def _pre_clean_text(self, text: str) -> str:
        text = re.sub(r'ARCHIVES\s+DU\s+CALVADOS[^,]*,\s*', '', text, flags=re.IGNORECASE)
        
        for error, correction in self.corrections_ocr_strictes.items():
            text = text.replace(error, correction)
            if error != correction:
                self.stats['corrections_ocr_appliquees'] += 1
        
        return text
    
    def _validate_child_ultra_strict(self, enfant: str) -> Dict[str, Any]:
        cache_key = enfant.lower().strip()
        if cache_key in self.cache_validation:
            return self.cache_validation[cache_key]
        
        result = {'valid': False, 'reason': '', 'score': 0.0}
        
        if len(enfant.strip()) < 4:
            result['reason'] = 'Trop court (< 4 caractères)'
            self.cache_validation[cache_key] = result
            return result
        
        for pattern in self.patterns_rejet_absolu:
            if pattern.search(enfant):
                result['reason'] = f'Pattern rejeté: {pattern.pattern[:30]}...'
                self.cache_validation[cache_key] = result
                return result
        
        enfant_lower = enfant.lower()
        for prefix in self.prefixes_interdits:
            if enfant_lower.startswith(prefix.lower()):
                result['reason'] = f'Préfixe interdit: {prefix}'
                self.cache_validation[cache_key] = result
                return result
        
        words = enfant.split()
        for word in words:
            if word.lower() in self.mots_interdits:
                result['reason'] = f'Mot interdit: {word}'
                self.cache_validation[cache_key] = result
                return result
        
        if not self._is_valid_first_name_structure(words[0] if words else ''):
            result['reason'] = f'Premier mot invalide: {words[0] if words else ""}'
            self.cache_validation[cache_key] = result
            return result
        
        score = self._calculate_name_quality_score(enfant, words)
        
        if score < 0.6:
            result['reason'] = f'Score qualité trop faible: {score:.2f}'
            self.cache_validation[cache_key] = result
            return result
        
        result = {'valid': True, 'reason': 'Validé', 'score': score}
        self.cache_validation[cache_key] = result
        return result
    
    def _is_valid_first_name_structure(self, first_word: str) -> bool:
        if not first_word or len(first_word) < 3:
            return False
        
        corrected = self.corrections_ocr_strictes.get(first_word, first_word)
        
        if corrected in self.prenoms_masculins or corrected in self.prenoms_feminins:
            return True
        
        if re.match(r'^[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]{2,}$', corrected):
            return True
        
        return False
    
    def _calculate_name_quality_score(self, enfant: str, words: List[str]) -> float:
        score = 0.2
        
        if 2 <= len(words) <= 4:
            score += 0.2
        
        first_word = words[0] if words else ''
        corrected_first = self.corrections_ocr_strictes.get(first_word, first_word)
        
        if corrected_first in self.prenoms_masculins or corrected_first in self.prenoms_feminins:
            score += 0.4
        
        if len(words) >= 2:
            last_word = words[-1]
            if last_word in self.noms_famille_valides:
                score += 0.2
        
        if re.search(r'[0-9]', enfant):
            score -= 0.3
        
        if re.search(r'[^a-zA-ZÀ-ÿ\s\-\']', enfant):
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _apply_strict_ocr_corrections(self, name: str) -> str:
        corrected = name
        for error, correction in self.corrections_ocr_strictes.items():
            if error in corrected:
                corrected = corrected.replace(error, correction)
        
        corrected = ' '.join(corrected.split())
        
        return corrected
    
    def _parse_parents_ultra_strict(self, parents_str: str) -> Dict[str, str]:
        parents = {'pere': '', 'mere': ''}
        
        cleaned = re.sub(r'^(feu\s+|défunt\s+|défunte\s+)', '', parents_str, flags=re.IGNORECASE)
        
        cleaned = self._apply_strict_ocr_corrections(cleaned)
        
        if ' et ' in cleaned.lower():
            parts = re.split(r'\s+et\s+(?:de\s+)?', cleaned, flags=re.IGNORECASE)
            if len(parts) >= 2:
                parents['pere'] = parts[0].strip()
                parents['mere'] = parts[1].strip()
        else:
            parents['pere'] = cleaned.strip()
        
        return parents
    
    def _final_validation(self, enfant: str, parents: Dict[str, str]) -> bool:
        if not enfant or len(enfant.strip()) < 4:
            return False
        
        if not parents.get('pere') and not parents.get('mere'):
            return False
        
        if enfant.lower() == parents.get('pere', '').lower():
            return False
        
        if enfant.lower() == parents.get('mere', '').lower():
            return False
        
        return True
    
    def _calculate_strict_confidence(self, enfant: str, parents: Dict[str, str]) -> float:
        confidence = 0.4
        
        words_enfant = enfant.split()
        if len(words_enfant) >= 2:
            confidence += 0.2
        
        first_word = words_enfant[0] if words_enfant else ''
        if first_word in self.prenoms_masculins or first_word in self.prenoms_feminins:
            confidence += 0.2
        
        pere = parents.get('pere', '')
        mere = parents.get('mere', '')
        
        if pere and len(pere.split()) >= 2:
            confidence += 0.1
        
        if mere and len(mere.split()) >= 2:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _categorize_rejection(self, reason: str):
        if 'pattern rejeté' in reason.lower():
            self.stats['rejets_pattern_absolu'] += 1
        elif 'mot interdit' in reason.lower():
            self.stats['rejets_mot_interdit'] += 1
        elif 'premier mot invalide' in reason.lower():
            self.stats['rejets_prenom_invalide'] += 1
        elif 'trop court' in reason.lower():
            self.stats['rejets_longueur'] += 1
        else:
            self.stats['rejets_validation'] += 1
    
    def export_to_legacy_format(self, relations: List[ValidatedRelation]) -> List[Dict[str, Any]]:
        filiations_csv = []
        
        for i, relation in enumerate(relations, 1):
            filiations_csv.append({
                'ID': i,
                'Enfant': relation.entities.get('enfant', ''),
                'Père': relation.entities.get('pere', ''),
                'Mère': relation.entities.get('mere', ''),
                'Source_Texte': relation.source_text,
                'Position_Debut': relation.position[0],
                'Position_Fin': relation.position[1],
                'Confiance': round(relation.confidence, 2)
            })
        
        return filiations_csv
    
    def get_processing_stats(self) -> Dict[str, Any]:
        total_examines = self.stats['candidats_examines']
        
        return {
            'candidats_examines': total_examines,
            'relations_validees': self.stats['relations_validees'],
            'taux_validation': (self.stats['relations_validees'] / max(total_examines, 1)) * 100,
            'rejets_detail': {
                'pattern_absolu': self.stats['rejets_pattern_absolu'],
                'mot_interdit': self.stats['rejets_mot_interdit'],
                'prenom_invalide': self.stats['rejets_prenom_invalide'],
                'longueur': self.stats['rejets_longueur'],
                'validation_finale': self.stats['rejets_validation']
            },
            'corrections_ocr': self.stats['corrections_ocr_appliquees']
        }

def create_ultra_strict_parser(text_parser=None):
    return UltraStrictGenealogyParser(text_parser)

def process_text_ultra_strict(text: str, parser: UltraStrictGenealogyParser = None) -> Dict[str, Any]:
    if parser is None:
        parser = UltraStrictGenealogyParser()
    
    relations = parser.extract_filiations_ultra_strict(text)
    filiations_csv = parser.export_to_legacy_format(relations)
    stats = parser.get_processing_stats()
    
    return {
        'filiations': filiations_csv,
        'statistiques': stats,
        'qualite_estimee': 'Excellente' if stats['taux_validation'] > 80 else 
                          'Bonne' if stats['taux_validation'] > 60 else 'Moyenne'
    }