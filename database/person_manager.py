import logging
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from functools import lru_cache

from core.models import Person, ValidationResult
from config.settings import ParserConfig
from ml.similarity_engine import SimilarityEngine
from validators.gender_validator import GenderValidator

class PersonManager:
    """Gestionnaire optimisé des personnes avec détection d'homonymes"""
    
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
        
        # Statistiques
        self.stats = {
            'persons_created': 0,
            'persons_merged': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def get_or_create_person(self, nom: str, prenom: str, 
                           extra_info: Dict = None) -> Person:
        """Récupération ou création de personne avec gestion d'homonymes"""
        if extra_info is None:
            extra_info = {}
        
        # Validation des entrées
        if not nom or not prenom or len(nom) < 2 or len(prenom) < 2:
            raise ValueError(f"Nom ou prénom invalide: '{prenom}' '{nom}'")
        
        # Validation du genre pour les titres
        self._validate_gender_titles(nom, prenom, extra_info)
        
        # Recherche de candidats similaires
        candidates = self._find_similar_persons(nom, prenom, extra_info)
        
        if candidates:
            best_candidate = self._select_best_candidate(candidates, extra_info)
            if best_candidate:
                self._merge_person_info(best_candidate, extra_info)
                self.stats['persons_merged'] += 1
                return best_candidate
        
        # Créer nouvelle personne
        person = self._create_new_person(nom, prenom, extra_info)
        self.stats['persons_created'] += 1
        return person
    
    def _validate_gender_titles(self, nom: str, prenom: str, extra_info: Dict):
        """Valide la cohérence genre/titres avant création"""
        context = extra_info.get('context', '')
        full_name = f"{prenom} {nom}"
        
        # Détecter le genre
        detected_gender = self.gender_validator.detect_gender_from_context(context, full_name)
        
        # Corriger les titres masculins pour les femmes
        if detected_gender == 'F' and extra_info.get('statut') in ['sieur', 'seigneur', 'écuyer']:
            self.logger.info(f"Titre masculin supprimé pour {full_name} (femme détectée)")
            extra_info['statut'] = None
    
    @lru_cache(maxsize=1000)
    def _find_similar_persons(self, nom: str, prenom: str, extra_info: Dict) -> List[Person]:
        """Recherche de personnes similaires avec cache"""
        cache_key = f"{nom.lower()}_{prenom.lower()}"
        
        # Vérifier le cache
        if cache_key in self._search_cache:
            self.stats['cache_hits'] += 1
            candidate_ids = self._search_cache[cache_key]
            return [self.persons[pid] for pid in candidate_ids if pid in self.persons]
        
        self.stats['cache_misses'] += 1
        candidates = []
        
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
            similarity_result = self.similarity_engine.calculate_name_similarity(
                person.nom, person.prenom, nom, prenom
            )
            
            if similarity_result.similarity_score > self.config.similarity_threshold:
                # Score contextuel bonus
                context_score = self._calculate_context_similarity(person, extra_info)
                final_score = similarity_result.similarity_score + context_score
                
                if final_score > 0.85:
                    candidates.append((person, final_score))
        
        # Trier par score et mettre en cache
        candidates.sort(key=lambda x: x[1], reverse=True)
        final_candidates = [c[0] for c in candidates]
        
        self._search_cache[cache_key] = [p.id for p in final_candidates]
        return final_candidates
    
    def _fuzzy_name_search(self, nom: str, prenom: str) -> List[int]:
        """Recherche floue dans l'index des noms"""
        potential_ids = set()
        
        # Recherche par prénom similaire
        for indexed_key, person_ids in self._name_index.items():
            if '_' in indexed_key:
                indexed_prenom, indexed_nom = indexed_key.split('_', 1)
                
                # Similarité approximative rapide
                if (abs(len(indexed_prenom) - len(prenom)) <= 2 and
                    abs(len(indexed_nom) - len(nom)) <= 3):
                    potential_ids.update(person_ids)
        
        return list(potential_ids)
    
    def _calculate_context_similarity(self, person: Person, extra_info: Dict) -> float:
        """Calcule la similarité contextuelle (professions, terres, etc.)"""
        score = 0.0
        
        # Bonus pour professions communes
        person_profs = set(person.profession)
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
        person_terres = set(person.terres)
        extra_terres = set(extra_info.get('terres', []))
        if person_terres and extra_terres:
            common_terres = person_terres & extra_terres
            if common_terres:
                score += 0.15 * (len(common_terres) / max(len(person_terres), len(extra_terres)))
        
        return min(score, 0.3)  # Limiter le bonus contextuel
    
    def _validate_chronological_coherence(self, person: Person, acte_date: Optional[str]) -> bool:
        """Validation chronologique obligatoire"""
        if not person.date_deces or not acte_date:
            return True
        
        from parsers.date_parser import DateParser
        date_parser = DateParser(self.config)
        
        person_death_year = date_parser.get_year_from_text(person.date_deces)
        acte_year = date_parser.get_year_from_text(acte_date)
        
        if person_death_year and acte_year and acte_year > person_death_year:
            return False
        
        return True
    
    def _select_best_candidate(self, candidates: List[Person], extra_info: Dict) -> Optional[Person]:
        """Sélectionne le meilleur candidat avec détection d'homonymes"""
        if len(candidates) == 1:
            return candidates[0]
        
        # Détection d'homonymes par terres distinctes
        terres_extra = set(extra_info.get('terres', []))
        
        for candidate in candidates:
            terres_candidate = set(candidate.terres)
            
            # Si les terres sont complètement différentes ET non vides, c'est un homonyme
            if (terres_extra and terres_candidate and 
                not terres_extra.intersection(terres_candidate)):
                self.logger.info(f"Homonyme détecté: {candidate.full_name} "
                               f"(terres: {terres_candidate} vs {terres_extra})")
                continue
            
            # Sinon, c'est probablement la même personne
            return candidate
        
        # Aucun candidat compatible (tous homonymes)
        return None
    
    def _merge_person_info(self, person: Person, extra_info: Dict):
        """Fusionne les informations avec optimisations"""
        # Fusion des professions
        if extra_info.get('professions'):
            for prof in extra_info['professions']:
                if prof not in person.profession:
                    person.profession.append(prof)
        
        # Fusion des terres
        if extra_info.get('terres'):
            for terre in extra_info['terres']:
                if terre not in person.terres:
                    person.terres.append(terre)
        
        # Mise à jour du statut (prendre le plus élevé)
        if extra_info.get('statut'):
            from core.models import PersonStatus
            statut_hierarchy = {
                PersonStatus.SEIGNEUR: 3,
                PersonStatus.ECUYER: 2, 
                PersonStatus.SIEUR: 1
            }
            
            current_rank = statut_hierarchy.get(person.statut, 0)
            new_status = getattr(PersonStatus, extra_info['statut'].upper(), None)
            new_rank = statut_hierarchy.get(new_status, 0)
            
            if new_rank > current_rank:
                person.statut = new_status
        
        # Mise à jour notable
        if extra_info.get('notable'):
            person.notable = True
        
        # Ajout des variations orthographiques
        nom_complet = extra_info.get('nom_complet', '')
        if nom_complet and nom_complet not in person.nom_variations:
            person.nom_variations.append(nom_complet)
        
        # Invalidation du cache pour cette personne
        self._invalidate_person_cache(person)
    
    def _create_new_person(self, nom: str, prenom: str, extra_info: Dict) -> Person:
        """Crée une nouvelle personne avec indexation"""
        from core.models import PersonStatus
        
        # Conversion du statut string vers enum
        statut = None
        if extra_info.get('statut'):
            try:
                statut = getattr(PersonStatus, extra_info['statut'].upper())
            except AttributeError:
                self.logger.warning(f"Statut inconnu: {extra_info['statut']}")
        
        person = Person(
            id=self.person_id_counter,
            nom=nom,
            prenom=prenom,
            profession=extra_info.get('professions', []),
            statut=statut,
            terres=extra_info.get('terres', []),
            notable=extra_info.get('notable', False),
            confidence_score=1.0
        )
        
        # Ajouter à la base et indexer
        self.persons[self.person_id_counter] = person
        self._add_to_index(person)
        self.person_id_counter += 1
        
        return person
    
    def _add_to_index(self, person: Person):
        """Ajoute une personne aux index de recherche"""
        search_key = f"{person.prenom.lower()}_{person.nom.lower()}"
        self._name_index[search_key].append(person.id)
    
    def _invalidate_person_cache(self, person: Person):
        """Invalide le cache pour une personne modifiée"""
        search_key = f"{person.nom.lower()}_{person.prenom.lower()}"
        if search_key in self._search_cache:
            del self._search_cache[search_key]
    
    def get_homonym_groups(self) -> Dict[str, List[Person]]:
        """Retourne les groupes d'homonymes"""
        name_groups = defaultdict(list)
        
        for person in self.persons.values():
            full_name = person.full_name
            name_groups[full_name].append(person)
        
        # Garder seulement les groupes avec plusieurs personnes
        return {name: persons for name, persons in name_groups.items() 
                if len(persons) > 1}
    
    def get_statistics(self) -> Dict:
        """Retourne les statistiques du manager"""
        homonym_groups = self.get_homonym_groups()
        
        return {
            'total_persons': len(self.persons),
            'persons_created': self.stats['persons_created'],
            'persons_merged': self.stats['persons_merged'],
            'homonym_groups': len(homonym_groups),
            'total_homonyms': sum(len(persons) for persons in homonym_groups.values()),
            'cache_hit_rate': (self.stats['cache_hits'] / 
                             max(1, self.stats['cache_hits'] + self.stats['cache_misses'])),
            'index_size': len(self._name_index)
        }