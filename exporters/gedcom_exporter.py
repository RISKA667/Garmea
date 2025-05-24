import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple 
from pathlib import Path

from core.models import Person, ActeParoissial, ActeType, PersonStatus
from config.settings import ParserConfig

class GedcomExporter:
    """Exporteur GEDCOM conforme aux standards généalogiques"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Compteurs pour les IDs GEDCOM
        self.person_counter = 1
        self.family_counter = 1
        
        # Mappings
        self.person_id_map: Dict[int, str] = {}  # internal_id -> GEDCOM_id
        self.family_id_map: Dict[tuple, str] = {}  # (husband_id, wife_id) -> GEDCOM_family_id
        
    def export(self, persons: Dict[int, Person], actes: Dict[int, ActeParoissial], 
               output_path: str) -> bool:
        """Export principal vers fichier GEDCOM"""
        try:
            self.logger.info(f"Début export GEDCOM vers {output_path}")
            
            # Préparation des mappings
            self._prepare_mappings(persons)
            
            # Écriture du fichier
            with open(output_path, 'w', encoding='utf-8') as f:
                self._write_gedcom_header(f)
                self._write_individuals(f, persons, actes)
                self._write_families(f, persons, actes)
                self._write_gedcom_trailer(f)
            
            self.logger.info(f"Export GEDCOM terminé: {len(persons)} personnes, {len(self.family_id_map)} familles")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur export GEDCOM: {e}")
            return False
    
    def _prepare_mappings(self, persons: Dict[int, Person]):
        """Prépare les mappings ID internes -> IDs GEDCOM"""
        for internal_id in persons.keys():
            gedcom_id = f"I{self.person_counter:04d}"
            self.person_id_map[internal_id] = gedcom_id
            self.person_counter += 1
    
    def _write_gedcom_header(self, f):
        """Écrit l'en-tête GEDCOM standard"""
        f.write("0 HEAD\n")
        f.write("1 SOUR Genealogy_Parser_Enhanced\n")
        f.write("2 VERS 2.0.0\n")
        f.write("2 NAME Enhanced Genealogy Parser for French Parish Records\n")
        f.write("1 DEST ANY\n")
        f.write("1 DATE " + datetime.now().strftime("%d %b %Y") + "\n")
        f.write("2 TIME " + datetime.now().strftime("%H:%M:%S") + "\n")
        f.write("1 SUBM @SUBM1@\n")
        f.write("1 FILE genealogy_export.ged\n")
        f.write("1 GEDC\n")
        f.write("2 VERS 5.5.1\n")
        f.write("2 FORM LINEAGE-LINKED\n")
        f.write("1 CHAR UTF-8\n")
        f.write("1 LANG French\n")
        f.write("0 @SUBM1@ SUBM\n")
        f.write("1 NAME Enhanced Genealogy Parser\n")
        f.write("1 ADDR Automated genealogy extraction\n")
    
    def _write_individuals(self, f, persons: Dict[int, Person], 
                          actes: Dict[int, ActeParoissial]):
        """Écrit les enregistrements individuels"""
        for internal_id, person in persons.items():
            gedcom_id = self.person_id_map[internal_id]
            
            f.write(f"0 @{gedcom_id}@ INDI\n")
            
            # Nom
            surname = person.nom.upper() if person.nom else "UNKNOWN"
            given_name = person.prenom if person.prenom else "Unknown"
            f.write(f"1 NAME {given_name} /{surname}/\n")
            
            # Variations du nom
            for variation in person.nom_variations:
                if variation != f"{person.prenom} {person.nom}":
                    var_parts = variation.split(' ', 1)
                    if len(var_parts) == 2:
                        f.write(f"1 NAME {var_parts[0]} /{var_parts[1].upper()}/\n")
                        f.write("2 TYPE variation\n")
            
            # Sexe (inféré depuis le contexte si possible)
            gender = self._infer_gender(person, actes)
            if gender:
                f.write(f"1 SEX {gender}\n")
            
            # Naissance
            if person.date_naissance:
                f.write("1 BIRT\n")
                gedcom_date = self._convert_to_gedcom_date(person.date_naissance)
                if gedcom_date:
                    f.write(f"2 DATE {gedcom_date}\n")
                if person.lieu_naissance:
                    f.write(f"2 PLAC {person.lieu_naissance}\n")
            
            # Décès
            if person.date_deces:
                f.write("1 DEAT\n")
                gedcom_date = self._convert_to_gedcom_date(person.date_deces)
                if gedcom_date:
                    f.write(f"2 DATE {gedcom_date}\n")
                if person.lieu_deces:
                    f.write(f"2 PLAC {person.lieu_deces}\n")
            
            # Inhumation
            if person.lieu_inhumation or person.notable:
                f.write("1 BURI\n")
                if person.lieu_inhumation:
                    f.write(f"2 PLAC {person.lieu_inhumation}\n")
                elif person.notable:
                    f.write("2 PLAC Dans l'église (notable)\n")
            
            # Professions
            for profession in person.profession:
                f.write(f"1 OCCU {profession}\n")
            
            # Statut social et terres
            if person.statut or person.terres:
                title_parts = []
                if person.statut:
                    title_parts.append(person.statut.value)
                if person.terres:
                    title_parts.extend([f"sr de {terre}" for terre in person.terres])
                title = ", ".join(title_parts)
                f.write(f"1 TITL {title}\n")
            
            # Note sur la confiance et les sources
            if person.confidence_score < 1.0 or person.sources:
                f.write("1 NOTE ")
                if person.confidence_score < 1.0:
                    f.write(f"Confiance: {person.confidence_score:.2f}. ")
                if person.sources:
                    f.write(f"Sources: {'; '.join(person.sources)}")
                f.write("\n")
            
            # Famille comme enfant
            if person.pere_id or person.mere_id:
                family_key = self._get_family_key(person.pere_id, person.mere_id)
                if family_key not in self.family_id_map:
                    family_id = f"F{self.family_counter:04d}"
                    self.family_id_map[family_key] = family_id
                    self.family_counter += 1
                else:
                    family_id = self.family_id_map[family_key]
                
                f.write(f"1 FAMC @{family_id}@\n")
            
            # Famille comme conjoint
            if person.conjoint_id:
                spouse_key = self._get_family_key(internal_id, person.conjoint_id)
                if spouse_key not in self.family_id_map:
                    family_id = f"F{self.family_counter:04d}"
                    self.family_id_map[spouse_key] = family_id
                    self.family_counter += 1
                else:
                    family_id = self.family_id_map[spouse_key]
                
                f.write(f"1 FAMS @{family_id}@\n")
    
    def _write_families(self, f, persons: Dict[int, Person], 
                       actes: Dict[int, ActeParoissial]):
        """Écrit les enregistrements familiaux"""
        processed_families = set()
        
        # Familles basées sur les relations parent-enfant
        for person in persons.values():
            if person.pere_id or person.mere_id:
                family_key = self._get_family_key(person.pere_id, person.mere_id)
                
                if family_key in processed_families:
                    continue
                
                processed_families.add(family_key)
                family_id = self.family_id_map.get(family_key)
                
                if family_id:
                    f.write(f"0 @{family_id}@ FAM\n")
                    
                    # Mari
                    if person.pere_id and person.pere_id in self.person_id_map:
                        husband_gedcom_id = self.person_id_map[person.pere_id]
                        f.write(f"1 HUSB @{husband_gedcom_id}@\n")
                    
                    # Épouse
                    if person.mere_id and person.mere_id in self.person_id_map:
                        wife_gedcom_id = self.person_id_map[person.mere_id]
                        f.write(f"1 WIFE @{wife_gedcom_id}@\n")
                    
                    # Date de mariage (si disponible)
                    marriage_date = self._find_marriage_date(person.pere_id, person.mere_id, persons)
                    if marriage_date:
                        f.write("1 MARR\n")
                        gedcom_date = self._convert_to_gedcom_date(marriage_date)
                        if gedcom_date:
                            f.write(f"2 DATE {gedcom_date}\n")
                    
                    # Enfants
                    children = self._find_children(person.pere_id, person.mere_id, persons)
                    for child_id in children:
                        if child_id in self.person_id_map:
                            child_gedcom_id = self.person_id_map[child_id]
                            f.write(f"1 CHIL @{child_gedcom_id}@\n")
        
        # Familles basées sur les mariages explicites
        for person in persons.values():
            if person.conjoint_id:
                family_key = self._get_family_key(person.id, person.conjoint_id)
                
                if family_key not in processed_families and family_key in self.family_id_map:
                    processed_families.add(family_key)
                    family_id = self.family_id_map[family_key]
                    
                    f.write(f"0 @{family_id}@ FAM\n")
                    
                    # Déterminer qui est le mari et qui est l'épouse
                    gender1 = self._infer_gender(person, actes)
                    spouse = persons.get(person.conjoint_id)
                    gender2 = self._infer_gender(spouse, actes) if spouse else None
                    
                    if gender1 == 'M':
                        f.write(f"1 HUSB @{self.person_id_map[person.id]}@\n")
                        if person.conjoint_id in self.person_id_map:
                            f.write(f"1 WIFE @{self.person_id_map[person.conjoint_id]}@\n")
                    elif gender1 == 'F':
                        f.write(f"1 WIFE @{self.person_id_map[person.id]}@\n")
                        if person.conjoint_id in self.person_id_map:
                            f.write(f"1 HUSB @{self.person_id_map[person.conjoint_id]}@\n")
                    
                    if person.date_mariage:
                        f.write("1 MARR\n")
                        gedcom_date = self._convert_to_gedcom_date(person.date_mariage)
                        if gedcom_date:
                            f.write(f"2 DATE {gedcom_date}\n")
    
    def _write_gedcom_trailer(self, f):
        """Écrit la fin du fichier GEDCOM"""
        f.write("0 TRLR\n")
    
    def _get_family_key(self, parent1_id: Optional[int], parent2_id: Optional[int]) -> tuple:
        """Génère une clé unique pour une famille"""
        if parent1_id is None and parent2_id is None:
            return (None, None)
        return tuple(sorted([parent1_id, parent2_id], key=lambda x: x or 0))
    
    def _find_children(self, father_id: Optional[int], mother_id: Optional[int], 
                      persons: Dict[int, Person]) -> List[int]:
        """Trouve tous les enfants d'un couple"""
        children = []
        for person_id, person in persons.items():
            if person.pere_id == father_id and person.mere_id == mother_id:
                children.append(person_id)
        return children
    
    def _find_marriage_date(self, husband_id: Optional[int], wife_id: Optional[int], 
                           persons: Dict[int, Person]) -> Optional[str]:
        """Trouve la date de mariage d'un couple"""
        if husband_id:
            husband = persons.get(husband_id)
            if husband and husband.date_mariage:
                return husband.date_mariage
        
        if wife_id:
            wife = persons.get(wife_id)
            if wife and wife.date_mariage:
                return wife.date_mariage
        
        return None
    
    def _infer_gender(self, person: Person, actes: Dict[int, ActeParoissial]) -> Optional[str]:
        """Infère le genre d'une personne pour GEDCOM"""
        if not person:
            return None
        
        # Basé sur les professions
        if any(prof in ['curé', 'prêtre'] for prof in person.profession):
            return 'M'
        
        # Basé sur les titres
        if person.statut in [PersonStatus.SIEUR, PersonStatus.SEIGNEUR, PersonStatus.ECUYER]:
            return 'M'
        
        # Basé sur les actes (parrain/marraine)
        for acte in actes.values():
            if acte.parrain_id == person.id:
                return 'M'
            elif acte.marraine_id == person.id:
                return 'F'
        
        return None
    
    def _convert_to_gedcom_date(self, date_str: str) -> Optional[str]:
        """Convertit une date française vers le format GEDCOM"""
        if not date_str:
            return None
        
        # Mapping des mois français vers anglais pour GEDCOM
        french_to_gedcom_months = {
            'janvier': 'JAN', 'février': 'FEB', 'mars': 'MAR', 'avril': 'APR',
            'mai': 'MAY', 'juin': 'JUN', 'juillet': 'JUL', 'août': 'AUG',
            'septembre': 'SEP', 'octobre': 'OCT', 'novembre': 'NOV', 'décembre': 'DEC'
        }
        
        # Essayer de parser différents formats
        import re
        
        # Format: "13 février 1646"
        match = re.search(r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})', 
                         date_str.lower())
        if match:
            day, month_fr, year = match.groups()
            month_gedcom = french_to_gedcom_months.get(month_fr)
            if month_gedcom:
                return f"{day} {month_gedcom} {year}"
        
        # Format: année seule
        year_match = re.search(r'\b(\d{4})\b', date_str)
        if year_match:
            return year_match.group(1)
        
        return None