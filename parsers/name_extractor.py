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
        
        # Patterns compilés pour prénoms multiples
        self.name_patterns = []
        self._compile_enhanced_patterns()
        
        # Patterns pour relations familiales étendues
        self.family_relation_patterns = self._compile_family_patterns()
        
        # Caches
        self._false_positives_cache = set()
        self._extraction_cache = {}
        self._validation_cache = {}
        
        # Statistiques
        self.stats = {
            'names_extracted': 0,
            'multiple_prenoms_found': 0,
            'extended_relations_found': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'sources_extracted': 0
        }
    
    def _compile_enhanced_patterns(self):
        """Compile les patterns pour supporter les prénoms multiples"""
        
        # Pattern pour prénom multiple : "Jean Pierre", "Marie Anne", etc.
        multi_prenom_pattern = r'(?:[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)*)'
        
        try:
            self.name_patterns = [
                # Pattern 1: Prénoms multiples + "Le + Nom"
                # Ex: "Jean Pierre Philippe Le Boucher"
                re.compile(
                    rf'\b({multi_prenom_pattern})\s+(Le\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß]+)*)',
                    re.UNICODE
                ),
                
                # Pattern 2: Prénoms multiples + particules "de"
                # Ex: "Jean Pierre de Montigny"
                re.compile(
                    rf'\b({multi_prenom_pattern})\s+(de\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-Za-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)*)',
                    re.UNICODE
                ),
                
                # Pattern 3: Prénoms multiples + "du"
                # Ex: "Pierre Jean du Marais"
                re.compile(
                    rf'\b({multi_prenom_pattern})\s+(du\s+[A-Za-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)',
                    re.UNICODE | re.IGNORECASE
                ),
                
                # Pattern 4: Prénoms multiples + nom simple
                # Ex: "Jean Pierre Martin", "Marie Anne Dubois"
                re.compile(
                    rf'\b({multi_prenom_pattern})\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]{{2,}})',
                    re.UNICODE
                )
            ]
            
            self.logger.debug(f"Patterns pour prénoms multiples compilés: {len(self.name_patterns)}")
            
        except Exception as e:
            self.logger.error(f"Erreur compilation patterns prénoms multiples: {e}")
            # Fallback vers patterns simples
            self.name_patterns = [
                re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+([A-Z][a-z]+)\b')
            ]
    
    def _compile_family_patterns(self) -> Dict[str, re.Pattern]:
        """Compile les patterns pour relations familiales étendues"""
        
        name_pattern = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+)*'
        
        return {
            # Relations de base (maintenues)
            'filiation_fils': re.compile(
                rf'({name_pattern}),?\s+fils\s+de\s+({name_pattern})(?:\s+et\s+de\s+({name_pattern}))?',
                re.IGNORECASE
            ),
            'filiation_fille': re.compile(
                rf'({name_pattern}),?\s+fille\s+de\s+({name_pattern})(?:\s+et\s+de\s+({name_pattern}))?',
                re.IGNORECASE
            ),
            'epouse': re.compile(
                rf'({name_pattern}),?\s+épouse\s+de\s+({name_pattern})',
                re.IGNORECASE
            ),
            
            # NOUVELLES relations étendues
            'frere': re.compile(
                rf'({name_pattern}),?\s+frère\s+de\s+({name_pattern})',
                re.IGNORECASE
            ),
            'soeur': re.compile(
                rf'({name_pattern}),?\s+s[oœ]ur\s+de\s+({name_pattern})',
                re.IGNORECASE
            ),
            'neveu': re.compile(
                rf'({name_pattern}),?\s+neveu\s+de\s+({name_pattern})',
                re.IGNORECASE
            ),
            'niece': re.compile(
                rf'({name_pattern}),?\s+nièce\s+de\s+({name_pattern})',
                re.IGNORECASE
            ),
            'oncle': re.compile(
                rf'({name_pattern}),?\s+oncle\s+de\s+({name_pattern})',
                re.IGNORECASE
            ),
            'tante': re.compile(
                rf'({name_pattern}),?\s+tante\s+de\s+({name_pattern})',
                re.IGNORECASE
            ),
            'cousin': re.compile(
                rf'({name_pattern}),?\s+cousin\s+de\s+({name_pattern})',
                re.IGNORECASE
            ),
            'cousine': re.compile(
                rf'({name_pattern}),?\s+cousine\s+de\s+({name_pattern})',
                re.IGNORECASE
            ),
            
            # Parrainages (maintenues)
            'parrain': re.compile(
                rf'parrain\s*:\s*({name_pattern})',
                re.IGNORECASE
            ),
            'marraine': re.compile(
                rf'marraine\s*:\s*({name_pattern})',
                re.IGNORECASE
            )
        }
    
    def extract_complete_names_with_sources(self, text: str, 
                                          source_reference: str = "",
                                          page_number: int = None) -> List[Dict]:
        """Extraction complète avec prénoms multiples et sources"""
        
        if not text or not isinstance(text, str):
            self.logger.warning(f"Texte invalide pour extraction: {type(text)}")
            return []
        
        # Cache avec source
        cache_key = self._create_cache_key(text, source_reference)
        
        if cache_key in self._extraction_cache:
            self.stats['cache_hits'] += 1
            return self._extraction_cache[cache_key]
        
        self.stats['cache_misses'] += 1
        
        # Extraction des personnes avec prénoms multiples
        persons = self._extract_persons_with_multiple_prenoms(text, source_reference, page_number)
        
        # Extraction des relations familiales étendues
        relations = self._extract_extended_family_relations(text, source_reference)
        
        # Associer les relations aux personnes
        persons = self._associate_relations_to_persons(persons, relations)
        
        # Déduplication finale
        persons = self._deduplicate_persons(persons)
        
        # Mise en cache
        self._extraction_cache[cache_key] = persons
        self.stats['names_extracted'] += len(persons)
        
        self.logger.debug(f"Extrait {len(persons)} personnes avec {len(relations)} relations")
        return persons
    
    def _extract_persons_with_multiple_prenoms(self, text: str, 
                                             source_reference: str,
                                             page_number: int = None) -> List[Dict]:
        """Extraction des personnes avec support prénoms multiples"""
        
        persons = []
        found_names = set()
        
        for pattern in self.name_patterns:
            for match in pattern.finditer(text):
                prenoms_str = match.group(1).strip()
                nom = match.group(2).strip()
                
                # Parser les prénoms multiples
                prenoms = self._parse_multiple_prenoms(prenoms_str)
                
                if not prenoms or not nom:
                    continue
                
                full_name = f"{prenoms_str} {nom}"
                
                if full_name in found_names or not self._is_valid_name_multiple_prenoms(prenoms, nom):
                    continue
                
                found_names.add(full_name)
                
                # Si plusieurs prénoms détectés
                if len(prenoms) > 1:
                    self.stats['multiple_prenoms_found'] += 1
                    self.logger.debug(f"Prénoms multiples détectés: {prenoms} {nom}")
                
                # Extraction des attributs contextuels
                context_start = max(0, match.start() - 100)
                context_end = min(len(text), match.end() + 100)
                context = text[context_start:context_end]
                
                person_info = {
                    'nom_complet': full_name,
                    'prenoms': prenoms,  # NOUVEAU: Liste des prénoms
                    'prenom': prenoms[0],  # Premier prénom pour compatibilité
                    'nom': nom,
                    'context': context,
                    'professions': self._extract_professions_from_context(context, full_name),
                    'statut': self._extract_status_from_context(context, full_name),
                    'terres': self._extract_terres_from_context(context, full_name),
                    'notable': self._is_notable_from_context(context),
                    'source_reference': source_reference,
                    'page_number': page_number,
                    'position': (match.start(), match.end())
                }
                
                persons.append(person_info)
        
        return persons
    
    def _parse_multiple_prenoms(self, prenoms_str: str) -> List[str]:
        """Parse une chaîne contenant potentiellement plusieurs prénoms"""
        
        if not prenoms_str:
            return []
        
        # Séparer par espaces
        words = prenoms_str.strip().split()
        prenoms = []
        
        for word in words:
            # Vérifier que c'est bien un prénom (commence par majuscule, pas trop long)
            if (word and 
                word[0].isupper() and 
                len(word) >= 2 and 
                len(word) <= 20 and
                word.isalpha()):
                prenoms.append(word)
        
        return prenoms
    
    def _extract_extended_family_relations(self, text: str, source_reference: str) -> List[Dict]:
        """Extraction des relations familiales étendues"""
        
        relations = []
        
        for relation_type, pattern in self.family_relation_patterns.items():
            for match in pattern.finditer(text):
                if relation_type in ['parrain', 'marraine']:
                    # Pattern différent pour parrainages
                    person_name = match.group(1).strip()
                    relation = {
                        'type': relation_type,
                        'person': person_name,
                        'source_reference': source_reference,
                        'position': (match.start(), match.end()),
                        'context': match.group(0)
                    }
                else:
                    # Relations binaires (personne1 relation personne2)
                    person1 = match.group(1).strip()
                    person2 = match.group(2).strip()
                    
                    relation = {
                        'type': relation_type,
                        'person1': person1,
                        'person2': person2,
                        'source_reference': source_reference,
                        'position': (match.start(), match.end()),
                        'context': match.group(0)
                    }
                
                relations.append(relation)
                self.stats['extended_relations_found'] += 1
        
        return relations
    
    def _associate_relations_to_persons(self, persons: List[Dict], relations: List[Dict]) -> List[Dict]:
        """Associe les relations aux personnes correspondantes"""
        
        # Créer un mapping nom -> personne
        name_to_person = {}
        for person in persons:
            name_to_person[person['nom_complet']] = person
        
        # Associer les relations
        for relation in relations:
            if relation['type'] in ['parrain', 'marraine']:
                person_name = relation['person']
                if person_name in name_to_person:
                    person = name_to_person[person_name]
                    if 'relations' not in person:
                        person['relations'] = []
                    person['relations'].append({
                        'type': relation['type'],
                        'context': relation['context']
                    })
            
            else:
                # Relations binaires
                person1_name = relation['person1']
                person2_name = relation['person2']
                
                # Ajouter la relation aux deux personnes
                if person1_name in name_to_person:
                    person1 = name_to_person[person1_name]
                    if 'relations' not in person1:
                        person1['relations'] = []
                    person1['relations'].append({
                        'type': relation['type'],
                        'avec': person2_name,
                        'context': relation['context']
                    })
                
                if person2_name in name_to_person:
                    person2 = name_to_person[person2_name]
                    if 'relations' not in person2:
                        person2['relations'] = []
                    
                    # Relation inverse
                    inverse_relations = {
                        'frere': 'frere',
                        'soeur': 'soeur', 
                        'cousin': 'cousin',
                        'cousine': 'cousine',
                        'oncle': 'neveu',
                        'tante': 'niece',
                        'neveu': 'oncle',
                        'niece': 'tante'
                    }
                    
                    inverse_type = inverse_relations.get(relation['type'], relation['type'])
                    person2['relations'].append({
                        'type': inverse_type,
                        'avec': person1_name,
                        'context': relation['context']
                    })
        
        return persons
    
    def _extract_sources_from_text(self, text: str) -> List[Dict]:
        """Extrait les références de sources du texte"""
        
        sources = []
        
        # Pattern pour sources : "Archive, Collection Années, p.XX"
        source_patterns = [
            # Ex: "Creully, BMS 1665-1701, p.34"
            r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\-\s]+),\s*([A-Z]{2,4}\s+\d{4}-\d{4}),\s*p\.(\d+)',
            
            # Ex: "Registres paroissiaux de Saint-Pierre, 1650-1700"
            r'(Registres\s+paroissiaux\s+de\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\-\s]+),\s*(\d{4}-\d{4})',
        ]
        
        for pattern in source_patterns:
            for match in re.finditer(pattern, text):
                source = {
                    'reference': match.group(0),
                    'archive': match.group(1).strip(),
                    'collection': match.group(2).strip() if len(match.groups()) > 2 else "",
                    'page': int(match.group(3)) if len(match.groups()) > 2 and match.group(3) else None,
                    'position': (match.start(), match.end())
                }
                sources.append(source)
                self.stats['sources_extracted'] += 1
        
        return sources
    
    def _is_valid_name_multiple_prenoms(self, prenoms: List[str], nom: str) -> bool:
        """Validation spécialisée pour prénoms multiples"""
        
        if not prenoms or not nom:
            return False
        
        # Vérifier chaque prénom individuellement
        for prenom in prenoms:
            if len(prenom) < 2 or len(prenom) > 20:
                return False
            if not re.match(r'^[A-ZÀ-ÿ][a-zà-ÿ\-\']*$', prenom):
                return False
            if self._is_common_word(prenom):
                return False
        
        # Vérifier le nom
        if len(nom) < 2 or len(nom) > 40:
            return False
        if not re.match(r'^[A-ZÀ-ÿ][A-Za-zà-ÿ\s\-\']*$', nom):
            return False
        
        # Vérifier que ce n'est pas un lieu connu
        full_name = f"{' '.join(prenoms)} {nom}"
        if any(lieu.lower() in full_name.lower() for lieu in self.known_places):
            return False
        
        return True
    
    def _create_cache_key(self, text: str, source_reference: str = "") -> str:
        """Crée une clé de cache incluant la source"""
        try:
            text_sample = text[:500] if len(text) > 500 else text
            cache_data = f"{text_sample}_{source_reference}"
            return hashlib.md5(cache_data.encode('utf-8')).hexdigest()
        except Exception as e:
            self.logger.debug(f"Erreur création clé cache: {e}")
            return str(hash(f"{text[:200]}_{source_reference}"))
    
    # Méthodes utilitaires (réutilisées des versions précédentes)
    def _extract_professions_from_context(self, context: str, person_name: str) -> List[str]:
        """Extraction des professions depuis le contexte"""
        # Implémentation similaire à la version précédente
        professions = []
        context_lower = context.lower()
        
        profession_patterns = [
            r'curé', r'prêtre', r'prestre',
            r'avocat\s+du\s+roi', r'avocat',
            r'conseiller', r'notaire', r'marchand'
        ]
        
        for pattern in profession_patterns:
            if re.search(pattern, context_lower):
                professions.append(pattern.replace(r'\s+', ' '))
        
        return professions
    
    def _extract_status_from_context(self, context: str, person_name: str) -> Optional[str]:
        """Extraction du statut depuis le contexte"""
        context_lower = context.lower()
        
        if re.search(r'\b(?:seigneur|sgr)\b', context_lower):
            return 'seigneur'
        elif re.search(r'\b(?:écuyer|éc\.)\b', context_lower):
            return 'écuyer'
        elif re.search(r'\b(?:sieur|sr)\b', context_lower):
            return 'sieur'
        
        return None
    
    def _extract_terres_from_context(self, context: str, person_name: str) -> List[str]:
        """Extraction des terres depuis le contexte"""
        terres = []
        
        terre_pattern = r'(?:sr|sieur|seigneur)\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?)(?:[,;.]|$)'
        
        for match in re.finditer(terre_pattern, context, re.IGNORECASE):
            terre = match.group(1).strip()
            if terre and terre not in terres:
                terres.append(terre)
        
        return terres
    
    def _is_notable_from_context(self, context: str) -> bool:
        """Détection de notabilité depuis le contexte"""
        context_lower = context.lower()
        notable_patterns = [
            "dans l'église", "sous le chœur", "près de l'autel",
            "dame", "damoiselle", "noble", "honnête femme"
        ]
        
        return any(pattern in context_lower for pattern in notable_patterns)
    
    def _is_common_word(self, word: str) -> bool:
        """Détecte les mots courants qui ne sont pas des prénoms"""
        common_words = {
            'grâce', 'jour', 'mars', 'nom', 'dieu', 'sans', 'aucune', 'opposition',
            'décès', 'naissance', 'église', 'chapelle', 'siège', 'roi', 'dans',
            'avec', 'pour', 'sur', 'sous', 'mais', 'donc', 'puis', 'ainsi'
        }
        return word.lower() in common_words
    
    def _deduplicate_persons(self, persons: List[Dict]) -> List[Dict]:
        """Déduplication des personnes avec prénoms multiples"""
        if not persons:
            return []
        
        # Grouper par nom complet normalisé
        name_groups = {}
        for person in persons:
            # Normaliser en ignorant l'ordre des prénoms
            prenoms_set = set(person.get('prenoms', [person.get('prenom', '')]))
            nom = person.get('nom', '')
            
            # Clé basée sur les prénoms (sans ordre) + nom
            key = f"{'_'.join(sorted(prenoms_set))}_{nom}".lower()
            
            if key not in name_groups:
                name_groups[key] = []
            name_groups[key].append(person)
        
        # Pour chaque groupe, garder la version la plus complète
        deduplicated = []
        for key, group in name_groups.items():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                # Prendre celle avec le plus de prénoms et d'attributs
                best = max(group, key=lambda p: (
                    len(p.get('prenoms', [])),
                    len(p.get('professions', [])),
                    len(p.get('terres', [])),
                    1 if p.get('statut') else 0
                ))
                deduplicated.append(best)
        
        return deduplicated
    
    def get_enhanced_statistics(self) -> Dict:
        """Retourne les statistiques étendues"""
        base_stats = {
            'names_extracted': self.stats['names_extracted'],
            'multiple_prenoms_found': self.stats['multiple_prenoms_found'],
            'extended_relations_found': self.stats['extended_relations_found'],
            'sources_extracted': self.stats['sources_extracted'],
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'cache_hit_rate': (self.stats['cache_hits'] / 
                             max(1, self.stats['cache_hits'] + self.stats['cache_misses'])) * 100
        }
        
        return base_stats

