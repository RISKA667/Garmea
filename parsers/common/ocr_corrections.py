import re
import unicodedata
from typing import Dict, List, Tuple
from functools import lru_cache

class OCRCorrector:
    def __init__(self):
        self.corrections_map = {
            # Corrections existantes
            'Aiicelle': 'Ancelle', 'Aiiber': 'Auber', 'Aiigotin': 'Antigotin',
            'Aiimont': 'Aumont', 'Aiivray': 'Auvray', 'Aii-': 'Anne',
            'Aiil': 'Anil', 'Aiine-': 'Anne-', 'Aiieelle': 'Ancelle',
            'Jaeques': 'Jacques', 'Franteois': 'François', 'Catlierhie': 'Catherine',
            'Guillaïune': 'Guillaume', 'Nicollas': 'Nicolas', 'Muiiie': 'Marie',
            'Cliarles': 'Charles', 'Jeau': 'Jean', 'Vietoire': 'Victoire',
            'Iagdeleine': 'Madeleine', 'Pi-ançois': 'François', 'Toussaiut': 'Toussaint',
            'Jlagdeleiue': 'Madeleine', 'Marie- An': 'Marie-Anne', 'Ade-': 'Adeline',
            'Alexandre-': 'Alexandre', 'Adrienne-': 'Adrienne', 'Agnès-': 'Agnès',
            
            # Nouvelles corrections identifiées
            'Tliomas': 'Thomas', 'Iichel': 'Michel', 'Hetiri': 'Henri',
            'Charlotle': 'Charlotte', 'Qaiesnel': 'Quesnel', 'Dumesiiil': 'Dumesnil',
            'Lefè': 'Lefèvre', 'Jehan': 'Jean', 'Jacobum': 'Jacques',
            'Sancti': 'Saint', 'Martini': 'Martin', 'Reué': 'René',
            'Dbm': 'Dom', 'Pliil': 'Philippe', 'Luee': 'Luce',
            'Apvrille': 'Aurville', 'Apvi': 'Aubin', 'Tartvenu': 'Taillevenu',
            
            # Corrections de particules et mots courants
            'épous de': 'épouse de', 'fils d ': 'fils de ', 'fille d ': 'fille de ',
            'parr ain': 'parrain', 'marr aine': 'marraine', 'mar riage': 'mariage',
            'bapt ême': 'baptême', 'inhum ation': 'inhumation', 'décèz': 'décès',
            
            # Corrections typographiques courantes
            'ï': 'i', 'ÿ': 'y', 'œ': 'oe', 'æ': 'ae',
            
            # Corrections de noms tronqués identifiés
            'Dom Fi': 'Dom Philippe', 'Dom Et': 'Dom Étienne', 'Dom Th': 'Dom Thomas',
            'Dom Pr': 'Dom Pierre', 'Denis Per': 'Denis Perrin', 'Henri Bi': 'Henri Billard',
            'Gilles Ai': 'Gilles Aimé', 'Angélique Cha': 'Angélique Charles',
            
            # Corrections de noms de famille composés
            'Le Paultonnier': 'Le Pautonnier', 'Le Pautonnier': 'Le Pautonnier',
            'Pauthonnier': 'Pautonnier', 'Dumesiiil Le Bastard': 'Dumesnil Le Bastard',
            
            # Corrections d'erreurs de casse
            'le roy': 'Le Roy', 'le baron': 'Le Baron', 'le comte': 'Le Comte',
            'le barbier': 'Le Barbier', 'le boucher': 'Le Boucher',
            
            # Corrections de prénoms anciens
            'Jehan': 'Jean', 'Michiel': 'Michel', 'Guillemette': 'Guillemette',
            'Mahieu': 'Mathieu', 'Anthoine': 'Antoine', 'Robinet': 'Robin'
        }
        
        self.systematic_patterns = {
            # Patterns pour corrections automatiques
            r'\bii\b': 'n',  # ii souvent lu comme n
            r'\brn\b': 'm',  # rn souvent lu comme m  
            r'\bcl\b': 'cl', # cl parfois mal lu
            r'\bvv\b': 'w',  # vv pour w
            r'\bnn\b': 'n',  # nn double pour n simple
            r'\s+([,\.;:])': r'\1',  # Espaces avant ponctuation
            r'([,\.;:])\s*([A-Z])': r'\1 \2',  # Espaces après ponctuation
        }
        
        self.ligature_corrections = {
            'ﬁ': 'fi', 'ﬂ': 'fl', 'œ': 'oe', 'æ': 'ae',
            'ß': 'ss', 'ſ': 's', 'ĳ': 'ij'
        }
        
        self.context_corrections = {
            # Corrections selon contexte
            'sieur d e': 'sieur de', 'seigneur d e': 'seigneur de',
            'écuyer d e': 'écuyer de', 'fils d e': 'fils de',
            'fille d e': 'fille de', 'épouse d e': 'épouse de',
            'dame d e': 'dame de', 'comte d e': 'comte de'
        }
        
        self.name_completion_rules = {
            # Règles pour compléter les noms tronqués
            r'^Dom\s+[A-Z][a-z]{1,2}$': self._complete_religious_name,
            r'^[A-Z][a-z]+\s+[A-Z][a-z]{1,2}$': self._complete_family_name,
            r'^[A-Z][a-z]{1,2}$': self._complete_single_name
        }
        
        # Dictionnaire des prénoms complets pour complétion
        self.common_first_names = {
            'Th': 'Thomas', 'Ph': 'Philippe', 'Fr': 'François', 'Ch': 'Charles',
            'Gu': 'Guillaume', 'Ni': 'Nicolas', 'Pi': 'Pierre', 'Mi': 'Michel',
            'An': 'Antoine', 'Je': 'Jean', 'Ja': 'Jacques', 'Ma': 'Marie',
            'Ca': 'Catherine', 'Lo': 'Louis', 'He': 'Henri', 'Et': 'Étienne'
        }
        
        self.compiled_patterns = {
            pattern: re.compile(pattern) for pattern in self.systematic_patterns.keys()
        }
        
        self.stats = {
            'corrections_applied': 0, 'texts_processed': 0, 
            'ligatures_fixed': 0, 'patterns_fixed': 0,
            'names_completed': 0, 'context_corrections': 0
        }
    
    @lru_cache(maxsize=3000)
    def correct_text(self, text: str) -> str:
        if not text:
            return ""
        
        self.stats['texts_processed'] += 1
        original_text = text
        
        # Normalisation Unicode
        text = unicodedata.normalize('NFKD', text)
        
        # Corrections de ligatures
        for ligature, replacement in self.ligature_corrections.items():
            if ligature in text:
                text = text.replace(ligature, replacement)
                self.stats['ligatures_fixed'] += 1
        
        # Corrections directes
        for incorrect, correct in self.corrections_map.items():
            if incorrect in text:
                text = text.replace(incorrect, correct)
                self.stats['corrections_applied'] += 1
        
        # Corrections contextuelles
        for context_error, context_fix in self.context_corrections.items():
            if context_error in text.lower():
                text = re.sub(re.escape(context_error), context_fix, text, flags=re.IGNORECASE)
                self.stats['context_corrections'] += 1
        
        # Corrections par patterns
        for pattern_str, replacement in self.systematic_patterns.items():
            pattern = self.compiled_patterns[pattern_str]
            if pattern.search(text):
                text = pattern.sub(replacement, text)
                self.stats['patterns_fixed'] += 1
        
        # Nettoyage final
        text = self._final_cleanup(text)
        
        return text.strip()
    
    @lru_cache(maxsize=2000)
    def correct_name(self, name: str) -> str:
        corrected = self.correct_text(name)
        
        # Complétion des noms tronqués
        for pattern_str, completion_func in self.name_completion_rules.items():
            if re.match(pattern_str, corrected):
                completed = completion_func(corrected)
                if completed != corrected:
                    self.stats['names_completed'] += 1
                    return completed
        
        # Corrections spécifiques aux noms
        words = corrected.split()
        corrected_words = []
        
        for word in words:
            # Vérification dans le dictionnaire de corrections
            if word in self.corrections_map:
                corrected_words.append(self.corrections_map[word])
            # Gestion des noms avec tiret
            elif word.endswith('-') and len(word) > 3:
                base = word[:-1]
                # Vérification si le nom de base existe
                if any(full_name.startswith(base) for full_name in [
                    'Adeline', 'Alexandre', 'Adrienne', 'Agnès', 'Antoine', 'André'
                ]):
                    corrected_words.append(base)
                else:
                    corrected_words.append(word)
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def _complete_religious_name(self, name: str) -> str:
        """Complète les noms religieux tronqués comme 'Dom Th' -> 'Dom Thomas'"""
        parts = name.split()
        if len(parts) == 2 and parts[0].lower() == 'dom':
            short_name = parts[1]
            if short_name in self.common_first_names:
                return f"Dom {self.common_first_names[short_name]}"
        return name
    
    def _complete_family_name(self, name: str) -> str:
        """Complète les noms de famille tronqués"""
        parts = name.split()
        if len(parts) == 2:
            first_name, short_family = parts
            
            # Règles heuristiques pour compléter les noms de famille
            common_endings = {
                'Le': ['Le Roy', 'Le Comte', 'Le Baron', 'Le Boucher'],
                'Gu': ['Guérin', 'Guerard', 'Guillaume'],
                'Ma': ['Martin', 'Malherbe', 'Marchand'],
                'Ro': ['Robert', 'Roger', 'Robillard']
            }
            
            if short_family in common_endings:
                # Retourne le premier nom probable
                return f"{first_name} {common_endings[short_family][0]}"
        
        return name
    
    def _complete_single_name(self, name: str) -> str:
        """Complète les noms d'un seul caractère ou très courts"""
        if len(name) <= 2 and name in self.common_first_names:
            return self.common_first_names[name]
        return name
    
    def _final_cleanup(self, text: str) -> str:
        """Nettoyage final du texte"""
        # Suppression des espaces multiples
        text = re.sub(r'\s+', ' ', text)
        
        # Correction de la ponctuation
        text = re.sub(r'\s+([,.;:])', r'\1', text)
        text = re.sub(r'([,.;:])\s*([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß])', r'\1 \2', text)
        
        # Correction des guillemets et apostrophes
        text = re.sub(r'[""„"‚'']', '"', text)
        text = re.sub(r'[–—―]', '-', text)
        
        return text
    
    def suggest_corrections(self, text: str) -> List[Tuple[str, str, float]]:
        """Suggère des corrections avec score de confiance"""
        suggestions = []
        
        words = text.split()
        for word in words:
            # Détection d'erreurs OCR probables
            if self._has_ocr_errors(word):
                suggested = self._suggest_word_correction(word)
                if suggested != word:
                    confidence = self._calculate_correction_confidence(word, suggested)
                    suggestions.append((word, suggested, confidence))
        
        return suggestions
    
    def _has_ocr_errors(self, word: str) -> bool:
        """Détecte les erreurs OCR probables"""
        error_patterns = [
            r'[il1]{2,}',  # Séquences de i, l, 1
            r'rn(?=[a-z])',  # rn au milieu d'un mot
            r'cl(?=[aeiou])',  # cl suivi de voyelle
            r'[A-Z]{3,}(?![A-Z])',  # Plus de 2 majuscules consécutives
            r'[0-9]',  # Chiffres dans les noms
        ]
        
        return any(re.search(pattern, word) for pattern in error_patterns)
    
    def _suggest_word_correction(self, word: str) -> str:
        """Suggère une correction pour un mot"""
        # Vérification directe dans le dictionnaire
        if word in self.corrections_map:
            return self.corrections_map[word]
        
        # Application des règles de patterns
        corrected = word
        for pattern_str, replacement in self.systematic_patterns.items():
            pattern = self.compiled_patterns[pattern_str]
            corrected = pattern.sub(replacement, corrected)
        
        return corrected
    
    def _calculate_correction_confidence(self, original: str, corrected: str) -> float:
        """Calcule la confiance d'une correction"""
        if original in self.corrections_map:
            return 0.95
        
        # Distance d'édition simple
        distance = self._levenshtein_distance(original, corrected)
        max_len = max(len(original), len(corrected))
        
        if max_len == 0:
            return 0.0
        
        similarity = 1.0 - (distance / max_len)
        return min(0.9, max(0.3, similarity))
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calcule la distance de Levenshtein entre deux chaînes"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()
    
    def add_correction(self, incorrect: str, correct: str):
        """Ajoute une nouvelle correction"""
        self.corrections_map[incorrect] = correct
        self.correct_text.cache_clear()
        self.correct_name.cache_clear()
    
    def add_bulk_corrections(self, corrections: Dict[str, str]):
        """Ajoute plusieurs corrections en lot"""
        self.corrections_map.update(corrections)
        self.correct_text.cache_clear()
        self.correct_name.cache_clear()
    
    def export_corrections_log(self) -> Dict[str, any]:
        """Exporte un log des corrections pour analyse"""
        return {
            'total_corrections': len(self.corrections_map),
            'stats': self.stats,
            'most_common_corrections': sorted(
                self.corrections_map.items(), 
                key=lambda x: len(x[0]), 
                reverse=True
            )[:20]
        }

ocr_corrector = OCRCorrector()