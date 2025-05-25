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

class RelationType(Enum):
    """Types de relations familiales étendues"""
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
    event_type: str              # "naissance", "mariage", "décès", etc.
    date: Optional[str] = None   # Date de l'événement
    lieu: Optional[str] = None   # Lieu de l'événement
    source_reference: str = ""   # Ex: "Creully, BMS 1665-1701, p.34"
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
    """Modèle Person étendu avec prénoms multiples et relations familiales complètes"""
    
    # Identité
    id: Optional[int] = None
    prenoms: List[str] = field(default_factory=list)  # MODIFIÉ: Liste de prénoms
    nom: str = ""
    nom_variations: List[str] = field(default_factory=list)
    
    # Dates et lieux
    date_naissance: Optional[str] = None
    date_deces: Optional[str] = None
    date_mariage: Optional[str] = None
    lieu_naissance: Optional[str] = None
    lieu_deces: Optional[str] = None
    lieu_inhumation: Optional[str] = None
    lieu_mariage: Optional[str] = None  # AJOUTÉ: Lieu du mariage
    
    # Statut social et professionnel
    profession: List[str] = field(default_factory=list)
    statut: Optional[PersonStatus] = None
    terres: List[str] = field(default_factory=list)
    notable: bool = False
    
    # Relations familiales de base
    pere_id: Optional[int] = None
    mere_id: Optional[int] = None
    conjoint_id: Optional[int] = None
    
    # AJOUTÉ: Relations familiales étendues
    freres_ids: List[int] = field(default_factory=list)      # Liste des frères
    soeurs_ids: List[int] = field(default_factory=list)      # Liste des soeurs
    neveux_ids: List[int] = field(default_factory=list)      # Liste des neveux
    nieces_ids: List[int] = field(default_factory=list)      # Liste des nièces
    oncles_ids: List[int] = field(default_factory=list)      # Liste des oncles
    tantes_ids: List[int] = field(default_factory=list)      # Liste des tantes
    cousins_ids: List[int] = field(default_factory=list)     # Liste des cousins
    cousines_ids: List[int] = field(default_factory=list)    # Liste des cousines
    
    # Parrainages
    parrain_id: Optional[int] = None
    marraine_id: Optional[int] = None
    filleuls_ids: List[int] = field(default_factory=list)    # Enfants dont cette personne est parrain/marraine
    
    # Métadonnées
    est_vivant: bool = True
    confidence_score: float = 1.0
    
    # AJOUTÉ: Sources détaillées par événement
    sources_events: List[SourceEvent] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)  # Sources générales (maintenu pour compatibilité)
    
    # Cache des propriétés calculées
    _full_name: Optional[str] = field(default=None, init=False)
    _primary_prenom: Optional[str] = field(default=None, init=False)
    _search_key: Optional[str] = field(default=None, init=False)
    
    @property
    def primary_prenom(self) -> str:
        """Retourne le prénom principal (le premier)"""
        if self._primary_prenom is None:
            if self.prenoms:
                self._primary_prenom = self.prenoms[0]
            else:
                self._primary_prenom = ""
        return self._primary_prenom
    
    @property
    def full_prenoms(self) -> str:
        """Retourne tous les prénoms concaténés"""
        return " ".join(self.prenoms) if self.prenoms else ""
    
    @property
    def full_name(self) -> str:
        """Nom complet avec tous les prénoms"""
        if self._full_name is None:
            if self.prenoms and self.nom:
                self._full_name = f"{self.full_prenoms} {self.nom}".strip()
            elif self.prenoms:
                self._full_name = self.full_prenoms
            elif self.nom:
                self._full_name = self.nom
            else:
                self._full_name = ""
        return self._full_name
    
    @property
    def search_key(self) -> str:
        """Clé de recherche normalisée"""
        if self._search_key is None:
            primary = self.primary_prenom.lower() if self.primary_prenom else ""
            nom_lower = self.nom.lower() if self.nom else ""
            self._search_key = f"{primary}_{nom_lower}"
        return self._search_key
    
    # AJOUTÉ: Compatibilité avec l'ancien système (propriété prenom)
    @property
    def prenom(self) -> str:
        """Retourne le prénom principal pour compatibilité"""
        return self.primary_prenom
    
    @prenom.setter
    def prenom(self, value: str):
        """Setter pour compatibilité - remplace le premier prénom"""
        if value:
            if not self.prenoms:
                self.prenoms = [value]
            else:
                self.prenoms[0] = value
            self._primary_prenom = None  # Reset cache
            self._full_name = None       # Reset cache
            self._search_key = None      # Reset cache
    
    def add_prenom(self, prenom: str):
        """Ajoute un prénom à la liste"""
        if prenom and prenom not in self.prenoms:
            self.prenoms.append(prenom)
            self._full_name = None  # Reset cache
            self._search_key = None # Reset cache
    
    def add_source_event(self, event_type: str, source_reference: str, 
                        date: str = None, lieu: str = None, **kwargs):
        """Ajoute une source pour un événement spécifique"""
        source_event = SourceEvent(
            event_type=event_type,
            date=date,
            lieu=lieu,
            source_reference=source_reference,
            **kwargs
        )
        self.sources_events.append(source_event)
    
    def get_sources_for_event(self, event_type: str) -> List[SourceEvent]:
        """Récupère les sources pour un type d'événement"""
        return [s for s in self.sources_events if s.event_type == event_type]
    
    def add_family_relation(self, person_id: int, relation_type: RelationType):
        """Ajoute une relation familiale"""
        if relation_type == RelationType.FRERE and person_id not in self.freres_ids:
            self.freres_ids.append(person_id)
        elif relation_type == RelationType.SOEUR and person_id not in self.soeurs_ids:
            self.soeurs_ids.append(person_id)
        elif relation_type == RelationType.NEVEU and person_id not in self.neveux_ids:
            self.neveux_ids.append(person_id)
        elif relation_type == RelationType.NIECE and person_id not in self.nieces_ids:
            self.nieces_ids.append(person_id)
        elif relation_type == RelationType.ONCLE and person_id not in self.oncles_ids:
            self.oncles_ids.append(person_id)
        elif relation_type == RelationType.TANTE and person_id not in self.tantes_ids:
            self.tantes_ids.append(person_id)
        elif relation_type == RelationType.COUSIN and person_id not in self.cousins_ids:
            self.cousins_ids.append(person_id)
        elif relation_type == RelationType.COUSINE and person_id not in self.cousines_ids:
            self.cousines_ids.append(person_id)
    
    def get_all_family_ids(self) -> Dict[str, List[int]]:
        """Retourne tous les IDs de famille organisés par type de relation"""
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
    """Modèle ActeParoissial avec sources détaillées"""
    
    id: Optional[int] = None
    type_acte: ActeType = ActeType.BAPTEME
    date: str = ""
    date_parsed: Optional[datetime] = None
    lieu: str = ""
    
    # Personnes impliquées
    personne_principale_id: Optional[int] = None
    pere_id: Optional[int] = None
    mere_id: Optional[int] = None
    conjoint_id: Optional[int] = None
    parrain_id: Optional[int] = None
    marraine_id: Optional[int] = None
    temoin_ids: List[int] = field(default_factory=list)
    
    # AJOUTÉ: Relations familiales étendues dans les actes
    freres_ids: List[int] = field(default_factory=list)
    soeurs_ids: List[int] = field(default_factory=list)
    oncles_ids: List[int] = field(default_factory=list)
    tantes_ids: List[int] = field(default_factory=list)
    neveux_ids: List[int] = field(default_factory=list)
    nieces_ids: List[int] = field(default_factory=list)
    cousins_ids: List[int] = field(default_factory=list)
    cousines_ids: List[int] = field(default_factory=list)
    
    # Contenu et validation
    texte_original: str = ""
    notable: bool = False
    validation_result: Optional[ValidationResult] = None
    
    # AJOUTÉ: Source détaillée de l'acte
    source_reference: str = ""  # Ex: "Creully, BMS 1665-1701, p.34"
    page_number: Optional[int] = None
    archive_location: str = ""   # Localisation aux archives
    
    # Métadonnées
    metadata: Dict = field(default_factory=dict)
    _year: Optional[int] = field(default=None, init=False)
    
    @property
    def year(self) -> Optional[int]:
        """Extrait l'année de la date"""
        if self._year is None and self.date:
            import re
            match = re.search(r'\b(\d{4})\b', self.date)
            self._year = int(match.group(1)) if match else None
        return self._year
    
    def add_family_member(self, person_id: int, relation_type: RelationType):
        """Ajoute un membre de famille à l'acte"""
        if relation_type == RelationType.FRERE:
            if person_id not in self.freres_ids:
                self.freres_ids.append(person_id)
        elif relation_type == RelationType.SOEUR:
            if person_id not in self.soeurs_ids:
                self.soeurs_ids.append(person_id)
        elif relation_type == RelationType.ONCLE:
            if person_id not in self.oncles_ids:
                self.oncles_ids.append(person_id)
        elif relation_type == RelationType.TANTE:
            if person_id not in self.tantes_ids:
                self.tantes_ids.append(person_id)
        elif relation_type == RelationType.NEVEU:
            if person_id not in self.neveux_ids:
                self.neveux_ids.append(person_id)
        elif relation_type == RelationType.NIECE:
            if person_id not in self.nieces_ids:
                self.nieces_ids.append(person_id)
        elif relation_type == RelationType.COUSIN:
            if person_id not in self.cousins_ids:
                self.cousins_ids.append(person_id)
        elif relation_type == RelationType.COUSINE:
            if person_id not in self.cousines_ids:
                self.cousines_ids.append(person_id)


