import re
import numpy as np
from typing import Dict, List, Tuple, Set, Optional
from functools import lru_cache
from collections import defaultdict, Counter
import unicodedata

class TextParser:
    def __init__(self, config=None):
        self.config = config or {}
        self.corrections_ocr = self._init_corrections_ocr()
        self.abreviations = self._init_abreviations()
        self.prenoms_valides = self._init_prenoms_valides()
        self.noms_famille_valides = self._init_noms_famille()
        self.mots_parasites = self._init_mots_parasites()
        self.patterns_compiled = self._compile_patterns()
        self.cache_normalization = {}
        self.stats = {'corrections_appliquees': 0, 'validations_effectuees': 0}
    
    def _init_corrections_ocr(self) -> Dict[str, str]:
        return {
            'Jaeques': 'Jacques', 'jaeques': 'jacques', 'Jeau': 'Jean', 'jeau': 'jean',
            'Vietoire': 'Victoire', 'vietoire': 'victoire', 'Piern': 'Pierre', 'piern': 'pierre',
            'Franijois': 'François', 'franijois': 'françois', 'Fran<;ois': 'François',
            'Nieholas': 'Nicholas', 'nieholas': 'nicholas', 'Miehel': 'Michel', 'miehel': 'michel',
            'Guillauine': 'Guillaume', 'guillauine': 'guillaume', 'Anthoiiie': 'Antoine',
            'Cathcrine': 'Catherine', 'cathcrine': 'catherine', 'Marguerilc': 'Marguerite',
            'Franijoise': 'Françoise', 'franijoise': 'françoise', 'Madelciue': 'Madeleine',
            'Jeaiine': 'Jeanne', 'jeaiine': 'jeanne', 'Louisc': 'Louise', 'louisc': 'louise',
            'Aehard': 'Achard', 'aehard': 'achard', 'Moriu': 'Morin', 'moriu': 'morin',
            'Dupoiit': 'Dupont', 'dupoiit': 'dupont', 'Le13lanc': 'Leblanc', 'le13lanc': 'leblanc',
            'Maraie': 'Marie', 'maraie': 'marie', 'Petiiot': 'Petiot', 'petiiot': 'petiot',
            'Benard': 'Bénard', 'benard': 'bénard', 'Jacquess': 'Jacques', 'jacquess': 'jacques',
            'Gilless': 'Gilles', 'gilless': 'gilles', 'Cilles': 'Gilles', 'cilles': 'gilles',
            'atherine': 'Catherine', 'Cathe rine': 'Catherine', 'arie': 'Marie',
            'arie Franeoise': 'Marie Françoise', 'arie Françoise': 'Marie Françoise',
            'ilarguerite': 'Marguerite', 'ilesnage': 'Mesnage', 'ilares cot': 'Marescot',
            'Phi lippe': 'Philippe', 'phi lippe': 'philippe', 'Pier re': 'Pierre',
            'Jac ques': 'Jacques', 'jac ques': 'jacques', 'Chai les': 'Charles',
            'Bé rot': 'Bérot', 'bé rot': 'bérot', 'Bo rel': 'Borel', 'bo rel': 'borel',
            'Bou vet': 'Bouvet', 'bou vet': 'bouvet', 'Béuédic': 'Bénédic',
            'Coliu': 'Colin', 'coliu': 'colin', 'Duce lier': 'Ducelier',
            'LechevaUier': 'Le Chevallier', 'ains': 'marraines', 'aine': 'marraine',
            'ais': 'Marais', 'ai nes': 'marraines', 'aie': 'Marie',
            'ans': 'Jean', 'aas': 'Jean', 'alle': 'Anne', 'abbé': 'Abbé',
            'adjugé': '', 'aiorel': '', 'assistée': '', 'aumerey': '',
            'feu': 'feu', 'défunt': 'défunt', 'défunte': 'défunte', 'veuve': 'veuve',
            'épouse': 'épouse', 'époux': 'époux', 'fils': 'fils', 'fille': 'fille',
            'parrain': 'parrain', 'marraine': 'marraine', 'témoin': 'témoin', 'témoins': 'témoins',
            'sieur': 'sieur', 'dame': 'dame', 'messire': 'messire', 'demoiselle': 'demoiselle',
            'monsieur': 'monsieur', 'madame': 'madame', 'mademoiselle': 'mademoiselle',
            'maître': 'maître', 'maîtresse': 'maîtresse', 'seigneur': 'seigneur',
            'baptême': 'baptême', 'mariage': 'mariage', 'inhumation': 'inhumation',
            'sépulture': 'sépulture', 'décès': 'décès', 'naissance': 'naissance',
            'présent': 'présent', 'présente': 'présente', 'absent': 'absent', 'absente': 'absente',
            'bapL': 'baptême', 'bapt': 'baptême', 'dessusd': 'dessus'
        }
    
    def _init_abreviations(self) -> Dict[str, str]:
        return {
            'bapt.': 'baptême', 'bapt': 'baptême', 'bap.': 'baptême', 'bap': 'baptême',
            'mar.': 'mariage', 'mar': 'mariage', 'inh.': 'inhumation', 'inh': 'inhumation',
            'sép.': 'sépulture', 'sép': 'sépulture', 'déc.': 'décès', 'déc': 'décès',
            'sr': 'sieur', 'sr.': 'sieur', 'dame': 'dame', 'dlle': 'demoiselle',
            'mlle': 'mademoiselle', 'me': 'maître', 'mme': 'madame', 'mr': 'monsieur',
            'janv.': 'janvier', 'févr.': 'février', 'mars': 'mars', 'avr.': 'avril',
            'mai': 'mai', 'juin': 'juin', 'juil.': 'juillet', 'août': 'août',
            'sept.': 'septembre', 'oct.': 'octobre', 'nov.': 'novembre', 'déc.': 'décembre',
            'St': 'Saint', 'Ste': 'Sainte', 'St.': 'Saint', 'Ste.': 'Sainte'
        }
    
    def _init_prenoms_valides(self) -> Set[str]:
        prenoms_masculins = {
            'Jean', 'Pierre', 'Jacques', 'Nicolas', 'François', 'Louis', 'Antoine',
            'Michel', 'Guillaume', 'Charles', 'Philippe', 'Gabriel', 'Thomas',
            'André', 'Claude', 'Henri', 'Paul', 'Denis', 'Étienne', 'Martin',
            'Barthélemy', 'Laurent', 'Julien', 'Gilles', 'Robert', 'Christophe',
            'Mathurin', 'Noël', 'Olivier', 'Simon', 'Vincent', 'Yves', 'Alain',
            'Bernard', 'Gérard', 'Marcel', 'Maurice', 'Roger', 'Alexandre',
            'Adrien', 'Alexis', 'Georges', 'Joseph', 'Marin', 'Daniel', 'Léonard',
            'Gaspard', 'Augustin', 'Dominique', 'Sébastien', 'Mathieu', 'Luc',
            'Marc', 'Matthieu', 'Roch', 'Tanneguy', 'Richard', 'Pascal', 'Abbé'
        }
        prenoms_feminins = {
            'Anne', 'Marie', 'Françoise', 'Catherine', 'Marguerite', 'Jeanne',
            'Elisabeth', 'Louise', 'Madeleine', 'Antoinette', 'Geneviève',
            'Suzanne', 'Renée', 'Nicole', 'Monique', 'Brigitte', 'Sylvie',
            'Charlotte', 'Isabelle', 'Henriette', 'Victoire', 'Gabrielle',
            'Hélène', 'Jacqueline', 'Ursule', 'Thérèse', 'Angélique',
            'Eulalie', 'Barbe', 'Perrine', 'Robine', 'Colombe', 'Perrette'
        }
        return prenoms_masculins | prenoms_feminins
    
    def _init_noms_famille(self) -> Set[str]:
        return {
            'Dupont', 'Martin', 'Bernard', 'Thomas', 'Petit', 'Robert', 'Richard',
            'Durand', 'Dubois', 'Moreau', 'Laurent', 'Simon', 'Michel', 'Lefebvre',
            'Le Boucher', 'Le Chevallier', 'Le Cordier', 'Costart', 'Georges',
            'Denis', 'Colin', 'Bénard', 'Auvray', 'Bazire', 'Bouvet', 'Bouet',
            'Morin', 'Fouques', 'Ancellé', 'Banquet', 'Patey', 'Chéron', 'Adam',
            'Adeline', 'Achard', 'Acher', 'Accard', 'Abher', 'Acaid', 'Acard',
            'Daumesnil', 'Delaunay', 'Frenier', 'Grimoult', 'Huet', 'Mesnage',
            'Pierrepont', 'Violette', 'Guesdon', 'Malbran', 'Jourdaine'
        }
    
    def _init_mots_parasites(self) -> Set[str]:
        return {
            'ans', 'aine', 'ais', 'ai', 'a', 'le', 'la', 'les', 'de', 'du', 'des',
            'et', 'en', 'un', 'une', 'ce', 'cette', 'ces', 'sur', 'dans', 'pour',
            'avec', 'sans', 'par', 'vers', 'chez', 'sous', 'avant', 'après',
            'pendant', 'depuis', 'jusqu', 'jusque', 'malgré', 'selon', 'contre',
            'entre', 'parmi', 'durant', 'moyennant', 'nonobstant', 'hormis',
            'excepté', 'sauf', 'outre', 'suivant', 'touchant', 'concernant',
            'été', 'présenté', 'fonds', 'baptême', 'ancien', 'lieutenant',
            'dra', 'gons', 'adjugé', 'Jeanne', 'fermier', 'comte', 'archives',
            'du', 'calvados', 'bapt', 'baptême', 'contrat', 'autre', 'assistée',
            'aumerey', 'août', 'ard', 'ar', 'aas', 'alle', 'abbé', 'aiorel',
            'capitaine', 'carabiniers', 'chevalier', 'commissaire', 'chirurgien',
            'curé', 'bourgeois', 'noble', 'homme', 'dame', 'messire', 'sieur'
        }
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        return {
            'nom_complet': re.compile(r'\b([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+(?:[-\s][A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+)*)\b'),
            'correction_tirets': re.compile(r'([a-z])-\s*([a-z])'),
            'correction_espaces': re.compile(r'\s+'),
            'caracteres_invalides': re.compile(r'[^\w\s\-\'\.,;:()àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]'),
            'mots_colles': re.compile(r'([a-z])([A-Z])'),
            'ponctuation_collee': re.compile(r'([.,;:])([A-Za-z])'),
            'ligatures': re.compile(r'[ﬁﬂœæ]'),
            'fragments_suspects': re.compile(r'\b(ans|aine|ais|ai|a|aas|alle|abbé|aiorel|ard|ar|août|aumerey)\b', re.IGNORECASE),
            'titres_interdits': re.compile(r'\b(archives|du|calvados|bapt|baptême|contrat|autre|assistée|capitaine|carabiniers|chevalier|commissaire|chirurgien|curé|bourgeois|noble|homme|dame|messire|sieur)\b', re.IGNORECASE)
        }
    
    @lru_cache(maxsize=10000)
    def normalize_text(self, text: str) -> Dict[str, any]:
        if text in self.cache_normalization:
            return self.cache_normalization[text]
        
        if not text or len(text.strip()) < 2:
            return {'normalized': text, 'ocr_corrections': [], 'abbreviations_expanded': [], 'improvement_ratio': 1.0}
        
        original_text = text
        corrections_applied = []
        abbreviations_expanded = []
        
        text = self._clean_basic_artifacts(text)
        text, ocr_fixes = self._apply_ocr_corrections_vectorized(text)
        corrections_applied.extend(ocr_fixes)
        text, abbrev_fixes = self._expand_abbreviations_vectorized(text)
        abbreviations_expanded.extend(abbrev_fixes)
        text = self._normalize_spacing_and_punctuation(text)
        text = self._remove_parasitic_elements(text)
        
        improvement_ratio = len(text) / max(len(original_text), 1)
        
        result = {
            'normalized': text.strip(),
            'ocr_corrections': corrections_applied,
            'abbreviations_expanded': abbreviations_expanded,
            'improvement_ratio': improvement_ratio
        }
        
        self.cache_normalization[text] = result
        self.stats['corrections_appliquees'] += len(corrections_applied)
        
        return result
    
    def _clean_basic_artifacts(self, text: str) -> str:
        text = self.patterns_compiled['ligatures'].sub(
            lambda m: {'ﬁ': 'fi', 'ﬂ': 'fl', 'œ': 'oe', 'æ': 'ae'}[m.group()], text
        )
        text = self.patterns_compiled['correction_tirets'].sub(r'\1\2', text)
        text = self.patterns_compiled['mots_colles'].sub(r'\1 \2', text)
        text = self.patterns_compiled['ponctuation_collee'].sub(r'\1 \2', text)
        text = self.patterns_compiled['caracteres_invalides'].sub(' ', text)
        return text
    
    def _apply_ocr_corrections_vectorized(self, text: str) -> Tuple[str, List[str]]:
        corrections_applied = []
        words = text.split()
        
        corrected_words = []
        for word in words:
            original_word = word
            word_clean = re.sub(r'[^\w\-\']', '', word).strip()
            
            if word_clean in self.corrections_ocr:
                correction = self.corrections_ocr[word_clean]
                if correction:
                    corrected_word = word.replace(word_clean, correction)
                    corrected_words.append(corrected_word)
                    corrections_applied.append(f"{original_word} → {corrected_word}")
                else:
                    pass
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words), corrections_applied
    
    def _expand_abbreviations_vectorized(self, text: str) -> Tuple[str, List[str]]:
        abbreviations_expanded = []
        words = text.split()
        
        expanded_words = []
        for word in words:
            original_word = word
            word_clean = re.sub(r'[^\w\.]', '', word).strip().lower()
            
            if word_clean in self.abreviations:
                expanded_word = word.replace(word_clean, self.abreviations[word_clean])
                expanded_words.append(expanded_word)
                abbreviations_expanded.append(f"{original_word} → {expanded_word}")
            else:
                expanded_words.append(word)
        
        return ' '.join(expanded_words), abbreviations_expanded
    
    def _normalize_spacing_and_punctuation(self, text: str) -> str:
        text = self.patterns_compiled['correction_espaces'].sub(' ', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r'([.,;:])([A-Za-z])', r'\1 \2', text)
        text = re.sub(r'\s+([.,;:])', r'\1', text)
        return text
    
    def _remove_parasitic_elements(self, text: str) -> str:
        words = text.split()
        filtered_words = []
        
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word).lower()
            if word_clean not in self.mots_parasites and len(word_clean) > 1:
                if not self.patterns_compiled['fragments_suspects'].search(word):
                    if not self.patterns_compiled['titres_interdits'].search(word):
                        filtered_words.append(word)
        
        return ' '.join(filtered_words)
    
    def extract_names_with_validation(self, text: str) -> List[Dict[str, any]]:
        normalized_result = self.normalize_text(text)
        normalized_text = normalized_result['normalized']
        
        names_found = []
        matches = self.patterns_compiled['nom_complet'].finditer(normalized_text)
        
        for match in matches:
            name_candidate = match.group(1).strip()
            validation_result = self._validate_name_structure(name_candidate)
            
            if validation_result['is_valid']:
                names_found.append({
                    'nom_complet': name_candidate,
                    'prenoms': validation_result['prenoms'],
                    'nom_famille': validation_result['nom_famille'],
                    'confiance': validation_result['confidence'],
                    'position': match.span(),
                    'source_text': match.group(0)
                })
        
        return self._deduplicate_names(names_found)
    
    def _validate_name_structure(self, name_candidate: str) -> Dict[str, any]:
        self.stats['validations_effectuees'] += 1
        
        if not name_candidate or len(name_candidate.strip()) < 3:
            return {'is_valid': False, 'confidence': 0.0}
        
        words = name_candidate.split()
        if len(words) < 1:
            return {'is_valid': False, 'confidence': 0.0}
        
        first_word = words[0]
        if first_word.lower() in self.mots_parasites:
            return {'is_valid': False, 'confidence': 0.0}
        
        if len(first_word) < 3:
            return {'is_valid': False, 'confidence': 0.0}
        
        prenoms = []
        nom_famille = None
        confidence = 0.5
        
        for i, word in enumerate(words):
            word_clean = re.sub(r'[^\w]', '', word)
            
            if word_clean in self.prenoms_valides:
                prenoms.append(word)
                confidence += 0.2
            elif word_clean in self.noms_famille_valides and i == len(words) - 1:
                nom_famille = word
                confidence += 0.3
            elif i == len(words) - 1 and word.istitle() and len(word) > 2:
                nom_famille = word
                confidence += 0.1
            elif word.istitle() and len(word) > 2:
                prenoms.append(word)
                confidence += 0.1
        
        if not prenoms or not nom_famille:
            if len(words) == 1 and words[0] in self.prenoms_valides:
                prenoms = [words[0]]
                nom_famille = ""
                confidence = 0.7
            else:
                return {'is_valid': False, 'confidence': 0.0}
        
        confidence = min(confidence, 1.0)
        
        return {
            'is_valid': confidence > 0.6,
            'prenoms': prenoms,
            'nom_famille': nom_famille,
            'confidence': confidence
        }
    
    def _deduplicate_names(self, names: List[Dict]) -> List[Dict]:
        unique_names = {}
        
        for name_data in names:
            key = name_data['nom_complet'].lower().strip()
            key_normalized = re.sub(r'\s+', ' ', key)
            
            if key_normalized not in unique_names:
                unique_names[key_normalized] = name_data
            else:
                existing = unique_names[key_normalized]
                if name_data['confiance'] > existing['confiance']:
                    unique_names[key_normalized] = name_data
        
        return list(unique_names.values())
    
    def extract_relations_with_validation(self, text: str) -> List[Dict[str, any]]:
        normalized_result = self.normalize_text(text)
        normalized_text = normalized_result['normalized']
        
        relations = []
        
        filiation_patterns = [
            re.compile(r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+)*),?\s+fils\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][^,.;]+)', re.IGNORECASE),
            re.compile(r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+)*),?\s+fille\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][^,.;]+)', re.IGNORECASE)
        ]
        
        mariage_patterns = [
            re.compile(r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+)*),?\s+épouse\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][^,.;]+)', re.IGNORECASE),
            re.compile(r'mariage\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][^,.;]+)\s+avec\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][^,.;]+)', re.IGNORECASE)
        ]
        
        parrainage_patterns = [
            re.compile(r'parrain:\s*([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][^,.;]+)', re.IGNORECASE),
            re.compile(r'marraine:\s*([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][^,.;]+)', re.IGNORECASE)
        ]
        
        for pattern in filiation_patterns:
            for match in pattern.finditer(normalized_text):
                enfant = match.group(1).strip()
                parent = match.group(2).strip()
                
                if self._validate_relation_quality(enfant, parent):
                    relations.append({
                        'type': 'filiation',
                        'enfant': enfant,
                        'parent': parent,
                        'source_text': match.group(0),
                        'position': match.span(),
                        'confiance': self._calculate_relation_confidence(enfant, parent)
                    })
        
        for pattern in mariage_patterns:
            for match in pattern.finditer(normalized_text):
                epouse = match.group(1).strip()
                epoux = match.group(2).strip()
                
                if self._validate_relation_quality(epouse, epoux):
                    relations.append({
                        'type': 'mariage',
                        'epouse': epouse,
                        'epoux': epoux,
                        'source_text': match.group(0),
                        'position': match.span(),
                        'confiance': self._calculate_relation_confidence(epouse, epoux)
                    })
        
        for i, pattern in enumerate(parrainage_patterns):
            role = 'parrain' if i == 0 else 'marraine'
            for match in pattern.finditer(normalized_text):
                personne = match.group(1).strip()
                
                if self._validate_single_name_quality(personne):
                    relations.append({
                        'type': 'parrainage',
                        'role': role,
                        'personne': personne,
                        'source_text': match.group(0),
                        'position': match.span(),
                        'confiance': self._calculate_single_name_confidence(personne)
                    })
        
        return relations
    
    def _validate_relation_quality(self, name1: str, name2: str) -> bool:
        if not name1 or not name2:
            return False
        
        if len(name1.strip()) < 3 or len(name2.strip()) < 3:
            return False
        
        words1 = name1.split()
        words2 = name2.split()
        
        if len(words1) < 1 or len(words2) < 1:
            return False
        
        for word in words1 + words2:
            word_clean = re.sub(r'[^\w]', '', word).lower()
            if word_clean in self.mots_parasites:
                return False
        
        if words1[0].lower() in self.mots_parasites or words2[0].lower() in self.mots_parasites:
            return False
        
        return True
    
    def _validate_single_name_quality(self, name: str) -> bool:
        if not name or len(name.strip()) < 3:
            return False
        
        words = name.split()
        if len(words) < 1:
            return False
        
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word).lower()
            if word_clean in self.mots_parasites:
                return False
        
        return True
    
    def _calculate_relation_confidence(self, name1: str, name2: str) -> float:
        confidence = 0.5
        
        words1 = name1.split()
        words2 = name2.split()
        
        for word in words1 + words2:
            word_clean = re.sub(r'[^\w]', '', word)
            if word_clean in self.prenoms_valides:
                confidence += 0.15
            elif word_clean in self.noms_famille_valides:
                confidence += 0.2
        
        if len(words1) >= 2 and len(words2) >= 2:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_single_name_confidence(self, name: str) -> float:
        confidence = 0.4
        
        words = name.split()
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word)
            if word_clean in self.prenoms_valides:
                confidence += 0.2
            elif word_clean in self.noms_famille_valides:
                confidence += 0.25
        
        if len(words) >= 2:
            confidence += 0.15
        
        return min(confidence, 1.0)
    
    def analyze_text_quality(self, text: str) -> Dict[str, any]:
        if not text:
            return {'quality_score': 0.0, 'issues': ['Texte vide'], 'confidence': 0.0}
        
        total_chars = len(text)
        valid_chars = len(re.sub(r'[^\w\s\-\'\.,;:()àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]', '', text))
        
        ocr_errors = 0
        for error_pattern in self.corrections_ocr.keys():
            ocr_errors += len(re.findall(re.escape(error_pattern), text, re.IGNORECASE))
        
        parasitic_words = 0
        words = text.split()
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word).lower()
            if word_clean in self.mots_parasites:
                parasitic_words += 1
        
        quality_score = (valid_chars / total_chars) * 0.5
        quality_score += max(0, (len(words) - ocr_errors) / max(len(words), 1)) * 0.3
        quality_score += max(0, (len(words) - parasitic_words) / max(len(words), 1)) * 0.2
        
        issues = []
        if quality_score < 0.3:
            issues.append('Qualité OCR très faible')
        if ocr_errors > len(words) * 0.1:
            issues.append('Nombreuses erreurs OCR détectées')
        if parasitic_words > len(words) * 0.2:
            issues.append('Beaucoup de mots parasites')
        
        return {
            'quality_score': min(quality_score, 1.0),
            'issues': issues,
            'confidence': min(quality_score, 1.0),
            'ocr_errors': ocr_errors,
            'parasitic_words': parasitic_words,
            'total_words': len(words)
        }
    
    def get_statistics(self) -> Dict[str, any]:
        return {
            'corrections_appliquees': self.stats['corrections_appliquees'],
            'validations_effectuees': self.stats['validations_effectuees'],
            'cache_size': len(self.cache_normalization),
            'corrections_ocr_disponibles': len(self.corrections_ocr),
            'abreviations_disponibles': len(self.abreviations),
            'prenoms_references': len(self.prenoms_valides),
            'noms_famille_references': len(self.noms_famille_valides)
        }
    
    def clear_cache(self):
        self.cache_normalization.clear()
        self.stats = {'corrections_appliquees': 0, 'validations_effectuees': 0}