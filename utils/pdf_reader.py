"""
Lecteur PDF utilisant exclusivement PyMuPDF avec extraction de sources détaillées
Garméa v.0.17.0 - Support sources par page
"""

import logging
import re
from typing import List, Dict, Optional, Generator, Tuple
from pathlib import Path
import time
from dataclasses import dataclass

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    raise ImportError("PyMuPDF est requis pour Garméa v.0.17.0. Installez avec: pip install PyMuPDF")

@dataclass
class PageSource:
    """Information de source pour une page"""
    page_number: int
    archive_name: str = ""
    collection: str = ""
    year_range: str = ""
    source_reference: str = ""
    
    def __post_init__(self):
        if not self.source_reference and self.archive_name:
            parts = []
            if self.archive_name:
                parts.append(self.archive_name)
            if self.collection:
                parts.append(self.collection)
            if self.year_range:
                parts.append(self.year_range)
            
            self.source_reference = ", ".join(parts)
            if self.page_number:
                self.source_reference += f", p.{self.page_number}"

class PyMuPDFOnlyReader:
    """Lecteur PDF exclusivement basé sur PyMuPDF avec extraction de sources"""
    
    def __init__(self):
        if not HAS_PYMUPDF:
            raise ImportError("PyMuPDF est requis pour ce module")
        
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'pages_processed': 0,
            'total_chars': 0,
            'processing_time': 0,
            'errors': 0,
            'sources_detected': 0,
            'registres_pages': 0
        }
        
        # Patterns pour détecter les sources dans les pages
        self.source_patterns = self._compile_source_patterns()
    
    def _compile_source_patterns(self) -> Dict[str, re.Pattern]:
        """Compile les patterns pour détecter les sources dans les textes"""
        
        return {
            # Pattern pour en-têtes de registres
            'registre_header': re.compile(
                r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\-\s]+)[\.,]\s*'
                r'(BMS|B[aâ]pt?\.|Mar?\.|Inh?\.)\s*'
                r'(\d{4}[-–]\d{4})',
                re.IGNORECASE
            ),
            
            # Pattern pour références d'archives
            'archive_reference': re.compile(
                r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\-\s]+),?\s*'
                r'([A-Z]{2,4})\s*'
                r'(\d{4}[-–]\d{4})',
                re.MULTILINE
            ),
            
            # Pattern pour numérotation de pages
            'page_number': re.compile(
                r'(?:p\.?\s*|page\s+)(\d+)',
                re.IGNORECASE
            ),
            
            # Pattern pour identification des registres paroissiaux
            'paroissial_indicators': re.compile(
                r'\b(?:baptême|bapt\.|mariage|mar\.|inhumation|inh\.|'
                r'registres?\s+paroissiaux?|curé|prêtre|église|paroisse)\b',
                re.IGNORECASE
            )
        }
    
    def read_pdf_with_sources(self, pdf_path: str, 
                            max_pages: Optional[int] = None,
                            page_range: Optional[Tuple[int, int]] = None,
                            extract_sources: bool = True) -> Dict[str, any]:
        """
        Lit un PDF avec extraction automatique des sources par page
        
        Returns:
            Dict contenant 'content', 'sources', 'pages_info'
        """
        
        start_time = time.time()
        
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"Fichier PDF introuvable: {pdf_path}")
        
        self.logger.info(f"Lecture PDF avec PyMuPDF: {Path(pdf_path).name}")
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            self.logger.info(f"Document PDF: {total_pages} pages")
            
            # Déterminer les pages à traiter
            start_page, end_page = self._get_page_range(total_pages, max_pages, page_range)
            
            # Structures de données
            content_parts = []
            page_sources = {}
            pages_info = []
            
            # Traiter chaque page
            for page_num in range(start_page, end_page):
                try:
                    page = doc[page_num]
                    page_text = page.get_text()
                    
                    if not page_text.strip():
                        continue
                    
                    page_number = page_num + 1  # Numérotation 1-based
                    
                    # Extraire les informations de source de cette page
                    page_source = None
                    if extract_sources:
                        page_source = self._extract_page_source(page_text, page_number)
                        if page_source:
                            page_sources[page_number] = page_source
                            self.stats['sources_detected'] += 1
                    
                    # Vérifier si c'est une page de registre paroissial
                    is_registre = self._is_registre_page(page_text)
                    if is_registre:
                        self.stats['registres_pages'] += 1
                    
                    # Ajouter le contenu avec métadonnées
                    content_parts.append(f"\n--- PAGE {page_number} ---")
                    if page_source and page_source.source_reference:
                        content_parts.append(f"Source: {page_source.source_reference}")
                    content_parts.append(page_text)
                    
                    # Informations détaillées de la page
                    page_info = {
                        'page_number': page_number,
                        'char_count': len(page_text),
                        'is_registre': is_registre,
                        'source': page_source.source_reference if page_source else "",
                        'archive': page_source.archive_name if page_source else "",
                        'collection': page_source.collection if page_source else "",
                        'year_range': page_source.year_range if page_source else ""
                    }
                    pages_info.append(page_info)
                    
                    self.stats['pages_processed'] += 1
                    
                    # Log de progression
                    if page_number % 50 == 0:
                        self.logger.info(f"Progression: {page_number}/{end_page} pages")
                        
                except Exception as e:
                    self.logger.warning(f"Erreur page {page_num + 1}: {e}")
                    self.stats['errors'] += 1
                    continue
            
            doc.close()
            
            # Assemblage final
            full_content = '\n'.join(content_parts)
            
            # Statistiques finales
            self.stats['total_chars'] = len(full_content)
            self.stats['processing_time'] = time.time() - start_time
            
            self.logger.info(
                f"PDF lu avec succès: {self.stats['pages_processed']} pages, "
                f"{self.stats['total_chars']:,} caractères, "
                f"{self.stats['sources_detected']} sources détectées, "
                f"{self.stats['registres_pages']} pages de registres, "
                f"{self.stats['processing_time']:.2f}s"
            )
            
            return {
                'content': full_content,
                'sources': page_sources,
                'pages_info': pages_info,
                'statistics': self.stats.copy()
            }
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Erreur lecture PDF: {e}")
            raise
    
    def _extract_page_source(self, page_text: str, page_number: int) -> Optional[PageSource]:
        """Extrait les informations de source d'une page"""
        
        # Chercher dans les premières lignes (en-tête)
        lines = page_text.split('\n')[:10]  # Première partie de la page
        header_text = '\n'.join(lines)
        
        # Chercher un en-tête de registre
        registre_match = self.source_patterns['registre_header'].search(header_text)
        if registre_match:
            archive_name = registre_match.group(1).strip()
            collection = registre_match.group(2).strip()
            year_range = registre_match.group(3).strip()
            
            return PageSource(
                page_number=page_number,
                archive_name=archive_name,
                collection=collection,
                year_range=year_range
            )
        
        # Chercher une référence d'archive
        archive_match = self.source_patterns['archive_reference'].search(header_text)
        if archive_match:
            archive_name = archive_match.group(1).strip()
            collection = archive_match.group(2).strip()
            year_range = archive_match.group(3).strip()
            
            return PageSource(
                page_number=page_number,
                archive_name=archive_name,
                collection=collection,
                year_range=year_range
            )
        
        # Si aucune source spécifique trouvée, créer une source basique
        if self._is_registre_page(page_text):
            return PageSource(
                page_number=page_number,
                archive_name="Archive départementale",
                collection="Registres paroissiaux",
                year_range="XVIIe-XVIIIe siècle"
            )
        
        return None
    
    def _is_registre_page(self, page_text: str) -> bool:
        """Détermine si une page contient des registres paroissiaux"""
        
        # Compter les indicateurs paroissiaux
        indicators = self.source_patterns['paroissial_indicators'].findall(page_text.lower())
        
        # Si plus de 2 indicateurs, c'est probablement une page de registre
        return len(indicators) >= 2
    
    def _get_page_range(self, total_pages: int, max_pages: Optional[int], 
                       page_range: Optional[Tuple[int, int]]) -> Tuple[int, int]:
        """Détermine la plage de pages à traiter"""
        
        if page_range:
            start_page = max(0, page_range[0] - 1)  # Conversion 1-based vers 0-based
            end_page = min(total_pages, page_range[1])
        else:
            start_page = 0
            end_page = min(total_pages, max_pages) if max_pages else total_pages
        
        return start_page, end_page
    
    def read_pdf_in_chunks_with_sources(self, pdf_path: str, 
                                      chunk_size: int = 50) -> Generator[Dict, None, None]:
        """
        Lit un PDF par chunks avec sources pour les très gros documents
        """        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        self.logger.info(f"Lecture par chunks de {chunk_size} pages: {total_pages} pages total")
        
        for start_page in range(0, total_pages, chunk_size):
            end_page = min(start_page + chunk_size, total_pages)
            
            chunk_data = self.read_pdf_with_sources(
                pdf_path, 
                page_range=(start_page + 1, end_page)  # Conversion vers 1-based
            )
            
            self.logger.info(f"Chunk {start_page + 1}-{end_page}: "
                           f"{len(chunk_data['content'])} caractères, "
                           f"{len(chunk_data['sources'])} sources")
            
            yield chunk_data
        
        doc.close()
    
    def extract_marriage_sources(self, pdf_path: str) -> List[Dict]:
        """
        Extrait spécifiquement les mariages avec leurs sources détaillées
        Ex: "Jean Le Boucher marié le 5 juillet 1677 à Jacqueline Dupré"
        """
        
        self.logger.info("Extraction des mariages avec sources détaillées")
        
        pdf_data = self.read_pdf_with_sources(pdf_path)
        content = pdf_data['content']
        page_sources = pdf_data['sources']
        
        marriages = []
        
        # Pattern pour mariages
        marriage_pattern = re.compile(
            r'(\d{1,2}\s+\w+\.?\s+\d{4})[^,]*,?\s*'
            r'mariage\s+de\s+'
            r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+?)'
            r'[^,]*,?\s*'
            r'(?:avec|à|et)\s+'
            r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\s]+)',
            re.IGNORECASE | re.MULTILINE
        )
        
        for match in marriage_pattern.finditer(content):
            date_str = match.group(1).strip()
            epoux = match.group(2).strip()
            epouse = match.group(3).strip()
            
            # Trouver la page source correspondante
            match_position = match.start()
            page_number = self._find_page_for_position(content, match_position)
            
            source_info = page_sources.get(page_number, PageSource(page_number))
            
            marriage_data = {
                'date': date_str,
                'epoux': epoux,
                'epouse': epouse,
                'lieu_mariage': self._extract_marriage_location(match.group(0)),
                'source_reference': source_info.source_reference,
                'page_number': page_number,
                'archive': source_info.archive_name,
                'collection': source_info.collection,
                'context': match.group(0)
            }
            
            marriages.append(marriage_data)
        
        self.logger.info(f"Mariages extraits avec sources: {len(marriages)}")
        return marriages
    
    def _find_page_for_position(self, content: str, position: int) -> int:
        """Trouve le numéro de page correspondant à une position dans le texte"""
        
        # Chercher les marqueurs de page avant cette position
        page_markers = list(re.finditer(r'--- PAGE (\d+) ---', content[:position]))
        
        if page_markers:
            last_marker = page_markers[-1]
            return int(last_marker.group(1))
        
        return 1  # Page par défaut
    
    def _extract_marriage_location(self, marriage_text: str) -> Optional[str]:
        """Extrait le lieu du mariage depuis le texte"""
        
        # Pattern pour lieu de mariage
        location_patterns = [
            r'en\s+l\'église\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\-\s]+)',
            r'à\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\-\s]+)',
            r'dans\s+la\s+paroisse\s+de\s+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\-\s]+)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, marriage_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def get_pdf_info(self, pdf_path: str) -> Dict:
        """Obtient les informations détaillées sur un PDF"""
        
        doc = fitz.open(pdf_path)
        
        info = {
            "pages": len(doc),
            "metadata": doc.metadata,
            "file_size": Path(pdf_path).stat().st_size,
            "estimated_processing_time": len(doc) * 0.05,  # PyMuPDF est rapide
            "supports_sources": True,
            "supports_chunks": True,
            "pymupdf_version": fitz.__version__ if hasattr(fitz, '__version__') else "unknown"
        }
        
        doc.close()
        return info
    
    def get_statistics(self) -> Dict:
        """Retourne les statistiques détaillées"""
        
        stats = self.stats.copy()
        
        if stats['processing_time'] > 0:
            stats['pages_per_second'] = stats['pages_processed'] / stats['processing_time']
            stats['chars_per_second'] = stats['total_chars'] / stats['processing_time']
        
        # Ratios utiles
        if stats['pages_processed'] > 0:
            stats['sources_per_page'] = stats['sources_detected'] / stats['pages_processed']
            stats['registres_ratio'] = stats['registres_pages'] / stats['pages_processed']
        
        return stats

# Exemple d'utilisation
if __name__ == "__main__":
    print("=== TEST LECTEUR PDF PYMUPDF EXCLUSIF ===")
    
    # Vérifier la disponibilité
    if not HAS_PYMUPDF:
        print("❌ PyMuPDF non disponible")
        print("Installation: pip install PyMuPDF")
        exit(1)
    
    reader = PyMuPDFOnlyReader()
    
    # Test sur un fichier d'exemple
    pdf_file = "inventairesommai03archuoft.pdf"
    
    if Path(pdf_file).exists():
        print(f"📄 Test sur: {pdf_file}")
        
        # Informations sur le PDF
        info = reader.get_pdf_info(pdf_file)
        print(f"Pages: {info['pages']}")
        print(f"Taille: {info['file_size'] / 1024 / 1024:.1f} MB")
        print(f"Version PyMuPDF: {info['pymupdf_version']}")
        
        # Lecture d'un échantillon
        result = reader.read_pdf_with_sources(pdf_file, max_pages=5)
        
        print(f"\n=== RÉSULTATS ===")
        print(f"Caractères extraits: {len(result['content']):,}")
        print(f"Sources détectées: {len(result['sources'])}")
        print(f"Pages de registres: {result['statistics']['registres_pages']}")
        
        # Afficher les sources trouvées
        if result['sources']:
            print(f"\n=== SOURCES DÉTECTÉES ===")
            for page_num, source in result['sources'].items():
                print(f"Page {page_num}: {source.source_reference}")
        
        # Test extraction mariages
        print(f"\n=== TEST EXTRACTION MARIAGES ===")
        marriages = reader.extract_marriage_sources(pdf_file)
        if marriages:
            print(f"Mariages trouvés: {len(marriages)}")
            for marriage in marriages[:3]:  # Premiers 3
                print(f"  {marriage['date']}: {marriage['epoux']} × {marriage['epouse']}")
                print(f"    Source: {marriage['source_reference']}")
        
        # Statistiques finales
        stats = reader.get_statistics()
        print(f"\n=== STATISTIQUES ===")
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")
    
    else:
        print(f"❌ Fichier PDF non trouvé: {pdf_file}")
        print("Test avec fichier fictif...")
        
        # Afficher juste les capacités
        print("✅ Capacités du lecteur PyMuPDF:")
        print("  - Extraction de sources par page")
        print("  - Détection automatique des registres paroissiaux")
        print("  - Extraction spécialisée des mariages")
        print("  - Lecture par chunks pour gros documents")
        print("  - Support exclusif PyMuPDF")
    
    print("\n🎉 Test terminé!")