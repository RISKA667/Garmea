from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

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

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence_score: float = 1.0

@dataclass
class Person:
    id: Optional[int] = None
    nom: str = ""
    prenom: str = ""
    nom_variations: List[str] = field(default_factory=list)
    date_naissance: Optional[str] = None
    date_deces: Optional[str] = None
    date_mariage: Optional[str] = None
    lieu_naissance: Optional[str] = None
    lieu_deces: Optional[str] = None
    lieu_inhumation: Optional[str] = None
    profession: List[str] = field(default_factory=list)
    statut: Optional[PersonStatus] = None
    terres: List[str] = field(default_factory=list)
    pere_id: Optional[int] = None
    mere_id: Optional[int] = None
    conjoint_id: Optional[int] = None
    est_vivant: bool = True
    notable: bool = False
    confidence_score: float = 1.0
    sources: List[str] = field(default_factory=list)
    _full_name: Optional[str] = field(default=None, init=False)
    _search_key: Optional[str] = field(default=None, init=False)
    
    @property
    def full_name(self) -> str:
        if self._full_name is None:
            self._full_name = f"{self.prenom} {self.nom}".strip()
        return self._full_name
    
    @property
    def search_key(self) -> str:
        if self._search_key is None:
            self._search_key = f"{self.prenom.lower()}_{self.nom.lower()}"
        return self._search_key

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
    texte_original: str = ""
    notable: bool = False
    validation_result: Optional[ValidationResult] = None
    metadata: Dict = field(default_factory=dict)
    _year: Optional[int] = field(default=None, init=False)
    
    @property
    def year(self) -> Optional[int]:
        if self._year is None and self.date:
            import re
            match = re.search(r'\b(\d{4})\b', self.date)
            self._year = int(match.group(1)) if match else None
        return self._year