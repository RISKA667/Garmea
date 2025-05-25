"""
Module de lecture PDF pour le parser généalogique
Permet de traiter des documents PDF de grande taille (600 pages+)
"""

import logging
from typing import List, Dict, Optional, Generator
from pathlib import Path
import time

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

class PDFReader:
    """Lecteur PDF optimisé pour gros documents généalogiques"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'pages_processed': 0,
            'total_chars': 0,
            'processing_time': 0,
            'errors': 0
        }
    
    def can_read_pdf(self) -> bool:
        """Vérifie si au moins une bibliothèque PDF est disponible"""
        return HAS_PYPDF2 or HAS_PDFPLUMBER or HAS_PYMUPDF
    
    def get_available_libraries(self) -> List[str]:
        """Retourne les bibliothèques PDF disponibles"""
        libraries = []
        if HAS_PYMUPDF:
            libraries.append("PyMuPDF (recommandé)")
        if HAS_PDFPLUMBER:
            libraries.append("pdfplumber (bon pour tableaux)")
        if HAS_PYPDF2:
            libraries.append("PyPDF2 (basique)")
        return libraries
    
    def read_pdf_file(self, pdf_path: str, 
                     max_pages: Optional[int] = None,
                     page_range: Optional[tuple] = None,
                     method: str = "auto") -> str:
        """
        Lit un fichier PDF et retourne le texte complet
        
        Args:
            pdf_path: Chemin vers le PDF
            max_pages: Nombre maximum de pages à traiter
            page_range: Tuple (start, end) pour traiter une plage
            method: "auto", "pymupdf", "pdfplumber", "pypdf2"
        """
        start_time = time.time()
        
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"Fichier PDF introuvable: {pdf_path}")
        
        # Choisir la méthode automatiquement
        if method == "auto":
            if HAS_PYMUPDF:
                method = "pymupdf"
            elif HAS_PDFPLUMBER:
                method = "pdfplumber"
            elif HAS_PYPDF2:
                method = "pypdf2"
            else:
                raise ImportError("Aucune bibliothèque PDF disponible")
        
        self.logger.info(f"Lecture PDF avec {method}: {pdf_path}")
        
        try:
            if method == "pymupdf":
                text = self._read_with_pymupdf(pdf_path, max_pages, page_range)
            elif method == "pdfplumber":
                text = self._read_with_pdfplumber(pdf_path, max_pages, page_range)
            elif method == "pypdf2":
                text = self._read_with_pypdf2(pdf_path, max_pages, page_range)
            else:
                raise ValueError(f"Méthode inconnue: {method}")
            
            # Statistiques
            self.stats['total_chars'] = len(text)
            self.stats['processing_time'] = time.time() - start_time
            
            self.logger.info(f"PDF lu avec succès: {self.stats['pages_processed']} pages, "
                           f"{self.stats['total_chars']} caractères, "
                           f"{self.stats['processing_time']:.2f}s")
            
            return text
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Erreur lecture PDF: {e}")
            raise
    
    def _read_with_pymupdf(self, pdf_path: str, max_pages: Optional[int], 
                          page_range: Optional[tuple]) -> str:
        """Lecture avec PyMuPDF (recommandé pour la performance)"""
        if not HAS_PYMUPDF:
            raise ImportError("PyMuPDF non disponible")
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        self.logger.info(f"Document PDF: {total_pages} pages")
        
        # Déterminer les pages à traiter
        start_page, end_page = self._get_page_range(total_pages, max_pages, page_range)
        
        text_parts = []
        
        for page_num in range(start_page, end_page):
            try:
                page = doc[page_num]
                page_text = page.get_text()
                
                if page_text.strip():  # Ignorer les pages vides
                    text_parts.append(f"\n--- PAGE {page_num + 1} ---\n")
                    text_parts.append(page_text)
                
                self.stats['pages_processed'] += 1
                
                # Log de progression pour gros documents
                if (page_num + 1) % 50 == 0:
                    self.logger.info(f"Progression: {page_num + 1}/{end_page} pages")
                    
            except Exception as e:
                self.logger.warning(f"Erreur page {page_num + 1}: {e}")
                self.stats['errors'] += 1
                continue
        
        doc.close()
        return '\n'.join(text_parts)
    
    def _read_with_pdfplumber(self, pdf_path: str, max_pages: Optional[int], 
                             page_range: Optional[tuple]) -> str:
        """Lecture avec pdfplumber (bon pour la mise en forme)"""
        if not HAS_PDFPLUMBER:
            raise ImportError("pdfplumber non disponible")
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            self.logger.info(f"Document PDF: {total_pages} pages")
            
            # Déterminer les pages à traiter
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
                    
                    # Log de progression
                    if (page_num + 1) % 50 == 0:
                        self.logger.info(f"Progression: {page_num + 1}/{end_page} pages")
                        
                except Exception as e:
                    self.logger.warning(f"Erreur page {page_num + 1}: {e}")
                    self.stats['errors'] += 1
                    continue
            
            return '\n'.join(text_parts)
    
    def _read_with_pypdf2(self, pdf_path: str, max_pages: Optional[int], 
                         page_range: Optional[tuple]) -> str:
        """Lecture avec PyPDF2 (basique)"""
        if not HAS_PYPDF2:
            raise ImportError("PyPDF2 non disponible")
        
        text_parts = []
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            self.logger.info(f"Document PDF: {total_pages} pages")
            
            # Déterminer les pages à traiter
            start_page, end_page = self._get_page_range(total_pages, max_pages, page_range)
            
            for page_num in range(start_page, end_page):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    if page_text and page_text.strip():
                        text_parts.append(f"\n--- PAGE {page_num + 1} ---\n")
                        text_parts.append(page_text)
                    
                    self.stats['pages_processed'] += 1
                    
                    # Log de progression
                    if (page_num + 1) % 50 == 0:
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
            start_page = max(0, page_range[0] - 1)  # Conversion 1-based vers 0-based
            end_page = min(total_pages, page_range[1])
        else:
            start_page = 0
            end_page = min(total_pages, max_pages) if max_pages else total_pages
        
        return start_page, end_page
    
    def read_pdf_in_chunks(self, pdf_path: str, 
                          chunk_size: int = 50) -> Generator[str, None, None]:
        """
        Lit un PDF par chunks pour les très gros documents
        Générateur qui yield des portions de texte
        """
        if not HAS_PYMUPDF:
            raise ImportError("PyMuPDF requis pour la lecture par chunks")
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        self.logger.info(f"Lecture par chunks de {chunk_size} pages: {total_pages} pages total")
        
        for start_page in range(0, total_pages, chunk_size):
            end_page = min(start_page + chunk_size, total_pages)
            
            chunk_text = []
            for page_num in range(start_page, end_page):
                try:
                    page = doc[page_num]
                    page_text = page.get_text()
                    
                    if page_text.strip():
                        chunk_text.append(f"\n--- PAGE {page_num + 1} ---\n")
                        chunk_text.append(page_text)
                    
                    self.stats['pages_processed'] += 1
                    
                except Exception as e:
                    self.logger.warning(f"Erreur page {page_num + 1}: {e}")
                    continue
            
            if chunk_text:
                chunk_content = '\n'.join(chunk_text)
                self.logger.info(f"Chunk {start_page + 1}-{end_page}: {len(chunk_content)} caractères")
                yield chunk_content
        
        doc.close()
    
    def get_pdf_info(self, pdf_path: str) -> Dict:
        """Obtient les informations sur un PDF"""
        if not HAS_PYMUPDF:
            return {"error": "PyMuPDF requis pour les infos PDF"}
        
        doc = fitz.open(pdf_path)
        
        info = {
            "pages": len(doc),
            "metadata": doc.metadata,
            "file_size": Path(pdf_path).stat().st_size,
            "estimated_processing_time": len(doc) * 0.1  # ~0.1s par page
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

# Fonction utilitaire pour installer les dépendances
def install_pdf_dependencies():
    """Instructions pour installer les dépendances PDF"""
    print("📚 INSTALLATION DES DÉPENDANCES PDF")
    print("=" * 50)
    print("Pour lire des fichiers PDF, installez une de ces bibliothèques:")
    print()
    print("🥇 RECOMMANDÉ (le plus rapide):")
    print("   pip install PyMuPDF")
    print()
    print("🥈 ALTERNATIVE (bonne qualité):")
    print("   pip install pdfplumber")
    print()
    print("🥉 BASIQUE:")
    print("   pip install PyPDF2")
    print()
    print("💡 Pour 600 pages, PyMuPDF est fortement recommandé!")

if __name__ == "__main__":
    # Test du module
    reader = PDFReader()
    
    if not reader.can_read_pdf():
        install_pdf_dependencies()
    else:
        print(f"✅ Bibliothèques PDF disponibles: {reader.get_available_libraries()}")