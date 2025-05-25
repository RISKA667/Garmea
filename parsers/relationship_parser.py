import re
import logging
from typing import List, Dict, Optional, Tuple
from functools import lru_cache
from config.settings import ParserConfig

class RelationshipParser:
    """Parser optimisé pour relations familiales dans registres paroissiaux français"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Compilation des patterns optimisés
        self._compile_relationship_patterns()
        
        # Cache des résultats
        self._relationship_cache = {}
        self._name_cache = {}
    
    def _compile_relationship_patterns(self):
        """Compile les patterns pour registres paroissiaux français réels"""
        
        # Pattern nom flexible pour registres historiques
        nom_pattern = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-]*(?:\s+[A-Za-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-]+)*'
        
        self.patterns = {
            # === FILIATIONS PRINCIPALES ===
            # "Jean Le Boucher, fils de Pierre Le Boucher et de Marie Dupré"
            'filiation_complete': re.compile(
                rf'({nom_pattern}),?\s+(?:fils|fille|filz)\s+de\s+({nom_pattern})(?:\s+et\s+(?:de\s+)?({nom_pattern}))?',
                re.IGNORECASE
            ),
            
            # "Charlotte, fille de Jean Le Boucher, éc., sr de La Granville, et de Françoise Varin"
            'filiation_avec_titres': re.compile(
                rf'({nom_pattern}),?\s+(?:fils|fille|filz)\s+de\s+({nom_pattern}(?:\s*,\s*[^,]*?)*?)(?:\s+et\s+(?:de\s+)?({nom_pattern}))?',
                re.IGNORECASE | re.DOTALL
            ),
            
            # === MARIAGES ===
            # "Françoise Picot, épouse de Charles Le Boucher"
            'epouse_de': re.compile(
                rf'({nom_pattern}),?\s+épouse\s+de\s+({nom_pattern})',
                re.IGNORECASE
            ),
            
            # "Marie, femme de Jean"
            'femme_de': re.compile(
                rf'({nom_pattern}),?\s+(?:femme|espouse)\s+de\s+({nom_pattern})',
                re.IGNORECASE
            ),
            
            # "Catherine, veuve de Pierre"
            'veuve_de': re.compile(
                rf'({nom_pattern}),?\s+veuve\s+de\s+({nom_pattern})',
                re.IGNORECASE
            ),
            
            # === PARRAINAGES ===
            # "parr.: Charles Le Boucher"
            'parrain_complet': re.compile(
                rf'parr?(?:ain)?\s*[\.:]?\s*({nom_pattern}(?:\s*,\s*[^;,]*?)*?)(?:[;,]|$|\s+marr)',
                re.IGNORECASE
            ),
            
            # "marraine: Perrette Dupré"
            'marraine_complete': re.compile(
                rf'marr?(?:aine)?\s*[\.:]?\s*({nom_pattern}(?:\s*,\s*[^;,]*?)*?)(?:[;,]|$)',
                re.IGNORECASE
            ),
            
            # === FORMATS STRUCTURÉS ===
            # Baptême complet avec parrainages
            'bapteme_structure': re.compile(
                rf'(?:baptême|bapt\.|naissance).*?(?:de\s+)?({nom_pattern}).*?(?:parr?(?:ain)?\s*[\.:]?\s*({nom_pattern})).*?(?:marr?(?:aine)?\s*[\.:]?\s*({nom_pattern}))',
                re.IGNORECASE | re.DOTALL
            ),
            
            # Mariage structuré
            'mariage_structure': re.compile(
                rf'mariage\s+de\s+({nom_pattern}).*?(?:avec|et|à)\s+({nom_pattern})',
                re.IGNORECASE | re.DOTALL
            ),
            
            # === RELATIONS CONTEXTUELLES ===
            # "Jean et Marie" (couples probables)
            'couple_et': re.compile(
                rf'({nom_pattern})\s+et\s+(?:de\s+)?({nom_pattern})',
                re.IGNORECASE
            ),
            
            # Relations avec conjonctions
            'parents_conjoints': re.compile(
                rf'({nom_pattern})\s+et\s+({nom_pattern}),?\s+(?:ses\s+)?(?:père\s+et\s+mère|parents)',
                re.IGNORECASE
            )
        }
    
    @lru_cache(maxsize=500)
    def extract_relationships(self, text: str) -> List[Dict]:
        """Extraction principale des relations avec cache optimisé"""
        if not text or len(text.strip()) < 10:
            return []
        
        # Vérifier le cache
        cache_key = hash(text[:500])  # Hash des premiers 500 caractères
        if cache_key in self._relationship_cache:
            return self._relationship_cache[cache_key]
        
        relationships = []
        processed_positions = set()
        
        # Traiter chaque pattern par priorité
        for pattern_name, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                # Éviter les chevauchements
                match_range = range(match.start(), match.end())
                if any(pos in processed_positions for pos in match_range):
                    continue
                
                relation = self._parse_relationship_match(pattern_name, match, text)
                if relation:
                    relationships.append(relation)
                    processed_positions.update(match_range)
        
        # Post-traitement pour nettoyer et valider
        relationships = self._validate_and_clean_relationships(relationships)
        
        # Mettre en cache
        self._relationship_cache[cache_key] = relationships
        
        return relationships
    
    def _parse_relationship_match(self, pattern_name: str, match: re.Match, full_text: str) -> Optional[Dict]:
        """Parse un match spécifique selon le pattern"""
        groups = match.groups()
        
        try:
            if pattern_name in ['filiation_complete', 'filiation_avec_titres']:
                enfant = self._clean_person_name(groups[0])
                pere = self._clean_person_name(groups[1]) if len(groups) > 1 and groups[1] else None
                mere = self._clean_person_name(groups[2]) if len(groups) > 2 and groups[2] else None
                
                if enfant:
                    # Détecter le genre depuis le pattern
                    match_text = match.group(0).lower()
                    genre = 'F' if 'fille' in match_text else 'M' if 'fils' in match_text or 'filz' in match_text else None
                    
                    return {
                        'type': 'filiation',
                        'enfant': enfant,
                        'pere': pere,
                        'mere': mere,
                        'genre': genre,
                        'position': (match.start(), match.end()),
                        'source_text': match.group(0)[:100]
                    }
            
            elif pattern_name in ['epouse_de', 'femme_de', 'veuve_de']:
                epouse = self._clean_person_name(groups[0])
                epoux = self._clean_person_name(groups[1])
                
                if epouse and epoux:
                    statut = 'veuve' if pattern_name == 'veuve_de' else 'mariée'
                    return {
                        'type': 'mariage',
                        'epouse': epouse,
                        'epoux': epoux,
                        'statut': statut,
                        'position': (match.start(), match.end()),
                        'source_text': match.group(0)[:100]
                    }
            
            elif pattern_name == 'parrain_complet':
                parrain = self._clean_person_name(groups[0])
                if parrain:
                    return {
                        'type': 'parrain',
                        'personne': parrain,
                        'position': (match.start(), match.end()),
                        'source_text': match.group(0)[:50]
                    }
            
            elif pattern_name == 'marraine_complete':
                marraine = self._clean_person_name(groups[0])
                if marraine:
                    return {
                        'type': 'marraine',
                        'personne': marraine,
                        'position': (match.start(), match.end()),
                        'source_text': match.group(0)[:50]
                    }
            
            elif pattern_name == 'bapteme_structure':
                enfant = self._clean_person_name(groups[0]) if groups[0] else None
                parrain = self._clean_person_name(groups[1]) if len(groups) > 1 and groups[1] else None
                marraine = self._clean_person_name(groups[2]) if len(groups) > 2 and groups[2] else None
                
                relations = []
                if enfant and parrain:
                    relations.append({
                        'type': 'parrain',
                        'enfant': enfant,
                        'personne': parrain,
                        'position': (match.start(), match.end()),
                        'source_text': match.group(0)[:100]
                    })
                if enfant and marraine:
                    relations.append({
                        'type': 'marraine',
                        'enfant': enfant,
                        'personne': marraine,
                        'position': (match.start(), match.end()),
                        'source_text': match.group(0)[:100]
                    })
                return relations[0] if relations else None
            
            elif pattern_name == 'mariage_structure':
                epoux = self._clean_person_name(groups[0])
                epouse = self._clean_person_name(groups[1])
                
                if epoux and epouse:
                    return {
                        'type': 'mariage',
                        'epoux': epoux,
                        'epouse': epouse,
                        'statut': 'mariage',
                        'position': (match.start(), match.end()),
                        'source_text': match.group(0)[:100]
                    }
            
            elif pattern_name == 'couple_et':
                personne1 = self._clean_person_name(groups[0])
                personne2 = self._clean_person_name(groups[1])
                
                if personne1 and personne2:
                    return {
                        'type': 'couple_potentiel',
                        'personne1': personne1,
                        'personne2': personne2,
                        'position': (match.start(), match.end()),
                        'source_text': match.group(0)[:50]
                    }
            
            elif pattern_name == 'parents_conjoints':
                pere = self._clean_person_name(groups[0])
                mere = self._clean_person_name(groups[1])
                
                if pere and mere:
                    return {
                        'type': 'parents_identifies',
                        'pere': pere,
                        'mere': mere,
                        'position': (match.start(), match.end()),
                        'source_text': match.group(0)[:100]
                    }
        
        except (IndexError, AttributeError) as e:
            self.logger.debug(f"Erreur parsing relation {pattern_name}: {e}")
        
        return None
    
    def _clean_person_name(self, name: str) -> Optional[str]:
        """Nettoyage avancé des noms pour registres français"""
        if not name:
            return None
        
        # Vérifier le cache
        if name in self._name_cache:
            return self._name_cache[name]
        
        original_name = name
        name = name.strip()
        
        # Supprimer les titres et qualifications en fin
        titres_suffixes = [
            r',\s*écuyer.*$', r',\s*éc\..*$', r',\s*sieur.*$', r',\s*sr\.?.*$',
            r',\s*seigneur.*$', r',\s*sgr\.?.*$', r',\s*avocat.*$', r',\s*conseiller.*$',
            r',\s*curé.*$', r',\s*prêtre.*$', r',\s*marchand.*$', r',\s*notable.*$'
        ]
        
        for suffix_pattern in titres_suffixes:
            name = re.sub(suffix_pattern, '', name, flags=re.IGNORECASE)
        
        # Nettoyer les particules problématiques
        name = re.sub(r'^(?:de|du|des|le|la|les)\s+', '', name, flags=re.IGNORECASE)
        
        # Normaliser les espaces multiples
        name = re.sub(r'\s+', ' ', name)
        
        # Supprimer les caractères de ponctuation parasites
        name = re.sub(r'[,;:\.]+$', '', name)
        name = name.strip()
        
        # Validation finale
        if len(name) < 2 or len(name) > 60:
            self._name_cache[original_name] = None
            return None
        
        # Vérifier format nom valide
        if not re.match(r'^[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß]', name):
            self._name_cache[original_name] = None
            return None
        
        # Capitalisation correcte
        words = name.split()
        capitalized_words = []
        
        for word in words:
            if word.lower() in ['de', 'du', 'des', 'le', 'la', 'les']:
                capitalized_words.append(word.lower())
            elif word.lower() in ['Le', 'Du', 'De']:  # Particules importantes
                capitalized_words.append(word.capitalize())
            else:
                capitalized_words.append(word.capitalize())
        
        clean_name = ' '.join(capitalized_words)
        
        # Cache et retour
        self._name_cache[original_name] = clean_name
        return clean_name
    
    def _validate_and_clean_relationships(self, relationships: List[Dict]) -> List[Dict]:
        """Validation et nettoyage des relations extraites"""
        if not relationships:
            return []
        
        validated = []
        seen_relations = set()
        
        for rel in relationships:
            try:
                # Créer une clé unique pour éviter les doublons
                if rel['type'] == 'filiation':
                    key = f"filiation_{rel.get('enfant', '')}_{rel.get('pere', '')}_{rel.get('mere', '')}"
                elif rel['type'] == 'mariage':
                    key = f"mariage_{rel.get('epoux', '')}_{rel.get('epouse', '')}"
                elif rel['type'] in ['parrain', 'marraine']:
                    key = f"{rel['type']}_{rel.get('personne', '')}_{rel.get('enfant', '')}"
                else:
                    key = f"{rel['type']}_{rel.get('personne1', '')}_{rel.get('personne2', '')}"
                
                if key not in seen_relations:
                    seen_relations.add(key)
                    validated.append(rel)
            
            except KeyError:
                continue
        
        return validated
    
    def extract_godparents(self, text: str) -> Dict[str, Optional[str]]:
        """Extraction spécialisée des parrainages"""
        godparents = {'parrain': None, 'marraine': None}
        
        relationships = self.extract_relationships(text)
        
        for rel in relationships:
            if rel['type'] == 'parrain' and not godparents['parrain']:
                godparents['parrain'] = rel['personne']
            elif rel['type'] == 'marraine' and not godparents['marraine']:
                godparents['marraine'] = rel['personne']
        
        return godparents
    
    def find_parents(self, text: str, child_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Trouve les parents d'un enfant spécifique"""
        relationships = self.extract_relationships(text)
        
        child_name_lower = child_name.lower()
        
        for rel in relationships:
            if rel['type'] == 'filiation':
                enfant_name = rel.get('enfant', '').lower()
                if enfant_name == child_name_lower:
                    return rel.get('pere'), rel.get('mere')
        
        return None, None
    
    def extract_marriages(self, text: str) -> List[Dict]:
        """Extraction spécialisée des mariages"""
        relationships = self.extract_relationships(text)
        marriages = []
        
        for rel in relationships:
            if rel['type'] == 'mariage':
                marriages.append({
                    'epoux': rel.get('epoux'),
                    'epouse': rel.get('epouse'),
                    'statut': rel.get('statut', 'mariée'),
                    'source_text': rel.get('source_text', '')
                })
        
        return marriages
    
    def get_statistics(self) -> Dict:
        """Statistiques du parser"""
        return {
            'cache_size': len(self._relationship_cache),
            'name_cache_size': len(self._name_cache),
            'patterns_count': len(self.patterns)
        }
    
    def clear_cache(self):
        """Vide les caches"""
        self._relationship_cache.clear()
        self._name_cache.clear()
    
    def debug_text_analysis(self, text: str) -> Dict:
        """Debug : analyse détaillée d'un texte"""
        debug_info = {
            'text_length': len(text),
            'patterns_matches': {},
            'relationships_found': [],
            'names_extracted': set()
        }
        
        # Tester chaque pattern
        for pattern_name, pattern in self.patterns.items():
            matches = list(pattern.finditer(text))
            debug_info['patterns_matches'][pattern_name] = len(matches)
            
            for match in matches[:3]:  # Limiter à 3 exemples
                debug_info['patterns_matches'][f"{pattern_name}_example"] = match.group(0)[:100]
        
        # Relations trouvées
        relationships = self.extract_relationships(text)
        debug_info['relationships_found'] = relationships
        
        # Noms uniques
        for rel in relationships:
            for key, value in rel.items():
                if isinstance(value, str) and len(value) > 2 and key != 'source_text':
                    debug_info['names_extracted'].add(value)
        
        debug_info['names_extracted'] = list(debug_info['names_extracted'])
        
        return debug_info