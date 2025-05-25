import logging
from collections import defaultdict
from functools import lru_cache
import hashlib
import json
from core.models import Person, ValidationResult, PersonStatus
from config.settings import ParserConfig
from ml.similarity_engine import SimilarityEngine
from validators.gender_validator import GenderValidator

class PersonManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.persons = {}
        self.person_id_counter = 1
        self._name_index = defaultdict(list)
        self._search_cache = {}
        self.similarity_engine = SimilarityEngine(config)
        self.gender_validator = GenderValidator(config)
        self.stats = {'persons_created': 0, 'persons_merged': 0, 'cache_hits': 0, 'cache_misses': 0, 'validation_errors': 0, 'gender_corrections': 0, 'homonym_detections': 0, 'status_corrections': 0}

    def get_or_create_person(self, nom, prenom, extra_info=None):
        if extra_info is None:
            extra_info = {}
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
            nom = nom.strip() if nom else ""
            prenom = prenom.strip() if prenom else ""
            if not nom and prenom:
                if len(prenom) >= 3:
                    context = extra_info.get('context', '')
                    if 'fille de' in context.lower():
                        nom = "Fille"
                    elif 'épouse de' in context.lower():
                        nom = "Épouse"
                    else:
                        nom = "Inconnu"
                    self.logger.info(f"CORRECTION: Nom manquant pour '{prenom}', utilisation de '{nom}'")
                else:
                    error_msg = f"Prénom trop court sans nom: '{prenom}'"
                    self.logger.warning(error_msg)
                    raise ValueError(error_msg)
            elif not prenom and nom:
                if len(nom) >= 3:
                    prenom = "Inconnu"
                    self.logger.info(f"CORRECTION: Prénom manquant pour '{nom}', utilisation de '{prenom}'")
                else:
                    error_msg = f"Nom trop court sans prénom: '{nom}'"
                    self.logger.warning(error_msg)
                    raise ValueError(error_msg)
            if not nom or not prenom or len(nom.strip()) < 2 or len(prenom.strip()) < 2:
                nom_complet = extra_info.get('nom_complet', '')
                if nom_complet and len(nom_complet) > 4:
                    parties = nom_complet.split()
                    if len(parties) >= 2:
                        prenom = parties[0]
                        nom = ' '.join(parties[1:])
                        self.logger.info(f"CORRECTION: Extraction depuis nom_complet '{nom_complet}' -> '{prenom}' '{nom}'")
                    else:
                        prenom = parties[0]
                        nom = "Inconnu"
                        self.logger.info(f"CORRECTION: Un seul mot '{nom_complet}' -> prénom '{prenom}', nom '{nom}'")
                else:
                    error_msg = f"Impossible de créer une personne valide: prénom='{prenom}', nom='{nom}'"
                    self.logger.warning(error_msg)
                    raise ValueError(error_msg)
            nom = nom.strip()
            prenom = prenom.strip()
            clean_extra_info = self._clean_extra_info(extra_info)
            self._validate_and_correct_gender_titles(nom, prenom, clean_extra_info)
            candidates = self._find_similar_persons(nom, prenom, clean_extra_info)
            if candidates:
                best_candidate = self._select_best_candidate(candidates, clean_extra_info)
                if best_candidate:
                    self._merge_person_info(best_candidate, clean_extra_info)
                    self.stats['persons_merged'] += 1
                    return best_candidate
            person = self._create_new_person(nom, prenom, clean_extra_info)
            self.stats['persons_created'] += 1
            return person
        except Exception as e:
            self.logger.error(f"Erreur lors de get_or_create_person pour {prenom} {nom}: {e}")
            self.stats['validation_errors'] += 1
            try:
                fallback_nom = nom if nom and len(nom) >= 2 else "Inconnu"
                fallback_prenom = prenom if prenom and len(prenom) >= 2 else "Inconnu"
                person = Person(id=self.person_id_counter, nom=fallback_nom, prenom=fallback_prenom, confidence_score=0.3)
                self.persons[self.person_id_counter] = person
                self._add_to_index(person)
                self.person_id_counter += 1
                self.logger.info(f"CRÉATION FALLBACK: {person.full_name} (score de confiance faible)")
                return person
            except Exception as fallback_error:
                self.logger.error(f"Échec création fallback: {fallback_error}")
                raise e

    def _clean_extra_info(self, extra_info):
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
                            if 'type' in item:
                                clean_list.append(item['type'])
                        else:
                            self.logger.debug(f"Type non-sérialisable ignoré dans liste {key}: {type(item)}")
                    clean_info[key] = clean_list
                elif hasattr(value, 'value'):
                    clean_info[key] = value.value
                else:
                    clean_info[key] = str(value)
                    self.logger.debug(f"Type complexe converti en string {key}: {type(value)}")
            except Exception as e:
                self.logger.debug(f"Erreur nettoyage extra_info[{key}]: {e}")
                continue
        return clean_info

    def _validate_and_correct_gender_titles(self, nom, prenom, extra_info):
        try:
            context = extra_info.get('context', '')
            full_name = f"{prenom} {nom}"
            detected_gender = self.gender_validator.detect_gender_from_context(context, full_name)
            if detected_gender == 'F':
                original_status = extra_info.get('statut')
                if original_status in ['sieur', 'seigneur', 'écuyer', 'sr', 'sgr', 'éc.']:
                    self.logger.info(f"CORRECTION GENRE: Titre masculin '{original_status}' supprimé pour {full_name} (femme détectée)")
                    extra_info['statut'] = None
                    self.stats['gender_corrections'] += 1
                if 'professions' in extra_info and extra_info['professions']:
                    original_profs = extra_info['professions'][:]
                    masculine_profs = ['avocat', 'avocat du Roi', 'conseiller', 'notaire']
                    extra_info['professions'] = [p for p in extra_info['professions'] if p not in masculine_profs]
                    if len(extra_info['professions']) != len(original_profs):
                        removed_profs = set(original_profs) - set(extra_info['professions'])
                        self.logger.info(f"CORRECTION GENRE: Professions masculines supprimées pour {full_name}: {removed_profs}")
                        self.stats['gender_corrections'] += 1
        except Exception as e:
            self.logger.warning(f"Erreur validation genre/titres pour {prenom} {nom}: {e}")

    def _create_cache_key(self, nom, prenom, extra_info):
        try:
            relevant_keys = ['statut', 'terres', 'professions', 'acte_date', 'notable']
            cache_data = {}
            for key in relevant_keys:
                if key in extra_info:
                    value = extra_info[key]
                    if isinstance(value, list):
                        cache_data[key] = tuple(sorted(value)) if value else ()
                    else:
                        cache_data[key] = value
            cache_str = f"{nom.lower()}_{prenom.lower()}_{json.dumps(cache_data, sort_keys=True)}"
            return hashlib.md5(cache_str.encode()).hexdigest()
        except Exception as e:
            self.logger.debug(f"Erreur création clé cache: {e}")
            return f"{nom.lower()}_{prenom.lower()}"

    def _find_similar_persons(self, nom, prenom, extra_info):
        cache_key = self._create_cache_key(nom, prenom, extra_info)
        if cache_key in self._search_cache:
            self.stats['cache_hits'] += 1
            candidate_ids = self._search_cache[cache_key]
            return [self.persons[pid] for pid in candidate_ids if pid in self.persons]
        self.stats['cache_misses'] += 1
        candidates = []
        try:
            search_key = f"{prenom.lower()}_{nom.lower()}"
            potential_ids = self._name_index.get(search_key, [])
            if not potential_ids:
                potential_ids = self._fuzzy_name_search(nom, prenom)
            acte_date = extra_info.get('acte_date')
            for person_id in potential_ids:
                person = self.persons.get(person_id)
                if not person:
                    continue
                if not self._validate_chronological_coherence(person, acte_date):
                    continue
                try:
                    similarity_result = self.similarity_engine.calculate_name_similarity(person.nom, person.prenom, nom, prenom)
                    if similarity_result.similarity_score > self.config.similarity_threshold:
                        context_score = self._calculate_context_similarity(person, extra_info)
                        final_score = similarity_result.similarity_score + context_score
                        if final_score > 0.85:
                            candidates.append((person, final_score))
                except Exception as e:
                    self.logger.warning(f"Erreur calcul similarité pour {person.full_name}: {e}")
                    continue
            candidates.sort(key=lambda x: x[1], reverse=True)
            final_candidates = [c[0] for c in candidates]
            self._search_cache[cache_key] = [p.id for p in final_candidates]
            return final_candidates
        except Exception as e:
            self.logger.error(f"Erreur dans _find_similar_persons: {e}")
            return []

    def _fuzzy_name_search(self, nom, prenom):
        potential_ids = set()
        try:
            for indexed_key, person_ids in self._name_index.items():
                if '_' in indexed_key:
                    indexed_prenom, indexed_nom = indexed_key.split('_', 1)
                    if (abs(len(indexed_prenom) - len(prenom)) <= 2 and abs(len(indexed_nom) - len(nom)) <= 3):
                        potential_ids.update(person_ids)
        except Exception as e:
            self.logger.warning(f"Erreur recherche floue: {e}")
        return list(potential_ids)

    def _calculate_context_similarity(self, person, extra_info):
        score = 0.0
        try:
            person_profs = set(person.profession) if person.profession else set()
            extra_profs = set(extra_info.get('professions', []))
            if person_profs and extra_profs:
                common_profs = person_profs & extra_profs
                if common_profs:
                    score += 0.2 * (len(common_profs) / max(len(person_profs), len(extra_profs)))
            if (person.statut and extra_info.get('statut') and person.statut.value == extra_info.get('statut')):
                score += 0.1
            person_terres = set(person.terres) if person.terres else set()
            extra_terres = set(extra_info.get('terres', []))
            if person_terres and extra_terres:
                common_terres = person_terres & extra_terres
                if common_terres:
                    score += 0.15 * (len(common_terres) / max(len(person_terres), len(extra_terres)))
        except Exception as e:
            self.logger.warning(f"Erreur calcul similarité contextuelle: {e}")
        return min(score, 0.3)

    def _validate_chronological_coherence(self, person, acte_date):
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

    def _select_best_candidate(self, candidates, extra_info):
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        try:
            terres_extra = set(extra_info.get('terres', []))
            for candidate in candidates:
                terres_candidate = set(candidate.terres) if candidate.terres else set()
                if (terres_extra and terres_candidate and not terres_extra.intersection(terres_candidate)):
                    self.logger.info(f"HOMONYME DÉTECTÉ: {candidate.full_name} (terres: {terres_candidate} vs {terres_extra})")
                    self.stats['homonym_detections'] += 1
                    continue
                person_profs = set(candidate.profession) if candidate.profession else set()
                extra_profs = set(extra_info.get('professions', []))
                ecclesiastical = {'curé', 'prêtre'}
                civil = {'avocat', 'avocat du Roi', 'conseiller', 'notaire'}
                if (person_profs.intersection(ecclesiastical) and extra_profs.intersection(civil)):
                    self.logger.info(f"HOMONYME DÉTECTÉ: {candidate.full_name} (professions incompatibles: {person_profs} vs {extra_profs})")
                    self.stats['homonym_detections'] += 1
                    continue
                return candidate
        except Exception as e:
            self.logger.warning(f"Erreur sélection candidat: {e}")
        return None

    def _merge_person_info(self, person, extra_info):
        try:
            if extra_info.get('professions'):
                for prof in extra_info['professions']:
                    if prof and prof not in person.profession:
                        person.profession.append(prof)
            if extra_info.get('terres'):
                for terre in extra_info['terres']:
                    if terre:
                        terre_clean = terre.strip().title()
                        if terre_clean not in person.terres:
                            person.terres.append(terre_clean)
            if extra_info.get('statut'):
                try:
                    statut_hierarchy = {PersonStatus.SEIGNEUR: 3, PersonStatus.ECUYER: 2, PersonStatus.SIEUR: 1}
                    current_rank = statut_hierarchy.get(person.statut, 0)
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
            if extra_info.get('notable'):
                person.notable = True
            nom_complet = extra_info.get('nom_complet', '')
            if nom_complet and nom_complet not in person.nom_variations:
                person.nom_variations.append(nom_complet)
            self._invalidate_person_cache(person)
        except Exception as e:
            self.logger.warning(f"Erreur fusion informations personne {person.full_name}: {e}")

    def _create_new_person(self, nom, prenom, extra_info):
        try:
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
            terres = []
            for terre in extra_info.get('terres', []):
                if terre:
                    terres.append(terre.strip().title())
            person = Person(id=self.person_id_counter, nom=nom, prenom=prenom, profession=extra_info.get('professions', []), statut=statut, terres=terres, notable=extra_info.get('notable', False), confidence_score=1.0)
            self.persons[self.person_id_counter] = person
            self._add_to_index(person)
            self.person_id_counter += 1
            return person
        except Exception as e:
            self.logger.error(f"Erreur création personne {prenom} {nom}: {e}")
            raise

    def _add_to_index(self, person):
        try:
            search_key = f"{person.prenom.lower()}_{person.nom.lower()}"
            self._name_index[search_key].append(person.id)
        except Exception as e:
            self.logger.warning(f"Erreur ajout index pour {person.full_name}: {e}")

    def _invalidate_person_cache(self, person):
        try:
            keys_to_remove = []
            for cache_key in self._search_cache.keys():
                if person.nom.lower() in cache_key or person.prenom.lower() in cache_key:
                    keys_to_remove.append(cache_key)
            for key in keys_to_remove:
                del self._search_cache[key]
        except Exception as e:
            self.logger.warning(f"Erreur invalidation cache: {e}")

    def get_homonym_groups(self):
        name_groups = defaultdict(list)
        try:
            for person in self.persons.values():
                full_name = person.full_name
                name_groups[full_name].append(person)
            homonym_groups = {name: persons for name, persons in name_groups.items() if len(persons) > 1}
            if homonym_groups:
                self.logger.info(f"Groupes d'homonymes détectés: {list(homonym_groups.keys())}")
            return homonym_groups
        except Exception as e:
            self.logger.error(f"Erreur récupération groupes homonymes: {e}")
            return {}

    def get_statistics(self):
        try:
            homonym_groups = self.get_homonym_groups()
            return {'total_persons': len(self.persons), 'persons_created': self.stats['persons_created'], 'persons_merged': self.stats['persons_merged'], 'validation_errors': self.stats['validation_errors'], 'gender_corrections': self.stats['gender_corrections'], 'homonym_detections': self.stats['homonym_detections'], 'status_corrections': self.stats['status_corrections'], 'homonym_groups': len(homonym_groups), 'total_homonyms': sum(len(persons) for persons in homonym_groups.values()), 'cache_hit_rate': (self.stats['cache_hits'] / max(1, self.stats['cache_hits'] + self.stats['cache_misses'])) * 100, 'index_size': len(self._name_index), 'cache_size': len(self._search_cache)}
        except Exception as e:
            self.logger.error(f"Erreur calcul statistiques: {e}")
            return {'total_persons': len(self.persons), 'error': str(e)}

    def clear_cache(self):
        try:
            self._search_cache.clear()
            self.logger.info("Cache PersonManager nettoyé")
        except Exception as e:
            self.logger.warning(f"Erreur nettoyage cache: {e}")

    def get_person_by_id(self, person_id):
        return self.persons.get(person_id)

    def get_persons_by_name(self, nom, prenom):
        try:
            search_key = f"{prenom.lower()}_{nom.lower()}"
            person_ids = self._name_index.get(search_key, [])
            return [self.persons[pid] for pid in person_ids if pid in self.persons]
        except Exception as e:
            self.logger.warning(f"Erreur recherche par nom {prenom} {nom}: {e}")
            return []

    def validate_person_data_integrity(self):
        validation_report = {'total_validated': 0, 'errors': [], 'warnings': [], 'corrections_applied': 0}
        try:
            for person in self.persons.values():
                validation_report['total_validated'] += 1
                if not person.nom or not person.prenom:
                    validation_report['errors'].append(f"Personne {person.id}: nom ou prénom manquant")
                if len(person.terres) != len(set(person.terres)):
                    duplicates = [t for t in person.terres if person.terres.count(t) > 1]
                    validation_report['warnings'].append(f"{person.full_name}: terres dupliquées {duplicates}")
                    person.terres = list(set(person.terres))
                    validation_report['corrections_applied'] += 1
                if len(person.profession) != len(set(person.profession)):
                    duplicates = [p for p in person.profession if person.profession.count(p) > 1]
                    validation_report['warnings'].append(f"{person.full_name}: professions dupliquées {duplicates}")
                    person.profession = list(set(person.profession))
                    validation_report['corrections_applied'] += 1
        except Exception as e:
            validation_report['errors'].append(f"Erreur validation: {e}")
        return validation_report

    def export_persons_summary(self):
        summary = []
        try:
            for person in self.persons.values():
                summary.append({'id': person.id, 'nom_complet': person.full_name, 'professions_count': len(person.profession), 'terres_count': len(person.terres), 'has_dates': bool(person.date_naissance or person.date_deces), 'notable': person.notable, 'confidence': person.confidence_score})
        except Exception as e:
            self.logger.error(f"Erreur export résumé: {e}")
        return summary

    def debug_person_creation_process(self, nom, prenom, extra_info=None):
        if extra_info is None:
            extra_info = {}
        debug_info = {'input': {'nom': nom, 'prenom': prenom, 'extra_info': extra_info}, 'steps': [], 'final_result': None, 'errors': []}
        try:
            clean_info = self._clean_extra_info(extra_info)
            debug_info['steps'].append(f"Nettoyage: {len(extra_info)} -> {len(clean_info)} champs")
            candidates = self._find_similar_persons(nom, prenom, clean_info)
            debug_info['steps'].append(f"Candidats trouvés: {len(candidates)}")
            if candidates:
                best = self._select_best_candidate(candidates, clean_info)
                debug_info['steps'].append(f"Meilleur candidat: {best.full_name if best else 'Aucun'}")
            debug_info['final_result'] = 'success'
        except Exception as e:
            debug_info['errors'].append(str(e))
            debug_info['final_result'] = 'error'
        return debug_info