# Test du système amélioré
if __name__ == "__main__":
    print("=== TEST NAME EXTRACTOR AMÉLIORÉ ===")
    
    from config.settings import ParserConfig
    
    config = ParserConfig()
    extractor = NameExtractor(config)
    
    # Test avec prénoms multiples
    test_text = """
    1677, 5 juillet, mariage de Jean Pierre Philippe Le Boucher, écuyer, 
    sr de Bréville, avec Marie Anne Catherine Dupré, fille de Guillaume Dupré 
    et de Françoise Martin. Parrain: Charles Antoine Le Maistre, 
    cousin de Jean Pierre Philippe Le Boucher.
    """
    
    source_ref = "Creully, BMS 1665-1701, p.34"
    
    print("Texte de test:")
    print(test_text)
    print(f"\nSource: {source_ref}")
    
    # Extraction
    persons = extractor.extract_complete_names_with_sources(test_text, source_ref, 34)
    
    print(f"\n=== RÉSULTATS ({len(persons)} personnes) ===")
    
    for i, person in enumerate(persons, 1):
        print(f"\n{i}. {person['nom_complet']}")
        print(f"   Prénoms: {person.get('prenoms', [])}")
        print(f"   Nom: {person['nom']}")
        if person.get('professions'):
            print(f"   Professions: {person['professions']}")
        if person.get('statut'):
            print(f"   Statut: {person['statut']}")
        if person.get('terres'):
            print(f"   Terres: {person['terres']}")
        if person.get('relations'):
            print(f"   Relations: {len(person['relations'])}")
            for rel in person['relations']:
                print(f"     - {rel['type']}: {rel.get('avec', rel.get('context', ''))}")
        if person.get('source_reference'):
            print(f"   Source: {person['source_reference']}")
    
    # Statistiques
    stats = extractor.get_enhanced_statistics()
    print(f"\n=== STATISTIQUES ===")
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print("\nTest terminé!")