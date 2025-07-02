import fitz
import re
import sys
import logging
import time
import gc
import threading
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from functools import lru_cache, wraps
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from csv_exporter import exporter_vers_csv
    CSV_EXPORT_AVAILABLE = True
except ImportError:
    CSV_EXPORT_AVAILABLE = False

try:
    from parsers.base.text_parser import TextParser
    TEXT_PARSER_AVAILABLE = True
except ImportError:
    TEXT_PARSER_AVAILABLE = False

try:
    from parsers.specialized.strict_parser import UltraStrictGenealogyParser
    ULTRA_STRICT_PARSER_AVAILABLE = True
except ImportError:
    ULTRA_STRICT_PARSER_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@dataclass
class PageAnalysis:
    page_number: int
    text_content: str
    person_count: int
    relationship_count: int
    date_count: int
    quality_score: float
    language: str
    preview: str
    parish_indicators_found: int
    word_count: int
    confidence_metrics: Dict[str, float] = field(default_factory=dict)
    extracted_entities: Dict[str, List[str]] = field(default_factory=dict)

@dataclass
class ProcessingResult:
    success: bool
    pages_analyzed: int
    pages_registers: int
    genealogical_results: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    performance_metrics: Dict[str, float]
    error_message: Optional[str] = None

class OptimizedPerformanceLogger:
    def __init__(self):
        self.timers = {}
        self.results = {}
        self.logger = logging.getLogger(f"{__name__}.performance")
    
    def start_timer(self, name: str):
        self.timers[name] = time.time()
    
    def end_timer(self, name: str) -> float:
        if name in self.timers:
            duration = time.time() - self.timers[name]
            self.results[name] = duration
            return duration
        return 0.0
    
    def get_total_time(self, name: str) -> float:
        return self.results.get(name, 0.0)
    
    def get_all_results(self) -> Dict[str, float]:
        return self.results.copy()

