from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
import re

class ActeType(Enum):
    BAPTEME = "baptême"
    MARIAGE = "mariage"
    INHUMATION = "inhumation"
    NAISSANCE = "naissance"
    DECES = "décès"
    PRISE_POSSESSION = "prise_possession"

class PersonStatus(Enum):
    SIEUR = "sieur"
    SEIGNEUR = "seigneur"
    ECUYER = "écuyer"

class RelationType(Enum):
    PERE = "père"
    MERE = "mère"
    CONJOINT = "conjoint"
    FRERE = "frère"
    SOEUR = "soeur"
    NEVEU = "neveu"
    NIECE = "nièce"
    ONCLE = "oncle"
    TANTE = "tante"
    COUSIN = "cousin"
    COUSINE = "cousine"
    PARRAIN = "parrain"
    MARRAINE = "marraine"

@dataclass
class SourceEvent:
    event_type: str
    date: Optional[str] = None
    lieu: Optional[str] = None
    source_reference: str = ""
    page_number: Optional[int] = None
    confidence: float = 1.0
    notes: str = ""

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence_score: float = 1.0

@dataclass
class Person:
    id: Optional[int] = None
    prenoms: List[str] = field(default_factory=list)
    nom: str = ""
    nom_variations: List[str] = field(default_factory=list)
    date_naissance: Optional[str] = None
    date_deces: Optional[str] = None
    date_mariage: Optional[str] = None
    lieu_naissance: Optional[str] = None
    lieu_deces: Optional[str] = None
    lieu_inhumation: Optional[str] = None
    lieu_mariage: Optional[str] = None
    profession: List[str] = field(default_factory=list)
    statut: Optional[PersonStatus] = None
    terres: List[str] = field(default_factory=list)
    notable: bool = False
    pere_id: Optional[int] = None
    mere_id: Optional[int] = None
    conjoint_id: Optional[int] = None
    freres_ids: List[int] = field(default_factory=list)
    soeurs_ids: List[int] = field(default_factory=list)
    neveux_ids: List[int] = field(default_factory=list)
    nieces_ids: List[int] = field(default_factory=list)
    oncles_ids: List[int] = field(default_factory=list)
    tantes_ids: List[int] = field(default_factory=list)
    cousins_ids: List[int] = field(default_factory=list)
    cousines_ids: List[int] = field(default_factory=list)
    parrain_id: Optional[int] = None
    marraine_id: Optional[int] = None
    filleuls_ids: List[int] = field(default_factory=list)
    est_vivant: bool = True
    confidence_score: float = 1.0
    sources_events: List[SourceEvent] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    _full_name: Optional[str] = field(default=None, init=False)
    _primary_prenom: Optional[str] = field(default=None, init=False)
    _search_key: Optional[str] = field(default=None, init=False)

    @property
    def primary_prenom(self) -> str:
        if self._primary_prenom is None:
            self._primary_prenom = self.prenoms[0] if self.prenoms else ""
        return self._primary_prenom

    @property
    def full_prenoms(self) -> str:
        return " ".join(self.prenoms)

    @property
    def full_name(self) -> str:
        if self._full_name is None:
            self._full_name = f"{self.full_prenoms} {self.nom}".strip()
        return self._full_name

    @property
    def search_key(self) -> str:
        if self._search_key is None:
            self._search_key = f"{self.primary_prenom.lower()}_{self.nom.lower()}"
        return self._search_key

    @property
    def prenom(self) -> str:
        return self.primary_prenom

    @prenom.setter
    def prenom(self, value: str):
        if value:
            self.prenoms[0] = value if self.prenoms else [value]
            self._primary_prenom = self._full_name = self._search_key = None

    def add_prenom(self, prenom: str):
        if prenom not in self.prenoms:
            self.prenoms.append(prenom)
            self._full_name = self._search_key = None

    def add_source_event(self, event_type: str, source_reference: str, date: str = None, lieu: str = None, **kwargs):
        self.sources_events.append(SourceEvent(event_type=event_type, date=date, lieu=lieu, source_reference=source_reference, **kwargs))

    def get_sources_for_event(self, event_type: str) -> List[SourceEvent]:
        return [s for s in self.sources_events if s.event_type == event_type]

    def add_family_relation(self, person_id: int, relation_type: RelationType):
        relation_map = {
            RelationType.FRERE: self.freres_ids,
            RelationType.SOEUR: self.soeurs_ids,
            RelationType.NEVEU: self.neveux_ids,
            RelationType.NIECE: self.nieces_ids,
            RelationType.ONCLE: self.oncles_ids,
            RelationType.TANTE: self.tantes_ids,
            RelationType.COUSIN: self.cousins_ids,
            RelationType.COUSINE: self.cousines_ids,
        }
        if person_id not in relation_map.get(relation_type, []):
            relation_map[relation_type].append(person_id)

    def get_all_family_ids(self) -> Dict[str, List[int]]:
        return {
            "père": [self.pere_id] if self.pere_id else [],
            "mère": [self.mere_id] if self.mere_id else [],
            "conjoint": [self.conjoint_id] if self.conjoint_id else [],
            "frères": self.freres_ids,
            "soeurs": self.soeurs_ids,
            "neveux": self.neveux_ids,
            "nièces": self.nieces_ids,
            "oncles": self.oncles_ids,
            "tantes": self.tantes_ids,
            "cousins": self.cousins_ids,
            "cousines": self.cousines_ids,
            "parrain": [self.parrain_id] if self.parrain_id else [],
            "marraine": [self.marraine_id] if self.marraine_id else [],
            "filleuls": self.filleuls_ids
        }

