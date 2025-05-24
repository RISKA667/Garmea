import logging
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from collections import defaultdict
from functools import lru_cache
import hashlib
import json

from core.models import Person, ValidationResult, PersonStatus
from config.settings import ParserConfig
from ml.similarity_engine import SimilarityEngine
from validators.gender_validator import GenderValidator

class PersonManager:
    """Gestionnaire optimisé des personnes avec détection d'homonymes - VERSION COMPLÈTEMENT CORRIGÉE"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Base de données en mémoire
        self.persons: Dict[int, Person] = {}
        self.person_id_counter = 1
        
        # Index pour recherches rapides
        self._name_index: Dict[str, List[int]] = defaultdict(list)
        self._search_cache: Dict[str, List[int]] = {}
        
        # Composants
        self.similarity_engine = SimilarityEngine(config)
        self.gender_validator = GenderValidator(config)
        
        # Statistiques détaillées
        self.stats = {
            'persons_created': 0,
            'persons_merged': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'validation_errors': 0,
            'gender_corrections': 0,
            'homonym_detections': 0,
            'status_corrections': 0
        }
    
    def get_or_create_person(self, nom: str, prenom: str, 
                           extra_info: Optional[Dict] = None) -> Person:
        """CORRIGÉ: Récupération ou création de personne avec gestion complète des erreurs"""
        if extra_info is None:
            extra_info = {}
        
        # CORRECTION: Validation stricte des types d'entrée
        try:
            if not isinstance(nom, str) or not isinstance(prenom, str):
                error_msg = f"nom et prenom doivent être des strings, reçu: nom={type(nom)}, prenom={type(prenom)}"
                self.logger.error(error_msg)
                self.stats['validation_errors'] += 1
                raise TypeError(error_msg)
            
            if not isinstance(extra_info, dict):
                error_msg = f"extra_info doit être un dict, reçu: {type(extra_info)}"
                self.logger.error(error_msg)
                self.stats['validation_errors'] += 1
                raise TypeError(error_msg)
            
            # Validation des valeurs
            if not nom or not prenom or len(nom.strip()) < 2 or len(prenom.strip()) < 2:
                error_msg = f"Nom ou prénom invalide: '{prenom}' '{nom}'"
                self.logger.warning(error_msg)
                raise ValueError(error_msg)
            
            # Nettoyer les entrées
            nom = nom.strip()
            prenom = prenom.strip()
            
            # CORRECTION: Nettoyer extra_info pour éviter les types non-sérialisables
            clean_extra_info = self._clean_extra_info(extra_info)
            
            # Validation du genre pour les titres
            self._validate_and_correct_gender_titles(nom, prenom, clean_extra_info)
            
            # Recherche de candidats similaires
            candidates = self._find_similar_persons(nom, prenom, clean_extra_info)
            
            if candidates:
                best_candidate = self._select_best_candidate(candidates, clean_extra_info)
                if best_candidate:
                    self._merge_person_info(best_candidate, clean_extra_info)
                    self.stats['persons_merged'] += 1
                    return best_candidate
            
            # Créer nouvelle personne
            person = self._create_new_person(nom, prenom, clean_extra_info)
            self.stats['persons_created'] += 1
            return person
            
        except Exception as e:
            self.logger.error(f"Erreur lors de get_or_create_person pour {prenom} {nom}: {e}")
            self.stats['validation_errors'] += 1
            raise
    
    def _clean_extra_info(self, extra_info: Dict) -> Dict:
        """CORRIGÉ: Nettoyage complet des types non-sérialisables"""
        clean_info = {}
        
        for key, value in extra_info.items():
            try:
                if isinstance(value, (str, int, float, bool)) or value is None:
                    clean_info[key] = value
                elif isinstance(value, list):
                    clean_list = []
                    for item in value:
                        if isinstance(item, (str, int, float, bool)) or item is None:
                            clean_list.append(item)
                        elif isinstance(item, dict):
                            # CORRIGÉ: Extraire seulement les informations utiles des dict
                            if 'type' in item:
                                clean_list.append(item['type'])
                            # Ignorer complètement les dict complexes
                        else:
                            self.logger.debug(f"Type non-sérialisable ignoré dans liste {key}: {type(item)}")
                    clean_info[key] = clean_list
                elif hasattr(value, 'value'):  # Enums
                    clean_info[key] = value.value
                else:
                    # Convertir en string les types complexes
                    clean_info[key] = str(value)
                    self.logger.debug(f"Type complexe converti en string {key}: {type(value)}")
                    
            except Exception as e:
                self.logger.debug(f"Erreur nettoyage extra_info[{key}]: {e}")
                continue
        
        return clean_info
    
    def _validate_and_correct_gender_titles(self, nom: str, prenom: str, extra_info: Dict):
        """NOUVEAU: Validation et correction automatique genre/titres"""
        try:
            context = extra_info.get('context', '')
            full_name = f"{prenom} {nom}"
            
            # Détecter le genre
            detected_gender = self.gender_validator.detect_gender_from_context(context, full_name)
            
            # NOUVEAU: Correction automatique des titres masculins pour les femmes
            if detected_gender == 'F':
                original_status = extra_info.get('statut')
                if original_status in ['sieur', 'seigneur', 'écuyer', 'sr', 'sgr', 'éc.']:
                    self.logger.info(f"CORRECTION GENRE: Titre masculin '{original_status}' supprimé pour {full_name} (femme détectée)")
                    extra_info['statut'] = None
                    self.stats['gender_corrections'] += 1
                
                # Correction des professions masculines pour les femmes
                if 'professions' in extra_info:
                    original_profs = extra_info['professions'][:]
                    masculine_profs = ['avocat', 'avocat du Roi', 'conseiller', 'notaire']
                    extra_info['professions'] = [p for p in extra_info['professions'] if p not in masculine_profs]
                    
                    if len(extra_info['professions']) != len(original_profs):
                        removed_profs = set(original_profs) - set(extra_info['professions'])
                        self.logger.info(f"CORRECTION GENRE: Professions masculines supprimées pour {full_name}: {removed_profs}")
                        self.stats['gender_corrections'] += 1
                        
        except Exception as e:
            self.logger.warning(f"Erreur validation genre/titres pour {prenom} {nom}: {e}")
    
    def _create_cache_key(self, nom: str, prenom: str, extra_info: Dict) -> str:
        """CORRIGÉ: Crée une clé de cache hashable pour extra_info"""
        try:
            # Créer une représentation hashable de extra_info
            relevant_keys = ['statut', 'terres', 'professions', 'acte_date', 'notable']
            cache_data = {}
            
            for key in relevant_keys:
                if key in extra_info:
                    value = extra_info[key]
                    if isinstance(value, list):
                        cache_data[key] = tuple(sorted(value)) if value else ()
                    else:
                        cache_data[key] = value
            
            # Créer un hash stable
            cache_str = f"{nom.lower()}_{prenom.lower()}_{json.dumps(cache_data, sort_keys=True)}"
            return hashlib.md5(cache_str.encode()).hexdigest()
            
        except Exception as e:
            self.logger.debug(f"Erreur création clé cache: {e}")
            # Fallback: clé simple sans extra_info
            return f"{nom.lower()}_{prenom.lower()}"
    
    def _find_similar_persons(self, nom: str, prenom: str, extra_info: Dict) -> List[Person]:
        """CORRIGÉ: Recherche de personnes similaires sans @lru_cache problématique"""
        
        # Créer une clé de cache hashable
        cache_key = self._create_cache_key(nom, prenom, extra_info)
        
        # Vérifier le cache
        if cache_key in self._search_cache:
            self.stats['cache_hits'] += 1
            candidate_ids = self._search_cache[cache_key]
            return [self.persons[pid] for pid in candidate_ids if pid in self.persons]
        
        self.stats['cache_misses'] += 1
        candidates = []
        
        try:
            # Recherche par index de noms
            search_key = f"{prenom.lower()}_{nom.lower()}"
            potential_ids = self._name_index.get(search_key, [])
            
            # Recherche étendue si pas de résultats exacts
            if not potential_ids:
                potential_ids = self._fuzzy_name_search(nom, prenom)
            
            # Évaluation de la similarité et validation chronologique
            acte_date = extra_info.get('acte_date')
            
            for person_id in potential_ids:
                person = self.persons.get(person_id)
                if not person:
                    continue
                
                # Validation chronologique obligatoire
                if not self._validate_chronological_coherence(person, acte_date):
                    continue
                
                # Calcul de similarité
                try:
                    similarity_result = self.similarity_engine.calculate_name_similarity(
                        person.nom, person.prenom, nom, prenom
                    )
                    
                    if similarity_result.similarity_score > self.config.similarity_threshold:
                        # Score contextuel bonus
                        context_score = self._calculate_context_similarity(person, extra_info)
                        final_score = similarity_result.similarity_score + context_score
                        
                        if final_score > 0.85:
                            candidates.append((person, final_score))
                            
                except Exception as e:
                    self.logger.warning(f"Erreur calcul similarité pour {person.full_name}: {e}")
                    continue
            
            # Trier par score et mettre en cache
            candidates.sort(key=lambda x: x[1], reverse=True)
            final_candidates = [c[0] for c in candidates]
            
            # Mettre en cache les IDs seulement
            self._search_cache[cache_key] = [p.id for p in final_candidates]
            
            return final_candidates
            
        except Exception as e:
            self.logger.error(f"Erreur dans _find_similar_persons: {e}")
            return []
    
    def _fuzzy_name_search(self, nom: str, prenom: str) -> List[int]:
        """Recherche floue dans l'index des noms"""
        potential_ids = set()
        
        try:
            # Recherche par prénom similaire
            for indexed_key, person_ids in self._name_index.items():
                if '_' in indexed_key:
                    indexed_prenom, indexed_nom = indexed_key.split('_', 1)
                    
                    # Similarité approximative rapide
                    if (abs(len(indexed_prenom) - len(prenom)) <= 2 and
                        abs(len(indexed_nom) - len(nom)) <= 3):
                        potential_ids.update(person_ids)
        
        except Exception as e:
            self.logger.warning(f"Erreur recherche floue: {e}")
        
        return list(potential_ids)
    
    def _calculate_context_similarity(self, person: Person, extra_info: Dict) -> float:
        """Calcule la similarité contextuelle (professions, terres, etc.)"""
        score = 0.0
        
        try:
            # Bonus pour professions communes
            person_profs = set(person.profession) if person.profession else set()
            extra_profs = set(extra_info.get('professions', []))
            if person_profs and extra_profs:
                common_profs = person_profs & extra_profs
                if common_profs:
                    score += 0.2 * (len(common_profs) / max(len(person_profs), len(extra_profs)))
            
            # Bonus pour même statut
            if (person.statut and extra_info.get('statut') and 
                person.statut.value == extra_info.get('statut')):
                score += 0.1
            
            # Bonus pour terres communes
            person_terres = set(person.terres) if person.terres else set()
            extra_terres = set(extra_info.get('terres', []))
            if person_terres and extra_terres:
                common_terres = person_terres & extra_terres
                if common_terres:
                    score += 0.15 * (len(common_terres) / max(len(person_terres), len(extra_terres)))
            
        except Exception as e:
            self.logger.warning(f"Erreur calcul similarité contextuelle: {e}")
        
        return min(score, 0.3)  # Limiter le bonus contextuel
    
    def _validate_chronological_coherence(self, person: Person, acte_date: Optional[str]) -> bool:
        """Validation chronologique obligatoire"""
        if not person.date_deces or not acte_date:
            return True
        
        try:
            from parsers.date_parser import DateParser
            date_parser = DateParser(self.config)
            
            person_death_year = date_parser.get_year_from_text(person.date_deces)
            acte_year = date_parser.get_year_from_text(acte_date)
            
            if person_death_year and acte_year and acte_year > person_death_year:
                self.logger.debug(f"Incohérence chronologique: {person.full_name} présent en {acte_year} mais décédé en {person_death_year}")
                return False
            
        except Exception as e:
            self.logger.warning(f"Erreur validation chronologique: {e}")
        
        return True
    
    def _select_best_candidate(self, candidates: List[Person], extra_info: Dict) -> Optional[Person]:
        """AMÉLIORÉ: Sélectionne le meilleur candidat avec détection d'homonymes raffinée"""
        if not candidates:
            return None
        
        if len(candidates) == 1:
            return candidates[0]
        
        try:
            # Détection d'homonymes par terres distinctes
            terres_extra = set(extra_info.get('terres', []))
            
            for candidate in candidates:
                terres_candidate = set(candidate.terres) if candidate.terres else set()
                
                # Si les terres sont complètement différentes ET non vides, c'est un homonyme
                if (terres_extra and terres_candidate and 
                    not terres_extra.intersection(terres_candidate)):
                    self.logger.info(f"HOMONYME DÉTECTÉ: {candidate.full_name} "
                                   f"(terres: {terres_candidate} vs {terres_extra})")
                    self.stats['homonym_detections'] += 1
                    continue
                
                # Vérification des professions incompatibles
                person_profs = set(candidate.profession) if candidate.profession else set()
                extra_profs = set(extra_info.get('professions', []))
                
                ecclesiastical = {'curé', 'prêtre'}
                civil = {'avocat', 'avocat du Roi', 'conseiller', 'notaire'}
                
                if (person_profs.intersection(ecclesiastical) and 
                    extra_profs.intersection(civil)):
                    self.logger.info(f"HOMONYME DÉTECTÉ: {candidate.full_name} "
                                   f"(professions incompatibles: {person_profs} vs {extra_profs})")
                    self.stats['homonym_detections'] += 1
                    continue
                
                # Sinon, c'est probablement la même personne
                return candidate
            
        except Exception as e:
            self.logger.warning(f"Erreur sélection candidat: {e}")
        
        # Aucun candidat compatible (tous homonymes) ou erreur
        return None
    
    def _merge_person_info(self, person: Person, extra_info: Dict):
        """AMÉLIORÉ: Fusionne les informations avec validations"""
        try:
            # Fusion des professions avec validation
            if extra_info.get('professions'):
                for prof in extra_info['professions']:
                    if prof and prof not in person.profession:
                        person.profession.append(prof)
            
            # Fusion des terres avec capitalisation
            if extra_info.get('terres'):
                for terre in extra_info['terres']:
                    if terre:
                        # Capitaliser la terre
                        terre_clean = terre.strip().title()
                        if terre_clean not in person.terres:
                            person.terres.append(terre_clean)
            
            # CORRIGÉ: Mise à jour du statut avec mapping correct
            if extra_info.get('statut'):
                try:
                    statut_hierarchy = {
                        PersonStatus.SEIGNEUR: 3,
                        PersonStatus.ECUYER: 2, 
                        PersonStatus.SIEUR: 1
                    }
                    
                    current_rank = statut_hierarchy.get(person.statut, 0)
                    
                    # CORRIGÉ: Mapping correct des statuts
                    statut_str = extra_info['statut'].lower()
                    new_status = None
                    if statut_str in ['écuyer', 'ecuyer', 'éc.', 'ec.', 'éc', 'ec']:
                        new_status = PersonStatus.ECUYER
                    elif statut_str in ['seigneur', 'sgr']:
                        new_status = PersonStatus.SEIGNEUR  
                    elif statut_str in ['sieur', 'sr']:
                        new_status = PersonStatus.SIEUR
                    
                    if new_status:
                        new_rank = statut_hierarchy.get(new_status, 0)
                        if new_rank > current_rank:
                            person.statut = new_status
                            self.stats['status_corrections'] += 1
                        
                except (AttributeError, KeyError) as e:
                    self.logger.warning(f"Erreur mise à jour statut: {e}")
            
            # Mise à jour notable
            if extra_info.get('notable'):
                person.notable = True
            
            # Ajout des variations orthographiques
            nom_complet = extra_info.get('nom_complet', '')
            if nom_complet and nom_complet not in person.nom_variations:
                person.nom_variations.append(nom_complet)
            
            # Invalidation du cache pour cette personne
            self._invalidate_person_cache(person)
            
        except Exception as e:
            self.logger.warning(f"Erreur fusion informations personne {person.full_name}: {e}")
    
    def _create_new_person(self, nom: str, prenom: str, extra_info: Dict) -> Person:
        """CORRIGÉ: Crée une nouvelle personne avec mapping de statut correct"""
        try:
            # CORRIGÉ: Conversion du statut string vers enum avec mapping correct
            statut = None
            if extra_info.get('statut'):
                statut_str = extra_info['statut'].lower()
                if statut_str in ['écuyer', 'ecuyer', 'éc.', 'ec.', 'éc', 'ec']:
                    statut = PersonStatus.ECUYER
                elif statut_str in ['seigneur', 'sgr']:
                    statut = PersonStatus.SEIGNEUR  
                elif statut_str in ['sieur', 'sr']:
                    statut = PersonStatus.SIEUR
                else:
                    self.logger.debug(f"Statut non reconnu: {extra_info['statut']}")
            
            # NOUVEAU: Capitaliser les terres lors de la création
            terres = []
            for terre in extra_info.get('terres', []):
                if terre:
                    terres.append(terre.strip().title())
            
            person = Person(
                id=self.person_id_counter,
                nom=nom,
                prenom=prenom,
                profession=extra_info.get('professions', []),
                statut=statut,
                terres=terres,
                notable=extra_info.get('notable', False),
                confidence_score=1.0
            )
            
            # Ajouter à la base et indexer
            self.persons[self.person_id_counter] = person
            self._add_to_index(person)
            self.person_id_counter += 1
            
            return person
            
        except Exception as e:
            self.logger.error(f"Erreur création personne {prenom} {nom}: {e}")
            raise
    
    def _add_to_index(self, person: Person):
        """Ajoute une personne aux index de recherche"""
        try:
            search_key = f"{person.prenom.lower()}_{person.nom.lower()}"
            self._name_index[search_key].append(person.id)
        except Exception as e:
            self.logger.warning(f"Erreur ajout index pour {person.full_name}: {e}")
    
    def _invalidate_person_cache(self, person: Person):
        """Invalide le cache pour une personne modifiée"""
        try:
            # Invalider toutes les entrées de cache qui pourraient concerner cette personne
            keys_to_remove = []
            for cache_key in self._search_cache.keys():
                # Vérifier si cette clé pourrait concerner cette personne
                # (approche conservative - on invalide potentiellement plus que nécessaire)
                if person.nom.lower() in cache_key or person.prenom.lower() in cache_key:
                    keys_to_remove.append(cache_key)
            
            for key in keys_to_remove:
                del self._search_cache[key]
                
        except Exception as e:
            self.logger.warning(f"Erreur invalidation cache: {e}")
    
    def get_homonym_groups(self) -> Dict[str, List[Person]]:
        """Retourne les groupes d'homonymes détectés"""
        name_groups = defaultdict(list)
        
        try:
            for person in self.persons.values():
                full_name = person.full_name
                name_groups[full_name].append(person)
            
            # Garder seulement les groupes avec plusieurs personnes
            homonym_groups = {name: persons for name, persons in name_groups.items() 
                            if len(persons) > 1}
            
            # Log des homonymes détectés
            if homonym_groups:
                self.logger.info(f"Groupes d'homonymes détectés: {list(homonym_groups.keys())}")
            
            return homonym_groups
                    
        except Exception as e:
            self.logger.error(f"Erreur récupération groupes homonymes: {e}")
            return {}
    
    def get_statistics(self) -> Dict:
        """AMÉLIORÉ: Retourne les statistiques complètes du manager"""
        try:
            homonym_groups = self.get_homonym_groups()
            
            return {
                'total_persons': len(self.persons),
                'persons_created': self.stats['persons_created'],
                'persons_merged': self.stats['persons_merged'],
                'validation_errors': self.stats['validation_errors'],
                'gender_corrections': self.stats['gender_corrections'],
                'homonym_detections': self.stats['homonym_detections'],
                'status_corrections': self.stats['status_corrections'],
                'homonym_groups': len(homonym_groups),
                'total_homonyms': sum(len(persons) for persons in homonym_groups.values()),
                'cache_hit_rate': (self.stats['cache_hits'] / 
                                 max(1, self.stats['cache_hits'] + self.stats['cache_misses'])) * 100,
                'index_size': len(self._name_index),
                'cache_size': len(self._search_cache)
            }
            
        except Exception as e:
            self.logger.error(f"Erreur calcul statistiques: {e}")
            return {
                'total_persons': len(self.persons),
                'error': str(e)
            }
    
    def clear_cache(self):
        """Nettoie le cache pour libérer la mémoire"""
        try:
            self._search_cache.clear()
            self.logger.info("Cache PersonManager nettoyé")
        except Exception as e:
            self.logger.warning(f"Erreur nettoyage cache: {e}")
    
    def get_person_by_id(self, person_id: int) -> Optional[Person]:
        """Récupère une personne par son ID"""
        return self.persons.get(person_id)
    
    def get_persons_by_name(self, nom: str, prenom: str) -> List[Person]:
        """Récupère toutes les personnes avec un nom donné"""
        try:
            search_key = f"{prenom.lower()}_{nom.lower()}"
            person_ids = self._name_index.get(search_key, [])
            return [self.persons[pid] for pid in person_ids if pid in self.persons]
        except Exception as e:
            self.logger.warning(f"Erreur recherche par nom {prenom} {nom}: {e}")
            return []
    
    def validate_person_data_integrity(self) -> Dict:
        """NOUVEAU: Valide l'intégrité des données des personnes"""
        validation_report = {
            'total_validated': 0,
            'errors': [],
            'warnings': [],
            'corrections_applied': 0
        }
        
        try:
            for person in self.persons.values():
                validation_report['total_validated'] += 1
                
                # Vérifier cohérence des données
                if not person.nom or not person.prenom:
                    validation_report['errors'].append(f"Personne {person.id}: nom ou prénom manquant")
                
                # Vérifier les terres en doublon
                if len(person.terres) != len(set(person.terres)):
                    duplicates = [t for t in person.terres if person.terres.count(t) > 1]
                    validation_report['warnings'].append(f"{person.full_name}: terres dupliquées {duplicates}")
                    
                    # Correction automatique
                    person.terres = list(set(person.terres))
                    validation_report['corrections_applied'] += 1
                
                # Vérifier les professions en doublon
                if len(person.profession) != len(set(person.profession)):
                    duplicates = [p for p in person.profession if person.profession.count(p) > 1]
                    validation_report['warnings'].append(f"{person.full_name}: professions dupliquées {duplicates}")
                    
                    # Correction automatique
                    person.profession = list(set(person.profession))
                    validation_report['corrections_applied'] += 1
                    
        except Exception as e:
            validation_report['errors'].append(f"Erreur validation: {e}")
        
        return validation_report
    
    def export_persons_summary(self) -> List[Dict]:
        """NOUVEAU: Exporte un résumé des personnes pour analyse"""
        summary = []
        
        try:
            for person in self.persons.values():
                summary.append({
                    'id': person.id,
                    'nom_complet': person.full_name,
                    'professions_count': len(person.profession),
                    'terres_count': len(person.terres),
                    'has_dates': bool(person.date_naissance or person.date_deces),
                    'notable': person.notable,
                    'confidence': person.confidence_score
                })
        except Exception as e:
            self.logger.error(f"Erreur export résumé: {e}")
        
        return summary
    
    def debug_person_creation_process(self, nom: str, prenom: str, extra_info: Dict = None) -> Dict:
        """NOUVEAU: Mode debug pour analyser le processus de création de personne"""
        if extra_info is None:
            extra_info = {}
        
        debug_info = {
            'input': {'nom': nom, 'prenom': prenom, 'extra_info': extra_info},
            'steps': [],
            'final_result': None,
            'errors': []
        }
        
        try:
            # Étape 1: Nettoyage
            clean_info = self._clean_extra_info(extra_info)
            debug_info['steps'].append(f"Nettoyage: {len(extra_info)} -> {len(clean_info)} champs")
            
            # Étape 2: Recherche candidats
            candidates = self._find_similar_persons(nom, prenom, clean_info)
            debug_info['steps'].append(f"Candidats trouvés: {len(candidates)}")
            
            # Étape 3: Sélection
            if candidates:
                best = self._select_best_candidate(candidates, clean_info)
                debug_info['steps'].append(f"Meilleur candidat: {best.full_name if best else 'Aucun'}")
            
            debug_info['final_result'] = 'success'
            
        except Exception as e:
            debug_info['errors'].append(str(e))
            debug_info['final_result'] = 'error'
        
        return debug_info