class VectorizedProgressTracker:
    def __init__(self, show_progress: bool = True):
        self.show_progress = show_progress
        self.total_items = 0
        self.processed_items = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def initialize(self, total: int):
        with self.lock:
            self.total_items = total
            self.processed_items = 0
            self.start_time = time.time()
    
    def update(self, increment: int = 1):
        if not self.show_progress:
            return
        
        with self.lock:
            self.processed_items += increment
            if self.total_items > 0:
                progress = (self.processed_items / self.total_items) * 100
                elapsed = time.time() - self.start_time
                if elapsed > 0:
                    rate = self.processed_items / elapsed
                    if progress > 0:
                        eta = (elapsed / progress) * (100 - progress)
                        if self.processed_items % max(1, self.total_items // 20) == 0:
                            print(f"\rProgress: {progress:.1f}% ({self.processed_items}/{self.total_items}) "
                                f"Rate: {rate:.1f}/s ETA: {eta:.0f}s", end='', flush=True)

class VectorizedPDFManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.document = None
        self.document_path = None
        self.lock = threading.Lock()
        self.page_cache = {}
        self.stats = {
            'pages_cached': 0,
            'cache_hits': 0,
            'total_extractions': 0,
            'document_opens': 0
        }
        self.patterns = self._compile_vectorized_patterns()
    
    def _compile_vectorized_patterns(self) -> Dict[str, re.Pattern]:
        return {
            'parish_indicators': re.compile(
                r'\b(?:baptême|bapt\.|baptisé|baptisée|mariage|marié|mariée|épouse|époux|'
                r'inhumation|inh\.|enterré|enterrée|décédé|décédée|sépulture|'
                r'parrain|marraine|parr\.|marr\.|filleul|filleule|'
                r'fils\s+de|fille\s+de|filz\s+de|'
                r'sieur|sr\.|écuyer|éc\.|seigneur|dame|demoiselle|'
                r'curé|vicaire|prêtre|église|paroisse|chapelle|'
                r'né|née|mort|morte|veuf|veuve|'
                r'registres?\s+paroissiaux?|'
                r'acte\s+de\s+(?:baptême|mariage|décès))\b',
                re.IGNORECASE | re.MULTILINE
            ),
            'names': re.compile(
                r'\b[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+'
                r'(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+)+',
                re.MULTILINE
            ),
            'relationships': re.compile(
                r'\b(?:fils\s+de|fille\s+de|filz\s+de|épouse\s+de|femme\s+de|veuve\s+de|'
                r'parrain\s*[\.:]|marraine\s*[\.:]|et\s+de\s+[A-Z][a-z]+\s+[A-Z][a-z]+|'
                r'père\s+et\s+mère|parents)\b',
                re.IGNORECASE | re.MULTILINE
            ),
            'dates': re.compile(
                r'\b(?:\d{4}|\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|'
                r'septembre|octobre|novembre|décembre|janv|févr|mars|avr|mai|juin|'
                r'juil|août|sept|oct|nov|déc)\.?)\b',
                re.IGNORECASE | re.MULTILINE
            )
        }
    
    def open_document(self, pdf_path: str) -> bool:
        with self.lock:
            try:
                if self.document is not None:
                    self.close_document()
                
                pdf_file = Path(pdf_path)
                if not pdf_file.exists():
                    raise FileNotFoundError(f"PDF file not found: {pdf_path}")
                
                self.document = fitz.open(str(pdf_path))
                if len(self.document) == 0:
                    raise ValueError("Empty PDF")
                
                self.document_path = str(pdf_path)
                self.page_cache.clear()
                self.stats['document_opens'] += 1
                
                self.logger.info(f"PDF opened: {len(self.document)} pages")
                return True
                
            except Exception as e:
                self.logger.error(f"PDF opening error: {e}")
                self.document = None
                self.document_path = None
                return False
    
    def close_document(self):
        with self.lock:
            if self.document is not None:
                try:
                    self.document.close()
                except Exception as e:
                    self.logger.warning(f"Document closing error: {e}")
                finally:
                    self.document = None
                    self.document_path = None
                    self.page_cache.clear()
                    gc.collect()
    
    def is_document_open(self) -> bool:
        try:
            return (self.document is not None and 
                    not self.document.is_closed and 
                    len(self.document) > 0)
        except:
            return False
    
    @lru_cache(maxsize=1000)
    def get_page_text(self, page_number: int) -> str:
        if not self.is_document_open():
            return ""
        
        if page_number in self.page_cache:
            self.stats['cache_hits'] += 1
            return self.page_cache[page_number]
        
        try:
            page_index = page_number - 1
            if 0 <= page_index < len(self.document):
                page = self.document[page_index]
                text = page.get_text()
                text = self._clean_extracted_text(text)
                
                self.page_cache[page_number] = text
                self.stats['pages_cached'] += 1
                self.stats['total_extractions'] += 1
                
                return text
            else:
                return ""
                
        except Exception as e:
            self.logger.error(f"Page extraction error {page_number}: {e}")
            return ""
    
    def _clean_extracted_text(self, text: str) -> str:
        if not text:
            return ""
        
        replacements = np.array([
            ['\x00', ''], ['\ufeff', ''], ['\xa0', ' '],
            ['\u2019', "'"], ['\u2018', "'"], ['\u201c', '"'], ['\u201d', '"'],
            ['\u2013', '-'], ['\u2014', '-'], ['\u2026', '...']
        ])
        
        for old, new in replacements:
            text = text.replace(old, new)
        
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    def vectorized_structure_analysis(self, max_pages: Optional[int] = None) -> Dict[str, Any]:
        if not self.is_document_open():
            return {}
        
        start_time = time.time()
        total_pages = len(self.document)
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        page_numbers = list(range(1, total_pages + 1))
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_page = {
                executor.submit(self._analyze_page_vectorized, page_num): page_num 
                for page_num in page_numbers
            }
            
            page_analyses = []
            for future in as_completed(future_to_page):
                try:
                    analysis = future.result()
                    if analysis:
                        page_analyses.append(analysis)
                except Exception as e:
                    page_num = future_to_page[future]
                    self.logger.warning(f"Page analysis error {page_num}: {e}")
        
        page_analyses.sort(key=lambda x: x.page_number)
        
        analysis_time = time.time() - start_time
        recommendation = self._generate_vectorized_recommendations(page_analyses)
        summary = self._generate_vectorized_summary(page_analyses)
        
        return {
            'total_pages_analyzed': len(page_analyses),
            'page_analyses': page_analyses,
            'recommendation': recommendation,
            'summary': summary,
            'analysis_time': analysis_time
        }
    
    def _analyze_page_vectorized(self, page_number: int) -> Optional[PageAnalysis]:
        text_content = self.get_page_text(page_number)
        
        if not text_content:
            return None
        
        parish_matches = self.patterns['parish_indicators'].findall(text_content)
        parish_count = len(parish_matches)
        
        name_matches = set(self.patterns['names'].findall(text_content))
        person_count = len(name_matches)
        
        relationship_matches = self.patterns['relationships'].findall(text_content)
        relationship_count = len(relationship_matches)
        
        date_matches = self.patterns['dates'].findall(text_content)
        date_count = len(date_matches)
        
        french_indicators = ['de', 'le', 'la', 'du', 'des', 'et', 'dans', 'avec']
        french_score = sum(1 for word in french_indicators if word in text_content.lower())
        language = "français" if french_score >= 3 else "other"
        
        word_count = len(text_content.split())
        
        quality_score = (
            parish_count * 3.0 +
            relationship_count * 2.5 +
            date_count * 1.5 +
            person_count * 0.8 +
            (2.0 if language == "français" else 0.5)
        )
        
        if word_count > 50:
            quality_score += 0.5
        if parish_count == 0 and relationship_count == 0:
            quality_score -= 2.0
        
        quality_score = max(0.0, quality_score)
        
        preview_lines = text_content.split('\n')[:3]
        preview = ' '.join(preview_lines).replace('\r', ' ')
        preview = re.sub(r'\s+', ' ', preview)[:150]
        
        return PageAnalysis(
            page_number=page_number,
            text_content=text_content,
            person_count=person_count,
            relationship_count=relationship_count,
            date_count=date_count,
            quality_score=quality_score,
            language=language,
            preview=preview,
            parish_indicators_found=parish_count,
            word_count=word_count
        )
    
    def _generate_vectorized_recommendations(self, page_analyses: List[PageAnalysis]) -> Dict:
        if not page_analyses:
            return {'suggested_pages': [], 'confidence': 0.0}
        
        pages_with_content = [p for p in page_analyses if p.word_count > 10]
        if not pages_with_content:
            return {'suggested_pages': [], 'confidence': 0.0}
        
        scores = np.array([p.quality_score for p in pages_with_content])
        score_max = np.max(scores)
        score_mean = np.mean(scores)
        
        if score_max > 10:
            threshold = max(4.0, score_mean * 0.6)
        elif score_max > 5:
            threshold = max(2.5, score_mean * 0.5)
        else:
            threshold = max(1.0, score_mean * 0.3)
        
        recommended_pages = [
            p for p in pages_with_content 
            if (p.quality_score >= threshold and 
                p.parish_indicators_found > 0 and
                p.language in ['français', 'latin'])
        ]
        
        if len(recommended_pages) < 3:
            recommended_pages = [
                p for p in pages_with_content 
                if p.quality_score >= threshold * 0.7 and p.word_count > 20
            ]
        
        confidence = 0.0
        if recommended_pages:
            confidence = min(100.0, 
                          (len(recommended_pages) / len(pages_with_content)) * 100 * 
                          (np.sum([p.quality_score for p in recommended_pages[:5]]) / 
                           (5 * max(1, score_max))))
        
        return {
            'suggested_pages': [p.page_number for p in recommended_pages],
            'confidence': round(confidence, 1),
            'threshold_used': round(threshold, 1),
            'details': [
                {
                    'page': p.page_number,
                    'score': round(p.quality_score, 1),
                    'relations': p.relationship_count,
                    'persons': p.person_count,
                    'dates': p.date_count
                }
                for p in recommended_pages[:10]
            ]
        }
    
    def _generate_vectorized_summary(self, page_analyses: List[PageAnalysis]) -> Dict:
        if not page_analyses:
            return {}
        
        total_pages = len(page_analyses)
        french_pages = len([p for p in page_analyses if p.language == "français"])
        scores = np.array([p.quality_score for p in page_analyses])
        
        return {
            'total_pages': total_pages,
            'french_pages': french_pages,
            'french_percentage': round((french_pages / total_pages) * 100, 1),
            'average_score': round(np.mean(scores), 2),
            'promising_pages': len([p for p in page_analyses if p.quality_score > 5.0])
        }
    
    def extract_selected_pages_vectorized(self, page_numbers: List[int]) -> str:
        if not self.is_document_open() or not page_numbers:
            return ""
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_page = {
                executor.submit(self.get_page_text, page_num): page_num 
                for page_num in page_numbers
            }
            
            page_texts = {}
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    text = future.result()
                    if text.strip():
                        page_texts[page_num] = text
                except Exception as e:
                    self.logger.error(f"Page extraction error {page_num}: {e}")
        
        combined_text = []
        extracted_count = 0
        
        for page_num in sorted(page_numbers):
            if page_num in page_texts:
                delimiter = f"\n{'='*20} PAGE {page_num} {'='*20}\n"
                combined_text.extend([delimiter, page_texts[page_num], "\n"])
                extracted_count += 1
        
        final_text = "\n".join(combined_text)
        self.logger.info(f"Vectorized extraction: {extracted_count}/{len(page_numbers)} pages")
        
        return final_text
    
    def get_statistics(self) -> Dict:
        stats = self.stats.copy()
        stats['document_open'] = self.is_document_open()
        stats['cached_pages'] = len(self.page_cache)
        
        if stats['total_extractions'] > 0:
            stats['cache_hit_rate'] = round(
                (stats['cache_hits'] / stats['total_extractions']) * 100, 1
            )
        else:
            stats['cache_hit_rate'] = 0.0
        
        return stats
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_document()

class OptimizedSmartPDFAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.performance_logger = OptimizedPerformanceLogger()
        
        if TEXT_PARSER_AVAILABLE:
            self.text_parser = TextParser()
            self.logger.info("TextParser loaded")
        else:
            self.text_parser = None
            self.logger.warning("TextParser not available")
        
        if ULTRA_STRICT_PARSER_AVAILABLE:
            self.genealogy_parser = UltraStrictGenealogyParser(self.text_parser)
            self.logger.info("UltraStrictGenealogyParser loaded")
        else:
            self.genealogy_parser = None
            self.logger.warning("UltraStrictGenealogyParser not available")
        
        self.global_stats = {
            'documents_processed': 0,
            'total_pages_analyzed': 0,
            'total_relations_found': 0,
            'processing_time_total': 0.0
        }
        
        self.logger.info("OptimizedSmartPDFAnalyzer initialized")
    
    def analyze_and_process_pdf(self, pdf_file: str, max_pages: Optional[int] = None) -> Optional[ProcessingResult]:
        pdf_path = Path(pdf_file)
        
        if not pdf_path.exists():
            self.logger.error(f"PDF file not found: {pdf_file}")
            return None
        
        self.logger.info(f"Starting PDF analysis: {pdf_path.name}")
        self.logger.info(f"Size: {pdf_path.stat().st_size / 1024 / 1024:.1f} MB")
        self.logger.info(f"Page limit: {max_pages or 'All'}")
        
        self.performance_logger.start_timer("total_processing")
        
        try:
            with VectorizedPDFManager() as pdf_manager:
                self.performance_logger.start_timer("document_opening")
                
                if not pdf_manager.open_document(str(pdf_path)):
                    self.logger.error("Cannot open PDF")
                    return None
                
                self.performance_logger.end_timer("document_opening")
                
                self.performance_logger.start_timer("structure_analysis")
                
                analysis = pdf_manager.vectorized_structure_analysis(max_pages)
                
                if not analysis.get('page_analyses'):
                    self.logger.error("No analyzable pages found")
                    return None
                
                self.performance_logger.end_timer("structure_analysis")
                
                recommendation = analysis['recommendation']
                summary = analysis['summary']
                
                self.logger.info(f"Analysis completed in {analysis['analysis_time']:.1f}s")
                self.logger.info(f"Pages analyzed: {analysis['total_pages_analyzed']}")
                self.logger.info(f"Recommended pages: {len(recommendation['suggested_pages'])}")
                self.logger.info(f"Confidence: {recommendation['confidence']:.1f}%")
                
                pages_to_process = recommendation['suggested_pages']
                
                if not pages_to_process:
                    self.logger.warning("No register pages detected")
                    return self._create_empty_result(analysis)
                
                self.performance_logger.start_timer("text_extraction")
                
                register_text = pdf_manager.extract_selected_pages_vectorized(pages_to_process)
                
                if not register_text:
                    self.logger.error("Text extraction failed")
                    return None
                
                self.performance_logger.end_timer("text_extraction")
                
                self.performance_logger.start_timer("genealogical_processing")
                
                try:
                    genealogical_result = self._process_genealogical_content_vectorized(register_text)
                    
                    self.performance_logger.end_timer("genealogical_processing")
                    
                    self._update_global_stats(analysis, genealogical_result)
                    
                    return self._build_final_result(
                        analysis, recommendation, genealogical_result, pages_to_process
                    )
                    
                except Exception as e:
                    self.logger.error(f"Genealogical processing error: {e}")
                    return self._create_partial_result(analysis, pages_to_process, str(e))
        
        except Exception as e:
            self.logger.error(f"Critical analysis error: {e}")
            return None
        
        finally:
            total_time = self.performance_logger.end_timer("total_processing")
            self.logger.info(f"Processing completed in {total_time:.2f}s")
    
    def _process_genealogical_content_vectorized(self, text: str) -> Dict:
        self.logger.info(f"Processing genealogical content: {len(text):,} characters")
        
        if self.text_parser:
            self.performance_logger.start_timer("text_normalization")
            normalization_result = self.text_parser.normalize_text(text)
            normalized_text = normalization_result['normalized']
            self.performance_logger.end_timer("text_normalization")
        else:
            normalized_text = text
            normalization_result = {'normalized': text, 'ocr_corrections': [], 'abbreviations_expanded': []}
        
        if self.genealogy_parser:
            self.performance_logger.start_timer("relation_extraction")
            
            if hasattr(self.genealogy_parser, 'extract_filiations_ultra_strict'):
                relations = self.genealogy_parser.extract_filiations_ultra_strict(normalized_text)
                filiations_data = self.genealogy_parser.export_to_legacy_format(relations)
                mariages_data = []
                parrainages_data = []
            else:
                document = self.genealogy_parser.process_document(normalized_text)
                filiations_data = [
                    {
                        'enfant': rel.entities.get('enfant', ''),
                        'pere': rel.entities.get('pere', ''),
                        'mere': rel.entities.get('mere', ''),
                        'source_text': rel.source_text,
                        'position': rel.position,
                        'confiance': rel.confidence
                    }
                    for rel in document.filiations
                ]
                mariages_data = [
                    {
                        'epouse': rel.entities.get('epouse', ''),
                        'epoux': rel.entities.get('epoux', ''),
                        'statut': rel.entities.get('statut', 'mariée'),
                        'source_text': rel.source_text,
                        'position': rel.position,
                        'confiance': rel.confidence
                    }
                    for rel in document.mariages
                ]
                parrainages_data = [
                    {
                        'type': rel.entities.get('role', ''),
                        'personne': rel.entities.get('personne', ''),
                        'source_text': rel.source_text,
                        'position': rel.position,
                        'confiance': rel.confidence
                    }
                    for rel in document.parrainages
                ]
            
            self.performance_logger.end_timer("relation_extraction")
        else:
            filiations_data = []
            mariages_data = []
            parrainages_data = []
        
        self.performance_logger.start_timer("person_extraction")
        
        if self.text_parser:
            persons_data = self.text_parser.extract_names_with_validation(normalized_text)
        else:
            persons_data = self._extract_persons_basic(normalized_text)
        
        self.performance_logger.end_timer("person_extraction")
        
        total_relations = len(filiations_data) + len(mariages_data) + len(parrainages_data)
        
        self.logger.info(f"Relations extracted: {total_relations} total")
        self.logger.info(f"  Filiations: {len(filiations_data)}")
        self.logger.info(f"  Marriages: {len(mariages_data)}")
        self.logger.info(f"  Godparents: {len(parrainages_data)}")
        self.logger.info(f"  Persons: {len(persons_data)}")
        
        validation_results = self._validate_data_vectorized(
            filiations_data, mariages_data, parrainages_data, persons_data
        )
        
        return {
            'relations_count': total_relations,
            'filiations': filiations_data,
            'mariages': mariages_data,
            'parrainages': parrainages_data,
            'personnes_extraites': persons_data,
            'validation': validation_results,
            'normalization': normalization_result,
            'processing_time': self.performance_logger.get_total_time("relation_extraction")
        }
    
    def _extract_persons_basic(self, text: str) -> List[Dict]:
        name_pattern = r'\b[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+'
        name_pattern += r'(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+)+'
        
        matches = re.findall(name_pattern, text)
        
        unique_persons = {}
        for match in matches:
            clean_name = re.sub(r'\s+', ' ', match.strip())
            if len(clean_name) > 3 and clean_name not in unique_persons:
                words = clean_name.split()
                unique_persons[clean_name] = {
                    'nom_complet': clean_name,
                    'prenoms': words[:-1] if len(words) > 1 else [words[0]] if words else [],
                    'nom_famille': words[-1] if words else '',
                    'occurrences': text.count(clean_name),
                    'confiance': 0.7 if len(words) >= 2 else 0.5
                }
        
        return list(unique_persons.values())
    
    def _validate_data_vectorized(self, filiations: List[Dict], mariages: List[Dict], 
                                 parrainages: List[Dict], persons: List[Dict]) -> Dict:
        total_relations = len(filiations) + len(mariages) + len(parrainages)
        
        if total_relations == 0 or len(persons) == 0:
            return {
                'validation_rate': 0.0,
                'data_quality': 'Faible',
                'total_persons': len(persons),
                'total_relations': total_relations,
                'coherence_score': 0.0,
                'confidence_moyenne': 0.0
            }
        
        persons_in_relations = set()
        confidences = []
        
        for rel in filiations:
            if rel.get('enfant'):
                persons_in_relations.add(rel['enfant'].lower())
            if rel.get('pere'):
                persons_in_relations.add(rel['pere'].lower())
            if rel.get('mere'):
                persons_in_relations.add(rel['mere'].lower())
            confidences.append(float(rel.get('confiance', 0.5)))
        
        for rel in mariages:
            if rel.get('epouse'):
                persons_in_relations.add(rel['epouse'].lower())
            if rel.get('epoux'):
                persons_in_relations.add(rel['epoux'].lower())
            confidences.append(float(rel.get('confiance', 0.6)))
        
        for rel in parrainages:
            if rel.get('personne'):
                persons_in_relations.add(rel['personne'].lower())
            confidences.append(float(rel.get('confiance', 0.4)))
        
        extracted_persons = {p['nom_complet'].lower() for p in persons}
        
        if extracted_persons:
            validation_rate = len(persons_in_relations.intersection(extracted_persons)) / len(extracted_persons) * 100
        else:
            validation_rate = 0.0
        
        confidence_moyenne = np.mean(confidences) if confidences else 0.0
        
        if validation_rate > 80:
            quality = "Excellente"
        elif validation_rate > 60:
            quality = "Bonne"
        elif validation_rate > 40:
            quality = "Moyenne"
        else:
            quality = "Faible"
        
        return {
            'validation_rate': round(validation_rate, 1),
            'data_quality': quality,
            'total_persons': len(persons),
            'total_relations': total_relations,
            'coherence_score': round(validation_rate / 100, 2),
            'confidence_moyenne': round(confidence_moyenne, 3)
        }
    
    def _update_global_stats(self, analysis: Dict, genealogical_result: Dict):
        self.global_stats['documents_processed'] += 1
        self.global_stats['total_pages_analyzed'] += analysis.get('total_pages_analyzed', 0)
        self.global_stats['total_relations_found'] += genealogical_result.get('relations_count', 0)
        self.global_stats['processing_time_total'] += self.performance_logger.get_total_time("total_processing")
    
    def _build_final_result(self, analysis: Dict, recommendation: Dict, 
                           genealogical_result: Dict, pages_to_process: List[int]) -> ProcessingResult:
        total_relations = genealogical_result.get('relations_count', 0)
        validation = genealogical_result.get('validation', {})
        
        return ProcessingResult(
            success=True,
            pages_analyzed=analysis['total_pages_analyzed'],
            pages_registers=len(pages_to_process),
            genealogical_results={
                'filiations': genealogical_result.get('filiations', []),
                'mariages': genealogical_result.get('mariages', []),
                'parrainages': genealogical_result.get('parrainages', []),
                'personnes_extraites': genealogical_result.get('personnes_extraites', []),
                'relations_count': total_relations
            },
            quality_metrics={
                'qualite_donnees': validation.get('data_quality', 'Non évaluée'),
                'taux_validation': validation.get('validation_rate', 0),
                'confidence_moyenne': validation.get('confidence_moyenne', 0)
            },
            performance_metrics=self.performance_logger.get_all_results()
        )
    
    def _create_empty_result(self, analysis: Dict) -> ProcessingResult:
        return ProcessingResult(
            success=False,
            pages_analyzed=analysis['total_pages_analyzed'],
            pages_registers=0,
            genealogical_results={'relations_count': 0},
            quality_metrics={'qualite_donnees': 'Aucune', 'taux_validation': 0},
            performance_metrics=self.performance_logger.get_all_results(),
            error_message='No register pages detected'
        )
    
    def _create_partial_result(self, analysis: Dict, pages: List[int], error: str) -> ProcessingResult:
        return ProcessingResult(
            success=False,
            pages_analyzed=analysis['total_pages_analyzed'],
            pages_registers=len(pages),
            genealogical_results={'relations_count': 0},
            quality_metrics={'qualite_donnees': 'Erreur', 'taux_validation': 0},
            performance_metrics=self.performance_logger.get_all_results(),
            error_message=error
        )
    
    def get_global_statistics(self) -> Dict:
        stats = self.global_stats.copy()
        
        if stats['documents_processed'] > 0:
            stats['average_pages_per_document'] = round(
                stats['total_pages_analyzed'] / stats['documents_processed'], 1
            )
            stats['average_relations_per_document'] = round(
                stats['total_relations_found'] / stats['documents_processed'], 1
            )
            stats['average_processing_time'] = round(
                stats['processing_time_total'] / stats['documents_processed'], 2
            )
        
        return stats

def analyze_and_process_pdf_optimized(pdf_file: str, max_pages: Optional[int] = None) -> Optional[Dict]:
    analyzer = OptimizedSmartPDFAnalyzer()
    result = analyzer.analyze_and_process_pdf(pdf_file, max_pages)
    
    if result is None:
        return None
    
    return {
        'success': result.success,
        'pages_analysees': result.pages_analyzed,
        'pages_registres': result.pages_registers,
        'resultats_genealogiques': result.genealogical_results,
        'qualite_extraction': result.quality_metrics,
        'performance': result.performance_metrics,
        'error': result.error_message
    }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Smart PDF Analyzer - Ultra-Optimized Version"
    )
    parser.add_argument(
        'pdf_file', 
        nargs='?',
        default=r'C:\Users\Louis\Documents\CodexGenea\inventairesommai03archuoft.pdf',
        help='PDF file to analyze'
    )
    parser.add_argument(
        '--max-pages', 
        type=int, 
        help='Maximum number of pages to analyze'
    )
    parser.add_argument(
        '--output', 
        help='Output file for results (JSON)'
    )
    parser.add_argument(
        '--csv-dir',
        default='RESULT',
        help='Directory for CSV exports (default: RESULT)'
    )
    parser.add_argument(
        '--no-csv',
        action='store_true',
        help='Disable automatic CSV export'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true', 
        help='Verbose mode'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not Path(args.pdf_file).exists():
        print(f"Error: File '{args.pdf_file}' not found")
        sys.exit(1)
    
    print("Smart PDF Analyzer - Ultra-Optimized Version 4.0")
    print("=" * 50)
    print(f"File: {Path(args.pdf_file).name}")
    print(f"Page limit: {args.max_pages or 'All'}")
    if not args.no_csv and CSV_EXPORT_AVAILABLE:
        print(f"CSV export: {args.csv_dir}")
    print()
    
    try:
        result = analyze_and_process_pdf_optimized(args.pdf_file, args.max_pages)
        
        if result:
            print("PROCESSING COMPLETED SUCCESSFULLY")
            print("=" * 50)
            
            if result.get('success', True):
                print(f"Register pages found: {result['pages_registres']}")
                
                genealogical = result.get('resultats_genealogiques', {})
                print(f"Persons extracted: {len(genealogical.get('personnes_extraites', []))}")
                print(f"Family relations: {genealogical.get('relations_count', 0)}")
                print(f"  - Filiations: {len(genealogical.get('filiations', []))}")
                print(f"  - Marriages: {len(genealogical.get('mariages', []))}")
                print(f"  - Godparents: {len(genealogical.get('parrainages', []))}")
                
                quality = result.get('qualite_extraction', {})
                print(f"Data quality: {quality.get('qualite_donnees', 'Not evaluated')}")
                print(f"Validation rate: {quality.get('taux_validation', 0):.1f}%")
                
                performance = result.get('performance', {})
                if 'total_processing' in performance:
                    print(f"Total time: {performance['total_processing']:.2f}s")
                
                if not args.no_csv and CSV_EXPORT_AVAILABLE:
                    print(f"\nAutomatic CSV export to {args.csv_dir}")
                    print("-" * 30)
                    try:
                        csv_files = exporter_vers_csv(result, args.csv_dir)
                        print(f"CSV files created:")
                        for file_type, path in csv_files.items():
                            filename = Path(path).name
                            print(f"  - {file_type}: {filename}")
                        
                        print(f"\nAll files are in: {Path(args.csv_dir).absolute()}")
                        
                    except Exception as e:
                        print(f"CSV export error: {e}")
                        if args.verbose:
                            import traceback
                            traceback.print_exc()
            else:
                print(f"PARTIAL PROCESSING: {result.get('error', 'Unknown error')}")
            
            if args.output:
                try:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"JSON results saved: {args.output}")
                except Exception as e:
                    print(f"JSON save error: {e}")
        
        else:
            print("PROCESSING FAILED")
            print("Check logs for details")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()