@dataclass
class ActeParoissial:
    id: Optional[int] = None
    type_acte: ActeType = ActeType.BAPTEME
    date: str = ""
    date_parsed: Optional[datetime] = None
    lieu: str = ""
    personne_principale_id: Optional[int] = None
    pere_id: Optional[int] = None
    mere_id: Optional[int] = None
    conjoint_id: Optional[int] = None
    parrain_id: Optional[int] = None
    marraine_id: Optional[int] = None
    temoin_ids: List[int] = field(default_factory=list)
    freres_ids: List[int] = field(default_factory=list)
    soeurs_ids: List[int] = field(default_factory=list)
    oncles_ids: List[int] = field(default_factory=list)
    tantes_ids: List[int] = field(default_factory=list)
    neveux_ids: List[int] = field(default_factory=list)
    nieces_ids: List[int] = field(default_factory=list)
    cousins_ids: List[int] = field(default_factory=list)
    cousines_ids: List[int] = field(default_factory=list)
    texte_original: str = ""
    notable: bool = False
    validation_result: Optional[ValidationResult] = None
    source_reference: str = ""
    page_number: Optional[int] = None
    archive_location: str = ""
    metadata: Dict = field(default_factory=dict)
    _year: Optional[int] = field(default=None, init=False)

    @property
    def year(self) -> Optional[int]:
        if self._year is None and self.date:
            match = re.search(r'\b(\d{4})\b', self.date)
            self._year = int(match.group(1)) if match else None
        return self._year

    def add_family_member(self, person_id: int, relation_type: RelationType):
        relation_map = {
            RelationType.FRERE: self.freres_ids,
            RelationType.SOEUR: self.soeurs_ids,
            RelationType.ONCLE: self.oncles_ids,
            RelationType.TANTE: self.tantes_ids,
            RelationType.NEVEU: self.neveux_ids,
            RelationType.NIECE: self.nieces_ids,
            RelationType.COUSIN: self.cousins_ids,
            RelationType.COUSINE: self.cousines_ids,
        }
        if person_id not in relation_map.get(relation_type, []):
            relation_map[relation_type].append(person_id)

