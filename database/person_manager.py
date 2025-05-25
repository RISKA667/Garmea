import logging
from collections import defaultdict
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Set
from core.models import Person, ValidationResult, PersonStatus, RelationType
from config.settings import ParserConfig
from ml.similarity_engine import SimilarityEngine
from validators.gender_validator import GenderValidator

class PersonManager:
    """Gestionnaire de personnes optimisé avec relations familiales complètes"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Stockage principal
        self.persons: Dict[int, Person] = {}
        self.person_id_counter = 1
        
        # Index optimisés
        self._name_index = defaultdict(list)  # nom_complet -> [person_ids]
        self._prenoms_index = defaultdict(list)  # prenom -> [person_ids]
        self._search_cache = {}
        
        # Composants
        self.similarity_engine = SimilarityEngine(config)
        self.gender_validator = GenderValidator(config)
        
        # Statistiques
        self.stats = {
            'persons_created': 0,
            'persons_merged': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'validation_errors': 0,
            'gender_corrections': 0,
            'homonym_detections': 0,
            'status_corrections': 0,
            'relations_established': 0
        }
    
    def get_or_create_person(self, nom: str, prenom: str, extra_info: Optional[Dict] = None) -> Person:
        """Création/récupération de personne avec gestion complète des informations"""
        if extra_info is None:
            extra_info = {}
        
        try:
            # Validation et nettoyage des entrées
            nom, prenoms_list = self._validate_and_clean_inputs(nom, prenom, extra_info)
            
            # Recherche de personnes similaires
            candidates = self._find_similar_persons(nom, prenoms_list[0], extra_info)
            
            if candidates:
                best_candidate = self._select_best_candidate(candidates, extra_info)
                if best_candidate:
                    self._enrich_person_info(best_candidate, extra_info, prenoms_list)
                    self.stats['persons_merged'] += 1
                    return best_candidate
            
            # Créer nouvelle personne
            person = self._create_new_person(nom, prenoms_list, extra_info)
            self.stats['persons_created'] += 1
            return person
            
        except Exception as e:
            self.logger.error(f"Erreur get_or_create_person pour {prenom} {nom}: {e}")
            self.stats['validation_errors'] += 1
            return self._create_fallback_person(nom, prenom)
    
    def _validate_and_clean_inputs(self, nom: str, prenom: str, extra_info: Dict) -> Tuple[str, List[str]]:
        """Validation et nettoyage des données d'entrée"""
        
        # Nettoyer et valider nom
        nom = (nom or "").strip()
        prenom = (prenom or "").strip()
        
        # Gestion nom manquant
        if not nom and prenom:
            if len(prenom) >= 3:
                context = extra_info.get('context', '').lower()
                if any(word in context for word in ['fille de', 'épouse de', 'veuve de']):
                    nom = "FEMME_INCONNUE"
                else:
                    nom = "PERSONNE_INCONNUE"
            else:
                raise ValueError(f"Prénom trop court sans nom: '{prenom}'")
        
        # Gestion prénom manquant
        if not prenom and nom:
            if len(nom) >= 3:
                prenom = "PRENOM_INCONNU"
            else:
                raise ValueError(f"Nom trop court sans prénom: '{nom}'")
        
        # Extraction depuis nom_complet si nécessaire
        if not nom or not prenom:
            nom_complet = extra_info.get('nom_complet', '')
            if nom_complet and len(nom_complet) > 4:
                from core.models import MultiPrenomUtils
                prenoms_extraits, nom_extrait = MultiPrenomUtils.extract_prenoms_from_fullname(nom_complet)
                
                if prenoms_extraits:
                    prenoms_list = prenoms_extraits
                    nom = nom_extrait or nom or "INCONNU"
                else:
                    prenoms_list = [prenom or "INCONNU"]
            else:
                prenoms_list = [prenom or "INCONNU"]
        else:
            # Gérer prénoms multiples
            if 'prenoms' in extra_info and extra_info['prenoms']:
                prenoms_list = extra_info['prenoms']
            else:
                prenoms_list = [prenom]
        
        return nom, prenoms_list
    
    def _find_similar_persons(self, nom: str, prenom_principal: str, extra_info: Dict) -> List[Person]:
        """Recherche de personnes similaires avec cache optimisé"""
        
        # Clé de cache
        cache_key = self._create_cache_key(nom, prenom_principal, extra_info)
        
        if cache_key in self._search_cache:
            self.stats['cache_hits'] += 1
            candidate_ids = self._search_cache[cache_key]
            return [self.persons[pid] for pid in candidate_ids if pid in self.persons]
        
        self.stats['cache_misses'] += 1
        candidates = []
        
        # Recherche par nom complet
        full_name_key = f"{prenom_principal} {nom}".lower()
        potential_ids = self._name_index.get(full_name_key, [])
        
        # Recherche par prénom si pas de résultat
        if not potential_ids:
            potential_ids = self._prenoms_index.get(prenom_principal.lower(), [])
        
        # Recherche floue si toujours pas de résultat
        if not potential_ids:
            potential_ids = self._fuzzy_search(nom, prenom_principal)
        
        # Évaluer chaque candidat
        for person_id in potential_ids:
            person = self.persons.get(person_id)
            if not person:
                continue
            
            # Vérification chronologique
            if not self._is_chronologically_coherent(person, extra_info):
                continue
            
            # Calcul similarité
            try:
                similarity_result = self.similarity_engine.calculate_name_similarity(
                    person.nom, person.primary_prenom, nom, prenom_principal
                )
                
                if similarity_result.similarity_score > self.config.similarity_threshold:
                    context_score = self._calculate_context_similarity(person, extra_info)
                    final_score = similarity_result.similarity_score + context_score
                    
                    if final_score > 0.80:
                        candidates.append((person, final_score))
            
            except Exception as e:
                self.logger.debug(f"Erreur similarité pour {person.full_name}: {e}")
                continue
        
        # Trier et retourner
        candidates.sort(key=lambda x: x[1], reverse=True)
        final_candidates = [c[0] for c in candidates]
        
        # Mise en cache
        self._search_cache[cache_key] = [p.id for p in final_candidates]
        
        return final_candidates
    
    def _select_best_candidate(self, candidates: List[Person], extra_info: Dict) -> Optional[Person]:
        """Sélection du meilleur candidat avec détection d'homonymes"""
        
        if len(candidates) == 1:
            return candidates[0]
        
        # Détection d'homonymes par terres/professions incompatibles
        terres_extra = set(extra_info.get('terres', []))
        professions_extra = set(extra_info.get('professions', []))
        
        for candidate in candidates:
            # Vérifier terres distinctes (homonymes probables)
            terres_candidate = set(candidate.terres)
            if terres_extra and terres_candidate and not terres_extra.intersection(terres_candidate):
                self.logger.info(f"HOMONYME détecté: {candidate.full_name} (terres différentes)")
                self.stats['homonym_detections'] += 1
                continue
            
            # Vérifier professions incompatibles
            professions_candidate = set(candidate.profession)
            ecclesiastical = {'curé', 'prêtre', 'vicaire'}
            civil = {'avocat', 'marchand', 'laboureur'}
            
            if (professions_candidate & ecclesiastical and professions_extra & civil):
                self.logger.info(f"HOMONYME détecté: {candidate.full_name} (professions incompatibles)")
                self.stats['homonym_detections'] += 1
                continue
            
            # Candidat acceptable
            return candidate
        
        return None
    
    def _enrich_person_info(self, person: Person, extra_info: Dict, prenoms_list: List[str]):
        """Enrichissement des informations d'une personne existante"""
        
        try:
            # Enrichir prénoms
            for prenom in prenoms_list:
                if prenom and prenom not in person.prenoms:
                    person.add_prenom(prenom)
            
            # Enrichir professions (sans doublons)
            for prof in extra_info.get('professions', []):
                if prof and prof not in person.profession:
                    person.profession.append(prof)
            
            # Enrichir terres
            for terre in extra_info.get('terres', []):
                if terre:
                    terre_clean = terre.strip().title()
                    if terre_clean not in person.terres:
                        person.terres.append(terre_clean)
            
            # Mise à jour statut (hiérarchique)
            self._update_person_status(person, extra_info.get('statut'))
            
            # Dates (prendre les plus complètes)
            self._update_person_dates(person, extra_info)
            
            # Notable
            if extra_info.get('notable'):
                person.notable = True
            
            # Variations du nom
            nom_complet = extra_info.get('nom_complet', '')
            if nom_complet and nom_complet not in person.nom_variations:
                person.nom_variations.append(nom_complet)
            
            # Sources
            source_ref = extra_info.get('source_reference', '')
            if source_ref and source_ref not in person.sources:
                person.sources.append(source_ref)
            
            # Invalider caches
            self._invalidate_person_cache(person)
            
        except Exception as e:
            self.logger.warning(f"Erreur enrichissement {person.full_name}: {e}")
    
    def _create_new_person(self, nom: str, prenoms_list: List[str], extra_info: Dict) -> Person:
        """Création d'une nouvelle personne avec toutes les informations"""
        
        # Conversion statut
        statut = self._parse_status(extra_info.get('statut'))
        
        # Nettoyage terres
        terres = [terre.strip().title() for terre in extra_info.get('terres', []) if terre]
        
        # Création
        person = Person(
            id=self.person_id_counter,
            nom=nom,
            prenoms=prenoms_list.copy(),
            profession=list(extra_info.get('professions', [])),
            statut=statut,
            terres=terres,
            notable=extra_info.get('notable', False),
            date_naissance=extra_info.get('date_naissance'),
            date_deces=extra_info.get('date_deces'),
            date_mariage=extra_info.get('date_mariage'),
            lieu_naissance=extra_info.get('lieu_naissance'),
            lieu_deces=extra_info.get('lieu_deces'),
            lieu_mariage=extra_info.get('lieu_mariage'),
            confidence_score=1.0
        )
        
        # Sources
        source_ref = extra_info.get('source_reference', '')
        if source_ref:
            person.sources.append(source_ref)
        
        # Nom complet en variation
        nom_complet = extra_info.get('nom_complet', '')
        if nom_complet:
            person.nom_variations.append(nom_complet)
        
        # Stockage et indexation
        self.persons[self.person_id_counter] = person
        self._add_to_indexes(person)
        self.person_id_counter += 1
        
        return person
    
    def _create_fallback_person(self, nom: str, prenom: str) -> Person:
        """Création de personne de secours en cas d'erreur"""
        
        fallback_nom = nom if nom and len(nom) >= 2 else "INCONNU"
        fallback_prenom = prenom if prenom and len(prenom) >= 2 else "INCONNU"
        
        person = Person(
            id=self.person_id_counter,
            nom=fallback_nom,
            prenoms=[fallback_prenom],
            confidence_score=0.3
        )
        
        self.persons[self.person_id_counter] = person
        self._add_to_indexes(person)
        self.person_id_counter += 1
        
        self.logger.info(f"CRÉATION FALLBACK: {person.full_name}")
        return person
    
    def establish_family_relationship(self, person1_id: int, person2_id: int, 
                                   relation_type: RelationType) -> bool:
        """Établit une relation familiale entre deux personnes"""
        
        person1 = self.persons.get(person1_id)
        person2 = self.persons.get(person2_id)
        
        if not person1 or not person2:
            return False
        
        try:
            # Relations directes
            if relation_type == RelationType.PERE:
                person2.pere_id = person1_id
            elif relation_type == RelationType.MERE:
                person2.mere_id = person1_id
            elif relation_type == RelationType.CONJOINT:
                person1.conjoint_id = person2_id
                person2.conjoint_id = person1_id
            elif relation_type == RelationType.PARRAIN:
                person2.parrain_id = person1_id
                if person2_id not in person1.filleuls_ids:
                    person1.filleuls_ids.append(person2_id)
            elif relation_type == RelationType.MARRAINE:
                person2.marraine_id = person1_id
                if person2_id not in person1.filleuls_ids:
                    person1.filleuls_ids.append(person2_id)
            else:
                # Relations étendues
                person1.add_family_relation(person2_id, relation_type)
                # Ajouter relation inverse si approprié
                inverse_relations = {
                    RelationType.FRERE: RelationType.FRERE,
                    RelationType.SOEUR: RelationType.SOEUR,
                    RelationType.ONCLE: RelationType.NEVEU,
                    RelationType.TANTE: RelationType.NIECE,
                    RelationType.NEVEU: RelationType.ONCLE,
                    RelationType.NIECE: RelationType.TANTE,
                    RelationType.COUSIN: RelationType.COUSIN,
                    RelationType.COUSINE: RelationType.COUSINE
                }
                
                if relation_type in inverse_relations:
                    person2.add_family_relation(person1_id, inverse_relations[relation_type])
            
            self.stats['relations_established'] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur établissement relation {relation_type}: {e}")
            return False
    
    def find_persons_by_name_fuzzy(self, nom: str, prenom: str, threshold: float = 0.8) -> List[Tuple[Person, float]]:
        """Recherche floue de personnes par nom"""
        
        matches = []
        
        for person in self.persons.values():
            try:
                result = self.similarity_engine.calculate_name_similarity(
                    person.nom, person.primary_prenom, nom, prenom
                )
                
                if result.similarity_score >= threshold:
                    matches.append((person, result.similarity_score))
            
            except Exception:
                continue
        
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def get_family_network(self, person_id: int) -> Dict[str, List[Person]]:
        """Récupère le réseau familial complet d'une personne"""
        
        person = self.persons.get(person_id)
        if not person:
            return {}
        
        network = {}
        
        # Relations directes
        if person.pere_id:
            network['père'] = [self.persons[person.pere_id]]
        if person.mere_id:
            network['mère'] = [self.persons[person.mere_id]]
        if person.conjoint_id:
            network['conjoint'] = [self.persons[person.conjoint_id]]
        
        # Relations étendues
        family_ids = person.get_all_family_ids()
        for relation_type, ids_list in family_ids.items():
            if ids_list:
                network[relation_type] = [self.persons[pid] for pid in ids_list if pid in self.persons]
        
        # Filleuls/parrainages
        if person.filleuls_ids:
            network['filleuls'] = [self.persons[pid] for pid in person.filleuls_ids if pid in self.persons]
        
        return network
    
    def _create_cache_key(self, nom: str, prenom: str, extra_info: Dict) -> str:
        """Création de clé de cache optimisée"""
        
        relevant_keys = ['statut', 'terres', 'professions', 'date_naissance', 'notable']
        cache_data = {
            'nom': nom.lower(),
            'prenom': prenom.lower()
        }
        
        for key in relevant_keys:
            if key in extra_info and extra_info[key]:
                value = extra_info[key]
                if isinstance(value, list):
                    cache_data[key] = tuple(sorted(value))
                else:
                    cache_data[key] = value
        
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _add_to_indexes(self, person: Person):
        """Ajout aux index de recherche"""
        
        # Index nom complet
        full_name_key = person.full_name.lower()
        self._name_index[full_name_key].append(person.id)
        
        # Index prénoms
        for prenom in person.prenoms:
            self._prenoms_index[prenom.lower()].append(person.id)
    
    def _fuzzy_search(self, nom: str, prenom: str) -> List[int]:
        """Recherche floue par similarité de noms"""
        
        potential_ids = set()
        
        # Recherche par longueur similaire
        for indexed_key, person_ids in self._name_index.items():
            if '_' in indexed_key:
                parts = indexed_key.split('_', 1)
                if len(parts) == 2:
                    indexed_prenom, indexed_nom = parts
                    if (abs(len(indexed_prenom) - len(prenom)) <= 2 and 
                        abs(len(indexed_nom) - len(nom)) <= 3):
                        potential_ids.update(person_ids)
        
        return list(potential_ids)
    
    def _parse_status(self, statut_str: Optional[str]) -> Optional[PersonStatus]:
        """Conversion chaîne vers PersonStatus"""
        
        if not statut_str:
            return None
        
        statut_lower = statut_str.lower()
        
        if statut_lower in ['écuyer', 'ecuyer', 'éc.', 'ec.', 'éc', 'ec']:
            return PersonStatus.ECUYER
        elif statut_lower in ['seigneur', 'sgr']:
            return PersonStatus.SEIGNEUR
        elif statut_lower in ['sieur', 'sr']:
            return PersonStatus.SIEUR
        
        return None
    
    def _update_person_status(self, person: Person, new_status_str: Optional[str]):
        """Mise à jour hiérarchique du statut"""
        
        if not new_status_str:
            return
        
        new_status = self._parse_status(new_status_str)
        if not new_status:
            return
        
        # Hiérarchie des statuts
        hierarchy = {PersonStatus.SEIGNEUR: 3, PersonStatus.ECUYER: 2, PersonStatus.SIEUR: 1}
        
        current_rank = hierarchy.get(person.statut, 0)
        new_rank = hierarchy.get(new_status, 0)
        
        if new_rank > current_rank:
            person.statut = new_status
            self.stats['status_corrections'] += 1
    
    def _update_person_dates(self, person: Person, extra_info: Dict):
        """Mise à jour intelligente des dates"""
        
        # Naissance (prendre la plus complète)
        new_birth = extra_info.get('date_naissance')
        if new_birth and (not person.date_naissance or len(new_birth) > len(person.date_naissance)):
            person.date_naissance = new_birth
        
        # Décès
        new_death = extra_info.get('date_deces')
        if new_death and (not person.date_deces or len(new_death) > len(person.date_deces)):
            person.date_deces = new_death
        
        # Mariage
        new_marriage = extra_info.get('date_mariage')
        if new_marriage and (not person.date_mariage or len(new_marriage) > len(person.date_mariage)):
            person.date_mariage = new_marriage
    
    def _calculate_context_similarity(self, person: Person, extra_info: Dict) -> float:
        """Calcul de similarité contextuelle"""
        
        score = 0.0
        
        # Professions communes
        person_profs = set(person.profession)
        extra_profs = set(extra_info.get('professions', []))
        if person_profs and extra_profs:
            common = person_profs & extra_profs
            if common:
                score += 0.2 * (len(common) / max(len(person_profs), len(extra_profs)))
        
        # Statut identique
        if (person.statut and extra_info.get('statut') and 
            person.statut.value == extra_info.get('statut')):
            score += 0.1
        
        # Terres communes
        person_terres = set(person.terres)
        extra_terres = set(extra_info.get('terres', []))
        if person_terres and extra_terres:
            common = person_terres & extra_terres
            if common:
                score += 0.15 * (len(common) / max(len(person_terres), len(extra_terres)))
        
        return min(score, 0.3)
    
    def _is_chronologically_coherent(self, person: Person, extra_info: Dict) -> bool:
        """Vérification cohérence chronologique"""
        
        acte_date = extra_info.get('acte_date')
        if not person.date_deces or not acte_date:
            return True
        
        try:
            from parsers.date_parser import DateParser
            date_parser = DateParser(self.config)
            
            person_death_year = date_parser.get_year_from_text(person.date_deces)
            acte_year = date_parser.get_year_from_text(acte_date)
            
            if person_death_year and acte_year and acte_year > person_death_year:
                return False
        
        except Exception:
            pass
        
        return True
    
    def _invalidate_person_cache(self, person: Person):
        """Invalidation du cache pour une personne"""
        
        keys_to_remove = []
        for cache_key in self._search_cache.keys():
            # Simple heuristique basée sur les noms
            if any(prenom.lower() in cache_key for prenom in person.prenoms):
                keys_to_remove.append(cache_key)
        
        for key in keys_to_remove:
            del self._search_cache[key]
    
    def get_homonym_groups(self) -> Dict[str, List[Person]]:
        """Identification des groupes d'homonymes"""
        
        name_groups = defaultdict(list)
        
        for person in self.persons.values():
            # Clé basée sur nom principal + premier prénom
            key = f"{person.primary_prenom} {person.nom}".lower()
            name_groups[key].append(person)
        
        # Filtrer pour garder seulement les vrais homonymes
        homonym_groups = {}
        for name, persons_list in name_groups.items():
            if len(persons_list) > 1:
                homonym_groups[name] = persons_list
        
        return homonym_groups
    
    def get_statistics(self) -> Dict:
        """Statistiques complètes du gestionnaire"""
        
        homonym_groups = self.get_homonym_groups()
        
        return {
            'total_persons': len(self.persons),
            'persons_created': self.stats['persons_created'],
            'persons_merged': self.stats['persons_merged'],
            'validation_errors': self.stats['validation_errors'],
            'gender_corrections': self.stats['gender_corrections'],
            'homonym_detections': self.stats['homonym_detections'],
            'status_corrections': self.stats['status_corrections'],
            'relations_established': self.stats['relations_established'],
            'homonym_groups': len(homonym_groups),
            'total_homonyms': sum(len(persons) for persons in homonym_groups.values()),
            'cache_hit_rate': (self.stats['cache_hits'] / 
                             max(1, self.stats['cache_hits'] + self.stats['cache_misses'])) * 100,
            'index_size': len(self._name_index),
            'cache_size': len(self._search_cache)
        }
    
    def clear_cache(self):
        """Nettoyage des caches"""
        self._search_cache.clear()
        self.logger.info("Cache PersonManager nettoyé")
    
    def get_person_by_id(self, person_id: int) -> Optional[Person]:
        """Récupération par ID"""
        return self.persons.get(person_id)
    
    def get_persons_by_name(self, nom: str, prenom: str) -> List[Person]:
        """Récupération par nom exact"""
        
        search_key = f"{prenom} {nom}".lower()
        person_ids = self._name_index.get(search_key, [])
        return [self.persons[pid] for pid in person_ids if pid in self.persons]