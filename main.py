import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Imports locaux
from config.settings import ParserConfig
from core.models import Person, ActeParoissial, ActeType
from parsers.text_parser import TextParser
from parsers.name_extractor import NameExtractor
from parsers.date_parser import DateParser
from parsers.profession_parser import ProfessionParser
from parsers.relationship_parser import RelationshipParser
from validators.chronology_validator import ChronologyValidator
from validators.gender_validator import GenderValidator
from database.person_manager import PersonManager
from database.acte_manager import ActeManager
from exporters.report_generator import ReportGenerator
from exporters.gedcom_exporter import GedcomExporter
from exporters.json_exporter import JsonExporter
from utils.logging_config import setup_logging, PerformanceLogger
from utils.text_utils import TextNormalizer

class GenealogyParser:
    """Parser généalogique principal avec architecture modulaire complète - VERSION COMPLÈTEMENT CORRIGÉE"""
    
    def __init__(self, config_path: Optional[str] = None):
        # Configuration
        self.config = ParserConfig.from_file(config_path) if config_path else ParserConfig()
        
        # Logging
        self.logger = setup_logging(
            level="INFO",
            log_file="logs/genealogy_parser.log",
            console_output=True
        )
        self.perf_logger = PerformanceLogger(self.logger)
        
        # Composants (lazy loading pour optimisation)
        self._text_parser = None
        self._name_extractor = None
        self._date_parser = None
        self._profession_parser = None
        self._relationship_parser = None
        self._person_manager = None
        self._acte_manager = None
        self._chronology_validator = None
        self._gender_validator = None
        self._report_generator = None
        
        # Statistiques globales
        self.global_stats = {
            'documents_processed': 0,
            'total_persons': 0,
            'total_actes': 0,
            'corrections_applied': 0,
            'processing_time': 0
        }
    
    # Properties avec lazy loading
    @property
    def text_parser(self) -> TextParser:
        if self._text_parser is None:
            self._text_parser = TextParser(self.config)
        return self._text_parser
    
    @property
    def name_extractor(self) -> NameExtractor:
        if self._name_extractor is None:
            self._name_extractor = NameExtractor(self.config)
        return self._name_extractor
    
    @property
    def date_parser(self) -> DateParser:
        if self._date_parser is None:
            self._date_parser = DateParser(self.config)
        return self._date_parser
    
    @property
    def profession_parser(self) -> ProfessionParser:
        if self._profession_parser is None:
            self._profession_parser = ProfessionParser(self.config)
        return self._profession_parser
    
    @property
    def relationship_parser(self) -> RelationshipParser:
        if self._relationship_parser is None:
            self._relationship_parser = RelationshipParser(self.config)
        return self._relationship_parser
    
    @property
    def person_manager(self) -> PersonManager:
        if self._person_manager is None:
            self._person_manager = PersonManager(self.config)
        return self._person_manager
    
    @property
    def acte_manager(self) -> ActeManager:
        if self._acte_manager is None:
            self._acte_manager = ActeManager(self.config)
        return self._acte_manager
    
    @property
    def chronology_validator(self) -> ChronologyValidator:
        if self._chronology_validator is None:
            self._chronology_validator = ChronologyValidator(self.config)
        return self._chronology_validator
    
    @property
    def gender_validator(self) -> GenderValidator:
        if self._gender_validator is None:
            self._gender_validator = GenderValidator(self.config)
        return self._gender_validator
    
    @property
    def report_generator(self) -> ReportGenerator:
        if self._report_generator is None:
            self._report_generator = ReportGenerator(self.config)
        return self._report_generator
    
    def process_document(self, text: str, lieu: str = "Notre-Dame d'Esméville") -> Dict:
        """Traitement complet d'un document avec toutes les optimisations - VERSION CORRIGÉE"""
        self.perf_logger.start_timer("process_document")
        self.logger.info(f"Début du traitement - Lieu: {lieu}")
        
        try:
            # 1. Normalisation du texte
            self.perf_logger.start_timer("text_normalization")
            normalized_text = self.text_parser.normalize_text(text)
            self.perf_logger.end_timer("text_normalization")
            
            # 2. Extraction des segments
            self.perf_logger.start_timer("segment_extraction")
            segments = self.text_parser.extract_segments(normalized_text)
            self.perf_logger.end_timer("segment_extraction")
            
            # 3. Extraction des personnes
            self.perf_logger.start_timer("person_extraction")
            persons_data = self.name_extractor.extract_complete_names(normalized_text)
            self.perf_logger.end_timer("person_extraction")
            
            # 4. Création/récupération des personnes avec validation
            self.perf_logger.start_timer("person_creation")
            created_persons = self._process_persons(persons_data, normalized_text)
            self.perf_logger.end_timer("person_creation")
            
            # 5. Extraction et création des actes
            self.perf_logger.start_timer("acte_processing")
            created_actes = self._process_actes(segments, created_persons)
            self.perf_logger.end_timer("acte_processing")
            
            # 6. Validation chronologique
            if self.config.chronology_validation:
                self.perf_logger.start_timer("chronology_validation")
                corrections = self.chronology_validator.validate_and_correct_chronology(
                    list(self.person_manager.persons.values()),
                    list(self.acte_manager.actes.values())
                )
                self.global_stats['corrections_applied'] += len(corrections)
                self.perf_logger.end_timer("chronology_validation")
            
            # 7. Validation des genres
            if self.config.gender_validation:
                self.perf_logger.start_timer("gender_validation")
                contexts = {p.id: normalized_text for p in created_persons}
                gender_corrections = self.gender_validator.correct_gender_inconsistencies(
                    created_persons, contexts
                )
                self.global_stats['corrections_applied'] += len(gender_corrections)
                self.perf_logger.end_timer("gender_validation")
            
            # 8. Génération du rapport final
            self.perf_logger.start_timer("report_generation")
            report = self.report_generator.generate_final_report(
                self.person_manager, 
                self.acte_manager,
                lieu
            )
            self.perf_logger.end_timer("report_generation")
            
            # Mise à jour des statistiques
            self.global_stats['documents_processed'] += 1
            self.global_stats['total_persons'] = len(self.person_manager.persons)
            self.global_stats['total_actes'] = len(self.acte_manager.actes)
            
            self.logger.info("Traitement terminé avec succès")
            self.perf_logger.end_timer("process_document")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Erreur durant le traitement: {e}", exc_info=True)
            raise
    
    def _process_persons(self, persons_data: List[Dict], context: str) -> List[Person]:
        """VERSION AMÉLIORÉE: Traitement des personnes avec extraction des dates"""
        created_persons = []
        
        for person_info in persons_data:
            try:
                # Nettoyer extra_info avant de passer à get_or_create_person
                clean_extra_info = self._clean_person_info(person_info)
                clean_extra_info['context'] = context
                
                # NOUVEAU: Extraction des dates spécifiques pour cette personne
                dates_info = self._extract_person_dates(person_info['nom_complet'], context)
                clean_extra_info.update(dates_info)
                
                person = self.person_manager.get_or_create_person(
                    person_info['nom'],
                    person_info['prenom'],
                    clean_extra_info
                )
                
                # NOUVEAU: Mise à jour des dates après création
                self._update_person_dates(person, dates_info, context)
                
                created_persons.append(person)
                
            except Exception as e:
                self.logger.warning(f"Erreur traitement personne {person_info.get('nom_complet', 'INCONNU')}: {e}")
                continue
        
        return created_persons
    
    def _extract_person_dates(self, person_name: str, context: str) -> Dict:
        """NOUVELLE MÉTHODE: Extrait les dates spécifiques à une personne"""
        dates_info = {}
        
        try:
            # Rechercher les mentions de cette personne avec des dates
            person_name_lower = person_name.lower()
            
            # 1. Date de décès avec inhumation
            # Pattern: "13 fév., décès, le 14, inhumation... de Jean Le Boucher"
            deces_pattern = rf'(\d{{1,2}}\s+\w+\.?),?\s+décès[^,]*,?\s+[^,]*inhumation[^,]*,?\s+de\s+{re.escape(person_name)}'
            deces_match = re.search(deces_pattern, context, re.IGNORECASE)
            
            if deces_match:
                date_deces = deces_match.group(1)
                # Ajouter l'année du contexte si disponible
                year_match = re.search(r'\b(\d{4})\b', context[:deces_match.start()])
                if year_match:
                    date_deces = f"{date_deces} {year_match.group(1)}"
                dates_info['date_deces'] = date_deces
                self.logger.info(f"DATE DÉCÈS DÉTECTÉE pour {person_name}: {date_deces}")
            
            # 2. Date de naissance avec baptême
            # Pattern: "24 oct., naissance, bapt.... de Charlotte, fille de..."
            naissance_pattern = rf'(\d{{1,2}}\s+\w+\.?).*?naissance.*?bapt.*?de\s+{re.escape(person_name)}'
            naissance_match = re.search(naissance_pattern, context, re.IGNORECASE)
            
            if not naissance_match:
                # Pattern alternatif: "Charlotte, fille de..." après une date
                fille_pattern = rf'(\d{{1,2}}\s+\w+\.?).*?{re.escape(person_name)},\s+fille\s+de'
                fille_match = re.search(fille_pattern, context, re.IGNORECASE)
                if fille_match:
                    naissance_match = fille_match
            
            if naissance_match:
                date_naissance = naissance_match.group(1)
                # Ajouter l'année du contexte si disponible
                year_match = re.search(r'\b(\d{4})\b', context[:naissance_match.start()])
                if year_match:
                    date_naissance = f"{date_naissance} {year_match.group(1)}"
                dates_info['date_naissance'] = date_naissance
                self.logger.info(f"DATE NAISSANCE DÉTECTÉE pour {person_name}: {date_naissance}")
            
            # 3. Prise de possession pour les prêtres
            # Pattern: "L'an de grâce 1643, le dimanche 8e jour de mars, moy, Charles Demontigny"
            possession_pattern = rf'l\'an\s+de\s+grâce\s+(\d{{4}})[^,]*,\s+[^,]*(\d+e?\s+jour\s+de\s+\w+)[^,]*,\s+[^,]*{re.escape(person_name)}'
            possession_match = re.search(possession_pattern, context, re.IGNORECASE)
            
            if possession_match:
                annee = possession_match.group(1)
                jour_mois = possession_match.group(2)
                date_possession = f"{jour_mois} {annee}"
                dates_info['date_prise_possession'] = date_possession
                self.logger.info(f"DATE PRISE POSSESSION DÉTECTÉE pour {person_name}: {date_possession}")
        
        except Exception as e:
            self.logger.warning(f"Erreur extraction dates pour {person_name}: {e}")
        
        return dates_info
    
    def _update_person_dates(self, person: Person, dates_info: Dict, context: str):
        """NOUVELLE MÉTHODE: Met à jour les dates d'une personne"""
        try:
            # Mettre à jour les dates si elles ne sont pas déjà définies
            if 'date_naissance' in dates_info and not person.date_naissance:
                person.date_naissance = dates_info['date_naissance']
                self.logger.info(f"DATE NAISSANCE ASSIGNÉE à {person.full_name}: {person.date_naissance}")
            
            if 'date_deces' in dates_info and not person.date_deces:
                person.date_deces = dates_info['date_deces']
                # Si décès détecté, marquer comme non vivant
                person.est_vivant = False
                self.logger.info(f"DATE DÉCÈS ASSIGNÉE à {person.full_name}: {person.date_deces}")
            
            if 'date_prise_possession' in dates_info:
                # Pour les prêtres, ajouter une note ou métadonnée
                if not hasattr(person, 'metadata'):
                    person.metadata = {}
                person.metadata['date_prise_possession'] = dates_info['date_prise_possession']
                self.logger.info(f"DATE PRISE POSSESSION ASSIGNÉE à {person.full_name}: {dates_info['date_prise_possession']}")
        
        except Exception as e:
            self.logger.warning(f"Erreur mise à jour dates pour {person.full_name}: {e}")
    
    def _clean_person_info(self, person_info: Dict) -> Dict:
        """Nettoie les informations de personne avant traitement"""
        clean_info = {}
        
        for key, value in person_info.items():
            try:
                if isinstance(value, (str, int, float, bool)) or value is None:
                    clean_info[key] = value
                elif isinstance(value, list):
                    # Nettoyer les listes
                    clean_list = []
                    for item in value:
                        if isinstance(item, (str, int, float, bool)) or item is None:
                            clean_list.append(item)
                        elif isinstance(item, dict):
                            # Ignorer les dict complexes
                            continue
                        else:
                            # Convertir en string les autres types
                            clean_list.append(str(item))
                    clean_info[key] = clean_list
                else:
                    clean_info[key] = str(value)
                    
            except Exception as e:
                self.logger.debug(f"Erreur nettoyage {key}: {e}")
                continue
        
        return clean_info
    
    def _process_actes(self, segments: List[Dict], persons: List[Person]) -> List[ActeParoissial]:
        """VERSION AMÉLIORÉE: Traitement des actes avec logging détaillé"""
        created_actes = []
        
        self.logger.info(f"Traitement de {len(segments)} segments pour créer des actes")
        
        for i, segment in enumerate(segments):
            if segment['type'] != 'acte':
                self.logger.debug(f"Segment {i} ignoré (type: {segment['type']})")
                continue
            
            try:
                self.logger.debug(f"Analyse du segment {i}: {segment['content'][:100]}...")
                
                # Analyse du segment pour détecter le type d'acte et relations
                acte_info = self._analyze_segment_for_acte(segment, persons)
                
                if acte_info:
                    # Créer l'acte
                    acte = self.acte_manager.create_acte(acte_info)
                    
                    # Validation de l'acte avec logging
                    validation = self.acte_manager.validate_acte(acte, self.person_manager)
                    if validation.errors:
                        self.logger.warning(f"Erreurs validation acte {acte.id}: {validation.errors}")
                    if validation.warnings:
                        self.logger.info(f"Avertissements acte {acte.id}: {validation.warnings}")
                    
                    created_actes.append(acte)
                    self.logger.info(f"ACTE {acte.id} CRÉÉ avec succès: {acte.type_acte.value}")
                else:
                    self.logger.warning(f"Impossible de créer un acte pour le segment {i}")
                    
            except Exception as e:
                self.logger.error(f"Erreur traitement segment {i}: {e}")
                continue
        
        self.logger.info(f"Nombre total d'actes créés: {len(created_actes)}")
        return created_actes
    
    def _analyze_segment_for_acte(self, segment: Dict, persons: List[Person]) -> Optional[Dict]:
        """VERSION AMÉLIORÉE: Analyse complète d'un segment avec extraction des relations et dates"""
        content = segment['content']
        
        # Détecter le type d'acte
        acte_type = self._detect_acte_type(content)
        if not acte_type:
            self.logger.warning(f"Aucun type d'acte détecté pour: {content[:50]}...")
            return None
        
        # Extraire les dates avec contexte amélioré
        dates = self.date_parser.extract_all_dates(content)
        main_date = dates[0] if dates else None
        
        # Extraire l'année du segment pour cohérence
        year_from_segment = None
        if segment.get('index', 0) > 0:  # Pas le premier segment (période)
            # Chercher l'année au début du segment ou dans le contexte précédent
            year_match = re.search(r'\b(\d{4})\b', content)
            if year_match:
                year_from_segment = int(year_match.group(1))
        
        # Extraire les relations spécifiques
        person_assignments = self._extract_relations_from_content(content)
        
        # Déterminer la date principale basée sur le type d'acte
        date_str = ""
        if main_date:
            date_str = main_date.original_text
        elif year_from_segment:
            date_str = str(year_from_segment)
        
        acte_info = {
            'type_acte': acte_type,
            'date': date_str,
            'texte_original': content,
            'person_assignments': person_assignments,
            'notable': self._is_acte_notable(content),
            'year': year_from_segment
        }
        
        # Mapper les noms vers les IDs de personnes
        acte_info = self._map_names_to_person_ids(acte_info, persons)
        
        # Logging détaillé pour debug
        self.logger.info(f"ACTE CRÉÉ: Type={acte_type}, Date={date_str}, Personnes={len(person_assignments)}")
        
        return acte_info
    
    def _extract_relations_from_content(self, content: str) -> Dict:
        """NOUVELLE VERSION: Extraction précise des relations depuis le contenu"""
        person_assignments = {}
        
        try:
            # 1. BAPTÊME: "Charlotte, fille de Jean Le Boucher... et de Françoise Varin"
            fille_pattern = r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+),\s+fille\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s,]+?)(?:\s*,\s*[^,]*?)?\s+et\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?)(?:[,;]|$)'
            fille_match = re.search(fille_pattern, content, re.IGNORECASE)
            
            if fille_match:
                enfant_nom = fille_match.group(1).strip()
                pere_desc = fille_match.group(2).strip()
                mere_nom = fille_match.group(3).strip()
                
                # Nettoyer le nom du père des attributs
                pere_nom = self._clean_name_from_description(pere_desc)
                
                person_assignments.update({
                    'enfant_nom': enfant_nom,
                    'pere_nom': pere_nom,
                    'mere_nom': mere_nom
                })
                self.logger.info(f"FILIATION DÉTECTÉE: {enfant_nom} fille de {pere_nom} et {mere_nom}")
            
            # 2. PATTERN PARRAIN: "parr.: Charles Le Boucher"
            parrain_pattern = r'parr\.?\s*:\s*([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s,]+?)(?:[,;.]|$)'
            parrain_match = re.search(parrain_pattern, content, re.IGNORECASE)
            
            if parrain_match:
                parrain_desc = parrain_match.group(1).strip()
                parrain_nom = self._clean_name_from_description(parrain_desc)
                person_assignments['parrain_nom'] = parrain_nom
                self.logger.info(f"PARRAIN DÉTECTÉ: {parrain_nom}")
            
            # 3. PATTERN MARRAINE: "marr.: Perrette Dupré"
            marraine_pattern = r'marr\.?\s*:\s*([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?)(?:[,;.]|$)'
            marraine_match = re.search(marraine_pattern, content, re.IGNORECASE)
            
            if marraine_match:
                marraine_nom = marraine_match.group(1).strip()
                person_assignments['marraine_nom'] = marraine_nom
                self.logger.info(f"MARRAINE DÉTECTÉE: {marraine_nom}")
            
            # 4. PATTERN ÉPOUSE: "Françoise Picot, épouse de Charles Le Boucher"
            epouse_pattern = r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?),\s+épouse\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?)(?:[,;.]|$)'
            epouse_match = re.search(epouse_pattern, content, re.IGNORECASE)
            
            if epouse_match:
                epouse_nom = epouse_match.group(1).strip()
                mari_desc = epouse_match.group(2).strip()
                mari_nom = self._clean_name_from_description(mari_desc)
                
                person_assignments.update({
                    'epouse_nom': epouse_nom,
                    'mari_nom': mari_nom
                })
                self.logger.info(f"MARIAGE DÉTECTÉ: {epouse_nom} épouse de {mari_nom}")
            
            # 5. PATTERN INHUMATION: "inhumation... de Jean Le Boucher"
            inhumation_pattern = r'inhumation[^,]*,\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s,]+?)(?:[,;.]|$)'
            inhumation_match = re.search(inhumation_pattern, content, re.IGNORECASE)
            
            if inhumation_match:
                defunt_desc = inhumation_match.group(1).strip()
                defunt_nom = self._clean_name_from_description(defunt_desc)
                person_assignments['defunt_nom'] = defunt_nom
                self.logger.info(f"INHUMATION DÉTECTÉE: {defunt_nom}")
            
            return person_assignments
            
        except Exception as e:
            self.logger.warning(f"Erreur extraction relations: {e}")
            return {}
    
    def _clean_name_from_description(self, description: str) -> Optional[str]:
        """NOUVELLE MÉTHODE: Nettoie un nom des attributs qui l'accompagnent"""
        try:
            if not description:
                return None
            
            # Supprimer les attributs courants pour isoler le nom
            clean_desc = description
            
            # Patterns à supprimer (attributs après le nom)
            patterns_to_remove = [
                r',\s*écuyer.*$', r',\s*éc\..*$', r',\s*sieur.*$', r',\s*sr\s+de.*$',
                r',\s*seigneur.*$', r',\s*sgr.*$', r',\s*avocat.*$', r',\s*conseiller.*$',
                r',\s*curé.*$', r',\s*prêtre.*$', r',\s*avocat\s+du\s+roi.*$', r',\s*notable.*$'
            ]
            
            for pattern in patterns_to_remove:
                clean_desc = re.sub(pattern, '', clean_desc, flags=re.IGNORECASE)
            
            # Nettoyer les espaces et virgules en trop
            clean_desc = clean_desc.strip().rstrip(',').strip()
            
            # Validation finale
            if len(clean_desc) >= 5 and ' ' in clean_desc:
                # Vérifier que c'est bien un nom (commence par une majuscule)
                if re.match(r'^[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß]', clean_desc):
                    return clean_desc
            
            # Si échec, prendre les 2-3 premiers mots comme nom
            words = clean_desc.split()
            if len(words) >= 2:
                name_candidate = ' '.join(words[:3] if len(words) >= 3 else words[:2])
                if re.match(r'^[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß]', name_candidate):
                    return name_candidate
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Erreur nettoyage nom: {e}")
            return None
    
    def _map_names_to_person_ids(self, acte_info: Dict, persons: List[Person]) -> Dict:
        """VERSION AMÉLIORÉE: Mappe les noms extraits vers les IDs des personnes"""
        person_assignments = acte_info.get('person_assignments', {})
        
        try:
            # Créer un mapping nom -> personne (insensible à la casse et aux variantes)
            name_to_person = {}
            
            for person in persons:
                # Mapping exact
                name_key = person.full_name.lower().strip()
                name_to_person[name_key] = person
                
                # Mapping des variations possibles
                variations = [
                    person.full_name.replace(' de ', ' '),  # "Charles de Montigny" -> "Charles Montigny"  
                    person.full_name.replace('de ', ''),    # "Charles de Montigny" -> "Charles Montigny"
                    person.full_name.replace(' Le ', ' le '), # Variations de casse
                ]
                
                for variation in variations:
                    var_key = variation.lower().strip()
                    if var_key != name_key and var_key not in name_to_person:
                        name_to_person[var_key] = person
            
            # Logging pour debug
            self.logger.debug(f"Mapping créé pour {len(name_to_person)} variations de noms")
            
            # Mapper chaque nom vers un ID avec logging
            mappings_found = []
            
            if 'enfant_nom' in person_assignments:
                enfant_name = person_assignments['enfant_nom'].lower().strip()
                if enfant_name in name_to_person:
                    acte_info['personne_principale_id'] = name_to_person[enfant_name].id
                    mappings_found.append(f"enfant: {person_assignments['enfant_nom']} -> ID {name_to_person[enfant_name].id}")
            
            if 'pere_nom' in person_assignments and person_assignments['pere_nom']:
                pere_name = person_assignments['pere_nom'].lower().strip()
                if pere_name in name_to_person:
                    acte_info['pere_id'] = name_to_person[pere_name].id
                    mappings_found.append(f"père: {person_assignments['pere_nom']} -> ID {name_to_person[pere_name].id}")
            
            if 'mere_nom' in person_assignments and person_assignments['mere_nom']:
                mere_name = person_assignments['mere_nom'].lower().strip()
                if mere_name in name_to_person:
                    acte_info['mere_id'] = name_to_person[mere_name].id
                    mappings_found.append(f"mère: {person_assignments['mere_nom']} -> ID {name_to_person[mere_name].id}")
            
            if 'parrain_nom' in person_assignments and person_assignments['parrain_nom']:
                parrain_name = person_assignments['parrain_nom'].lower().strip()
                if parrain_name in name_to_person:
                    acte_info['parrain_id'] = name_to_person[parrain_name].id
                    mappings_found.append(f"parrain: {person_assignments['parrain_nom']} -> ID {name_to_person[parrain_name].id}")
            
            if 'marraine_nom' in person_assignments and person_assignments['marraine_nom']:
                marraine_name = person_assignments['marraine_nom'].lower().strip()
                if marraine_name in name_to_person:
                    acte_info['marraine_id'] = name_to_person[marraine_name].id
                    mappings_found.append(f"marraine: {person_assignments['marraine_nom']} -> ID {name_to_person[marraine_name].id}")
            
            if 'epouse_nom' in person_assignments and 'mari_nom' in person_assignments:
                epouse_name = person_assignments['epouse_nom'].lower().strip()
                mari_name = person_assignments['mari_nom'].lower().strip()
                
                if epouse_name in name_to_person:
                    acte_info['personne_principale_id'] = name_to_person[epouse_name].id
                    mappings_found.append(f"épouse: {person_assignments['epouse_nom']} -> ID {name_to_person[epouse_name].id}")
                    
                if mari_name in name_to_person:
                    acte_info['conjoint_id'] = name_to_person[mari_name].id
                    mappings_found.append(f"mari: {person_assignments['mari_nom']} -> ID {name_to_person[mari_name].id}")
            
            if 'defunt_nom' in person_assignments and person_assignments['defunt_nom']:
                defunt_name = person_assignments['defunt_nom'].lower().strip()
                if defunt_name in name_to_person:
                    acte_info['personne_principale_id'] = name_to_person[defunt_name].id
                    mappings_found.append(f"défunt: {person_assignments['defunt_nom']} -> ID {name_to_person[defunt_name].id}")
            
            # Log des mappings réussis
            if mappings_found:
                self.logger.info(f"MAPPINGS RÉUSSIS: {'; '.join(mappings_found)}")
            else:
                self.logger.warning("Aucun mapping nom->ID réussi")
                
            # Log des noms non trouvés
            for key, name in person_assignments.items():
                if name and key.endswith('_nom'):
                    name_lower = name.lower().strip()
                    if name_lower not in name_to_person:
                        self.logger.warning(f"NOM NON TROUVÉ: {name} (clé: {key})")
                        
        except Exception as e:
            self.logger.error(f"Erreur mapping noms->IDs: {e}")
        
        return acte_info
    
    def _detect_acte_type(self, content: str) -> Optional[str]:
        """VERSION AMÉLIORÉE: Détection des types d'actes avec logging"""
        if not content:
            return None
        
        content_lower = content.lower()
        
        # Logging pour debug
        self.logger.debug(f"Détection type acte pour: {content[:100]}...")
        
        detected_type = None
        
        # Priorité aux mots-clés spécifiques avec logging
        if 'prise de possession' in content_lower:
            detected_type = 'prise_possession'
        elif any(word in content_lower for word in ['fille de', 'fils de']):
            detected_type = 'baptême'
        elif any(word in content_lower for word in ['baptême', 'bapt.', 'naissance et baptême']):
            detected_type = 'baptême'
        elif any(word in content_lower for word in ['mariage', 'mar.', 'époux', 'épouse de']):
            detected_type = 'mariage'
        elif any(word in content_lower for word in ['inhumation', 'inh.', 'décès', 'enterrement']):
            detected_type = 'inhumation'
        elif 'acte de vente' in content_lower:
            detected_type = 'acte_vente'
        
        if detected_type:
            self.logger.info(f"TYPE ACTE DÉTECTÉ: {detected_type}")
        else:
            self.logger.warning(f"AUCUN TYPE ACTE DÉTECTÉ pour: {content[:50]}...")
        
        return detected_type
    
    def _is_acte_notable(self, content: str) -> bool:
        """Détermine si l'acte concerne un notable"""
        if not content:
            return False
        
        content_lower = content.lower()
        notable_indicators = [
            "dans l'église", "dans l'eglise", "dans la chapelle",
            "sous le chœur", "près de l'autel", "inhumé dans l'église"
        ]
        return any(indicator in content_lower for indicator in notable_indicators)
    
    def export_to_gedcom(self, output_path: str):
        """Export au format GEDCOM"""
        try:
            gedcom_exporter = GedcomExporter(self.config)
            gedcom_exporter.export(
                self.person_manager.persons,
                self.acte_manager.actes,
                output_path
            )
            self.logger.info(f"Export GEDCOM créé: {output_path}")
        except Exception as e:
            self.logger.error(f"Erreur export GEDCOM: {e}")
    
    def export_to_json(self, output_path: str):
        """Export au format JSON"""
        try:
            json_exporter = JsonExporter(self.config)
            json_exporter.export(
                self.person_manager.persons,
                self.acte_manager.actes,
                output_path
            )
            self.logger.info(f"Export JSON créé: {output_path}")
        except Exception as e:
            self.logger.error(f"Erreur export JSON: {e}")
    
    def get_global_statistics(self) -> Dict:
        """Retourne les statistiques globales du parser"""
        try:
            person_stats = self.person_manager.get_statistics()
            acte_stats = self.acte_manager.get_statistics()
            
            return {
                'global': self.global_stats,
                'persons': person_stats,
                'actes': acte_stats,
                'performance': {
                    'cache_hit_rate': person_stats.get('cache_hit_rate', 0),
                    'avg_processing_time': self.global_stats['processing_time'] / max(1, self.global_stats['documents_processed'])
                }
            }
        except Exception as e:
            self.logger.error(f"Erreur calcul statistiques: {e}")
            return {'error': str(e)}

