import re
import logging
from typing import Dict, List, Optional, Tuple, Set
import hashlib
from functools import lru_cache
from collections import Counter, defaultdict
from config.settings import ParserConfig

class TextParser:
    """Parser de texte avec corrections OCR intégrées pour registres paroissiaux"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Statistiques enrichies
        self.stats = {
            'texts_processed': 0,
            'total_chars_processed': 0,
            'ocr_corrections_applied': 0,
            'abbreviations_expanded': 0,
            'segments_extracted': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Configuration du cache optimisé
        self._normalize_cache = {}
        self._ocr_cache = {}
        self._cache_max_size = 1000
        self._cache_hit_threshold = 3  # Seuil pour garder en cache
        
        # Dictionnaire de corrections OCR découvertes
        self.corrections_ocr = {
            # === ERREURS "Aii" SYSTÉMATIQUES ===
            'Aiicelle': 'Ancelle',
            'Aiiber': 'Auber', 
            'Aiieelle': 'Ancelle',
            'Aiigotin': 'Antigotin',
            'Aiimont': 'Aumont',
            'Aiil': 'Anil',
            'Aiine-': 'Anne-',
            'Aiivray': 'Auvray',
            'Aii-': 'Anne',
            
            # === ERREURS TRANSCRIPTION COURANTES ===
            'Jaeques': 'Jacques',
            'Franteois': 'François',
            'Catlierhie': 'Catherine',
            'Guillaïune': 'Guillaume',
            'Iagdeleine': 'Madeleine',
            'Pi-ançois': 'François',
            'Nicollas': 'Nicolas',
            'Toussaiut': 'Toussaint',
            'Muiiie': 'Marie',
            'Jlagdeleiue': 'Madeleine',
            'Cliarles': 'Charles',
            'Jeau': 'Jean',
            'Vietoire': 'Victoire',
            
            # === NOMS TRONQUÉS IDENTIFIÉS ===
            'Ade-': 'Adeline',
            'Marie- An': 'Marie-Anne',
            'Adrienne-': 'Adrienne',
            'Afigus-': 'Affiches',
            'Agnès-': 'Agnès',
            'Amfr-': 'Amfreville',
            'An-': 'Anne',
            'Ame-': 'Amélie',
            'Alal-': 'Alain',
            'Alau-': 'Alain',
            'Alexandre-': 'Alexandre',
            'Aimée-': 'Aimée',
            'Aimép': 'Aimée',
            
            # === CORRECTIONS ADDITIONNELLES ===
            'Padelaine': 'Madeleine',
            'Cardinne': 'Catherine',
            'Gabi-iel': 'Gabriel',
            'Eléonore': 'Éléonore'
        }
        
        # Abréviations spécifiques aux registres paroissiaux français
        self.abbreviations_paroissiaux = {
            # Actes et cérémonies
            'bapt.': 'baptême',
            'Bapt.': 'Baptême',
            'mar.': 'mariage',
            'Mar.': 'Mariage',
            'inh.': 'inhumation',
            'Inh.': 'Inhumation',
            'sép.': 'sépulture',
            'Sép.': 'Sépulture',
            'ondoy.': 'ondoyé',
            'adm.': 'administration',
            
            # Titres et statuts
            'sr': 'sieur',
            'Sr': 'Sieur',
            'sgr': 'seigneur',
            'Sgr': 'Seigneur', 
            'éc.': 'écuyer',
            'Éc.': 'Écuyer',
            'ec.': 'écuyer',
            'Ec.': 'Écuyer',
            'pbre': 'prêtre',
            'Pbre': 'Prêtre',
            'curé': 'curé',
            'Curé': 'Curé',
            
            # Relations familiales
            'veuf.': 'veuf',
            'veuve.': 'veuve',
            'vve': 'veuve',
            'Vve': 'Veuve',
            
            # Mois
            'janv.': 'janvier',
            'févr.': 'février', 
            'fév.': 'février',
            'sept.': 'septembre',
            'oct.': 'octobre',
            'nov.': 'novembre',
            'déc.': 'décembre',
            'xbre': 'décembre',
            '7bre': 'septembre',
            '8bre': 'octobre',
            '9bre': 'novembre',
            '10bre': 'décembre',
            
            # Lieux et institutions
            'par.': 'paroisse',
            'Par.': 'Paroisse',
            'égl.': 'église',
            'Égl.': 'Église',
            'chap.': 'chapelle',
            'Chap.': 'Chapelle',
            'hosp.': 'hôpital',
            'Hosp.': 'Hôpital'
        }
        
        # Fusionner avec les abréviations de config
        self.all_abbreviations = {
            **getattr(config, 'abbreviations', {}),
            **self.abbreviations_paroissiaux
        }
        
        # Compilation des patterns pour performance
        self._compile_enhanced_patterns()
    
    def _compile_enhanced_patterns(self):
        """Compile les patterns de normalisation avec améliorations OCR"""
        
        # Patterns d'abréviations (existants)
        self.abbrev_patterns = {}
        for abbrev, full in self.all_abbreviations.items():
            escaped_abbrev = re.escape(abbrev)
            self.abbrev_patterns[abbrev] = re.compile(
                r'\b' + escaped_abbrev + r'\b', re.IGNORECASE
            )
        
        # Patterns OCR spécifiques
        self.ocr_patterns = {}
        for erreur, correction in self.corrections_ocr.items():
            escaped_erreur = re.escape(erreur)
            self.ocr_patterns[erreur] = re.compile(
                escaped_erreur, re.IGNORECASE
            )
        
        # Patterns de nettoyage améliorés pour registres paroissiaux
        self.cleaning_patterns = {
            # Corrections OCR communes
            'l_to_I': re.compile(r'\bl\b(?=[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß])'),  # l -> I devant majuscule
            'digit_to_letter': re.compile(r'\b1(?=[a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ])'),  # 1 -> l
            'zero_to_o': re.compile(r'\b0(?=[a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ])'),  # 0 -> o
            'rn_to_m': re.compile(r'rn(?=[aeiouàáâãäåæèéêëìíîïòóôõöùúûüý])'),  # rn -> m devant voyelle
            'cl_to_d': re.compile(r'cl(?=[aeiouàáâãäåæèéêëìíîïòóôõöùúûüý])'),  # cl -> d devant voyelle
            
            # Ligatures mal reconnues
            'ligature_fi': re.compile(r'ﬁ'),
            'ligature_fl': re.compile(r'ﬂ'),
            'ligature_ffi': re.compile(r'ﬃ'),
            'ligature_ffl': re.compile(r'ﬄ'),
            'ligature_oe': re.compile(r'œ'),
            
            # Caractères de ponctuation problématiques
            'quotes_normalize': re.compile(r'[""''`]'),
            'ellipsis_normalize': re.compile(r'…'),
            'em_dash_normalize': re.compile(r'—'),
            'en_dash_normalize': re.compile(r'–'),
            
            # Espaces et caractères de contrôle
            'control_chars': re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]'),
            'multiple_spaces': re.compile(r'\s+'),
            'space_punct': re.compile(r'\s+([,.;:!?])'),  # Espace avant ponctuation
            'punct_space': re.compile(r'([,.;:!?])\s*([a-zA-ZÀ-ÿ])'),  # Manque d'espace après ponctuation
        }
    
    def _create_cache_key(self, text: str, include_length: bool = True) -> str:
        """Crée une clé de cache optimisée"""
        try:
            # Inclure la longueur pour éviter les collisions
            content = f"{len(text)}:{text}" if include_length else text
            return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]  # Raccourcir pour économiser mémoire
        except Exception:
            return str(hash(text))[:16]
    
    def _manage_cache_size(self):
        """Gestion intelligente de la taille du cache"""
        
        if len(self._normalize_cache) > self._cache_max_size:
            # Stratégie LRU approximative : supprimer les entrées les moins utilisées
            # (Dans un vrai système, on utiliserait functools.lru_cache ou une vraie implémentation LRU)
            keys_to_remove = list(self._normalize_cache.keys())[:200]
            for key in keys_to_remove:
                self._normalize_cache.pop(key, None)
        
        if len(self._ocr_cache) > self._cache_max_size // 2:
            keys_to_remove = list(self._ocr_cache.keys())[:100]
            for key in keys_to_remove:
                self._ocr_cache.pop(key, None)
    
    @lru_cache(maxsize=500)
    def apply_ocr_corrections(self, text: str) -> Tuple[str, List[str]]:
        """
        Applique les corrections OCR avec cache et statistiques
        
        Returns:
            Tuple[str, List[str]]: (texte_corrigé, liste_corrections_appliquées)
        """
        if not text or len(text) < 2:
            return text, []
        
        corrected_text = text
        corrections_applied = []
        
        # 1. Corrections exactes (priorité haute)
        for erreur, correction in self.corrections_ocr.items():
            if erreur in corrected_text:
                corrected_text = corrected_text.replace(erreur, correction)
                corrections_applied.append(f"{erreur} → {correction}")
                self.stats['ocr_corrections_applied'] += 1
        
        # 2. Corrections par patterns OCR
        replacements = {
            'l_to_I': 'I',
            'digit_to_letter': 'l', 
            'zero_to_o': 'o',
            'rn_to_m': 'm',
            'cl_to_d': 'd'
        }
        
        for pattern_name, replacement in replacements.items():
            if pattern_name in self.cleaning_patterns:
                pattern = self.cleaning_patterns[pattern_name]
                new_text = pattern.sub(replacement, corrected_text)
                if new_text != corrected_text:
                    corrections_applied.append(f"Pattern {pattern_name}")
                    corrected_text = new_text
        
        # 3. Corrections de ligatures
        ligature_replacements = {
            'ligature_fi': 'fi',
            'ligature_fl': 'fl',
            'ligature_ffi': 'ffi',
            'ligature_ffl': 'ffl',
            'ligature_oe': 'oe'
        }
        
        for pattern_name, replacement in ligature_replacements.items():
            if pattern_name in self.cleaning_patterns:
                pattern = self.cleaning_patterns[pattern_name]
                new_text = pattern.sub(replacement, corrected_text)
                if new_text != corrected_text:
                    corrections_applied.append(f"Ligature {replacement}")
                    corrected_text = new_text
        
        return corrected_text, corrections_applied
    
    def normalize_text(self, text: str, apply_ocr_corrections: bool = True) -> Dict:
        """
        Normalisation complète du texte avec métadonnées
        
        Args:
            text: Texte à normaliser
            apply_ocr_corrections: Appliquer les corrections OCR
            
        Returns:
            Dict: {
                'normalized': str,
                'ocr_corrections': List[str],
                'abbreviations_expanded': List[str],
                'original_length': int,
                'normalized_length': int
            }
        """
        if not text:
            return {
                'normalized': '',
                'ocr_corrections': [],
                'abbreviations_expanded': [],
                'original_length': 0,
                'normalized_length': 0
            }
        
        # Vérifier le cache
        cache_key = self._create_cache_key(text)
        if cache_key in self._normalize_cache:
            self.stats['cache_hits'] += 1
            return self._normalize_cache[cache_key]
        
        self.stats['cache_misses'] += 1
        self.stats['texts_processed'] += 1
        self.stats['total_chars_processed'] += len(text)
        
        original_length = len(text)
        normalized = text
        ocr_corrections = []
        abbreviations_expanded = []
        
        # 1. Corrections OCR (si activées)
        if apply_ocr_corrections:
            normalized, ocr_corrections = self.apply_ocr_corrections(normalized)
        
        # 2. Expansion des abréviations
        for abbrev, pattern in self.abbrev_patterns.items():
            full_form = self.all_abbreviations[abbrev]
            new_text = pattern.sub(full_form, normalized)
            if new_text != normalized:
                abbreviations_expanded.append(f"{abbrev} → {full_form}")
                normalized = new_text
                self.stats['abbreviations_expanded'] += 1
        
        # 3. Nettoyage final
        normalized = self._clean_text_enhanced(normalized)
        
        # Créer le résultat
        result = {
            'normalized': normalized,
            'ocr_corrections': ocr_corrections,
            'abbreviations_expanded': abbreviations_expanded,
            'original_length': original_length,
            'normalized_length': len(normalized),
            'improvement_ratio': (len(ocr_corrections) + len(abbreviations_expanded)) / max(len(text.split()), 1)
        }
        
        # Mettre en cache
        self._manage_cache_size()
        self._normalize_cache[cache_key] = result
        
        return result
    
    def _clean_text_enhanced(self, text: str) -> str:
        """Nettoyage du texte amélioré pour registres paroissiaux"""
        
        cleaned = text
        
        # 1. Supprimer caractères de contrôle
        if 'control_chars' in self.cleaning_patterns:
            cleaned = self.cleaning_patterns['control_chars'].sub('', cleaned)
        
        # 2. Normaliser la ponctuation
        ponctuation_replacements = {
            'quotes_normalize': '"',
            'ellipsis_normalize': '...',
            'em_dash_normalize': '—',  # Garder les tirets longs pour la segmentation
            'en_dash_normalize': '–'
        }
        
        for pattern_name, replacement in ponctuation_replacements.items():
            if pattern_name in self.cleaning_patterns:
                cleaned = self.cleaning_patterns[pattern_name].sub(replacement, cleaned)
        
        # 3. Fixer l'espacement
        if 'multiple_spaces' in self.cleaning_patterns:
            cleaned = self.cleaning_patterns['multiple_spaces'].sub(' ', cleaned)
        
        # Fixer ponctuation mal espacée
        if 'space_punct' in self.cleaning_patterns:
            cleaned = self.cleaning_patterns['space_punct'].sub(r'\1', cleaned)
        
        if 'punct_space' in self.cleaning_patterns:
            cleaned = self.cleaning_patterns['punct_space'].sub(r'\1 \2', cleaned)
        
        # 4. Corrections spécifiques aux registres paroissiaux
        cleaned = self._fix_parish_specific_issues(cleaned)
        
        return cleaned.strip()
    
    def _fix_parish_specific_issues(self, text: str) -> str:
        """Corrections spécifiques aux registres paroissiaux"""
        
        fixes = {
            # Mots collés fréquents
            r'(\w)([A-Z][a-z])': r'\1 \2',  # motMot -> mot Mot
            
            # Corrections de ponctuation dans dates
            r'(\d+)\s*,\s*(\w+)\s*,\s*(\d+)': r'\1 \2 \3',  # "1, janvier, 1650" -> "1 janvier 1650"
            
            # Corrections dans les noms composés
            r'([a-z])-\s+([A-Z])': r'\1-\2',  # "Marie- Anne" -> "Marie-Anne"
            
            # Espacement autour des titres
            r'\b(sr|sgr|éc\.?|ec\.?)\s*([A-Z])': r'\1 \2',  # "srJean" -> "sr Jean"
            
            # Corrections dans les relations familiales
            r'\b(fils?|filles?)\s+d\s+': r'\1 de ',  # "fils d " -> "fils de "
            r'\b(épouse?|femme)\s+d\s+': r'\1 de ',  # "épouse d " -> "épouse de "
        }
        
        cleaned = text
        for pattern, replacement in fixes.items():
            cleaned = re.sub(pattern, replacement, cleaned)
        
        return cleaned
    
    def extract_segments(self, text: str, normalize_segments: bool = True) -> List[Dict]:
        """
        Extraction des segments améliorée avec normalisation optionnelle
        
        Args:
            text: Texte à segmenter
            normalize_segments: Normaliser chaque segment
            
        Returns:
            List[Dict]: Liste des segments avec métadonnées
        """
        segments = []
        
        # Normaliser le texte entier d'abord si demandé
        if normalize_segments:
            normalization_result = self.normalize_text(text)
            text_to_process = normalization_result['normalized']
        else:
            text_to_process = text
        
        # Découper par "—" selon spécification (améliorer la regex)
        raw_segments = re.split(r'\s*[—–]\s*', text_to_process)
        
        for i, segment in enumerate(raw_segments):
            segment = segment.strip()
            
            # Ignorer segments trop courts ou vides
            if len(segment) < 10:
                continue
            
            # Analyser le type de segment
            segment_info = self._analyze_segment(segment, i)
            
            # Ajouter métadonnées de normalisation si applicable
            if normalize_segments and i < len(raw_segments):
                segment_normalization = self.normalize_text(segment)
                segment_info.update({
                    'ocr_corrections_count': len(segment_normalization['ocr_corrections']),
                    'abbreviations_expanded_count': len(segment_normalization['abbreviations_expanded']),
                    'improvement_ratio': segment_normalization['improvement_ratio']
                })
            
            segments.append(segment_info)
            self.stats['segments_extracted'] += 1
        
        return segments
    
    def _analyze_segment(self, segment: str, index: int) -> Dict:
        """Analyse un segment pour déterminer son type et extraire des métadonnées"""
        
        segment_info = {
            'type': 'unknown',
            'content': segment,
            'index': index,
            'length': len(segment),
            'word_count': len(segment.split()),
            'date_patterns': [],
            'name_patterns': [],
            'act_type': None
        }
        
        # Détecter le type de segment
        # 1. Période (ex: "1643-1687", "1650-1660")
        if index == 0 and re.match(r'^\d{4}-\d{4}', segment):
            segment_info['type'] = 'period'
            segment_info['period_range'] = re.findall(r'\d{4}', segment)
            return segment_info
        
        # 2. Acte paroissial
        act_patterns = {
            'bapteme': r'\b(?:bapt[êe]?me?s?|baptis[ée]s?|ondoy[ée]s?)\b',
            'mariage': r'\b(?:mariages?|mar\.|épous[ée]s?|épousailles)\b', 
            'inhumation': r'\b(?:inhumations?|inh\.|sépultures?|sép\.|enterrements?)\b',
            'administration': r'\b(?:administrations?|adm\.|sacrements?)\b'
        }
        
        for act_type, pattern in act_patterns.items():
            if re.search(pattern, segment, re.IGNORECASE):
                segment_info['type'] = 'acte'
                segment_info['act_type'] = act_type
                break
        
        # Si pas identifié comme acte mais contient des noms et dates, probablement un acte
        if segment_info['type'] == 'unknown' and index > 0:
            date_count = len(re.findall(r'\b\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\b', segment, re.IGNORECASE))
            name_count = len(re.findall(r'\b[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+\b', segment))
            
            if date_count > 0 and name_count > 2:
                segment_info['type'] = 'acte'
                segment_info['act_type'] = 'inferred'
        
        # 3. Extraire patterns de dates
        date_patterns = re.findall(
            r'\b\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre|janv\.|févr\.|sept\.|oct\.|nov\.|déc\.)\s*,?\s*\d{4}?\b',
            segment, re.IGNORECASE
        )
        segment_info['date_patterns'] = date_patterns
        
        # 4. Extraire patterns de noms (approximatif)
        name_patterns = re.findall(
            r'\b[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)*\b',
            segment
        )
        segment_info['name_patterns'] = name_patterns[:10]  # Limiter pour éviter le bruit
        
        return segment_info
    
    def preprocess_large_text(self, text: str, chunk_size: int = 8000, overlap: int = 200) -> List[Dict]:
        """
        Préprocesse de gros textes par chunks avec chevauchement pour éviter les coupures
        
        Args:
            text: Texte à traiter
            chunk_size: Taille des chunks
            overlap: Chevauchement entre chunks
            
        Returns:
            List[Dict]: Chunks normalisés avec métadonnées
        """
        if len(text) <= chunk_size:
            normalization_result = self.normalize_text(text)
            return [{
                'chunk_index': 0,
                'chunk_start': 0,
                'chunk_end': len(text),
                **normalization_result
            }]
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # Définir la fin du chunk
            end = min(start + chunk_size, len(text))
            
            # Si ce n'est pas le dernier chunk, essayer de couper à un endroit approprié
            if end < len(text):
                # Chercher un point de coupure idéal dans les derniers 20% du chunk
                search_start = max(start + int(chunk_size * 0.8), start + 1)
                
                # Priorité 1: Fin de segment (—)
                last_segment_break = text.rfind('—', search_start, end)
                if last_segment_break > search_start:
                    end = last_segment_break
                else:
                    # Priorité 2: Fin de phrase
                    last_sentence = text.rfind('.', search_start, end)
                    if last_sentence > search_start:
                        end = last_sentence + 1
                    else:
                        # Priorité 3: Espace
                        last_space = text.rfind(' ', search_start, end)
                        if last_space > search_start:
                            end = last_space
            
            # Extraire le chunk
            chunk_text = text[start:end]
            
            # Normaliser le chunk
            normalization_result = self.normalize_text(chunk_text)
            
            chunk_info = {
                'chunk_index': chunk_index,
                'chunk_start': start,
                'chunk_end': end,
                'chunk_size': len(chunk_text),
                **normalization_result
            }
            
            chunks.append(chunk_info)
            
            # Préparer pour le chunk suivant avec chevauchement
            if end >= len(text):
                break
            
            start = max(end - overlap, start + 1)
            chunk_index += 1
        
        return chunks
    
    def get_enhanced_statistics(self) -> Dict:
        """Statistiques détaillées du parser"""
        
        return {
            **self.stats,
            'cache_efficiency': (
                self.stats['cache_hits'] / max(self.stats['cache_hits'] + self.stats['cache_misses'], 1)
            ) * 100,
            'avg_chars_per_text': (
                self.stats['total_chars_processed'] / max(self.stats['texts_processed'], 1)
            ),
            'ocr_correction_rate': (
                self.stats['ocr_corrections_applied'] / max(self.stats['texts_processed'], 1)
            ),
            'abbreviation_expansion_rate': (
                self.stats['abbreviations_expanded'] / max(self.stats['texts_processed'], 1)
            ),
            'cache_size': len(self._normalize_cache),
            'ocr_cache_size': len(self._ocr_cache),
            'known_abbreviations': len(self.all_abbreviations),
            'known_ocr_corrections': len(self.corrections_ocr)
        }
    
    def clear_caches(self):
        """Vide tous les caches pour libérer la mémoire"""
        self._normalize_cache.clear()
        self._ocr_cache.clear()
        # Vider aussi le cache LRU de apply_ocr_corrections
        self.apply_ocr_corrections.cache_clear()
    
    def validate_and_repair_text(self, text: str) -> Dict:
        """
        Validation et réparation complète d'un texte
        
        Returns:
            Dict avec diagnostic complet et texte réparé
        """
        diagnostic = {
            'original_length': len(text),
            'issues_detected': [],
            'repairs_applied': [],
            'quality_score': 0.0,
            'confidence': 0.0
        }
        
        if not text:
            return {**diagnostic, 'repaired_text': text}
        
        repaired = text
        
        # 1. Détecter problèmes OCR
        ocr_issues = 0
        for erreur in self.corrections_ocr.keys():
            if erreur in text:
                ocr_issues += 1
                diagnostic['issues_detected'].append(f"OCR error: {erreur}")
        
        # 2. Appliquer normalisation complète
        normalization_result = self.normalize_text(repaired)
        repaired = normalization_result['normalized']
        
        diagnostic['repairs_applied'].extend(normalization_result['ocr_corrections'])
        diagnostic['repairs_applied'].extend(normalization_result['abbreviations_expanded'])
        
        # 3. Calculer score de qualité
        total_repairs = len(normalization_result['ocr_corrections']) + len(normalization_result['abbreviations_expanded'])
        diagnostic['quality_score'] = max(0.0, 100.0 - (total_repairs * 5))  # -5 points par réparation
        
        # 4. Calculer confiance
        if len(text.split()) > 0:
            diagnostic['confidence'] = max(0.5, 1.0 - (total_repairs / len(text.split())))
        else:
            diagnostic['confidence'] = 1.0
        
        diagnostic['repaired_text'] = repaired
        diagnostic['improvement_ratio'] = normalization_result['improvement_ratio']
        
        return diagnostic

# === TESTS ET VALIDATION ===

if __name__ == "__main__":
    from config.settings import ParserConfig
    
    # Test du TextParser amélioré
    config = ParserConfig()
    parser = TextParser(config)
    
    # Texte de test avec erreurs OCR et abréviations
    test_text = """
    1643-1687 — 23 janv., bapt. de Jean Aiicelle, fils de Pierre et Catlierhie Aiimont; 
    parr.: Jaeques- Roch Adam, sr de la Granville; marr.: Marguerite Ade- — 
    15 févr., mar. de Franteois Guillaïune avec Marie- An, fille de Nicolas éc. et de Vietoire.
    """
    
    print("=== TEST TEXT PARSER AMÉLIORÉ ===\n")
    print(f"Texte original:\n{test_text}\n")
    
    # Test normalisation complète
    print("🔧 NORMALISATION COMPLÈTE:")
    result = parser.normalize_text(test_text)
    
    print(f"Texte normalisé:\n{result['normalized']}\n")
    
    if result['ocr_corrections']:
        print(f"✅ Corrections OCR appliquées ({len(result['ocr_corrections'])}):")
        for correction in result['ocr_corrections']:
            print(f"   - {correction}")
        print()
    
    if result['abbreviations_expanded']:
        print(f"📝 Abréviations développées ({len(result['abbreviations_expanded'])}):")
        for abbrev in result['abbreviations_expanded']:
            print(f"   - {abbrev}")
        print()
    
    # Test segmentation
    print("📋 SEGMENTATION:")
    segments = parser.extract_segments(test_text)
    
    for i, segment in enumerate(segments):
        print(f"Segment {i+1} ({segment['type']}):")
        print(f"   Contenu: {segment['content'][:80]}...")
        if segment.get('act_type'):
            print(f"   Type d'acte: {segment['act_type']}")
        if segment.get('date_patterns'):
            print(f"   Dates: {segment['date_patterns']}")
        print()
    
    # Test validation et réparation
    print("🔍 VALIDATION ET RÉPARATION:")
    diagnostic = parser.validate_and_repair_text(test_text)
    
    print(f"Score de qualité: {diagnostic['quality_score']:.1f}%")
    print(f"Confiance: {diagnostic['confidence']:.2f}")
    print(f"Problèmes détectés: {len(diagnostic['issues_detected'])}")
    print(f"Réparations appliquées: {len(diagnostic['repairs_applied'])}")
    
    # Statistiques finales
    print("\n📊 STATISTIQUES:")
    stats = parser.get_enhanced_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")