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
        return HAS_PYMUPDF
    
    def get_available_libraries(self) -> List[str]:
        libraries = []
        if HAS_PYMUPDF:
            libraries.append("PyMuPDF")
        return libraries
    
    def read_pdf_file(self, pdf_path: str, max_pages: Optional[int] = None,
                     page_range: Optional[tuple] = None, method: str = "auto") -> str:
        start_time = time.time()
        
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"Fichier PDF introuvable: {pdf_path}")
        
        if not HAS_PYMUPDF:
            raise ImportError("PyMuPDF requis mais non disponible")
        
        self.logger.info(f"Lecture PDF avec PyMuPDF: {Path(pdf_path).name}")
        
        try:
            text = self._read_with_pymupdf(pdf_path, max_pages, page_range)
            
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
                
                if (page_num + 1) % 50 == 0:
                    self.logger.info(f"Progression: {page_num + 1}/{end_page} pages")
                    
            except Exception as e:
                self.logger.warning(f"Erreur page {page_num + 1}: {e}")
                self.stats['errors'] += 1
                continue
        
        doc.close()
        return '\n'.join(text_parts)
    
    def _get_page_range(self, total_pages: int, max_pages: Optional[int], 
                       page_range: Optional[tuple]) -> tuple:
        if page_range:
            start_page = max(0, page_range[0] - 1)
            end_page = min(total_pages, page_range[1])
        else:
            start_page = 0
            end_page = min(total_pages, max_pages) if max_pages else total_pages
        
        return start_page, end_page
    
    def get_pdf_info(self, pdf_path: str) -> Dict:
        if not HAS_PYMUPDF:
            return {
                "pages": "Unknown",
                "file_size": Path(pdf_path).stat().st_size,
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
        stats = self.stats.copy()
        if stats['processing_time'] > 0:
            stats['pages_per_second'] = stats['pages_processed'] / stats['processing_time']
            stats['chars_per_second'] = stats['total_chars'] / stats['processing_time']
        return stats

class GenealogyParser:
    """Parser généalogique principal avec support PDF PyMuPDF"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = ParserConfig.from_file(config_path) if config_path else ParserConfig()
        
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
        
        self.global_stats = {
            'documents_processed': 0,
            'total_persons': 0,
            'total_actes': 0,
            'corrections_applied': 0,
            'processing_time': 0
        }
    
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
        """Traitement complet d'un document"""
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
            persons_data = self.name_extractor.extract_complete_names_with_sources(normalized_text)
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
        """Traitement des personnes avec extraction complète"""
        created_persons = []
        
        for person_info in persons_data:
            try:
                clean_extra_info = self._clean_person_info(person_info)
                clean_extra_info['context'] = context
                
                person = self.person_manager.get_or_create_person(
                    person_info['nom'],
                    person_info['prenom'],
                    clean_extra_info
                )
                
                created_persons.append(person)
                
            except Exception as e:
                self.logger.warning(f"Erreur traitement personne {person_info.get('nom_complet', 'INCONNU')}: {e}")
                continue
        
        return created_persons
    
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
        """Traitement des actes avec logging détaillé"""
        created_actes = []
        
        self.logger.info(f"Traitement de {len(segments)} segments pour créer des actes")
        
        for i, segment in enumerate(segments):
            if segment['type'] != 'acte':
                continue
            
            try:
                acte_info = self._analyze_segment_for_acte(segment, persons)
                
                if acte_info:
                    acte = self.acte_manager.create_acte(acte_info)
                    created_actes.append(acte)
                    self.logger.info(f"ACTE {acte.id} CRÉÉ: {acte.type_acte.value}")
                    
            except Exception as e:
                self.logger.error(f"Erreur traitement segment {i}: {e}")
                continue
        
        self.logger.info(f"Nombre total d'actes créés: {len(created_actes)}")
        return created_actes
    
    def _analyze_segment_for_acte(self, segment: Dict, persons: List[Person]) -> Optional[Dict]:
        """Analyse complète d'un segment"""
        content = segment['content']
        
        acte_type = self._detect_acte_type(content)
        if not acte_type:
            return None
        
        dates = self.date_parser.extract_all_dates(content)
        main_date = dates[0] if dates else None
        
        year_from_segment = None
        year_match = re.search(r'\b(\d{4})\b', content)
        if year_match:
            year_from_segment = int(year_match.group(1))
        
        date_str = ""
        if main_date:
            date_str = main_date.original_text
        elif year_from_segment:
            date_str = str(year_from_segment)
        
        acte_info = {
            'type_acte': acte_type,
            'date': date_str,
            'texte_original': content,
            'notable': self._is_acte_notable(content),
            'year': year_from_segment
        }
        
        return acte_info
    
    def _detect_acte_type(self, content: str) -> Optional[str]:
        """Détection des types d'actes"""
        if not content:
            return None
        
        content_lower = content.lower()
        
        if 'prise de possession' in content_lower or 'pris possession' in content_lower:
            return 'prise_possession'
        elif any(word in content_lower for word in ['fille de', 'fils de']):
            return 'baptême'
        elif any(word in content_lower for word in ['baptême', 'bapt.', 'naissance et baptême']):
            return 'baptême'
        elif any(word in content_lower for word in ['mariage', 'mar.', 'époux', 'épouse de']):
            return 'mariage'
        elif any(word in content_lower for word in ['inhumation', 'inh.', 'décès']):
            return 'inhumation'
        
        return None
    
    def _is_acte_notable(self, content: str) -> bool:
        """Détermine si l'acte concerne un notable"""
        if not content:
            return False
        
        content_lower = content.lower()
        notable_indicators = [
            "dans l'église", "dans l'eglise", "dans la chapelle",
            "sous le chœur", "près de l'autel"
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
    parser = argparse.ArgumentParser(description='Parser généalogique pour registres paroissiaux PDF')
    parser.add_argument('input_file', nargs='?', 
                       default=r'C:\Users\Louis\Documents\CodexGenea\inventairesommai03archuoft.pdf',
                       help='Fichier texte ou PDF à analyser')
    parser.add_argument('-o', '--output', help='Répertoire de sortie', default='output')
    parser.add_argument('-c', '--config', help='Fichier de configuration')
    parser.add_argument('-l', '--lieu', help='Lieu du registre', default='Archive départementale')
    parser.add_argument('--pdf-pages', type=int, help='Nombre max de pages PDF à traiter')
    parser.add_argument('--pdf-range', type=str, help='Plage de pages (ex: 1-50)')
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
            
            pdf_reader = PDFReader()
            if not pdf_reader.can_read_pdf():
                print("PyMuPDF non disponible!")
                print("Installez avec: pip install PyMuPDF")
                sys.exit(1)
            
            pdf_options = {'max_pages': args.pdf_pages}
            
            if args.pdf_range:
                try:
                    start, end = map(int, args.pdf_range.split('-'))
                    pdf_options['page_range'] = (start, end)
                except ValueError:
                    print(f"Format de plage invalide: {args.pdf_range}")
                    sys.exit(1)
            
            pdf_info = pdf_reader.get_pdf_info(str(input_path))
            print(f"PDF: {pdf_info['pages']} pages, {pdf_info['file_size']/1024/1024:.1f} MB")
            
            print("Lecture PDF...")
            text_content = pdf_reader.read_pdf_file(str(input_path), **pdf_options)
            
            stats = pdf_reader.get_statistics()
            print(f"PDF lu: {stats['pages_processed']} pages, "
                  f"{stats['total_chars']:,} caractères")
        
        else:
            print(f"Lecture fichier texte: {input_path.name}")
            with open(input_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
        
        if not text_content.strip():
            print("Aucun contenu textuel extrait!")
            sys.exit(1)
        
        print(f"Contenu extrait: {len(text_content):,} caractères")
        print("Traitement généalogique...")
        
        if len(text_content) > 500000:
            print("Document volumineux - traitement optimisé...")
            text_content = text_content[:500000]
        
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
    
    print("=== DÉMONSTRATION PARSER ===\n")
    
    pdf_reader = PDFReader()
    if pdf_reader.can_read_pdf():
        print("Support PDF PyMuPDF activé!")
    else:
        print("PyMuPDF non disponible")
    
    parser = GenealogyParser()
    result = parser.process_document(sample_text)
    ReportGenerator.print_formatted_results(result)
    
    return result

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("LANCEMENT AUTOMATIQUE avec PDF par défaut...")
        
        default_pdf = r'C:\Users\Louis\Documents\CodexGenea\inventairesommai03archuoft.pdf'
        if Path(default_pdf).exists():
            sys.argv = ['main.py', default_pdf, '--pdf-pages', '10', '-v']
            main()
        else:
            print("Fichier PDF par défaut introuvable")
            demo_usage()
    else:
        main()