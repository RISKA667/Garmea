import json
import logging
from datetime import datetime
from typing import Dict, Any, List  # CORRECTION: Ajouter List
from pathlib import Path

from core.models import Person, ActeParoissial
from config.settings import ParserConfig

class JsonExporter:
    """Exporteur JSON avec structure enrichie pour APIs"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def export(self, persons: Dict[int, Person], actes: Dict[int, ActeParoissial], 
               output_path: str) -> bool:
        """Export principal vers fichier JSON"""
        try:
            self.logger.info(f"Début export JSON vers {output_path}")
            
            # Construction de la structure JSON
            json_data = {
                "metadata": self._build_metadata(persons, actes),
                "persons": self._serialize_persons(persons),
                "actes": self._serialize_actes(actes),
                "relationships": self._extract_relationships(persons, actes),
                "statistics": self._calculate_statistics(persons, actes),
                "indexes": self._build_indexes(persons, actes)
            }
            
            # Écriture du fichier
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Export JSON terminé: {len(persons)} personnes, {len(actes)} actes")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur export JSON: {e}")
            return False
    
    def _build_metadata(self, persons: Dict[int, Person], 
                       actes: Dict[int, ActeParoissial]) -> Dict[str, Any]:
        """Construit les métadonnées du fichier"""
        return {
            "export_date": datetime.now().isoformat(),
            "parser_version": "2.0.0",
            "format_version": "1.0",
            "total_persons": len(persons),
            "total_actes": len(actes),
            "source": "Enhanced Genealogy Parser",
            "description": "Export JSON des données généalogiques extraites des registres paroissiaux"
        }
    
    def _serialize_persons(self, persons: Dict[int, Person]) -> List[Dict[str, Any]]:  # CORRECTION: Syntaxe corrigée
        """Sérialise les personnes avec enrichissement"""
        serialized_persons = []
        
        for person in persons.values():
            person_data = {
                "id": person.id,
                "nom": person.nom,
                "prenom": person.prenom,
                "nom_complet": person.full_name,
                "nom_variations": person.nom_variations,
                "dates": {
                    "naissance": person.date_naissance,
                    "deces": person.date_deces,
                    "mariage": person.date_mariage
                },
                "lieux": {
                    "naissance": person.lieu_naissance,
                    "deces": person.lieu_deces,
                    "inhumation": person.lieu_inhumation
                },
                "attributs": {
                    "professions": person.profession,
                    "statut": person.statut.value if person.statut else None,
                    "terres": person.terres,
                    "notable": person.notable,
                    "est_vivant": person.est_vivant
                },
                "relations": {
                    "pere_id": person.pere_id,
                    "mere_id": person.mere_id,
                    "conjoint_id": person.conjoint_id
                },
                "metadata": {
                    "confidence_score": person.confidence_score,
                    "sources": person.sources,
                    "search_key": person.search_key
                }
            }
            
            serialized_persons.append(person_data)
        
        return serialized_persons

    def _serialize_actes(self, actes: Dict[int, ActeParoissial]) -> List[Dict[str, Any]]:
        """Sérialise les actes avec détails complets"""
        serialized_actes = []
        
        for acte in actes.values():
            acte_data = {
                "id": acte.id,
                "type": acte.type_acte.value,
                "date": {
                    "original": acte.date,
                    "parsed": acte.date_parsed.isoformat() if acte.date_parsed else None,
                    "year": acte.year
                },
                "lieu": acte.lieu,
                "personnes_impliquees": {
                    "principale": acte.personne_principale_id,
                    "pere": acte.pere_id,
                    "mere": acte.mere_id,
                    "conjoint": acte.conjoint_id,
                    "parrain": acte.parrain_id,
                    "marraine": acte.marraine_id,
                    "temoins": acte.temoin_ids
                },
                "contenu": {
                    "texte_original": acte.texte_original,
                    "notable": acte.notable
                },
                "validation": {
                    "result": {
                        "is_valid": acte.validation_result.is_valid if acte.validation_result else None,
                        "errors": acte.validation_result.errors if acte.validation_result else [],
                        "warnings": acte.validation_result.warnings if acte.validation_result else [],
                        "confidence_score": acte.validation_result.confidence_score if acte.validation_result else None
                    } if acte.validation_result else None
                },
                "metadata": acte.metadata
            }
            
            serialized_actes.append(acte_data)
        
        return serialized_actes

    def _extract_relationships(self, persons: Dict[int, Person], 
                              actes: Dict[int, ActeParoissial]) -> Dict[str, List[Dict]]:
        """Extrait toutes les relations familiales"""
        relationships = {
            "parent_child": [],
            "marriages": [],
            "godparenthood": []
        }
        
        # Relations parent-enfant
        for person in persons.values():
            if person.pere_id or person.mere_id:
                relationship = {
                    "child_id": person.id,
                    "child_name": person.full_name,
                    "father_id": person.pere_id,
                    "mother_id": person.mere_id
                }
                
                if person.pere_id:
                    father = persons.get(person.pere_id)
                    relationship["father_name"] = father.full_name if father else None
                
                if person.mere_id:
                    mother = persons.get(person.mere_id)
                    relationship["mother_name"] = mother.full_name if mother else None
                
                relationships["parent_child"].append(relationship)
        
        # Mariages
        processed_couples = set()
        for person in persons.values():
            if person.conjoint_id:
                couple_key = tuple(sorted([person.id, person.conjoint_id]))
                if couple_key not in processed_couples:
                    processed_couples.add(couple_key)
                    
                    spouse = persons.get(person.conjoint_id)
                    marriage = {
                        "husband_id": person.id,
                        "husband_name": person.full_name,
                        "wife_id": person.conjoint_id,
                        "wife_name": spouse.full_name if spouse else None,
                        "marriage_date": person.date_mariage or (spouse.date_mariage if spouse else None)
                    }
                    relationships["marriages"].append(marriage)
        
        # Parrainages
        for acte in actes.values():
            if acte.parrain_id or acte.marraine_id:
                godparenthood = {
                    "godchild_id": acte.personne_principale_id,
                    "baptism_date": acte.date,
                    "godfather_id": acte.parrain_id,
                    "godmother_id": acte.marraine_id
                }
                
                # Ajouter les noms
                if acte.personne_principale_id:
                    godchild = persons.get(acte.personne_principale_id)
                    godparenthood["godchild_name"] = godchild.full_name if godchild else None
                
                if acte.parrain_id:
                    godfather = persons.get(acte.parrain_id)
                    godparenthood["godfather_name"] = godfather.full_name if godfather else None
                
                if acte.marraine_id:
                    godmother = persons.get(acte.marraine_id)
                    godparenthood["godmother_name"] = godmother.full_name if godmother else None
                
                relationships["godparenthood"].append(godparenthood)
        
        return relationships

    def _calculate_statistics(self, persons: Dict[int, Person], 
                             actes: Dict[int, ActeParoissial]) -> Dict[str, Any]:
        """Calcule des statistiques détaillées"""
        from collections import Counter
        
        # Statistiques des personnes
        profession_counts = Counter()
        status_counts = Counter()
        
        for person in persons.values():
            for profession in person.profession:
                profession_counts[profession] += 1
            
            if person.statut:
                status_counts[person.statut.value] += 1
        
        # Statistiques des actes
        acte_type_counts = Counter(acte.type_acte.value for acte in actes.values())
        
        # Statistiques temporelles
        years = [acte.year for acte in actes.values() if acte.year]
        year_range = (min(years), max(years)) if years else (None, None)
        
        return {
            "persons": {
                "total": len(persons),
                "with_professions": sum(1 for p in persons.values() if p.profession),
                "nobles": sum(1 for p in persons.values() if p.notable),
                "with_birth_date": sum(1 for p in persons.values() if p.date_naissance),
                "with_death_date": sum(1 for p in persons.values() if p.date_deces),
                "profession_distribution": dict(profession_counts),
                "status_distribution": dict(status_counts)
            },
            "actes": {
                "total": len(actes),
                "type_distribution": dict(acte_type_counts),
                "with_validation": sum(1 for a in actes.values() if a.validation_result),
                "notable_actes": sum(1 for a in actes.values() if a.notable)
            },
            "temporal": {
                "year_range": year_range,
                "years_covered": len(set(years)) if years else 0,
                "total_years_span": (year_range[1] - year_range[0]) if year_range[0] and year_range[1] else 0
            }
        }

    def _build_indexes(self, persons: Dict[int, Person], 
                      actes: Dict[int, ActeParoissial]) -> Dict[str, Any]:
        """Construit des index pour recherche rapide"""
        indexes = {
            "persons_by_name": {},
            "persons_by_year": {},
            "actes_by_type": {},
            "actes_by_year": {},
            "locations": set()
        }
        
        # Index des personnes par nom
        for person in persons.values():
            name_key = person.full_name.lower()
            if name_key not in indexes["persons_by_name"]:
                indexes["persons_by_name"][name_key] = []
            indexes["persons_by_name"][name_key].append(person.id)
        
        # Index des personnes par année de naissance
        for person in persons.values():
            from utils.date_utils import DateUtils
            birth_year = DateUtils.extract_year(person.date_naissance) if person.date_naissance else None
            if birth_year:
                if birth_year not in indexes["persons_by_year"]:
                    indexes["persons_by_year"][birth_year] = []
                indexes["persons_by_year"][birth_year].append(person.id)
        
        # Index des actes par type
        for acte in actes.values():
            acte_type = acte.type_acte.value
            if acte_type not in indexes["actes_by_type"]:
                indexes["actes_by_type"][acte_type] = []
            indexes["actes_by_type"][acte_type].append(acte.id)
        
        # Index des actes par année
        for acte in actes.values():
            if acte.year:
                if acte.year not in indexes["actes_by_year"]:
                    indexes["actes_by_year"][acte.year] = []
                indexes["actes_by_year"][acte.year].append(acte.id)
        
        # Lieux mentionnés
        for person in persons.values():
            for lieu in [person.lieu_naissance, person.lieu_deces, person.lieu_inhumation]:
                if lieu:
                    indexes["locations"].add(lieu)
            for terre in person.terres:
                indexes["locations"].add(terre)
        
        for acte in actes.values():
            if acte.lieu:
                indexes["locations"].add(acte.lieu)
        
        # Convertir les sets en listes pour sérialisation JSON
        indexes["locations"] = list(indexes["locations"])
        
        return indexes