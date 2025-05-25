import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
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

try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

HAS_PDF_SUPPORT = HAS_PYMUPDF or HAS_PDFPLUMBER or HAS_PYPDF2

class PDFReader:
    def __init__(self):
        self.logger = setup_logging().getChild('pdf_reader')
        self.stats = {
            'pages_processed': 0,
            'total_chars': 0,
            'processing_time': 0,
            'errors': 0
        }
    
    def can_read_pdf(self) -> bool:
        return HAS_PDF_SUPPORT
    
    def get_available_libraries(self) -> List[str]:
        libraries = []
        if HAS_PYMUPDF:
            libraries.append("PyMuPDF (recommandé)")
        if HAS_PDFPLUMBER:
            libraries.append("pdfplumber")
        if HAS_PYPDF2:
            libraries.append("PyPDF2")
        return libraries
    
    def read_pdf_file(self, pdf_path: str, max_pages: Optional[int] = None,
                     page_range: Optional[tuple] = None, method: str = "auto") -> str:
        start_time = time.time()
        
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"Fichier PDF introuvable: {pdf_path}")
        
        if method == "auto":
            if HAS_PYMUPDF:
                method = "pymupdf"
            elif HAS_PDFPLUMBER:
                method = "pdfplumber"
            elif HAS_PYPDF2:
                method = "pypdf2"
            else:
                raise ImportError("Aucune bibliothèque PDF disponible")
        
        self.logger.info(f"Lecture PDF avec {method}: {Path(pdf_path).name}")
        
        try:
            if method == "pymupdf":
                text = self._read_with_pymupdf(pdf_path, max_pages, page_range)
            elif method == "pdfplumber":
                text = self._read_with_pdfplumber(pdf_path, max_pages, page_range)
            elif method == "pypdf2":
                text = self._read_with_pypdf2(pdf_path, max_pages, page_range)
            else:
                raise ValueError(f"Méthode inconnue: {method}")
            
            self.stats['total_chars'] = len(text)
            self.stats['processing_time'] = time.time() - start_time
            self.logger.info(f"PDF lu avec succès: {self.stats['pages_processed']} pages, "
                           f"{self.stats['total_chars']:,} caractères, "
                           f"{self.stats['processing_time']:.2f}s")
            
            return text
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Erreur lecture PDF: {e}")
            raise
    
    def _read_with_pymupdf(self, pdf_path: str, max_pages: Optional[int], 
                          page_range: Optional[tuple]) -> str:
        if not HAS_PYMUPDF:
            raise ImportError("PyMuPDF non disponible")
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        self.logger.info(f"Document PDF: {total_pages} pages")
        start_page, end_page = self._get_page_range(total_pages, max_pages, page_range)
        
        text_parts = []
        
        for page_num in range(start_page, end_page):
            try:
                page = doc[page_num]
                page_text = page.get_text()
                
                if page_text.strip():
                    text_parts.append(f"\n--- PAGE {page_num + 1} ---\n")
                    text_parts.append(page_text)
                
                self.stats['pages_processed'] += 1
                
                # Log de progression pour gros documents
                if (page_num + 1) % 100 == 0:
                    self.logger.info(f"Progression: {page_num + 1}/{end_page} pages")
                    
            except Exception as e:
                self.logger.warning(f"Erreur page {page_num + 1}: {e}")
                self.stats['errors'] += 1
                continue
        
        doc.close()
        return '\n'.join(text_parts)
    
    def _read_with_pdfplumber(self, pdf_path: str, max_pages: Optional[int], 
                             page_range: Optional[tuple]) -> str:
        """Lecture avec pdfplumber"""
        if not HAS_PDFPLUMBER:
            raise ImportError("pdfplumber non disponible")
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            self.logger.info(f"Document PDF: {total_pages} pages")
            
            start_page, end_page = self._get_page_range(total_pages, max_pages, page_range)
            
            text_parts = []
            
            for page_num in range(start_page, end_page):
                try:
                    page = pdf.pages[page_num]
                    page_text = page.extract_text()
                    
                    if page_text and page_text.strip():
                        text_parts.append(f"\n--- PAGE {page_num + 1} ---\n")
                        text_parts.append(page_text)
                    
                    self.stats['pages_processed'] += 1
                    
                    if (page_num + 1) % 100 == 0:
                        self.logger.info(f"Progression: {page_num + 1}/{end_page} pages")
                        
                except Exception as e:
                    self.logger.warning(f"Erreur page {page_num + 1}: {e}")
                    self.stats['errors'] += 1
                    continue
            
            return '\n'.join(text_parts)
    
    def _read_with_pypdf2(self, pdf_path: str, max_pages: Optional[int], 
                         page_range: Optional[tuple]) -> str:
        """Lecture avec PyPDF2"""
        if not HAS_PYPDF2:
            raise ImportError("PyPDF2 non disponible")
        
        text_parts = []
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            self.logger.info(f"Document PDF: {total_pages} pages")
            
            start_page, end_page = self._get_page_range(total_pages, max_pages, page_range)
            
            for page_num in range(start_page, end_page):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    if page_text and page_text.strip():
                        text_parts.append(f"\n--- PAGE {page_num + 1} ---\n")
                        text_parts.append(page_text)
                    
                    self.stats['pages_processed'] += 1
                    
                    if (page_num + 1) % 100 == 0:
                        self.logger.info(f"Progression: {page_num + 1}/{end_page} pages")
                        
                except Exception as e:
                    self.logger.warning(f"Erreur page {page_num + 1}: {e}")
                    self.stats['errors'] += 1
                    continue
        
        return '\n'.join(text_parts)
    
    def _get_page_range(self, total_pages: int, max_pages: Optional[int], 
                       page_range: Optional[tuple]) -> tuple:
        """Détermine la plage de pages à traiter"""
        if page_range:
            start_page = max(0, page_range[0] - 1)
            end_page = min(total_pages, page_range[1])
        else:
            start_page = 0
            end_page = min(total_pages, max_pages) if max_pages else total_pages
        
        return start_page, end_page
    
    def get_pdf_info(self, pdf_path: str) -> Dict:
        """Obtient les informations sur un PDF"""
        if not HAS_PYMUPDF:
            file_size = Path(pdf_path).stat().st_size
            return {
                "pages": "Unknown",
                "file_size": file_size,
                "estimated_processing_time": "Unknown"
            }
        
        doc = fitz.open(pdf_path)
        info = {
            "pages": len(doc),
            "metadata": doc.metadata,
            "file_size": Path(pdf_path).stat().st_size,
            "estimated_processing_time": len(doc) * 0.1
        }
        doc.close()
        return info
    
    def get_statistics(self) -> Dict:
        """Retourne les statistiques de traitement"""
        stats = self.stats.copy()
        if stats['processing_time'] > 0:
            stats['pages_per_second'] = stats['pages_processed'] / stats['processing_time']
            stats['chars_per_second'] = stats['total_chars'] / stats['processing_time']
        return stats

