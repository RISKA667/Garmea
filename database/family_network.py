import logging
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from core.models import Person, ActeParoissial
from config.settings import ParserConfig

@dataclass
class FamilyRelation:
    person1_id: int
    person2_id: int
    relation_type: str
    confidence: float
    evidence: List[str]

@dataclass
class FamilyNetwork:
    persons: Dict[int, Person]
    relations: List[FamilyRelation]
    generations: Dict[int, int]
    family_groups: List[Set[int]]
class FamilyNetworkAnalyzer:
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def build_family_network(self, persons: Dict[int, Person], 
                           actes: Dict[int, ActeParoissial]) -> FamilyNetwork:
        self.logger.info(f"Construction du réseau familial pour {len(persons)} personnes")
        relations = self._extract_all_relations(persons, actes)
        generations = self._calculate_generations(persons, relations)
        family_groups = self._identify_family_groups(persons, relations)
        inferred_relations = self._infer_missing_relations(persons, relations, actes)
        relations.extend(inferred_relations)
        network = FamilyNetwork(
            persons=persons,
            relations=relations,
            generations=generations,
            family_groups=family_groups)
        self.logger.info(f"Réseau construit: {len(relations)} relations, {len(family_groups)} groupes familiaux")
        return network
    
    def _extract_all_relations(self, persons: Dict[int, Person], 
                              actes: Dict[int, ActeParoissial]) -> List[FamilyRelation]:
        relations = []
        
        for person in persons.values():
            if person.pere_id:
                relations.append(FamilyRelation(
                    person1_id=person.pere_id,
                    person2_id=person.id,
                    relation_type='parent',
                    confidence=0.95,
                    evidence=[f"Père déclaré de {person.full_name}"]))
            
            if person.mere_id:
                relations.append(FamilyRelation(
                    person1_id=person.mere_id,
                    person2_id=person.id,
                    relation_type='parent',
                    confidence=0.95,
                    evidence=[f"Mère déclarée de {person.full_name}"]))
            
            if person.conjoint_id:
                relations.append(FamilyRelation(
                    person1_id=person.id,
                    person2_id=person.conjoint_id,
                    relation_type='spouse',
                    confidence=0.90,
                    evidence=[f"Conjoint déclaré"]))
        
        for acte in actes.values():
            if acte.parrain_id and acte.personne_principale_id:
                relations.append(FamilyRelation(
                    person1_id=acte.parrain_id,
                    person2_id=acte.personne_principale_id,
                    relation_type='godparent',
                    confidence=0.85,
                    evidence=[f"Parrain lors du baptême {acte.date}"]))
            
            if acte.marraine_id and acte.personne_principale_id:
                relations.append(FamilyRelation(
                    person1_id=acte.marraine_id,
                    person2_id=acte.personne_principale_id,
                    relation_type='godparent',
                    confidence=0.85,
                    evidence=[f"Marraine lors du baptême {acte.date}"]))
        return relations
    
    def _calculate_generations(self, persons: Dict[int, Person], 
                             relations: List[FamilyRelation]) -> Dict[int, int]:
        generations = {}
        parent_child_graph = defaultdict(list)
        child_parent_graph = defaultdict(list)
        
        for relation in relations:
            if relation.relation_type == 'parent':
                parent_child_graph[relation.person1_id].append(relation.person2_id)
                child_parent_graph[relation.person2_id].append(relation.person1_id)
        
        roots = []
        for person_id in persons.keys():
            if person_id not in child_parent_graph:
                roots.append(person_id)
        
        queue = deque([(root_id, 0) for root_id in roots])
        visited = set()
        
        while queue:
            person_id, generation = queue.popleft()
            
            if person_id in visited:
                continue
            
            visited.add(person_id)
            generations[person_id] = generation
            
            for child_id in parent_child_graph[person_id]:
                if child_id not in visited:
                    queue.append((child_id, generation + 1))
        
        for person_id in persons.keys():
            if person_id not in generations:
                generations[person_id] = 0
        return generations
    
    def _identify_family_groups(self, persons: Dict[int, Person], 
                               relations: List[FamilyRelation]) -> List[Set[int]]:
        graph = defaultdict(set)
        for relation in relations:
            if relation.relation_type in ['parent', 'spouse', 'sibling']:
                graph[relation.person1_id].add(relation.person2_id)
                graph[relation.person2_id].add(relation.person1_id)
        
        visited = set()
        family_groups = []
        
        for person_id in persons.keys():
            if person_id not in visited:
                group = self._dfs_family_group(person_id, graph, visited)
                if len(group) > 1:
                    family_groups.append(group)
        
        return family_groups
    
    def _dfs_family_group(self, start_id: int, graph: Dict[int, Set[int]], 
                         visited: Set[int]) -> Set[int]:
        group = set()
        stack = [start_id]
        
        while stack:
            person_id = stack.pop()
            
            if person_id in visited:
                continue
            
            visited.add(person_id)
            group.add(person_id)
            
            for connected_id in graph[person_id]:
                if connected_id not in visited:
                    stack.append(connected_id)
        return group
    
    def _infer_missing_relations(self, persons: Dict[int, Person], 
                               existing_relations: List[FamilyRelation],
                               actes: Dict[int, ActeParoissial]) -> List[FamilyRelation]:
        inferred_relations = []
        siblings = self._infer_sibling_relations(persons, existing_relations)
        inferred_relations.extend(siblings)
        marriages = self._infer_marriage_relations(persons, existing_relations)
        inferred_relations.extend(marriages)
        grandparent_relations = self._infer_grandparent_relations(persons, existing_relations)
        inferred_relations.extend(grandparent_relations)
        return inferred_relations
    
    def _infer_sibling_relations(self, persons: Dict[int, Person], 
                               relations: List[FamilyRelation]) -> List[FamilyRelation]:
        siblings = []
        children_by_parents = defaultdict(list)
        
        for relation in relations:
            if relation.relation_type == 'parent':
                parent_id = relation.person1_id
                child_id = relation.person2_id
                children_by_parents[parent_id].append(child_id)
        
        for parent_id, children in children_by_parents.items():
            if len(children) > 1:
                for i, child1_id in enumerate(children):
                    for child2_id in children[i+1:]:
                        siblings.append(FamilyRelation(
                            person1_id=child1_id,
                            person2_id=child2_id,
                            relation_type='sibling',
                            confidence=0.85,
                            evidence=[f"Enfants du même parent (ID: {parent_id})"]))
        return siblings
    
    def _infer_marriage_relations(self, persons: Dict[int, Person], 
                                relations: List[FamilyRelation]) -> List[FamilyRelation]:
        marriages = []
        parent_pairs = defaultdict(list)
        
        for person in persons.values():
            if person.pere_id and person.mere_id:
                pair_key = tuple(sorted([person.pere_id, person.mere_id]))
                parent_pairs[pair_key].append(person.id)      
        existing_marriages = {
            (rel.person1_id, rel.person2_id) for rel in relations 
            if rel.relation_type == 'spouse'}
        
        for (parent1_id, parent2_id), children in parent_pairs.items():
            pair_key = tuple(sorted([parent1_id, parent2_id]))
            
            if pair_key not in existing_marriages and len(children) > 0:
                marriages.append(FamilyRelation(
                    person1_id=parent1_id,
                    person2_id=parent2_id,
                    relation_type='spouse',
                    confidence=0.80,
                    evidence=[f"Parents communs de {len(children)} enfant(s)"]))
        return marriages
    
    def _infer_grandparent_relations(self, persons: Dict[int, Person], 
                                   relations: List[FamilyRelation]) -> List[FamilyRelation]:
        grandparent_relations = []
        parent_child_map = {}
        for relation in relations:
            if relation.relation_type == 'parent':
                parent_child_map[relation.person2_id] = relation.person1_id
        
        for person_id, parent_id in parent_child_map.items():
            grandparent_id = parent_child_map.get(parent_id)
            if grandparent_id:
                grandparent_relations.append(FamilyRelation(
                    person1_id=grandparent_id,
                    person2_id=person_id,
                    relation_type='grandparent',
                    confidence=0.75,
                    evidence=[f"Grand-parent inféré via {parent_id}"]))
        return grandparent_relations
    
    def analyze_family_patterns(self, network: FamilyNetwork) -> Dict:
        analysis = {
            'total_persons': len(network.persons),
            'total_relations': len(network.relations),
            'family_groups': len(network.family_groups),
            'generation_depth': max(network.generations.values()) if network.generations else 0,
            'relation_types': defaultdict(int),
            'largest_family': 0,
            'average_children_per_couple': 0}
        
        for relation in network.relations:
            analysis['relation_types'][relation.relation_type] += 1
        
        if network.family_groups:
            analysis['largest_family'] = max(len(group) for group in network.family_groups)
        
        couples_with_children = defaultdict(int)
        for relation in network.relations:
            if relation.relation_type == 'parent':
                parent_id = relation.person1_id
                for other_rel in network.relations:
                    if (other_rel.relation_type == 'spouse' and 
                        parent_id in [other_rel.person1_id, other_rel.person2_id]):
                        couple_key = tuple(sorted([other_rel.person1_id, other_rel.person2_id]))
                        couples_with_children[couple_key] += 1
        
        if couples_with_children:
            analysis['average_children_per_couple'] = sum(couples_with_children.values()) / len(couples_with_children)
        return dict(analysis)
    
    def find_common_ancestors(self, person1_id: int, person2_id: int, 
                            network: FamilyNetwork) -> List[Tuple[int, int]]:
        ancestors1 = self._get_ancestors_path(person1_id, network.relations)
        ancestors2 = self._get_ancestors_path(person2_id, network.relations)
        common_ancestors = []
        for ancestor_id in ancestors1:
            if ancestor_id in ancestors2:
                distance1 = ancestors1[ancestor_id]
                distance2 = ancestors2[ancestor_id]
                common_ancestors.append((ancestor_id, distance1 + distance2))
        common_ancestors.sort(key=lambda x: x[1])
        return common_ancestors
    
    def _get_ancestors_path(self, person_id: int, relations: List[FamilyRelation]) -> Dict[int, int]:
        ancestors = {}
        queue = deque([(person_id, 0)])
        visited = set()
        
        while queue:
            current_id, distance = queue.popleft()
            
            if current_id in visited:
                continue
            visited.add(current_id)
            
            if distance > 0:
                ancestors[current_id] = distance
            
            for relation in relations:
                if (relation.relation_type == 'parent' and 
                    relation.person2_id == current_id and
                    relation.person1_id not in visited):
                    queue.append((relation.person1_id, distance + 1))
        return ancestors