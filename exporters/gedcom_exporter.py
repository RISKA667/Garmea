import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Union
from pathlib import Path
import re
import numpy as np
from dataclasses import dataclass
from multiprocessing import Pool
from functools import partial

# Modèles de données optimisés
@dataclass
class GedcomDate:
    day: Optional[int] = None
    month: Optional[str] = None
    year: Optional[int] = None
    precision: str = "exact"  # exact, about, before, after
    
    def to_gedcom(self) -> str:
        parts = []
        if self.day:
            parts.append(str(self.day))
        if self.month:
            parts.append(self.month)
        if self.year:
            parts.append(str(self.year))
        return " ".join(parts) if parts else ""

class GedcomExporter:
    """Exporteur GEDCOM haute performance avec vectorisation partielle"""
    
    # Mapping statique pour les conversions
    FRENCH_TO_GEDCOM_MONTHS = {
        'janvier': 'JAN', 'février': 'FEB', 'mars': 'MAR', 'avril': 'APR',
        'mai': 'MAY', 'juin': 'JUN', 'juillet': 'JUL', 'août': 'AUG',
        'septembre': 'SEP', 'octobre': 'OCT', 'novembre': 'NOV', 'décembre': 'DEC'
    }
    
    GENDER_INFERENCE_RULES = {
        'professions': {
            'M': {'curé', 'prêtre', 'laboureur', 'maçon', 'charpentier'},
            'F': {'fileuse', 'couturière', 'ménagère'}
        },
        'titles': {
            'M': {PersonStatus.SIEUR, PersonStatus.SEIGNEUR, PersonStatus.ECUYER},
            'F': {PersonStatus.DAME, PersonStatus.DEMOISELLE}
        }
    }
    
    def __init__(self, config: ParserConfig, parallel_processing: bool = True):
        self.config = config
        self.parallel = parallel_processing
        self.logger = logging.getLogger(__name__)
        
        # Structures optimisées
        self.person_id_map: np.ndarray = None  # Vectorisé pour les accès rapides
        self.family_graph: Dict[Tuple[int, int], Set[int]] = {}  # Graphe familial
        self.date_cache: Dict[str, GedcomDate] = {}  # Cache des dates parsées
        
        # Compteurs
        self.counters = {
            'individuals': 0,
            'families': 0,
            'sources': 0,
            'media': 0
        }

    def export(self, persons: Dict[int, Person], actes: Dict[int, ActeParoissial], 
               output_path: Union[str, Path]) -> bool:
        """Export principal optimisé"""
        try:
            output_path = Path(output_path)
            self.logger.info(f"Initialisation de l'export GEDCOM vers {output_path}")
            
            # Préparation des données vectorisées
            self._prepare_data_structures(persons, actes)
            
            # Export parallélisé si activé
            with open(output_path, 'w', encoding='utf-8') as f:
                self._write_gedcom_header(f)
                
                if self.parallel:
                    with Pool() as pool:
                        # Écriture parallèle des individus
                        chunks = self._chunk_persons(persons, chunk_size=1000)
                        pool.map(partial(self._process_person_chunk, f=f), chunks)
                        
                        # Écriture des familles
                        family_chunks = self._chunk_families(chunk_size=500)
                        pool.map(partial(self._process_family_chunk, f=f), family_chunks)
                else:
                    self._write_individuals(f, persons, actes)
                    self._write_families(f, persons, actes)
                
                self._write_gedcom_trailer(f)
            
            self.logger.info(
                f"Export réussi: {self.counters['individuals']} personnes, "
                f"{self.counters['families']} familles, "
                f"{self.counters['sources']} sources, "
                f"{self.counters['media']} médias"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur critique lors de l'export: {str(e)}", exc_info=True)
            return False
    
    def _prepare_data_structures(self, persons: Dict[int, Person], actes: Dict[int, ActeParoissial]):
        """Prépare les structures de données optimisées"""
        # Vectorisation des IDs
        max_id = max(persons.keys()) if persons else 0
        self.person_id_map = np.full(max_id + 1, '', dtype='U8')
        
        for internal_id in persons.keys():
            self.person_id_map[internal_id] = f"I{self.counters['individuals']:06d}"
            self.counters['individuals'] += 1
        
        # Construction du graphe familial
        self._build_family_graph(persons)
        
        # Pré-cache des dates
        self._precache_dates(persons, actes)
    
    def _build_family_graph(self, persons: Dict[int, Person]):
        """Construit un graphe familial optimisé"""
        for person in persons.values():
            # Liens parents-enfants
            if person.pere_id or person.mere_id:
                family_key = self._get_family_key(person.pere_id, person.mere_id)
                self.family_graph.setdefault(family_key, set()).add(person.id)
            
            # Liens conjugaux
            if person.conjoint_id:
                spouse_key = self._get_family_key(person.id, person.conjoint_id)
                self.family_graph.setdefault(spouse_key, set())
    
    def _precache_dates(self, persons: Dict[int, Person], actes: Dict[int, ActeParoissial]):
        """Pré-cache les dates pour traitement rapide"""
        date_strings = set()
        
        # Dates des personnes
        for person in persons.values():
            if person.date_naissance:
                date_strings.add(person.date_naissance)
            if person.date_deces:
                date_strings.add(person.date_deces)
            if person.date_mariage:
                date_strings.add(person.date_mariage)
        
        # Dates des actes
        for acte in actes.values():
            if acte.date:
                date_strings.add(acte.date)
        
        # Parsing vectorisé
        with Pool() as pool:
            results = pool.map(self._parse_date, date_strings)
            self.date_cache = dict(zip(date_strings, results))
    
    def _parse_date(self, date_str: str) -> GedcomDate:
        """Parse une date française en objet GedcomDate optimisé"""
        if not date_str:
            return GedcomDate()
        
        # Utilisation d'expressions régulières compilées pour la performance
        date_pattern = re.compile(
            r'(?P<day>\d{1,2})?\s*(?P<month>janvier|février|mars|avril|mai|juin|'
            r'juillet|août|septembre|octobre|novembre|décembre)?\s*(?P<year>\d{4})?'
        )
        
        match = date_pattern.search(date_str.lower())
        if match:
            day = int(match.group('day')) if match.group('day') else None
            month = self.FRENCH_TO_GEDCOM_MONTHS.get(match.group('month')) if match.group('month') else None
            year = int(match.group('year')) if match.group('year') else None
            
            return GedcomDate(day=day, month=month, year=year)
        
        return GedcomDate()
    
    def _write_gedcom_header(self, f):
        """En-tête GEDCOM enrichi"""
        header = [
            "0 HEAD",
            "1 SOUR Genealogy_Parser_Pro",
            "2 VERS 3.0.0",
            "2 NAME Advanced French Parish Records Processor",
            "1 DEST ANY",
            f"1 DATE {datetime.now().strftime('%d %b %Y')}",
            f"2 TIME {datetime.now().strftime('%H:%M:%S')}",
            "1 SUBM @SUBM1@",
            "1 FILE genealogy_export.ged",
            "1 GEDC",
            "2 VERS 5.5.1",
            "2 FORM LINEAGE-LINKED",
            "1 CHAR UTF-8",
            "1 LANG French",
            "1 NOTE Export généré avec des algorithmes avancés de reconstruction familiale",
            "0 @SUBM1@ SUBM",
            "1 NAME Advanced Genealogy Parser",
            "1 ADDR Automated high-quality genealogy extraction",
            "1 WWW https://github.com/your-repo",
            "1 LANG French"
        ]
        
        f.write("\n".join(header) + "\n")
    
    def _process_person_chunk(self, person_ids: List[int], f, persons: Dict[int, Person]):
        """Traitement parallèle d'un chunk de personnes"""
        for person_id in person_ids:
            person = persons.get(person_id)
            if person:
                self._write_individual(f, person)
    
    def _write_individual(self, f, person: Person):
        """Écrit un individu avec toutes les métadonnées"""
        gedcom_id = self.person_id_map[person.id]
        
        lines = [
            f"0 @{gedcom_id}@ INDI",
            f"1 NAME {person.prenom or 'Unknown'} /{person.nom.upper() if person.nom else 'UNKNOWN'}/"
        ]
        
        # Variations de noms
        for variation in person.nom_variations:
            lines.append(f"1 NAME {variation}")
            lines.append("2 TYPE aka")
        
        # Genre inféré
        gender = self._infer_gender_advanced(person)
        if gender:
            lines.append(f"1 SEX {gender}")
        
        # Événements vitaux
        if person.date_naissance:
            lines.extend(self._create_event("BIRT", person.date_naissance, person.lieu_naissance))
        
        if person.date_deces:
            lines.extend(self._create_event("DEAT", person.date_deces, person.lieu_deces))
        
        # Profession et statut
        for profession in person.profession:
            lines.append(f"1 OCCU {profession}")
            lines.append(f"2 NOTE Source: {person.sources[0]}" if person.sources else "")
        
        # Sources et médias
        for source in person.sources:
            self.counters['sources'] += 1
            source_id = f"S{self.counters['sources']:06d}"
            lines.extend([
                f"1 SOUR @{source_id}@",
                "2 PAGE Acte de référence",
                "2 DATA",
                f"3 TEXT {source}"
            ])
        
        f.write("\n".join(lines) + "\n")
    
    def _create_event(self, event_type: str, date_str: str, place: str = None) -> List[str]:
        """Génère des lignes GEDCOM pour un événement"""
        lines = [f"1 {event_type}"]
        
        if date_str in self.date_cache:
            gedcom_date = self.date_cache[date_str].to_gedcom()
            if gedcom_date:
                lines.append(f"2 DATE {gedcom_date}")
        
        if place:
            lines.append(f"2 PLAC {place}")
            # Ajout possible de coordonnées géographiques ici
        
        return lines
    
    def _infer_gender_advanced(self, person: Person) -> Optional[str]:
        """Inférence de genre avec règles avancées"""
        # Règles basées sur la profession
        for gender, professions in self.GENDER_INFERENCE_RULES['professions'].items():
            if any(prof.lower() in professions for prof in person.profession):
                return gender
        
        # Règles basées sur le titre
        for gender, titles in self.GENDER_INFERENCE_RULES['titles'].items():
            if person.statut in titles:
                return gender
        
        # Règles basées sur les rôles dans les actes (à implémenter si disponible)
        return None
    
    def _process_family_chunk(self, family_keys: List[Tuple[int, int]], f, persons: Dict[int, Person]):
        """Traitement parallèle d'un chunk de familles"""
        for key in family_keys:
            self._write_family(f, key, persons)
    
    def _write_family(self, f, family_key: Tuple[int, int]], persons: Dict[int, Person]):
        """Écrit une famille avec toutes les relations"""
        husband_id, wife_id = family_key
        family_id = f"F{self.counters['families']:06d}"
        self.counters['families'] += 1
        
        lines = [f"0 @{family_id}@ FAM"]
        
        # Conjoints
        if husband_id and husband_id in self.person_id_map:
            lines.append(f"1 HUSB @{self.person_id_map[husband_id]}@")
        
        if wife_id and wife_id in self.person_id_map:
            lines.append(f"1 WIFE @{self.person_id_map[wife_id]}@")
        
        # Enfants
        for child_id in self.family_graph.get(family_key, set()):
            if child_id in self.person_id_map:
                lines.append(f"1 CHIL @{self.person_id_map[child_id]}@")
        
        # Événements familiaux
        marriage_date = self._get_marriage_date(husband_id, wife_id, persons)
        if marriage_date:
            lines.extend(self._create_event("MARR", marriage_date))
        
        f.write("\n".join(lines) + "\n")
    
    def _get_marriage_date(self, husband_id: int, wife_id: int, persons: Dict[int, Person]) -> Optional[str]:
        """Trouve la date de mariage la plus probable"""
        candidates = []
        
        if husband_id:
            husband = persons.get(husband_id)
            if husband and husband.date_mariage:
                candidates.append(husband.date_mariage)
        
        if wife_id:
            wife = persons.get(wife_id)
            if wife and wife.date_mariage:
                candidates.append(wife.date_mariage)
        
        # Retourne la date la plus récente si plusieurs
        return max(candidates, key=lambda d: self.date_cache[d].year) if candidates else None
    
    def _chunk_persons(self, persons: Dict[int, Person], chunk_size: int = 1000) -> List[List[int]]:
        """Découpe les personnes en chunks pour traitement parallèle"""
        ids = list(persons.keys())
        return [ids[i:i + chunk_size] for i in range(0, len(ids), chunk_size)]
    
    def _chunk_families(self, chunk_size: int = 500) -> List[List[Tuple[int, int]]]:
        """Découpe les familles en chunks pour traitement parallèle"""
        keys = list(self.family_graph.keys())
        return [keys[i:i + chunk_size] for i in range(0, len(keys), chunk_size)]
    
    def _write_gedcom_trailer(self, f):
        """Fin du fichier GEDCOM"""
        f.write("0 TRLR\n")

    @staticmethod
    def _get_family_key(parent1_id: Optional[int], parent2_id: Optional[int]) -> Tuple[int, int]:
        """Génère une clé de famille normalisée"""
        return tuple(sorted(filter(None, [parent1_id, parent2_id])))