class GenealogyParser:
    """Parser généalogique principal avec support PDF intégré - VERSION COMPLÈTE"""
    
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
        
        # Composants (lazy loading)
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
        """Traitement complet d'un document - VERSION FINALE CORRIGÉE"""
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
        """VERSION FINALE: Traitement des personnes avec extraction complète"""
        created_persons = []
        
        # S'assurer que toutes les personnes mentionnées dans les relations sont créées
        self._ensure_all_persons_from_relations(context)
        
        for person_info in persons_data:
            try:
                clean_extra_info = self._clean_person_info(person_info)
                clean_extra_info['context'] = context
                
                # Extraction des dates spécifiques
                dates_info = self._extract_person_dates(person_info['nom_complet'], context)
                clean_extra_info.update(dates_info)
                
                person = self.person_manager.get_or_create_person(
                    person_info['nom'],
                    person_info['prenom'],
                    clean_extra_info
                )
                
                # Mise à jour des dates après création
                self._update_person_dates(person, dates_info, context)
                
                created_persons.append(person)
                
            except Exception as e:
                self.logger.warning(f"Erreur traitement personne {person_info.get('nom_complet', 'INCONNU')}: {e}")
                continue
        
        return created_persons
    
    def _ensure_all_persons_from_relations(self, context: str):
        """NOUVEAU: S'assurer que toutes les personnes mentionnées dans les relations sont créées"""
        try:
            relation_names = set()
            
            # Pattern pour Charlotte dans "Charlotte, fille de..."
            charlotte_pattern = r'\b(Charlotte)\b[^,]*,\s+fille'
            charlotte_match = re.search(charlotte_pattern, context, re.IGNORECASE)
            if charlotte_match:
                relation_names.add("Charlotte")
            
            # Pattern pour parrains/marraines
            parrain_pattern = r'parr\.?\s*:\s*([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?)(?:[,;.]|$)'
            marraine_pattern = r'marr\.?\s*:\s*([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?)(?:[,;.]|$)'
            
            for match in re.finditer(parrain_pattern, context, re.IGNORECASE):
                name = self._clean_name_from_description(match.group(1).strip())
                if name:
                    relation_names.add(name)
            
            for match in re.finditer(marraine_pattern, context, re.IGNORECASE):
                name = match.group(1).strip()
                if name:
                    relation_names.add(name)
            
            # Créer les personnes manquantes
            for name in relation_names:
                if ' ' in name:
                    prenom, nom = name.split(' ', 1)
                    existing = self.person_manager.get_persons_by_name(nom, prenom)
                    
                    if not existing:
                        self.logger.info(f"CRÉATION PERSONNE MANQUANTE: {name}")
                        self.person_manager.get_or_create_person(nom, prenom, {
                            'context': context,
                            'professions': [],
                            'terres': [],
                            'notable': False
                        })
                elif len(name) > 2:
                    existing = self.person_manager.get_persons_by_name("", name)
                    
                    if not existing:
                        self.logger.info(f"CRÉATION PERSONNE MANQUANTE (prénom seul): {name}")
                        self.person_manager.get_or_create_person("", name, {
                            'context': context,
                            'professions': [],
                            'terres': [],
                            'notable': False
                        })
                        
        except Exception as e:
            self.logger.warning(f"Erreur création personnes manquantes: {e}")
    
    def _extract_person_dates(self, person_name: str, context: str) -> Dict:
        """NOUVEAU: Extrait les dates spécifiques à une personne"""
        dates_info = {}
        
        try:
            person_name_lower = person_name.lower()
            
            # Date de décès avec inhumation
            deces_pattern = rf'(\d{{1,2}}\s+\w+\.?),?\s+décès[^,]*,?\s+[^,]*inhumation[^,]*,?\s+de\s+{re.escape(person_name)}'
            deces_match = re.search(deces_pattern, context, re.IGNORECASE)
            
            if deces_match:
                date_deces = deces_match.group(1)
                year_match = re.search(r'\b(\d{4})\b', context[:deces_match.start()])
                if year_match:
                    date_deces = f"{date_deces} {year_match.group(1)}"
                dates_info['date_deces'] = date_deces
                self.logger.info(f"DATE DÉCÈS DÉTECTÉE pour {person_name}: {date_deces}")
            
            # Date de naissance avec baptême
            naissance_pattern = rf'(\d{{1,2}}\s+\w+\.?).*?naissance.*?bapt.*?de\s+{re.escape(person_name)}'
            naissance_match = re.search(naissance_pattern, context, re.IGNORECASE)
            
            if not naissance_match:
                fille_pattern = rf'(\d{{1,2}}\s+\w+\.?).*?{re.escape(person_name)},\s+fille\s+de'
                fille_match = re.search(fille_pattern, context, re.IGNORECASE)
                if fille_match:
                    naissance_match = fille_match
            
            if naissance_match:
                date_naissance = naissance_match.group(1)
                year_match = re.search(r'\b(\d{4})\b', context[:naissance_match.start()])
                if year_match:
                    date_naissance = f"{date_naissance} {year_match.group(1)}"
                dates_info['date_naissance'] = date_naissance
                self.logger.info(f"DATE NAISSANCE DÉTECTÉE pour {person_name}: {date_naissance}")
            
            # Prise de possession pour les prêtres
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
        """NOUVEAU: Met à jour les dates d'une personne"""
        try:
            if 'date_naissance' in dates_info and not person.date_naissance:
                person.date_naissance = dates_info['date_naissance']
                self.logger.info(f"DATE NAISSANCE ASSIGNÉE à {person.full_name}: {person.date_naissance}")
            
            if 'date_deces' in dates_info and not person.date_deces:
                person.date_deces = dates_info['date_deces']
                person.est_vivant = False
                self.logger.info(f"DATE DÉCÈS ASSIGNÉE à {person.full_name}: {person.date_deces}")
            
            if 'date_prise_possession' in dates_info:
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
                    clean_list = []
                    for item in value:
                        if isinstance(item, (str, int, float, bool)) or item is None:
                            clean_list.append(item)
                        elif isinstance(item, dict):
                            continue
                        else:
                            clean_list.append(str(item))
                    clean_info[key] = clean_list
                else:
                    clean_info[key] = str(value)
                    
            except Exception as e:
                self.logger.debug(f"Erreur nettoyage {key}: {e}")
                continue
        
        return clean_info
    
    def _process_actes(self, segments: List[Dict], persons: List[Person]) -> List[ActeParoissial]:
        """VERSION FINALE: Traitement des actes avec logging détaillé"""
        created_actes = []
        
        self.logger.info(f"Traitement de {len(segments)} segments pour créer des actes")
        
        for i, segment in enumerate(segments):
            if segment['type'] != 'acte':
                self.logger.debug(f"Segment {i} ignoré (type: {segment['type']})")
                continue
            
            try:
                self.logger.debug(f"Analyse du segment {i}: {segment['content'][:100]}...")
                
                acte_info = self._analyze_segment_for_acte(segment, persons)
                
                if acte_info:
                    acte = self.acte_manager.create_acte(acte_info)
                    
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
        """VERSION FINALE: Analyse complète d'un segment"""
        content = segment['content']
        
        acte_type = self._detect_acte_type(content)
        if not acte_type:
            self.logger.warning(f"Aucun type d'acte détecté pour: {content[:50]}...")
            return None
        
        dates = self.date_parser.extract_all_dates(content)
        main_date = dates[0] if dates else None
        
        year_from_segment = None
        if segment.get('index', 0) > 0:
            year_match = re.search(r'\b(\d{4})\b', content)
            if year_match:
                year_from_segment = int(year_match.group(1))
        
        person_assignments = self._extract_relations_from_content(content)
        
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
        
        acte_info = self._map_names_to_person_ids(acte_info, persons)
        
        self.logger.info(f"ACTE CRÉÉ: Type={acte_type}, Date={date_str}, Personnes={len(person_assignments)}")
        
        return acte_info
    
    def _extract_relations_from_content(self, content: str) -> Dict:
        """VERSION FINALE: Extraction précise des relations"""
        person_assignments = {}
        
        try:
            # 1. BAPTÊME: "Charlotte, fille de Jean Le Boucher... et de Françoise Varin"
            fille_pattern = r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]+),\s+fille\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s,]+?)(?:\s*,\s*[^,]*?)?\s+et\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?)(?:[,;]|$)'
            fille_match = re.search(fille_pattern, content, re.IGNORECASE)
            
            if fille_match:
                enfant_nom = fille_match.group(1).strip()
                pere_desc = fille_match.group(2).strip()
                mere_nom = fille_match.group(3).strip()
                
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
            
            # 4. CORRECTION: Pattern épouse amélioré
            epouse_pattern = r'(?:de\s+)?([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?),\s+épouse\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?)(?:[,;.]|$)'
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
        """NOUVEAU: Nettoie un nom des attributs qui l'accompagnent"""
        try:
            if not description:
                return None
            
            clean_desc = description
            
            patterns_to_remove = [
                r',\s*écuyer.*$', r',\s*éc\..*$', r',\s*sieur.*$', r',\s*sr\s+de.*$',
                r',\s*seigneur.*$', r',\s*sgr.*$', r',\s*avocat.*$', r',\s*conseiller.*$',
                r',\s*curé.*$', r',\s*prêtre.*$', r',\s*avocat\s+du\s+roi.*$', r',\s*notable.*$'
            ]
            
            for pattern in patterns_to_remove:
                clean_desc = re.sub(pattern, '', clean_desc, flags=re.IGNORECASE)
            
            clean_desc = clean_desc.strip().rstrip(',').strip()
            
            if len(clean_desc) >= 5 and ' ' in clean_desc:
                if re.match(r'^[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß]', clean_desc):
                    return clean_desc
            
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
        """VERSION FINALE: Mappe les noms extraits vers les IDs des personnes"""
        person_assignments = acte_info.get('person_assignments', {})
        
        try:
            name_to_person = {}
            
            for person in persons:
                full_name_key = person.full_name.lower().strip()
                name_to_person[full_name_key] = person
                
                # NOUVEAU: Mapping par prénom seul pour Charlotte
                if person.prenom and not person.nom:
                    prenom_key = person.prenom.lower().strip()
                    name_to_person[prenom_key] = person
                
                variations = [
                    person.full_name.replace(' de ', ' '),
                    person.full_name.replace('de ', ''),
                    person.full_name.replace(' Le ', ' le '),
                ]
                
                for variation in variations:
                    var_key = variation.lower().strip()
                    if var_key != full_name_key and var_key not in name_to_person:
                        name_to_person[var_key] = variation
            
            self.logger.debug(f"Mapping créé pour {len(name_to_person)} variations de noms")
            
            mappings_found = []
            
            # CORRECTION: Mapping pour enfant (Charlotte)
            if 'enfant_nom' in person_assignments:
                enfant_name = person_assignments['enfant_nom'].lower().strip()
                
                if enfant_name in name_to_person:
                    acte_info['personne_principale_id'] = name_to_person[enfant_name].id
                    mappings_found.append(f"enfant: {person_assignments['enfant_nom']} -> ID {name_to_person[enfant_name].id}")
                else:
                    self.logger.warning(f"Création personne manquante pour enfant: {person_assignments['enfant_nom']}")
                    enfant_person = self._create_missing_person(person_assignments['enfant_nom'])
                    if enfant_person:
                        persons.append(enfant_person)
                        acte_info['personne_principale_id'] = enfant_person.id
                        mappings_found.append(f"enfant (créé): {person_assignments['enfant_nom']} -> ID {enfant_person.id}")
            
            # Mapping pour père
            if 'pere_nom' in person_assignments and person_assignments['pere_nom']:
                pere_name = person_assignments['pere_nom'].lower().strip()
                if pere_name in name_to_person:
                    acte_info['pere_id'] = name_to_person[pere_name].id
                    mappings_found.append(f"père: {person_assignments['pere_nom']} -> ID {name_to_person[pere_name].id}")
            
            # Mapping pour mère
            if 'mere_nom' in person_assignments and person_assignments['mere_nom']:
                mere_name = person_assignments['mere_nom'].lower().strip()
                if mere_name in name_to_person:
                    acte_info['mere_id'] = name_to_person[mere_name].id
                    mappings_found.append(f"mère: {person_assignments['mere_nom']} -> ID {name_to_person[mere_name].id}")
            
            # Mapping pour parrain
            if 'parrain_nom' in person_assignments and person_assignments['parrain_nom']:
                parrain_name = person_assignments['parrain_nom'].lower().strip()
                if parrain_name in name_to_person:
                    acte_info['parrain_id'] = name_to_person[parrain_name].id
                    mappings_found.append(f"parrain: {person_assignments['parrain_nom']} -> ID {name_to_person[parrain_name].id}")
            
            # Mapping pour marraine  
            if 'marraine_nom' in person_assignments and person_assignments['marraine_nom']:
                marraine_name = person_assignments['marraine_nom'].lower().strip()
                if marraine_name in name_to_person:
                    acte_info['marraine_id'] = name_to_person[marraine_name].id
                    mappings_found.append(f"marraine: {person_assignments['marraine_nom']} -> ID {name_to_person[marraine_name].id}")
            
            # Mapping pour épouse/mari
            if 'epouse_nom' in person_assignments and 'mari_nom' in person_assignments:
                epouse_name = person_assignments['epouse_nom'].lower().strip()
                mari_name = person_assignments['mari_nom'].lower().strip()
                
                if epouse_name in name_to_person:
                    acte_info['personne_principale_id'] = name_to_person[epouse_name].id
                    mappings_found.append(f"épouse: {person_assignments['epouse_nom']} -> ID {name_to_person[epouse_name].id}")
                    
                if mari_name in name_to_person:
                    acte_info['conjoint_id'] = name_to_person[mari_name].id
                    mappings_found.append(f"mari: {person_assignments['mari_nom']} -> ID {name_to_person[mari_name].id}")
            
            # Mapping pour défunt
            if 'defunt_nom' in person_assignments and person_assignments['defunt_nom']:
                defunt_name = person_assignments['defunt_nom'].lower().strip()
                if defunt_name in name_to_person:
                    acte_info['personne_principale_id'] = name_to_person[defunt_name].id
                    mappings_found.append(f"défunt: {person_assignments['defunt_nom']} -> ID {name_to_person[defunt_name].id}")
            
            if mappings_found:
                self.logger.info(f"MAPPINGS RÉUSSIS: {'; '.join(mappings_found)}")
            else:
                self.logger.warning("Aucun mapping nom->ID réussi")
                
            for key, name in person_assignments.items():
                if name and key.endswith('_nom'):
                    name_lower = name.lower().strip()
                    if name_lower not in name_to_person:
                        self.logger.warning(f"NOM NON TROUVÉ: {name} (clé: {key})")
                        
        except Exception as e:
            self.logger.error(f"Erreur mapping noms->IDs: {e}")
        
        return acte_info
    
    def _create_missing_person(self, name: str) -> Optional[Person]:
        """NOUVEAU: Crée une personne manquante"""
        try:
            if ' ' in name:
                prenom, nom = name.split(' ', 1)
            else:
                prenom, nom = name, ""
            
            person = self.person_manager.get_or_create_person(nom, prenom, {
                'professions': [],
                'terres': [],
                'notable': False,
                'context': f"Personne créée automatiquement pour: {name}"
            })
            
            self.logger.info(f"PERSONNE MANQUANTE CRÉÉE: {person.full_name} (ID: {person.id})")
            return person
            
        except Exception as e:
            self.logger.error(f"Erreur création personne manquante {name}: {e}")
            return None
    
    def _detect_acte_type(self, content: str) -> Optional[str]:
        """VERSION FINALE: Détection des types d'actes"""
        if not content:
            return None
        
        content_lower = content.lower()
        
        self.logger.debug(f"Détection type acte pour: {content[:100]}...")
        
        detected_type = None
        
        if 'prise de possession' in content_lower or 'pris possession' in content_lower:
            detected_type = 'prise_possession'
        elif any(word in content_lower for word in ['fille de', 'fils de']):
            detected_type = 'baptême'
        elif any(word in content_lower for word in ['baptême', 'bapt.', 'naissance et baptême', 'cérémonies du bapt']):
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
    parser = argparse.ArgumentParser(description='Parser généalogique pour registres paroissiaux et PDF')
    parser.add_argument('input_file', nargs='?', 
                       default=r'C:\Users\Louis\Documents\CodexGenea\inventairesommai03archuoft.pdf',
                       help='Fichier texte ou PDF à analyser')
    parser.add_argument('-o', '--output', help='Répertoire de sortie', default='output')
    parser.add_argument('-c', '--config', help='Fichier de configuration')
    parser.add_argument('-l', '--lieu', help='Lieu du registre', default='Archive départementale')
    parser.add_argument('--pdf-method', choices=['auto', 'pymupdf', 'pdfplumber', 'pypdf2'], 
                       default='auto', help='Méthode de lecture PDF')
    parser.add_argument('--pdf-pages', type=int, help='Nombre max de pages PDF à traiter')
    parser.add_argument('--pdf-range', type=str, help='Plage de pages (ex: 1-50)')
    parser.add_argument('--pdf-chunks', type=int, default=100, 
                       help='Taille des chunks pour gros PDF (pages)')
    parser.add_argument('--gedcom', action='store_true', help='Exporter en GEDCOM')
    parser.add_argument('--json', action='store_true', help='Exporter en JSON')
    parser.add_argument('--format', choices=['console', 'file'], default='console', 
                       help='Format de sortie du rapport')
    parser.add_argument('-v', '--verbose', action='store_true', help='Mode verbeux')
    args = parser.parse_args()
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Erreur: Fichier '{args.input_file}' introuvable")
        sys.exit(1)
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    genealogy_parser = GenealogyParser(args.config)
    
    try:
        text_content = ""
        file_extension = input_path.suffix.lower()
        
        if file_extension == '.pdf':
            print(f"Fichier PDF détecté: {input_path.name}")
            
            if not HAS_PDF_SUPPORT:
                print("Support PDF non disponible!")
                print("Installez les dépendances avec: pip install PyMuPDF")
                sys.exit(1)
            
            pdf_reader = PDFReader()
            pdf_options = {
                'method': args.pdf_method,
                'max_pages': args.pdf_pages
            }
            
            if args.pdf_range:
                try:
                    start, end = map(int, args.pdf_range.split('-'))
                    pdf_options['page_range'] = (start, end)
                except ValueError:
                    print(f"Format de plage invalide: {args.pdf_range} (utilisez: 1-50)")
                    sys.exit(1)
            
            pdf_info = pdf_reader.get_pdf_info(str(input_path))
            print(f"PDF: {pdf_info['pages']} pages, {pdf_info['file_size']/1024/1024:.1f} MB")
            print(f"Temps estimé: {pdf_info['estimated_processing_time']:.1f}s")
            
            if isinstance(pdf_info['pages'], int) and pdf_info['pages'] > 200:
                print(f"Traitement par chunks de {args.pdf_chunks} pages...")
                all_chunks = []
                chunk_count = 0
                
                try:
                    for chunk_text in pdf_reader.read_pdf_in_chunks(str(input_path), args.pdf_chunks):
                        chunk_count += 1
                        print(f"Traitement chunk {chunk_count}...")
                        all_chunks.append(chunk_text)
                        if chunk_count >= 10:
                            print("Limitation à 10 chunks pour éviter la surcharge")
                            break
                
                    text_content = '\n\n'.join(all_chunks)
                except:
                    print("Fallback vers lecture normale...")
                    text_content = pdf_reader.read_pdf_file(str(input_path), **pdf_options)
                
            else:
                print(f"Lecture PDF...")
                text_content = pdf_reader.read_pdf_file(str(input_path), **pdf_options)
            
            stats = pdf_reader.get_statistics()
            print(f"PDF lu: {stats['pages_processed']} pages, "
                  f"{stats['total_chars']:,} caractères, "
                  f"{stats['processing_time']:.2f}s")
            
            if stats['errors'] > 0:
                print(f"{stats['errors']} erreurs de lecture")
        
        else:
            print(f"Lecture fichier texte: {input_path.name}")
            with open(input_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
        
        if not text_content.strip():
            print("Aucun contenu textuel extrait!")
            sys.exit(1)
        
        print(f"Contenu extrait: {len(text_content):,} caractères")
        
        print(f"Traitement généalogique...")
        
        if len(text_content) > 500000:
            print("Document volumineux détecté - traitement optimisé...")
            text_content = text_content[:500000] + "\n... [Document tronqué pour le traitement]"
        report = genealogy_parser.process_document(text_content, args.lieu)
        
        if args.format == 'console':
            ReportGenerator.print_formatted_results(report)
      
        if args.format == 'file':
            report_path = output_dir / f"rapport_{input_path.stem}.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                import contextlib, io
                f_buffer = io.StringIO()
                with contextlib.redirect_stdout(f_buffer):
                    ReportGenerator.print_formatted_results(report)
                f.write(f_buffer.getvalue())
            print(f"Rapport sauvegardé: {report_path}")
        
        if args.gedcom:
            gedcom_path = output_dir / f"{input_path.stem}.ged"
            genealogy_parser.export_to_gedcom(str(gedcom_path))
            print(f"Export GEDCOM: {gedcom_path}")
        
        if args.json:
            json_path = output_dir / f"{input_path.stem}.json"
            genealogy_parser.export_to_json(str(json_path))
            print(f"Export JSON: {json_path}")
        
        if args.verbose:
            stats = genealogy_parser.get_global_statistics()
            print("\nSTATISTIQUES DÉTAILLÉES")
            print("=" * 40)
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        
        print(f"\nTraitement terminé avec succès!")
        print(f"Fichier traité: {input_path.name}")
        
    except Exception as e:
        print(f"Erreur durant le traitement: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def demo_usage():
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
    
    print("=== DÉMONSTRATION DU PARSER AVEC SUPPORT PDF ===\n")
    
    if HAS_PDF_SUPPORT:
        print("Support PDF activé!")
        pdf_reader = PDFReader()
        print(f"Bibliothèques disponibles: {pdf_reader.get_available_libraries()}")
    else:
        print("Support PDF non disponible")
        print("Installez: pip install PyMuPDF")
    
    parser = GenealogyParser()
    result = parser.process_document(sample_text)
    ReportGenerator.print_formatted_results(result)
    
    print("\n💡 UTILISATION PDF:")
    print(f"python main.py # Utilise le PDF par défaut")
    print(f"python main.py votre_fichier.pdf")
    print(f"python main.py document.pdf --pdf-pages 100")
    print(f"python main.py document.pdf --pdf-range 1-50 -v")
    return result

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        print("LANCEMENT AUTOMATIQUE avec PDF par défaut...")
        print(f"Fichier: C:\\Users\\Louis\\Documents\\CodexGenea\\inventairesommai03archuoft.pdf")
        print()
        
        default_pdf = r'C:\Users\Louis\Documents\CodexGenea\inventairesommai03archuoft.pdf'
        if Path(default_pdf).exists():
            sys.argv = ['main.py', default_pdf, '--pdf-pages', '10', '-v']
            main()
        else:
            print("Fichier PDF par défaut introuvable")
            print("Démonstration avec contenu texte...")
            demo_usage()
    else:
        main()