def main():
    """Point d'entrée principal avec interface en ligne de commande"""
    parser = argparse.ArgumentParser(description='Parser généalogique pour registres paroissiaux')
    
    parser.add_argument('input_file', help='Fichier texte à analyser')
    parser.add_argument('-o', '--output', help='Répertoire de sortie', default='output')
    parser.add_argument('-c', '--config', help='Fichier de configuration')
    parser.add_argument('-l', '--lieu', help='Lieu du registre', default='Notre-Dame d\'Esméville')
    parser.add_argument('--gedcom', action='store_true', help='Exporter en GEDCOM')
    parser.add_argument('--json', action='store_true', help='Exporter en JSON')
    parser.add_argument('--format', choices=['console', 'file'], default='console', 
                       help='Format de sortie du rapport')
    parser.add_argument('-v', '--verbose', action='store_true', help='Mode verbeux')
    
    args = parser.parse_args()
    
    # Vérification du fichier d'entrée
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Erreur: Fichier '{args.input_file}' introuvable")
        sys.exit(1)
    
    # Création du répertoire de sortie
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialisation du parser
    genealogy_parser = GenealogyParser(args.config)
    
    try:
        # Lecture du fichier
        with open(input_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
        
        print(f"Traitement de {input_path.name}...")
        
        # Traitement principal
        report = genealogy_parser.process_document(text_content, args.lieu)
        
        # Affichage du rapport
        if args.format == 'console':
            ReportGenerator.print_formatted_results(report)
        
        # Sauvegarde du rapport
        if args.format == 'file':
            report_path = output_dir / f"rapport_{input_path.stem}.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                # Rediriger la sortie console vers le fichier
                import contextlib, io
                f_buffer = io.StringIO()
                with contextlib.redirect_stdout(f_buffer):
                    ReportGenerator.print_formatted_results(report)
                f.write(f_buffer.getvalue())
            print(f"Rapport sauvegardé: {report_path}")
        
        # Exports optionnels
        if args.gedcom:
            gedcom_path = output_dir / f"{input_path.stem}.ged"
            genealogy_parser.export_to_gedcom(str(gedcom_path))
        
        if args.json:
            json_path = output_dir / f"{input_path.stem}.json"
            genealogy_parser.export_to_json(str(json_path))
        
        # Statistiques finales
        if args.verbose:
            stats = genealogy_parser.get_global_statistics()
            print("\n=== STATISTIQUES DÉTAILLÉES ===")
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        
        print(f"\nTraitement terminé avec succès!")
        
    except Exception as e:
        print(f"Erreur durant le traitement: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

# =====================================
# Exemple d'usage simple
# =====================================

def demo_usage():
    """Exemple d'utilisation simple du parser"""
    
    sample_text = """
    1643-1687. — Bapt., mar., inh. — Charles de Montigny, Guillaume Le Breton, curés.
    — « L'an de grâce 1643, le dimanche 8e jour de mars, moy, Charles Demontigny, prestre, 
    ay, au nom de Dieu, pris possession du bénéfice Notre-Dame d'Esméville, sans aucune opposition. » 
    — 1646, 13 fév., décès, le 14, inhumation, dans l'église, de Jean Le Boucher, écuyer, sr de Bréville. 
    — 1651, 23 janv., inh., dans l'église, de Françoise Picot, épouse de Charles Le Boucher, 
    éc., sr du Hausey, avocat du Roi au siège de Saint-Sylvain; 24 oct., naissance, bapt., 
    et, le 21 nov., cérémonies du bapt. de Charlotte, fille de Jean Le Boucher, éc., sr de 
    La Granville, et de Françoise Varin; marr.: Perrette Dupré; parr.: Charles Le Boucher, 
    éc., sr du Hozey, conseiller et avocat du Roi à Saint-Sylvain.
    """
    
    # Initialisation
    parser = GenealogyParser()
    
    # Traitement
    result = parser.process_document(sample_text)
    
    # Affichage
    ReportGenerator.print_formatted_results(result)
    
    # Export optionnel
    # parser.export_to_gedcom("exemple.ged")
    # parser.export_to_json("exemple.json")
    
    return result

# Test rapide
if __name__ == "__main__":
    # Possibilité de lancer soit la démo soit le main complet
    import sys
    if len(sys.argv) == 1:
        print("=== DÉMONSTRATION DU PARSER ===\n")
        demo_usage()
    else:
        main()