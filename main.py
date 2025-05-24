import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Imports locaux
from config.settings import ParserConfig
from core.models import Person, ActeParoissial
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
from exporters.gedcom_exporter import GedcomExporter  # CORRECTION: Ajouter import manquant
from exporters.json_exporter import JsonExporter
from utils.logging_config import setup_logging, PerformanceLogger
from utils.text_utils import TextNormalizer

class GenealogyParser:
    """Parser généalogique principal avec architecture modulaire complète"""
    
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
        """Traitement complet d'un document avec toutes les optimisations"""
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
        """Traitement optimisé des personnes"""
        created_persons = []
        
        for person_info in persons_data:
            # Ajouter le contexte global pour validation
            person_info['context'] = context
            
            try:
                person = self.person_manager.get_or_create_person(
                    person_info['nom'],
                    person_info['prenom'],
                    person_info
                )
                created_persons.append(person)
                
            except Exception as e:
                self.logger.warning(f"Erreur traitement personne {person_info.get('nom_complet')}: {e}")
                continue
        
        return created_persons
    
    def _process_actes(self, segments: List[Dict], persons: List[Person]) -> List[ActeParoissial]:
        """Traitement des actes à partir des segments"""
        created_actes = []
        
        for segment in segments:
            if segment['type'] != 'acte':
                continue
            
            try:
                # Analyse du segment pour détecter le type d'acte
                acte_info = self._analyze_segment_for_acte(segment, persons)
                
                if acte_info:
                    acte = self.acte_manager.create_acte(acte_info)
                    
                    # Validation de l'acte
                    validation = self.acte_manager.validate_acte(acte, self.person_manager)
                    
                    created_actes.append(acte)
                    
            except Exception as e:
                self.logger.warning(f"Erreur traitement segment: {e}")
                continue
        
        return created_actes
    
    def _analyze_segment_for_acte(self, segment: Dict, persons: List[Person]) -> Optional[Dict]:
        """Analyse un segment pour créer un acte"""
        content = segment['content']
        
        # Détecter le type d'acte
        acte_type = self._detect_acte_type(content)
        if not acte_type:
            return None
        
        # Extraire les dates
        dates = self.date_parser.extract_all_dates(content)
        main_date = dates[0] if dates else None
        
        # Extraire les relations
        relationships = self.relationship_parser.extract_relationships(content)
        
        # Identifier les personnes impliquées
        person_assignments = self._assign_persons_to_acte(content, relationships, persons)
        
        return {
            'type_acte': acte_type,
            'date': main_date.original_text if main_date else "",
            'texte_original': content,
            'notable': self._is_acte_notable(content),
            **person_assignments
        }
    
    def _detect_acte_type(self, content: str) -> Optional[str]:
        """Détecte le type d'acte depuis le contenu"""
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ['baptême', 'bapt.']):
            return 'baptême'
        elif any(keyword in content_lower for keyword in ['mariage', 'mar.', 'épouse']):
            return 'mariage'
        elif any(keyword in content_lower for keyword in ['inhumation', 'inh.']):
            return 'inhumation'
        elif 'prise de possession' in content_lower:
            return 'prise_possession'
        
        return None
    
    def _assign_persons_to_acte(self, content: str, relationships: List[Dict], 
                              persons: List[Person]) -> Dict:
        """Assigne les personnes aux rôles dans l'acte"""
        assignments = {}
        
        # Logique d'assignation basée sur les relations et le contenu
        # Cette partie nécessiterait une logique plus complexe selon le type d'acte
        
        return assignments
    
    def _is_acte_notable(self, content: str) -> bool:
        """Détermine si l'acte concerne un notable"""
        content_lower = content.lower()
        notable_indicators = [
            "dans l'église", "dans l'eglise", "dans la chapelle",
            "sous le chœur", "près de l'autel"
        ]
        return any(indicator in content_lower for indicator in notable_indicators)
    
    def export_to_gedcom(self, output_path: str):
        """Export au format GEDCOM"""
        gedcom_exporter = GedcomExporter(self.config)
        gedcom_exporter.export(
            self.person_manager.persons,
            self.acte_manager.actes,
            output_path
        )
        self.logger.info(f"Export GEDCOM créé: {output_path}")
    
    def export_to_json(self, output_path: str):
        """Export au format JSON"""
        json_exporter = JsonExporter(self.config)
        json_exporter.export(
            self.person_manager.persons,
            self.acte_manager.actes,
            output_path
        )
        self.logger.info(f"Export JSON créé: {output_path}")
    
    def get_global_statistics(self) -> Dict:
        """Retourne les statistiques globales du parser"""
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