# AJOUTÉ: Utilitaires pour la gestion des prénoms multiples
class MultiPrenomUtils:
    """Utilitaires pour gérer les prénoms multiples"""
    
    @staticmethod
    def parse_prenoms(full_prenoms: str) -> List[str]:
        """Parse une chaîne de prénoms multiples"""
        if not full_prenoms:
            return []
        
        # Séparer par espaces, en gardant les prénoms composés avec tiret
        prenoms = []
        words = full_prenoms.strip().split()
        
        current_prenom = []
        for word in words:
            # Si le mot commence par une majuscule et qu'on a déjà un prénom en cours
            # C'est un nouveau prénom
            if word[0].isupper() and current_prenom and not word.startswith('-'):
                prenoms.append(' '.join(current_prenom))
                current_prenom = [word]
            else:
                current_prenom.append(word)
        
        # Ajouter le dernier prénom
        if current_prenom:
            prenoms.append(' '.join(current_prenom))
        
        return prenoms
    
    @staticmethod
    def extract_prenoms_from_fullname(full_name: str) -> tuple:
        """Extrait les prénoms et le nom d'un nom complet"""
        if not full_name:
            return [], ""
        
        parts = full_name.strip().split()
        if len(parts) < 2:
            return [parts[0]] if parts else [], ""
        
        # Le nom de famille est généralement la dernière partie
        # sauf si elle commence par une minuscule (particule)
        nom_parts = []
        prenom_parts = []
        
        # Chercher la première partie qui ressemble à un nom de famille (commence par majuscule)
        # en partant de la fin
        for i in range(len(parts) - 1, -1, -1):
            if parts[i][0].isupper() and (len(nom_parts) == 0 or parts[i].lower() in ['de', 'du', 'des', 'le', 'la']):
                nom_parts.insert(0, parts[i])
            else:
                prenom_parts = parts[:i+1]
                break
        
        if not nom_parts:
            # Si aucun nom de famille détecté, prendre la dernière partie
            nom_parts = [parts[-1]]
            prenom_parts = parts[:-1]
        
        prenoms = MultiPrenomUtils.parse_prenoms(' '.join(prenom_parts))
        nom = ' '.join(nom_parts)
        
        return prenoms, nom

# AJOUTÉ: Gestionnaire de sources
class SourceManager:
    """Gestionnaire des sources documentaires"""
    
    @staticmethod
    def create_source_reference(archive: str, collection: str, 
                              years: str, page: int = None) -> str:
        """Crée une référence de source standardisée"""
        reference = f"{archive}, {collection} {years}"
        if page:
            reference += f", p.{page}"
        return reference
    
    @staticmethod
    def parse_source_reference(reference: str) -> Dict[str, Optional[str]]:
        """Parse une référence de source"""
        import re
        
        # Pattern pour "Creully, BMS 1665-1701, p.34"
        pattern = r'^([^,]+),\s*([^,]+),\s*(?:p\.(\d+))?'
        match = re.match(pattern, reference)
        
        if match:
            return {
                'archive': match.group(1).strip(),
                'collection': match.group(2).strip(),
                'page': int(match.group(3)) if match.group(3) else None
            }
        
        return {
            'archive': None,
            'collection': reference,
            'page': None
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