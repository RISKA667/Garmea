import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from functools import lru_cache
import hashlib

from config.settings import ParserConfig

class NameExtractor:
    """Extracteur de noms optimisé avec cache - VERSION CORRIGÉE PROPRE"""
    
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
        """CORRIGÉ: Compile les patterns regex pour capturer les noms complets"""
        try:
            self.name_patterns = [
                # CORRIGÉ: Noms "Le + Nom" complets (ex: Guillaume Le Breton)
                re.compile(
                    r'\b([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)\s+'
                    r'(Le\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ÷øùúûüýþÿ]+)*)',
                    re.UNICODE
                ),
                
                # CORRIGÉ: Noms avec particules "de" complets
                re.compile(
                    r'\b([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)\s+'
                    r'(de\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-Za-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)*)',
                    re.UNICODE
                ),
                
                # Noms avec "du"  
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
            # Fallback pattern simple
            self.name_patterns = [
                re.compile(r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b')
            ]
    
    def extract_complete_names(self, text: str) -> List[Dict]:
        """CORRIGÉ: Extraction optimisée avec cache et gestion d'erreurs robuste"""
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
        persons = []
        found_names = set()
        
        try:
            # Extraction avec tous les patterns
            for pattern_idx, pattern in enumerate(self.name_patterns):
                try:
                    for match in pattern.finditer(text):
                        result = self._process_name_match(match, text, found_names, pattern_idx)
                        if result:
                            persons.append(result)
                            
                except Exception as e:
                    self.logger.warning(f"Erreur pattern {pattern_idx}: {e}")
                    continue
            
            # Déduplication finale et validation
            persons = self._deduplicate_persons(persons)
            
            # Mise en cache du résultat
            self._extraction_cache[cache_key] = persons
            self.stats['names_extracted'] += len(persons)
            
            self.logger.debug(f"Extrait {len(persons)} personnes uniques du texte")
            return persons
            
        except Exception as e:
            self.logger.error(f"Erreur extraction noms: {e}")
            return []
    
    def _create_cache_key(self, text: str) -> str:
        """NOUVEAU: Crée une clé de cache stable pour le texte"""
        try:
            # Utiliser les premiers 500 caractères pour la clé
            text_sample = text[:500] if len(text) > 500 else text
            return hashlib.md5(text_sample.encode('utf-8')).hexdigest()
        except Exception as e:
            self.logger.debug(f"Erreur création clé cache: {e}")
            return str(hash(text[:200]))
    
    def _process_name_match(self, match: re.Match, text: str, found_names: Set[str], 
                           pattern_idx: int) -> Optional[Dict]:
        """NOUVEAU: Traite un match de nom individuel"""
        try:
            prenom = match.group(1).strip()
            nom = match.group(2).strip()
            full_name = f"{prenom} {nom}"
            
            # Optimisation: vérification rapide des doublons
            if full_name in found_names:
                return None
            
            # Optimisation: cache des faux positifs
            if full_name in self._false_positives_cache:
                self.stats['false_positives'] += 1
                return None
            
            # Validation du nom
            if not self._is_valid_name(prenom, nom, full_name):
                self._false_positives_cache.add(full_name)
                self.stats['false_positives'] += 1
                return None
            
            # Ajouter aux noms trouvés
            found_names.add(full_name)
            
            # Extraire le contexte
            context = self._extract_context(text, match.start(), match.end())
            
            # Construire les informations de la personne
            person_info = {
                'nom_complet': full_name,
                'prenom': prenom,
                'nom': nom,
                'context': context,
                'pattern_used': pattern_idx,
                'position': (match.start(), match.end())
            }
            
            # CORRIGÉ: Extraction des attributs avec attribution précise
            attributes = self._extract_attributes_safe(context, full_name)
            person_info.update(attributes)
            
            return person_info
            
        except Exception as e:
            self.logger.warning(f"Erreur traitement match: {e}")
            return None
    
    def _is_valid_name(self, prenom: str, nom: str, full_name: str) -> bool:
        """CORRIGÉ: Validation optimisée des noms avec filtrage des lieux"""
        validation_key = full_name.lower()
        
        # Vérifier le cache de validation
        if validation_key in self._validation_cache:
            return self._validation_cache[validation_key]
        
        try:
            # NOUVEAU: Filtrer les lieux qui ne sont pas des noms de personnes
            if full_name in ["La Granville", "Le Hausey", "Le Hozey"]:
                result = False
            # Validations de base
            elif len(prenom) < 2 or len(nom) < 2:
                result = False
            elif len(prenom) > 25 or len(nom) > 40:  # Noms trop longs
                result = False
            elif not re.match(r'^[A-ZÀ-ÿ][a-zà-ÿ\s\-\']*$', prenom):
                result = False
            elif not re.match(r'^[A-ZÀ-ÿ][A-Za-zà-ÿ\s\-\']*$', nom):
                result = False
            # Vérifier que ce n'est pas un lieu connu
            elif any(lieu.lower() in full_name.lower() for lieu in self.known_places):
                result = False
            # Éviter les mots courants non-noms
            elif self._is_common_word(prenom) or self._is_common_word(nom):
                result = False
            else:
                result = True
            
            # Mettre en cache
            self._validation_cache[validation_key] = result
            return result
            
        except Exception as e:
            self.logger.debug(f"Erreur validation nom {full_name}: {e}")
            return False
    
    def _is_common_word(self, word: str) -> bool:
        """NOUVEAU: Détecte les mots courants qui ne sont pas des noms"""
        common_words = {
            'grâce', 'jour', 'mars', 'nom', 'dieu', 'sans', 'aucune', 'opposition',
            'décès', 'naissance', 'église', 'chapelle', 'siège', 'roi', 'dans'
        }
        return word.lower() in common_words
    
    def _extract_context(self, text: str, start: int, end: int, context_size: int = 200) -> str:
        """Extraction de contexte optimisée avec validation"""
        try:
            context_start = max(0, start - context_size)
            context_end = min(len(text), end + context_size)
            context = text[context_start:context_end]
            
            # Nettoyer le contexte
            context = re.sub(r'\s+', ' ', context).strip()
            return context
            
        except Exception as e:
            self.logger.debug(f"Erreur extraction contexte: {e}")
            return ""
    
    def _extract_attributes_safe(self, context: str, full_name: str) -> Dict:
        """CORRIGÉ: Extraction des attributs avec attribution précise par proximité"""
        attributes = {
            'professions': [],
            'statut': None,
            'terres': [],
            'notable': False,
            'relationships': []
        }
        
        try:
            # CORRIGÉ: Trouver la position exacte du nom dans le contexte
            context_lower = context.lower()
            full_name_lower = full_name.lower()
            name_pos = context_lower.find(full_name_lower)
            
            if name_pos == -1:
                return attributes
            
            # NOUVEAU: Contexte immédiat (±80 caractères autour du nom)
            start = max(0, name_pos - 80)
            end = min(len(context), name_pos + len(full_name) + 80)
            immediate_context = context[start:end].lower()
            
            # CORRIGÉ: Extraction précise dans le contexte immédiat uniquement
            
            # Professions - attribution individuelle
            professions_found = []
            
            # Vérifier chaque profession individuellement
            if re.search(r'\bcur[ée]s?\b', immediate_context):
                professions_found.append('curé')
            if re.search(r'\bpr[eê]stres?\b', immediate_context):
                professions_found.append('prêtre')
            if re.search(r'\bavocat\s+du\s+roi\b', immediate_context):
                professions_found.append('avocat du Roi')
            elif re.search(r'\bavocats?\b', immediate_context):
                professions_found.append('avocat')
            if re.search(r'\bconseiller[s]?\b', immediate_context):
                professions_found.append('conseiller')
            if re.search(r'\bnotaires?\b', immediate_context):
                professions_found.append('notaire')
            if re.search(r'\bmarchands?\b', immediate_context):
                professions_found.append('marchand')
            if re.search(r'\blaboureurs?\b', immediate_context):
                professions_found.append('laboureur')
            
            attributes['professions'] = professions_found
            
            # Statut social - vérification de proximité
            if re.search(r'\bseigneurs?\b|\bsgrs?\b', immediate_context):
                attributes['statut'] = 'seigneur'
            elif re.search(r'\b[ée]c\.?\s*|\b[ée]cuyers?\b', immediate_context):
                attributes['statut'] = 'écuyer'
            elif re.search(r'\bsieurs?\b|\bsrs?\b', immediate_context):
                attributes['statut'] = 'sieur'
            
            # CORRIGÉ: Terres - recherche précise autour du nom
            terres_pattern = r'(?:sr|sieur|seigneur|sgr|éc\.?)\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)*)'
            terres_matches = re.findall(terres_pattern, immediate_context, re.IGNORECASE)
            
            # Nettoyer et déduplicquer les terres
            terres_clean = []
            for terre in terres_matches:
                terre_clean = terre.strip()
                if terre_clean and terre_clean not in terres_clean:
                    terres_clean.append(terre_clean)
            
            attributes['terres'] = terres_clean
            
            # Notable - vérification locale
            attributes['notable'] = self._is_notable(immediate_context)
            
            # Relations basiques - dans le contexte immédiat
            relationships = []
            if 'épouse de' in immediate_context:
                relationships.append({'type': 'épouse', 'context': immediate_context[:100]})
            if 'fils de' in immediate_context:
                relationships.append({'type': 'fils', 'context': immediate_context[:100]})
            if 'fille de' in immediate_context:
                relationships.append({'type': 'fille', 'context': immediate_context[:100]})
            if 'parrain' in immediate_context and full_name_lower in immediate_context:
                relationships.append({'type': 'parrain', 'context': immediate_context[:100]})
            if 'marraine' in immediate_context and full_name_lower in immediate_context:
                relationships.append({'type': 'marraine', 'context': immediate_context[:100]})
            
            attributes['relationships'] = relationships
            
        except Exception as e:
            self.logger.warning(f"Erreur extraction attributs pour {full_name}: {e}")
            self.stats['validation_errors'] += 1
        
        return attributes
    
    @lru_cache(maxsize=500)
    def _is_notable(self, context: str) -> bool:
        """CORRIGÉ: Détection de notabilité avec cache - ligne complète"""
        if not context:
            return False
        
        context_lower = context.lower()
        notable_patterns = [
            "dans l'église", "dans l'eglise", "dans la chapelle",
            "sous le chœur", "près de l'autel", "inhumé dans",
            "inhumation dans", "enterré dans"
        ]
        
        # CORRECTION: Ligne complète avec return
        return any(pattern in context_lower for pattern in notable_patterns)
    
    def _deduplicate_persons(self, persons: List[Dict]) -> List[Dict]:
        """NOUVEAU: Déduplication avancée des personnes"""
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
    
    def extract_names_from_segment(self, segment: str, segment_type: str = "acte") -> List[Dict]:
        """NOUVEAU: Extraction spécialisée par type de segment"""
        try:
            if segment_type == "period":
                # Pour les segments de période, extraction différente
                return self._extract_period_names(segment)
            else:
                # Extraction normale pour les actes
                return self.extract_complete_names(segment)
                
        except Exception as e:
            self.logger.error(f"Erreur extraction segment {segment_type}: {e}")
            return []
    
    def _extract_period_names(self, segment: str) -> List[Dict]:
        """NOUVEAU: Extraction pour segments de période (curés, etc.)"""
        names = []
        
        try:
            # Pattern spécial pour "Charles de Montigny, Guillaume Le Breton, curés"
            curates_pattern = re.compile(
                r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s,]+),\s*cur[ée]s',
                re.IGNORECASE
            )
            
            match = curates_pattern.search(segment)
            if match:
                curates_text = match.group(1)
                # Séparer les noms
                individual_names = re.split(r',\s*', curates_text)
                
                for name_text in individual_names:
                    name_text = name_text.strip()
                    if len(name_text) > 5:  # Filtrer les fragments trop courts
                        parts = name_text.split()
                        if len(parts) >= 2:
                            prenom = parts[0]
                            nom = ' '.join(parts[1:])
                            
                            if self._is_valid_name(prenom, nom, name_text):
                                names.append({
                                    'nom_complet': name_text,
                                    'prenom': prenom,
                                    'nom': nom,
                                    'context': segment,
                                    'professions': ['curé'],
                                    'statut': None,
                                    'terres': [],
                                    'notable': False,
                                    'relationships': []
                                })
            
        except Exception as e:
            self.logger.warning(f"Erreur extraction noms période: {e}")
        
        return names
    
    def get_statistics(self) -> Dict:
        """NOUVEAU: Retourne les statistiques de l'extracteur"""
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
    
    def clear_caches(self):
        """NOUVEAU: Nettoie tous les caches"""
        self._extraction_cache.clear()
        self._validation_cache.clear()
        self._false_positives_cache.clear()
        self.logger.info("Caches de l'extracteur nettoyés")
    
    def validate_extraction_quality(self, text: str, expected_names: List[str] = None) -> Dict:
        """NOUVEAU: Validation de la qualité d'extraction"""
        try:
            extracted = self.extract_complete_names(text)
            extracted_names = [p['nom_complet'] for p in extracted]
            
            result = {
                'total_extracted': len(extracted_names),
                'extracted_names': extracted_names,
                'quality_score': 0.0
            }
            
            if expected_names:
                found = set(extracted_names) & set(expected_names)
                missed = set(expected_names) - set(extracted_names)
                false_positives = set(extracted_names) - set(expected_names)
                
                precision = len(found) / len(extracted_names) if extracted_names else 0
                recall = len(found) / len(expected_names) if expected_names else 0
                f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                
                result.update({
                    'expected_names': expected_names,
                    'found_names': list(found),
                    'missed_names': list(missed),
                    'false_positives': list(false_positives),
                    'precision': precision,
                    'recall': recall,
                    'f1_score': f1_score,
                    'quality_score': f1_score
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur validation qualité: {e}")
            return {'error': str(e)}