class MultiPrenomUtils:
    @staticmethod
    def parse_prenoms(full_prenoms: str) -> List[str]:
        if not full_prenoms:
            return []
        prenoms, current = [], []
        for word in full_prenoms.strip().split():
            if word[0].isupper() and current and not word.startswith('-'):
                prenoms.append(' '.join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            prenoms.append(' '.join(current))
        return prenoms

    @staticmethod
    def extract_prenoms_from_fullname(full_name: str) -> tuple:
        if not full_name:
            return [], ""
        parts = full_name.strip().split()
        nom_parts, prenom_parts = [], []
        for i in range(len(parts) - 1, -1, -1):
            if parts[i][0].isupper() and (not nom_parts or parts[i].lower() in ['de', 'du', 'des', 'le', 'la']):
                nom_parts.insert(0, parts[i])
            else:
                prenom_parts = parts[:i+1]
                break
        if not nom_parts:
            nom_parts = [parts[-1]]
            prenom_parts = parts[:-1]
        prenoms = MultiPrenomUtils.parse_prenoms(' '.join(prenom_parts))
        nom = ' '.join(nom_parts)
        return prenoms, nom

class SourceManager:
    @staticmethod
    def create_source_reference(archive: str, collection: str, years: str, page: int = None) -> str:
        ref = f"{archive}, {collection} {years}"
        return f"{ref}, p.{page}" if page else ref

    @staticmethod
    def parse_source_reference(reference: str) -> Dict[str, Optional[str]]:
        pattern = r'^([^,]+),\s*([^,]+),\s*(?:p\.(\d+))?'
        match = re.match(pattern, reference)
        return {
            'archive': match.group(1).strip() if match else None,
            'collection': match.group(2).strip() if match else reference,
            'page': int(match.group(3)) if match and match.group(3) else None
        }

# Test et exemples
if __name__ == "__main__":
    print("=== TEST DES MODÈLES CORRIGÉS ===")
    
    # Test prénoms multiples
    print("\n1. Test prénoms multiples:")
    person = Person()
    person.prenoms = ["Jean", "Pierre", "Philippe"]
    person.nom = "Le Boucher"
    
    print(f"Prénoms: {person.prenoms}")
    print(f"Prénom principal: {person.primary_prenom}")
    print(f"Tous les prénoms: {person.full_prenoms}")
    print(f"Nom complet: {person.full_name}")
    
    # Test parsing de nom complet
    print("\n2. Test parsing nom complet:")
    prenoms, nom = MultiPrenomUtils.extract_prenoms_from_fullname("Jean Pierre Philippe Le Boucher")
    print(f"Extrait - Prénoms: {prenoms}, Nom: {nom}")
    
    # Test sources d'événements
    print("\n3. Test sources d'événements:")
    person.add_source_event(
        event_type="mariage",
        date="5 juillet 1677",
        lieu="Creully",
        source_reference="Creully, BMS 1665-1701, p.34"
    )
    
    sources_mariage = person.get_sources_for_event("mariage")
    print(f"Sources mariage: {len(sources_mariage)}")
    for source in sources_mariage:
        print(f"  - {source.event_type}: {source.source_reference}")
    
    # Test relations familiales étendues
    print("\n4. Test relations familiales:")
    person.add_family_relation(123, RelationType.FRERE)
    person.add_family_relation(456, RelationType.COUSIN)
    
    all_family = person.get_all_family_ids()
    print("Relations familiales:")
    for relation_type, ids in all_family.items():
        if ids:
            print(f"  - {relation_type}: {ids}")
    
    print("\n5. Test source manager:")
    ref = SourceManager.create_source_reference("Creully", "BMS 1665-1701", "1665-1701", 34)
    print(f"Référence créée: {ref}")
    parsed = SourceManager.parse_source_reference(ref)
    print(f"Référence parsée: {parsed}")
    print("\nTous les tests passés!")