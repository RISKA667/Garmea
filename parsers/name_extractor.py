import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from functools import lru_cache
import hashlib
from config.settings import ParserConfig

class NameExtractor:
    def __init__(self, config: ParserConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.known_places = set(config.known_places)
        
        # Patterns compilés pour performance
        self.name_patterns = []
        self._compile_patterns()
        
        # Caches
        self._false_positives_cache = set()
        self._extraction_cache = {}
        self._validation_cache = {}
        
        # Statistiques
        self.stats = {
            'names_extracted': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'false_positives': 0,
            'validation_errors': 0
        }
    
    def _compile_patterns(self):
        """Compile les patterns regex pour capturer les noms complets"""
        try:
            self.name_patterns = [
                # Noms "Le + Nom" complets (ex: Guillaume Le Breton)
                re.compile(
                    r'\b([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)\s+'
                    r'(Le\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß]+)*)',
                    re.UNICODE
                ),
                
                # Noms avec particules "de" complets
                re.compile(
                    r'\b([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)\s+'
                    r'(de\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-Za-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)*)',
                    re.UNICODE
                ),
                
                ## A ajouter : Noms avec "des" complets


                # Noms avec "du" complets
                re.compile(
                    r'\b([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)\s+'
                    r'(du\s+[A-Za-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)',
                    re.UNICODE | re.IGNORECASE
                ),
                
                # Noms composés simples (en dernier pour éviter conflicts)
                re.compile(
                    r'\b([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]{2,})\s+'
                    r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]{2,})',
                    re.UNICODE
                )
            ]
            
            self.logger.debug(f"Patterns compilés: {len(self.name_patterns)} patterns")
            
        except Exception as e:
            self.logger.error(f"Erreur compilation patterns: {e}")
            self.name_patterns = [
                re.compile(r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b')
            ]
    
    def extract_complete_names(self, text: str) -> List[Dict]:
        """Extraction optimisée avec analyse contextuelle précise"""
        if not text or not isinstance(text, str):
            self.logger.warning(f"Texte invalide pour extraction: {type(text)}")
            return []
        
        # Créer une clé de cache stable
        cache_key = self._create_cache_key(text)
        
        # Vérifier le cache
        if cache_key in self._extraction_cache:
            self.stats['cache_hits'] += 1
            return self._extraction_cache[cache_key]
        
        self.stats['cache_misses'] += 1
        
        # NOUVEAU: Analyse en deux passes pour attribution précise
        persons = self._extract_with_precise_attribution(text)
        
        # Déduplication finale et validation
        persons = self._deduplicate_persons(persons)
        
        # Mise en cache du résultat
        self._extraction_cache[cache_key] = persons
        self.stats['names_extracted'] += len(persons)
        
        self.logger.debug(f"Extrait {len(persons)} personnes uniques du texte")
        return persons
    
    def _extract_with_precise_attribution(self, text: str) -> List[Dict]:
        """NOUVEAU: Extraction avec attribution précise des attributs"""
        persons = []
        found_names = set()
        
        try:
            # Analyser chaque segment du texte séparément
            segments = self._split_text_into_semantic_units(text)
            
            for segment in segments:
                segment_persons = self._extract_from_segment(segment, found_names)
                persons.extend(segment_persons)
            
            return persons
            
        except Exception as e:
            self.logger.error(f"Erreur extraction avec attribution précise: {e}")
            return []
    
    def _split_text_into_semantic_units(self, text: str) -> List[str]:
        """NOUVEAU: Divise le texte en unités sémantiques pour attribution précise"""
        # Diviser par les points-virgules et les phrases complètes
        units = []
        
        # Premier niveau: segments par —
        major_segments = re.split(r'\s*—\s*', text)
        
        for segment in major_segments:
            if len(segment.strip()) < 20:
                continue
            
            # Deuxième niveau: sous-segments par point-virgule
            sub_segments = re.split(r';\s*', segment)
            
            for sub_segment in sub_segments:
                if len(sub_segment.strip()) > 15:
                    units.append(sub_segment.strip())
        
        return units
    
    def _extract_from_segment(self, segment: str, found_names: Set[str]) -> List[Dict]:
        """NOUVEAU: Extraction depuis un segment avec attribution directe"""
        persons = []
        
        try:
            # Analyser les structures spécifiques d'abord
            specific_persons = self._extract_specific_structures(segment, found_names)
            persons.extend(specific_persons)
            
            # Puis extraction générale pour les noms restants
            general_persons = self._extract_remaining_names(segment, found_names)
            persons.extend(general_persons)
            
            return persons
            
        except Exception as e:
            self.logger.warning(f"Erreur extraction segment: {e}")
            return []
    
    def _extract_specific_structures(self, segment: str, found_names: Set[str]) -> List[Dict]:
        """NOUVEAU: Extraction des structures spécifiques avec attribution directe"""
        persons = []
        
        try:
            # Structure 1: "Nom, épouse de Nom" 
            epouse_pattern = r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?),\s+épouse\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s,]+?)(?:[,;]|$)'
            
            for match in re.finditer(epouse_pattern, segment, re.IGNORECASE):
                epouse_name = match.group(1).strip()
                mari_desc = match.group(2).strip()
                
                # Extraire le nom du mari des descriptions
                mari_name = self._extract_clean_name_from_description(mari_desc)
                
                if self._is_valid_full_name(epouse_name) and epouse_name not in found_names:
                    found_names.add(epouse_name)
                    prenom, nom = self._split_full_name(epouse_name)
                    
                    person_info = {
                        'nom_complet': epouse_name,
                        'prenom': prenom,
                        'nom': nom,
                        'context': segment,
                        'professions': [],  # Femme mariée = pas de profession propre dans ce contexte
                        'statut': None,     # Pas de titre propre
                        'terres': [],       # Pas de terres propres
                        'notable': False,
                        'relationships': [{'type': 'épouse', 'de': mari_name}]
                    }
                    persons.append(person_info)
                    
                # Traiter le mari avec ses attributs
                if mari_name and self._is_valid_full_name(mari_name) and mari_name not in found_names:
                    found_names.add(mari_name)
                    prenom_mari, nom_mari = self._split_full_name(mari_name)
                    
                    # Extraire les attributs du mari depuis sa description
                    mari_attributes = self._extract_attributes_from_description(mari_desc)
                    
                    person_info_mari = {
                        'nom_complet': mari_name,
                        'prenom': prenom_mari,
                        'nom': nom_mari,
                        'context': segment,
                        'professions': mari_attributes['professions'],
                        'statut': mari_attributes['statut'],
                        'terres': mari_attributes['terres'],
                        'notable': mari_attributes['notable'],
                        'relationships': [{'type': 'époux', 'de': epouse_name}]
                    }
                    persons.append(person_info_mari)
            
            # Structure 2: "Nom, fille de Nom et de Nom"
            fille_pattern = r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+),\s+fille\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s,]+?)(?:\s+et\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?))?[,;]'
            
            for match in re.finditer(fille_pattern, segment, re.IGNORECASE):
                fille_name = match.group(1).strip()
                pere_desc = match.group(2).strip() if match.group(2) else ""
                mere_name = match.group(3).strip() if match.group(3) else ""
                
                if self._is_valid_full_name(fille_name) and fille_name not in found_names:
                    found_names.add(fille_name)
                    prenom, nom = self._split_full_name(fille_name)
                    
                    # Extraire le nom propre du père
                    pere_name = self._extract_clean_name_from_description(pere_desc)
                    
                    person_info = {
                        'nom_complet': fille_name,
                        'prenom': prenom,
                        'nom': nom,
                        'context': segment,
                        'professions': [],
                        'statut': None,
                        'terres': [],
                        'notable': False,
                        'relationships': [
                            {'type': 'fille', 'pere': pere_name, 'mere': mere_name}
                        ]
                    }
                    persons.append(person_info)
                    
                    # Traiter le père avec ses attributs
                    if pere_name and self._is_valid_full_name(pere_name) and pere_name not in found_names:
                        found_names.add(pere_name)
                        prenom_pere, nom_pere = self._split_full_name(pere_name)
                        
                        pere_attributes = self._extract_attributes_from_description(pere_desc)
                        
                        person_info_pere = {
                            'nom_complet': pere_name,
                            'prenom': prenom_pere,
                            'nom': nom_pere,
                            'context': segment,
                            'professions': pere_attributes['professions'],
                            'statut': pere_attributes['statut'],
                            'terres': pere_attributes['terres'],
                            'notable': pere_attributes['notable'],
                            'relationships': [{'type': 'père', 'de': fille_name}]
                        }
                        persons.append(person_info_pere)
                    
                    # Traiter la mère
                    if mere_name and self._is_valid_full_name(mere_name) and mere_name not in found_names:
                        found_names.add(mere_name)
                        prenom_mere, nom_mere = self._split_full_name(mere_name)
                        
                        person_info_mere = {
                            'nom_complet': mere_name,
                            'prenom': prenom_mere,
                            'nom': nom_mere,
                            'context': segment,
                            'professions': [],
                            'statut': None,
                            'terres': [],
                            'notable': False,
                            'relationships': [{'type': 'mère', 'de': fille_name}]
                        }
                        persons.append(person_info_mere)
            
            # Structure 3: "inhumation de Nom, description"
            inhumation_pattern = r'inhumation[^,]+,\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?)(?:[,;.]|$)'
            
            for match in re.finditer(inhumation_pattern, segment, re.IGNORECASE):
                full_desc = match.group(1).strip()
                name = self._extract_clean_name_from_description(full_desc)
                
                if name and self._is_valid_full_name(name) and name not in found_names:
                    found_names.add(name)
                    prenom, nom = self._split_full_name(name)
                    
                    attributes = self._extract_attributes_from_description(full_desc)
                    attributes['notable'] = True  # Inhumé dans l'église = notable
                    
                    person_info = {
                        'nom_complet': name,
                        'prenom': prenom,
                        'nom': nom,
                        'context': segment,
                        'professions': attributes['professions'],
                        'statut': attributes['statut'],
                        'terres': attributes['terres'],
                        'notable': attributes['notable'],
                        'relationships': []
                    }
                    persons.append(person_info)
            
            return persons
            
        except Exception as e:
            self.logger.warning(f"Erreur extraction structures spécifiques: {e}")
            return []
    
    def _extract_clean_name_from_description(self, description: str) -> Optional[str]:
        """NOUVEAU: Extrait le nom propre d'une description avec attributs"""
        try:
            # Supprimer les attributs courants pour isoler le nom
            clean_desc = description
            
            # Supprimer les attributs en fin de description
            attributs_a_supprimer = [
                r',\s*écuyer.*$', r',\s*éc\..*$', r',\s*sieur.*$', r',\s*sr.*$',
                r',\s*seigneur.*$', r',\s*sgr.*$', r',\s*avocat.*$', r',\s*conseiller.*$',
                r',\s*curé.*$', r',\s*prêtre.*$', r',\s*notable.*$'
            ]
            
            for pattern in attributs_a_supprimer:
                clean_desc = re.sub(pattern, '', clean_desc, flags=re.IGNORECASE)
            
            # Nettoyer et valider
            clean_desc = clean_desc.strip().rstrip(',')
            
            if self._is_valid_full_name(clean_desc):
                return clean_desc
            
            # Si échec, prendre les 2-3 premiers mots
            words = clean_desc.split()
            if len(words) >= 2:
                name_candidate = ' '.join(words[:3] if len(words) >= 3 else words[:2])
                if self._is_valid_full_name(name_candidate):
                    return name_candidate
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Erreur extraction nom propre: {e}")
            return None
    
    def _extract_attributes_from_description(self, description: str) -> Dict:
        """NOUVEAU: Extrait les attributs depuis une description de personne"""
        attributes = {
            'professions': [],
            'statut': None,
            'terres': [],
            'notable': False
        }
        
        try:
            desc_lower = description.lower()
            
            # Professions
            if re.search(r'\bcur[ée]s?\b', desc_lower):
                attributes['professions'].append('curé')
            if re.search(r'\bpr[eê]stres?\b', desc_lower):
                attributes['professions'].append('prêtre')
            if re.search(r'\bavocat\s+du\s+roi\b', desc_lower):
                attributes['professions'].append('avocat du Roi')
            elif re.search(r'\bavocats?\b', desc_lower):
                attributes['professions'].append('avocat')
            if re.search(r'\bconseiller[s]?\b', desc_lower):
                attributes['professions'].append('conseiller')
            
            # Statut social
            if re.search(r'\bseigneurs?\b|\bsgrs?\b', desc_lower):
                attributes['statut'] = 'seigneur'
            elif re.search(r'\b[ée]c\.?\s*|\b[ée]cuyers?\b', desc_lower):
                attributes['statut'] = 'écuyer'
            elif re.search(r'\bsieurs?\b|\bsrs?\b', desc_lower):
                attributes['statut'] = 'sieur'
            
            # Terres
            terres_pattern = r'(?:sr|sieur|seigneur|sgr|éc\.?)\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?)(?:[,;.]|$)'
            terres_matches = re.findall(terres_pattern, description, re.IGNORECASE)
            
            for terre in terres_matches:
                terre_clean = terre.strip()
                if terre_clean and terre_clean not in attributes['terres']:
                    attributes['terres'].append(terre_clean)
            
            # Notable
            attributes['notable'] = any(pattern in desc_lower for pattern in [
                "dans l'église", "dans l'eglise", "dans la chapelle", "inhumé dans"
            ])
            
        except Exception as e:
            self.logger.warning(f"Erreur extraction attributs: {e}")
        
        return attributes
    
    def _extract_remaining_names(self, segment: str, found_names: Set[str]) -> List[Dict]:
        """NOUVEAU: Extraction des noms restants non traités par les structures spécifiques"""
        persons = []
        
        try:
            # Appliquer les patterns généraux
            for pattern_idx, pattern in enumerate(self.name_patterns):
                for match in pattern.finditer(segment):
                    prenom = match.group(1).strip()
                    nom = match.group(2).strip()
                    full_name = f"{prenom} {nom}"
                    
                    if full_name in found_names or not self._is_valid_name(prenom, nom, full_name):
                        continue
                    
                    found_names.add(full_name)
                    
                    # Attribution contextuelle prudente (seulement si très proche du nom)
                    name_pos = match.start()
                    context_window = segment[max(0, name_pos-50):name_pos+len(full_name)+50]
                    
                    person_info = {
                        'nom_complet': full_name,
                        'prenom': prenom,
                        'nom': nom,
                        'context': segment,
                        'professions': self._extract_close_professions(context_window, full_name),
                        'statut': self._extract_close_status(context_window, full_name),
                        'terres': self._extract_close_terres(context_window, full_name),
                        'notable': self._is_notable(context_window),
                        'relationships': []
                    }
                    
                    persons.append(person_info)
                    
        except Exception as e:
            self.logger.warning(f"Erreur extraction noms restants: {e}")
        
        return persons
    
    def _extract_close_professions(self, context: str, full_name: str) -> List[str]:
        """NOUVEAU: Extraction des professions seulement si très proches du nom"""
        professions = []
        context_lower = context.lower()
        name_pos = context_lower.find(full_name.lower())
        
        if name_pos == -1:
            return professions
        
        # Vérifier uniquement dans un rayon de 30 caractères autour du nom
        start = max(0, name_pos - 30)
        end = min(len(context), name_pos + len(full_name) + 30)
        close_context = context_lower[start:end]
        
        # Professions seulement si elles suivent directement le nom
        if re.search(rf'{re.escape(full_name.lower())}[^a-z]*cur[ée]', close_context):
            professions.append('curé')
        if re.search(rf'{re.escape(full_name.lower())}[^a-z]*pr[eê]stre', close_context):
            professions.append('prêtre')
        
        return professions
    
    def _extract_close_status(self, context: str, full_name: str) -> Optional[str]:
        """NOUVEAU: Extraction du statut seulement si très proche du nom"""
        context_lower = context.lower()
        name_pos = context_lower.find(full_name.lower())
        
        if name_pos == -1:
            return None
        
        # Vérifier uniquement dans un rayon de 30 caractères autour du nom
        start = max(0, name_pos - 30)
        end = min(len(context), name_pos + len(full_name) + 30)
        close_context = context_lower[start:end]
        
        if re.search(rf'{re.escape(full_name.lower())}[^a-z]*[ée]c\.?', close_context):
            return 'écuyer'
        elif re.search(rf'{re.escape(full_name.lower())}[^a-z]*s[gr]r', close_context):
            return 'sieur'
        
        return None
    
    def _extract_close_terres(self, context: str, full_name: str) -> List[str]:
        """NOUVEAU: Extraction des terres seulement si très proches du nom"""
        terres = []
        context_lower = context.lower()
        name_pos = context_lower.find(full_name.lower())
        
        if name_pos == -1:
            return terres
        
        # Chercher "sr de [terre]" après le nom dans les 50 caractères
        after_name = context[name_pos + len(full_name):name_pos + len(full_name) + 50]
        
        terre_pattern = r'[,\s]*(?:sr|sieur)\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?)(?:[,;.]|$)'
        
        for match in re.finditer(terre_pattern, after_name, re.IGNORECASE):
            terre = match.group(1).strip()
            if terre and terre not in terres:
                terres.append(terre)
        
        return terres
    
    # Méthodes utilitaires corrigées
    
    def _create_cache_key(self, text: str) -> str:
        """Crée une clé de cache stable pour le texte"""
        try:
            text_sample = text[:500] if len(text) > 500 else text
            return hashlib.md5(text_sample.encode('utf-8')).hexdigest()
        except Exception as e:
            self.logger.debug(f"Erreur création clé cache: {e}")
            return str(hash(text[:200]))
    
    def _is_valid_full_name(self, full_name: str) -> bool:
        """Valide un nom complet"""
        if not full_name or len(full_name) < 5:
            return False
        
        parts = full_name.split()
        if len(parts) < 2:
            return False
        
        prenom, nom = parts[0], ' '.join(parts[1:])
        return self._is_valid_name(prenom, nom, full_name)
    
    def _split_full_name(self, full_name: str) -> Tuple[str, str]:
        """Sépare un nom complet en prénom et nom"""
        parts = full_name.strip().split()
        if len(parts) == 1:
            return parts[0], ""
        elif len(parts) == 2:
            return parts[0], parts[1]
        else:
            return parts[0], " ".join(parts[1:])
    
    def _is_valid_name(self, prenom: str, nom: str, full_name: str) -> bool:
        """Validation optimisée des noms avec filtrage des lieux"""
        validation_key = full_name.lower()
        
        if validation_key in self._validation_cache:
            return self._validation_cache[validation_key]
        
        try:
            # Filtrer les lieux qui ne sont pas des noms de personnes
            if full_name in ["La Granville", "Le Hausey", "Le Hozey"]:
                result = False
            elif len(prenom) < 2 or len(nom) < 2:
                result = False
            elif len(prenom) > 25 or len(nom) > 40:
                result = False
            elif not re.match(r'^[A-ZÀ-ÿ][a-zà-ÿ\s\-\']*$', prenom):
                result = False
            elif not re.match(r'^[A-ZÀ-ÿ][A-Za-zà-ÿ\s\-\']*$', nom):
                result = False
            elif any(lieu.lower() in full_name.lower() for lieu in self.known_places):
                result = False
            elif self._is_common_word(prenom) or self._is_common_word(nom):
                result = False
            else:
                result = True
            
            self._validation_cache[validation_key] = result
            return result
            
        except Exception as e:
            self.logger.debug(f"Erreur validation nom {full_name}: {e}")
            return False
    
    def _is_common_word(self, word: str) -> bool:
        """Détecte les mots courants qui ne sont pas des noms"""
        common_words = {
            'grâce', 'jour', 'mars', 'nom', 'dieu', 'sans', 'aucune', 'opposition',
            'décès', 'naissance', 'église', 'chapelle', 'siège', 'roi', 'dans'
        }
        return word.lower() in common_words
    
    @lru_cache(maxsize=500)
    def _is_notable(self, context: str) -> bool:
        """Détection de notabilité avec cache"""
        if not context:
            return False
        
        context_lower = context.lower()
        notable_patterns = [
            "dans l'église", "dans l'eglise", "dans la chapelle",
            "sous le chœur", "près de l'autel", "inhumé dans",
            "inhumation dans", "enterré dans"
        ]
        
        return any(pattern in context_lower for pattern in notable_patterns)
    
    def _deduplicate_persons(self, persons: List[Dict]) -> List[Dict]:
        """Déduplication avancée des personnes"""
        if not persons:
            return []
        
        # Grouper par nom complet
        name_groups = {}
        for person in persons:
            name_key = person['nom_complet'].lower()
            if name_key not in name_groups:
                name_groups[name_key] = []
            name_groups[name_key].append(person)
        
        # Pour chaque groupe, garder la meilleure occurrence
        deduplicated = []
        for name, group in name_groups.items():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                # Prendre celle avec le plus d'attributs
                best = max(group, key=lambda p: len(p.get('professions', [])) + 
                                               len(p.get('terres', [])) + 
                                               (1 if p.get('statut') else 0))
                deduplicated.append(best)
        
        return deduplicated
    
    def get_statistics(self) -> Dict:
        """Retourne les statistiques de l'extracteur"""
        try:
            return {
                'names_extracted': self.stats['names_extracted'],
                'cache_hits': self.stats['cache_hits'],
                'cache_misses': self.stats['cache_misses'],
                'cache_hit_rate': (self.stats['cache_hits'] / 
                                 max(1, self.stats['cache_hits'] + self.stats['cache_misses'])) * 100,
                'false_positives': self.stats['false_positives'],
                'validation_errors': self.stats['validation_errors'],
                'patterns_count': len(self.name_patterns),
                'cache_sizes': {
                    'extraction': len(self._extraction_cache),
                    'validation': len(self._validation_cache),
                    'false_positives': len(self._false_positives_cache)
                }
            }
        except Exception as e:
            self.logger.error(f"Erreur calcul statistiques: {e}")
            return {'error': str(e)}