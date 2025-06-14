# smart_pdf_analyzer.py
"""
Analyseur PDF intelligent pour registres paroissiaux - Version Corrigée
Version 3.0.1 - Code restructuré et optimisé

Corrections apportées:
- Structure du code réorganisée
- Élimination des redéfinitions de fonctions
- Gestion d'erreurs améliorée
- Imports conditionnels optimisés
- Performance et cache améliorés
- Interface utilisateur clarifiée

Auteur: Smart PDF Analyzer Team
Date: 2025-06-14
"""

import fitz
import re
import sys
import logging
import time
import gc
import threading
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import numpy as np
from functools import lru_cache, wraps

# Import conditionnel pour l'export CSV
try:
    from csv_exporter import exporter_vers_csv
    CSV_EXPORT_AVAILABLE = True
except ImportError:
    CSV_EXPORT_AVAILABLE = False

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@dataclass
class PageAnalysis:
    """Analyse détaillée d'une page de PDF"""
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
class RelationshipMatch:
    """Relation familiale extraite avec métadonnées"""
    type: str
    persons: Dict[str, str]
    confidence: float
    source_span: Tuple[int, int]
    context: str
    page_number: Optional[int] = None

class PerformanceLogger:
    """Logger de performance pour mesurer les temps d'exécution"""
    
    def __init__(self):
        self.timers = {}
        self.results = {}
        self.logger = logging.getLogger(f"{__name__}.performance")
    
    def start_timer(self, name: str):
        """Démarre un timer"""
        self.timers[name] = time.time()
    
    def end_timer(self, name: str) -> float:
        """Termine un timer et retourne la durée"""
        if name in self.timers:
            duration = time.time() - self.timers[name]
            self.results[name] = duration
            self.logger.debug(f"Timer {name}: {duration:.2f}s")
            return duration
        return 0.0
    
    def get_total_time(self, name: str) -> float:
        """Retourne le temps total pour un timer"""
        return self.results.get(name, 0.0)
    
    def get_all_results(self) -> Dict[str, float]:
        """Retourne tous les résultats de timing"""
        return self.results.copy()

class RobustRelationshipParser:
    """Parser de relations robuste et tolérant aux erreurs OCR"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_patterns()
        self._cache = {}
        self.stats = {
            'total_processed': 0,
            'relations_found': 0,
            'pattern_successes': defaultdict(int)
        }
    
    def _setup_patterns(self):
        """Configure les patterns progressifs pour l'extraction"""
        
        # Nom très permissif pour OCR dégradé
        nom = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-\s\.]{1,50}'
        
        # Variations OCR courantes
        fils_vars = r'(?:fils|filz|fls|f1ls|flls)'
        fille_vars = r'(?:fille|filles|flle|f1lle)'
        de_vars = r'(?:de|du|des|dé|dc|do|da)'
        epouse_vars = r'(?:épouse|espouse|cpouse|femme|fame|fcmme)'
        
        self.patterns = {
            # Filiations de base
            'filiation_fils': re.compile(
                rf'({nom})\s*[,\.]*\s*{fils_vars}\s+{de_vars}\s+({nom})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            'filiation_fille': re.compile(
                rf'({nom})\s*[,\.]*\s*{fille_vars}\s+{de_vars}\s+({nom})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            'filiation_avec_mere': re.compile(
                rf'({nom})\s*[,\.]*\s*(?:{fils_vars}|{fille_vars})\s+{de_vars}\s+({nom})\s+et\s+(?:{de_vars}\s+)?({nom})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # Mariages
            'mariage_epouse': re.compile(
                rf'({nom})\s*[,\.]*\s*{epouse_vars}\s+{de_vars}\s+({nom})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            'veuvage': re.compile(
                rf'({nom})\s*[,\.]*\s*veuve?\s+{de_vars}\s+({nom})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # Parrainages
            'parrain': re.compile(
                rf'(?:parr?(?:ain)?[\.:\s]*|parr?[\.:])\s*({nom})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            'marraine': re.compile(
                rf'(?:marr?(?:aine)?[\.:\s]*|marr?[\.:])\s*({nom})',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # Patterns contextuels
            'bapteme_context': re.compile(
                rf'(?:bapt[êe]?me?|bapt\.?|baptisé[e]?)\s+.*?({nom}).*?'
                rf'(?:parr?[\.:]?\s*({nom}))?.*?'
                rf'(?:marr?[\.:]?\s*({nom}))?',
                re.IGNORECASE | re.MULTILINE | re.DOTALL
            )
        }
    
    @lru_cache(maxsize=1000)
    def extract_relationships(self, text: str) -> List[Dict]:
        """Extraction principale des relations avec cache"""
        if not text or len(text.strip()) < 10:
            return []
        
        # Normalisation du texte
        normalized_text = self._normalize_text(text)
        
        relationships = []
        used_positions = set()
        
        for pattern_name, pattern in self.patterns.items():
            matches = self._get_non_overlapping_matches(pattern, normalized_text, used_positions)
            
            for match in matches:
                relation = self._parse_relationship_match(pattern_name, match, normalized_text)
                if relation:
                    relationships.append(relation)
                    used_positions.update(range(match.start(), match.end()))
                    self.stats['pattern_successes'][pattern_name] += 1
        
        self.stats['total_processed'] += 1
        self.stats['relations_found'] += len(relationships)
        
        return self._validate_and_clean_relationships(relationships)
    
    def _normalize_text(self, text: str) -> str:
        """Normalise le texte pour améliorer l'extraction"""
        if not text:
            return ""
        
        # Corrections OCR communes
        corrections = {
            r'\bf1ls\b': 'fils',
            r'\bf1lle\b': 'fille',
            r'\bflls\b': 'fils',
            r'\bdc\b': 'de',
            r'\bdo\b': 'de',
            r'\bcpouse\b': 'épouse',
            r'\bfcmme\b': 'femme'
        }
        
        normalized = text
        for error, correction in corrections.items():
            normalized = re.sub(error, correction, normalized, flags=re.IGNORECASE)
        
        # Normaliser les espaces
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[\.;:]+', ',', normalized)
        
        return normalized.strip()
    
    def _get_non_overlapping_matches(self, pattern, text, used_positions):
        """Retourne les matches qui ne chevauchent pas avec les positions utilisées"""
        matches = []
        for match in pattern.finditer(text):
            match_range = set(range(match.start(), match.end()))
            if not match_range.intersection(used_positions):
                matches.append(match)
        return matches
    
    def _parse_relationship_match(self, pattern_name: str, match, text: str) -> Optional[Dict]:
        """Parse un match spécifique selon le pattern"""
        groups = match.groups()
        
        try:
            if 'filiation' in pattern_name:
                enfant = self._clean_name(groups[0])
                pere = self._clean_name(groups[1]) if len(groups) > 1 else None
                mere = self._clean_name(groups[2]) if len(groups) > 2 else None
                
                if enfant and pere:
                    return {
                        'type': 'filiation',
                        'enfant': enfant,
                        'pere': pere,
                        'mere': mere,
                        'position': match.span(),
                        'source_text': match.group(0)[:100]
                    }
            
            elif 'mariage' in pattern_name or 'veuvage' in pattern_name:
                epouse = self._clean_name(groups[0])
                epoux = self._clean_name(groups[1])
                
                if epouse and epoux:
                    return {
                        'type': 'mariage',
                        'epouse': epouse,
                        'epoux': epoux,
                        'statut': 'veuve' if 'veuvage' in pattern_name else 'mariée',
                        'position': match.span(),
                        'source_text': match.group(0)[:100]
                    }
            
            elif 'parrain' in pattern_name or 'marraine' in pattern_name:
                personne = self._clean_name(groups[0])
                if personne:
                    return {
                        'type': 'marraine' if 'marraine' in pattern_name else 'parrain',
                        'personne': personne,
                        'position': match.span(),
                        'source_text': match.group(0)[:50]
                    }
                    
        except Exception as e:
            self.logger.debug(f"Erreur parsing relation {pattern_name}: {e}")
        
        return None
    
    @lru_cache(maxsize=500)
    def _clean_name(self, name: str) -> Optional[str]:
        """Nettoie un nom extrait"""
        if not name:
            return None
        
        # Supprimer ponctuation et normaliser
        clean = re.sub(r'[,\.;:\-]+', ' ', name)
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        # Validations
        if len(clean) < 2 or len(clean) > 50:
            return None
        
        if not re.search(r'[a-zA-ZàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ]', clean):
            return None
        
        return clean
    
    def _validate_and_clean_relationships(self, relationships: List[Dict]) -> List[Dict]:
        """Valide et nettoie les relations"""
        valid_relations = []
        
        for rel in relationships:
            # Éviter les relations où les noms sont identiques
            if rel['type'] == 'filiation':
                if rel.get('enfant') and rel.get('pere'):
                    if rel['enfant'].lower() != rel['pere'].lower():
                        valid_relations.append(rel)
            elif rel['type'] == 'mariage':
                if rel.get('epouse') and rel.get('epoux'):
                    if rel['epouse'].lower() != rel['epoux'].lower():
                        valid_relations.append(rel)
            else:
                valid_relations.append(rel)
        
        return valid_relations

class PDFManagerUnifie:
    """Gestionnaire PDF unifié qui évite les ouvertures/fermetures multiples"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.document = None
        self.document_path = None
        self.lock = threading.Lock()
        self._page_cache = {}
        self.stats = {
            'pages_cached': 0,
            'cache_hits': 0,
            'total_extractions': 0,
            'document_opens': 0
        }
        self._setup_patterns()
    
    def _setup_patterns(self):
        """Configure les patterns d'analyse pour registres paroissiaux"""
        self.parish_indicators = [
            r'baptême|bapt\.|baptisé|baptisée|baptiser',
            r'mariage|marié|mariée|épouse|époux|épouser',
            r'inhumation|inh\.|enterré|enterrée|décédé|décédée|sépulture',
            r'parrain|marraine|parr\.|marr\.|filleul|filleule',
            r'fils\s+de|fille\s+de|filz\s+de',
            r'sieur|sr\.|écuyer|éc\.|seigneur|dame|demoiselle',
            r'curé|vicaire|prêtre|église|paroisse|chapelle',
            r'né|née|mort|morte|veuf|veuve',
            r'registres?\s+paroissiaux?',
            r'acte\s+de\s+(?:baptême|mariage|décès)'
        ]
        
        self.name_patterns = [
            r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ-]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ-]+)+',
            r'[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?'
        ]
        
        self.relationship_patterns = [
            r'fils\s+de|fille\s+de|filz\s+de',
            r'épouse\s+de|femme\s+de|veuve\s+de',
            r'parrain\s*[\.:]|marraine\s*[\.:]',
            r'et\s+de\s+[A-Z][a-z]+\s+[A-Z][a-z]+',
            r'père\s+et\s+mère|parents'
        ]
        
        self.date_patterns = [
            r'\b\d{4}\b',
            r'\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)',
            r'\d{1,2}\s+(?:janv|févr|mars|avr|mai|juin|juil|août|sept|oct|nov|déc)\.?'
        ]
    
    def ouvrir_document(self, pdf_path: str) -> bool:
        """Ouvre le document PDF de manière sécurisée"""
        with self.lock:
            try:
                if self.document is not None:
                    self.fermer_document()
                
                pdf_file = Path(pdf_path)
                if not pdf_file.exists():
                    raise FileNotFoundError(f"Fichier PDF non trouvé: {pdf_path}")
                
                self.logger.info(f"Ouverture PDF: {pdf_file.name}")
                
                self.document = fitz.open(str(pdf_path))
                if len(self.document) == 0:
                    raise ValueError("PDF vide ou sans pages")
                
                self.document_path = str(pdf_path)
                self._page_cache.clear()
                self.stats['document_opens'] += 1
                
                self.logger.info(f"PDF ouvert avec succès: {len(self.document)} pages")
                return True
                
            except Exception as e:
                self.logger.error(f"Erreur ouverture PDF: {e}")
                self.document = None
                self.document_path = None
                return False
    
    def fermer_document(self):
        """Ferme le document de manière sécurisée"""
        with self.lock:
            if self.document is not None:
                try:
                    self.document.close()
                    self.logger.info("Document PDF fermé")
                except Exception as e:
                    self.logger.warning(f"Erreur fermeture document: {e}")
                finally:
                    self.document = None
                    self.document_path = None
                    self._page_cache.clear()
                    gc.collect()
    
    def verifier_document_ouvert(self) -> bool:
        """Vérifie que le document est ouvert et accessible"""
        try:
            return (self.document is not None and 
                    not self.document.is_closed and 
                    len(self.document) > 0)
        except:
            return False
    
    def obtenir_texte_page(self, page_number: int) -> str:
        """Obtient le texte d'une page avec mise en cache"""
        if not self.verifier_document_ouvert():
            return ""
        
        if page_number in self._page_cache:
            self.stats['cache_hits'] += 1
            return self._page_cache[page_number]
        
        try:
            page_index = page_number - 1
            if 0 <= page_index < len(self.document):
                page = self.document[page_index]
                text = page.get_text()
                text = self._nettoyer_texte_extrait(text)
                
                self._page_cache[page_number] = text
                self.stats['pages_cached'] += 1
                self.stats['total_extractions'] += 1
                
                return text
            else:
                self.logger.warning(f"Page {page_number} hors limites")
                return ""
                
        except Exception as e:
            self.logger.error(f"Erreur extraction page {page_number}: {e}")
            return ""
    
    def _nettoyer_texte_extrait(self, texte: str) -> str:
        """Nettoie le texte extrait pour améliorer la qualité"""
        if not texte:
            return ""
        
        # Replacements des caractères problématiques
        replacements = {
            '\x00': '', '\ufeff': '', '\xa0': ' ',
            '\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"',
            '\u2013': '-', '\u2014': '-', '\u2026': '...'
        }
        
        for ancien, nouveau in replacements.items():
            texte = texte.replace(ancien, nouveau)
        
        # Normaliser les espaces
        texte = re.sub(r'\s+', ' ', texte)
        texte = re.sub(r'\n\s*\n', '\n\n', texte)
        
        return texte.strip()
    
    def analyser_structure_complete(self, max_pages: Optional[int] = None) -> Dict[str, Any]:
        """Analyse complète de la structure PDF"""
        if not self.verifier_document_ouvert():
            return {}
        
        start_time = time.time()
        total_pages = len(self.document)
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        self.logger.info(f"Analyse structure PDF: {total_pages} pages")
        
        page_analyses = []
        
        for page_num in range(1, total_pages + 1):
            try:
                text = self.obtenir_texte_page(page_num)
                if text:
                    analysis = self._analyser_contenu_page(page_num, text)
                    page_analyses.append(analysis)
                
                if page_num % 25 == 0 or page_num == total_pages:
                    self.logger.info(f"Analysé {page_num}/{total_pages} pages")
                    
            except Exception as e:
                self.logger.warning(f"Erreur analyse page {page_num}: {e}")
                continue
        
        analysis_time = time.time() - start_time
        recommandation = self._generer_recommandations(page_analyses)
        resume = self._generer_resume(page_analyses)
        
        self.logger.info(f"Analyse terminée en {analysis_time:.2f}s")
        
        return {
            'total_pages_analyzed': len(page_analyses),
            'page_analyses': page_analyses,
            'recommandation': recommandation,
            'summary': resume,
            'analysis_time': analysis_time
        }
    
    def extraire_pages_selectionnees(self, page_numbers: List[int]) -> str:
        """Extrait le texte des pages sélectionnées"""
        if not self.verifier_document_ouvert() or not page_numbers:
            return ""
        
        self.logger.info(f"Extraction de {len(page_numbers)} pages")
        
        combined_text = []
        extracted_count = 0
        
        for page_num in page_numbers:
            try:
                text = self.obtenir_texte_page(page_num)
                if text.strip():
                    delimiter = f"\n{'='*20} PAGE {page_num} {'='*20}\n"
                    combined_text.append(delimiter)
                    combined_text.append(text)
                    combined_text.append("\n")
                    extracted_count += 1
                    
            except Exception as e:
                self.logger.error(f"Erreur extraction page {page_num}: {e}")
                continue
        
        final_text = "\n".join(combined_text)
        self.logger.info(f"Extraction terminée: {extracted_count}/{len(page_numbers)} pages")
        
        return final_text
    
    def _analyser_contenu_page(self, page_number: int, text_content: str) -> PageAnalysis:
        """Analyse détaillée du contenu d'une page"""
        if not text_content:
            return PageAnalysis(
                page_number=page_number, text_content="", person_count=0,
                relationship_count=0, date_count=0, quality_score=0.0,
                language="inconnu", preview="", parish_indicators_found=0, word_count=0
            )
        
        # Compter les indicateurs paroissiaux
        parish_count = 0
        for pattern in self.parish_indicators:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            parish_count += len(matches)
        
        # Compter les noms de personnes avec déduplication
        person_matches = set()
        for pattern in self.name_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                clean_name = re.sub(r'\s+', ' ', match.strip())
                if len(clean_name) > 3:
                    person_matches.add(clean_name.lower())
        person_count = len(person_matches)
        
        # Compter les relations familiales
        relationship_count = 0
        for pattern in self.relationship_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            relationship_count += len(matches)
        
        # Compter les dates
        date_count = 0
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            date_count += len(matches)
        
        # Détecter la langue
        french_words = ['de', 'le', 'la', 'du', 'des', 'et', 'dans', 'avec']
        french_score = sum(1 for word in french_words if word in text_content.lower())
        language = "français" if french_score >= 3 else "autre"
        
        # Calculer le score de qualité
        word_count = len(text_content.split())
        quality_score = (
            parish_count * 3.0 +
            relationship_count * 2.5 +
            date_count * 1.5 +
            person_count * 0.8 +
            (2.0 if language == "français" else 0.5)
        )
        
        # Bonus pour diversité et contenu substantiel
        if word_count > 50:
            quality_score += 0.5
        if parish_count == 0 and relationship_count == 0:
            quality_score -= 2.0
        
        quality_score = max(0.0, quality_score)
        
        # Preview du contenu
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
    
    def _generer_recommandations(self, page_analyses: List[PageAnalysis]) -> Dict:
        """Génère des recommandations basées sur l'analyse"""
        if not page_analyses:
            return {'pages_suggerees': [], 'confiance': 0.0}
        
        pages_avec_contenu = [p for p in page_analyses if p.word_count > 10]
        if not pages_avec_contenu:
            return {'pages_suggerees': [], 'confiance': 0.0}
        
        pages_triees = sorted(pages_avec_contenu, key=lambda p: p.quality_score, reverse=True)
        
        scores = [p.quality_score for p in pages_triees]
        score_max = max(scores)
        score_moyen = sum(scores) / len(scores)
        
        if score_max > 10:
            seuil_qualite = max(4.0, score_moyen * 0.6)
        elif score_max > 5:
            seuil_qualite = max(2.5, score_moyen * 0.5)
        else:
            seuil_qualite = max(1.0, score_moyen * 0.3)
        
        pages_recommendees = [
            p for p in pages_triees 
            if (p.quality_score >= seuil_qualite and 
                p.parish_indicators_found > 0 and
                p.language in ['français', 'latin'])
        ]
        
        if len(pages_recommendees) < 3:
            pages_recommendees = [
                p for p in pages_triees 
                if p.quality_score >= seuil_qualite * 0.7 and p.word_count > 20
            ]
        
        confiance = 0.0
        if pages_recommendees:
            confiance = min(100.0, 
                          (len(pages_recommendees) / len(pages_avec_contenu)) * 100 * 
                          (sum(p.quality_score for p in pages_recommendees[:5]) / 
                           (5 * max(1, score_max))))
        
        details_pages = []
        for page in pages_recommendees[:15]:
            details_pages.append({
                'page': page.page_number,
                'score': round(page.quality_score, 1),
                'relations': page.relationship_count,
                'personnes': page.person_count,
                'dates': page.date_count,
                'langue': page.language,
                'preview': page.preview[:80] + "..." if len(page.preview) > 80 else page.preview
            })
        
        return {
            'pages_suggerees': [p.page_number for p in pages_recommendees],
            'confiance': round(confiance, 1),
            'seuil_utilise': round(seuil_qualite, 1),
            'details_pages': details_pages
        }
    
    def _generer_resume(self, page_analyses: List[PageAnalysis]) -> Dict:
        """Génère un résumé de l'analyse"""
        if not page_analyses:
            return {}
        
        total_pages = len(page_analyses)
        french_pages = len([p for p in page_analyses if p.language == "français"])
        
        return {
            'pages_totales': total_pages,
            'pages_francais': french_pages,
            'pourcentage_francais': round((french_pages / total_pages) * 100, 1),
            'score_moyen': round(sum(p.quality_score for p in page_analyses) / total_pages, 2),
            'pages_prometteuses': len([p for p in page_analyses if p.quality_score > 5.0])
        }
    
    def obtenir_statistiques(self) -> Dict:
        """Retourne les statistiques du gestionnaire"""
        stats = self.stats.copy()
        stats['document_ouvert'] = self.verifier_document_ouvert()
        stats['pages_en_cache'] = len(self._page_cache)
        
        if stats['total_extractions'] > 0:
            stats['taux_cache_hit'] = round(
                (stats['cache_hits'] / stats['total_extractions']) * 100, 1
            )
        else:
            stats['taux_cache_hit'] = 0.0
        
        return stats
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fermer_document()

class SmartPDFAnalyzer:
    """Analyseur PDF intelligent pour registres paroissiaux - Version corrigée"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.performance_logger = PerformanceLogger()
        self.relationship_parser = RobustRelationshipParser()
        
        # Statistiques globales
        self.global_stats = {
            'documents_processed': 0,
            'total_pages_analyzed': 0,
            'total_relations_found': 0,
            'processing_time_total': 0.0
        }
        
        self.logger.info("SmartPDFAnalyzer initialisé")
    
    def analyser_et_traiter_pdf(self, pdf_file: str, max_pages: Optional[int] = None) -> Optional[Dict]:
        """
        Analyse et traite un PDF avec gestion unifiée du document
        
        Args:
            pdf_file: Chemin vers le fichier PDF
            max_pages: Nombre maximum de pages à analyser
            
        Returns:
            Dict contenant les résultats de l'analyse ou None en cas d'erreur
        """
        
        pdf_path = Path(pdf_file)
        
        if not pdf_path.exists():
            self.logger.error(f"Fichier PDF introuvable: {pdf_file}")
            return None
        
        self.logger.info(f"Début analyse PDF: {pdf_path.name}")
        self.logger.info(f"Taille: {pdf_path.stat().st_size / 1024 / 1024:.1f} MB")
        self.logger.info(f"Limite pages: {max_pages or 'Toutes'}")
        
        self.performance_logger.start_timer("total_processing")
        
        try:
            with PDFManagerUnifie() as pdf_manager:
                
                # Phase 1: Ouverture sécurisée
                self.performance_logger.start_timer("document_opening")
                
                if not pdf_manager.ouvrir_document(str(pdf_path)):
                    self.logger.error("Impossible d'ouvrir le PDF")
                    return None
                
                self.performance_logger.end_timer("document_opening")
                
                # Phase 2: Analyse structure
                self.performance_logger.start_timer("structure_analysis")
                
                analyse = pdf_manager.analyser_structure_complete(max_pages)
                
                if not analyse.get('page_analyses'):
                    self.logger.error("Aucune page analysable trouvée")
                    return None
                
                self.performance_logger.end_timer("structure_analysis")
                
                recommandation = analyse['recommandation']
                resume = analyse['summary']
                
                self.logger.info(f"Analyse terminée en {analyse['analysis_time']:.1f}s")
                self.logger.info(f"Pages analysées: {analyse['total_pages_analyzed']}")
                self.logger.info(f"Pages recommandées: {len(recommandation['pages_suggerees'])}")
                self.logger.info(f"Confiance: {recommandation['confiance']:.1f}%")
                
                # Affichage des meilleures pages
                for i, detail in enumerate(recommandation['details_pages'][:5], 1):
                    self.logger.info(f"Page {detail['page']}: Score {detail['score']} "
                                   f"({detail['relations']} rel, {detail['personnes']} pers)")
                
                # Phase 3: Extraction du texte
                pages_a_traiter = recommandation['pages_suggerees']
                
                if not pages_a_traiter:
                    self.logger.warning("Aucune page de registre détectée")
                    return self._create_empty_result(analyse)
                
                self.performance_logger.start_timer("text_extraction")
                
                texte_registres = pdf_manager.extraire_pages_selectionnees(pages_a_traiter)
                
                if not texte_registres:
                    self.logger.error("Échec de l'extraction du texte")
                    return None
                
                self.performance_logger.end_timer("text_extraction")
                
                # Phase 4: Traitement généalogique
                self.performance_logger.start_timer("genealogical_processing")
                
                try:
                    resultat_genealogique = self._traiter_contenu_genealogique(texte_registres)
                    
                    self.performance_logger.end_timer("genealogical_processing")
                    
                    # Mise à jour des statistiques globales
                    self._update_global_stats(analyse, resultat_genealogique)
                    
                    # Construction du résultat final
                    return self._build_final_result(
                        analyse, recommandation, resultat_genealogique, pages_a_traiter
                    )
                    
                except Exception as e:
                    self.logger.error(f"Erreur traitement généalogique: {e}")
                    return self._create_partial_result(analyse, pages_a_traiter, str(e))
        
        except Exception as e:
            self.logger.error(f"Erreur critique durant l'analyse: {e}")
            return None
        
        finally:
            total_time = self.performance_logger.end_timer("total_processing")
            self.logger.info(f"Traitement terminé en {total_time:.2f}s")
    
    def _traiter_contenu_genealogique(self, texte: str) -> Dict:
        """Traite le contenu généalogique extrait"""
        
        self.logger.info(f"Traitement généalogique de {len(texte):,} caractères")
        
        # Extraction des relations avec le parser robuste
        self.performance_logger.start_timer("relationship_extraction")
        
        relations = self.relationship_parser.extract_relationships(texte)
        
        self.performance_logger.end_timer("relationship_extraction")
        
        # Classification des relations par type
        filiations = [r for r in relations if r.get('type') == 'filiation']
        mariages = [r for r in relations if r.get('type') == 'mariage']
        parrainages = [r for r in relations if r.get('type') in ['parrain', 'marraine']]
        
        self.logger.info(f"Relations extraites: {len(relations)} total")
        self.logger.info(f"  Filiations: {len(filiations)}")
        self.logger.info(f"  Mariages: {len(mariages)}")
        self.logger.info(f"  Parrainages: {len(parrainages)}")
        
        # Extraction des entités nommées (personnes)
        personnes_extraites = self._extraire_personnes(texte)
        
        # Validation et calcul de qualité
        validation_results = self._valider_donnees(relations, personnes_extraites)
        
        return {
            'relations_count': len(relations),
            'filiations': filiations,
            'mariages': mariages,
            'parrainages': parrainages,
            'personnes_extraites': personnes_extraites,
            'validation': validation_results,
            'parser_stats': self.relationship_parser.stats.copy(),
            'processing_time': self.performance_logger.get_total_time("relationship_extraction")
        }
    
    def _extraire_personnes(self, texte: str) -> List[Dict]:
        """Extrait les personnes mentionnées dans le texte"""
        
        # Pattern pour noms de personnes
        name_pattern = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\-]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\-]+)+'
        
        matches = re.findall(name_pattern, texte)
        
        # Déduplication et nettoyage
        personnes_uniques = {}
        for match in matches:
            clean_name = re.sub(r'\s+', ' ', match.strip())
            if len(clean_name) > 3 and clean_name not in personnes_uniques:
                personnes_uniques[clean_name] = {
                    'nom_complet': clean_name,
                    'occurrences': texte.count(clean_name)
                }
        
        return list(personnes_uniques.values())
    
    def _valider_donnees(self, relations: List[Dict], personnes: List[Dict]) -> Dict:
        """Valide la cohérence des données extraites"""
        
        validation_rate = 0.0
        quality_score = "Moyenne"
        
        if relations and personnes:
            # Calculer un taux de validation basé sur la cohérence
            personnes_dans_relations = set()
            for rel in relations:
                if rel.get('type') == 'filiation':
                    if rel.get('enfant'):
                        personnes_dans_relations.add(rel['enfant'].lower())
                    if rel.get('pere'):
                        personnes_dans_relations.add(rel['pere'].lower())
                    if rel.get('mere'):
                        personnes_dans_relations.add(rel['mere'].lower())
                elif rel.get('type') == 'mariage':
                    if rel.get('epouse'):
                        personnes_dans_relations.add(rel['epouse'].lower())
                    if rel.get('epoux'):
                        personnes_dans_relations.add(rel['epoux'].lower())
            
            personnes_extraites = {p['nom_complet'].lower() for p in personnes}
            
            if personnes_extraites:
                validation_rate = len(personnes_dans_relations.intersection(personnes_extraites)) / len(personnes_extraites) * 100
                
                if validation_rate > 70:
                    quality_score = "Excellente"
                elif validation_rate > 40:
                    quality_score = "Bonne"
                elif validation_rate > 20:
                    quality_score = "Moyenne"
                else:
                    quality_score = "Faible"
        
        return {
            'validation_rate': round(validation_rate, 1),
            'data_quality': quality_score,
            'total_persons': len(personnes),
            'total_relations': len(relations),
            'coherence_score': round(validation_rate / 100, 2)
        }
    
    def _update_global_stats(self, analyse: Dict, resultat_genealogique: Dict):
        """Met à jour les statistiques globales"""
        self.global_stats['documents_processed'] += 1
        self.global_stats['total_pages_analyzed'] += analyse.get('total_pages_analyzed', 0)
        self.global_stats['total_relations_found'] += resultat_genealogique.get('relations_count', 0)
        self.global_stats['processing_time_total'] += self.performance_logger.get_total_time("total_processing")
    
    def _build_final_result(self, analyse: Dict, recommandation: Dict, 
                           resultat_genealogique: Dict, pages_a_traiter: List[int]) -> Dict:
        """Construit le résultat final complet"""
        
        total_relations = resultat_genealogique.get('relations_count', 0)
        validation = resultat_genealogique.get('validation', {})
        
        return {
            'success': True,
            'pages_analysees': analyse['total_pages_analyzed'],
            'pages_registres': len(pages_a_traiter),
            'pages_suggerees': pages_a_traiter,
            'resultats_genealogiques': resultat_genealogique,
            'statistiques': {
                'persons': {'total_persons': len(resultat_genealogique.get('personnes_extraites', []))},
                'relations': {
                    'total_relations': total_relations,
                    'filiations': len(resultat_genealogique.get('filiations', [])),
                    'mariages': len(resultat_genealogique.get('mariages', [])),
                    'parrainages': len(resultat_genealogique.get('parrainages', []))
                }
            },
            'analyse_pdf': analyse,
            'qualite_extraction': {
                'relations_extraites': total_relations,
                'qualite_donnees': validation.get('data_quality', 'Non évaluée'),
                'taux_validation': validation.get('validation_rate', 0)
            },
            'performance': self.performance_logger.get_all_results(),
            'recommandation': recommandation
        }
    
    def _create_empty_result(self, analyse: Dict) -> Dict:
        """Crée un résultat vide quand aucune page n'est trouvée"""
        return {
            'success': False,
            'pages_analysees': analyse['total_pages_analyzed'],
            'pages_registres': 0,
            'pages_suggerees': [],
            'resultats_genealogiques': {'relations_count': 0},
            'analyse_pdf': analyse,
            'error': 'Aucune page de registre détectée'
        }
    
    def _create_partial_result(self, analyse: Dict, pages: List[int], error: str) -> Dict:
        """Crée un résultat partiel en cas d'erreur de traitement"""
        return {
            'success': False,
            'pages_analysees': analyse['total_pages_analyzed'],
            'pages_registres': len(pages),
            'pages_suggerees': pages,
            'analyse_pdf': analyse,
            'error': error
        }
    
    def obtenir_statistiques_globales(self) -> Dict:
        """Retourne les statistiques globales de l'analyseur"""
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

def analyser_et_traiter_pdf(pdf_file: str, max_pages: Optional[int] = None) -> Optional[Dict]:
    """
    Fonction principale d'analyse et traitement d'un PDF
    Version corrigée sans erreur "document closed"
    
    Args:
        pdf_file: Chemin vers le fichier PDF
        max_pages: Nombre maximum de pages à analyser
        
    Returns:
        Dict contenant les résultats ou None en cas d'erreur
    """
    
    analyzer = SmartPDFAnalyzer()
    return analyzer.analyser_et_traiter_pdf(pdf_file, max_pages)

def main():
    """Fonction principale avec interface en ligne de commande et export CSV"""
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Smart PDF Analyzer - Analyseur de registres paroissiaux"
    )
    parser.add_argument(
        'pdf_file', 
        nargs='?',
        default=r'C:\Users\Louis\Documents\CodexGenea\inventairesommai03archuoft.pdf',
        help='Fichier PDF à analyser'
    )
    parser.add_argument(
        '--max-pages', 
        type=int, 
        help='Nombre maximum de pages à analyser'
    )
    parser.add_argument(
        '--output', 
        help='Fichier de sortie pour les résultats (JSON)'
    )
    parser.add_argument(
        '--csv-dir',
        default='RESULT',
        help='Dossier pour les exports CSV (défaut: RESULT)'
    )
    parser.add_argument(
        '--no-csv',
        action='store_true',
        help='Désactiver l\'export CSV automatique'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true', 
        help='Mode verbeux'
    )
    parser.add_argument(
        '--stats-only', 
        action='store_true', 
        help='Afficher uniquement les statistiques'
    )
    
    args = parser.parse_args()
    
    # Configuration du niveau de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Vérification du fichier
    if not Path(args.pdf_file).exists():
        print(f"Erreur: Fichier '{args.pdf_file}' introuvable")
        sys.exit(1)
    
    print("Smart PDF Analyzer - Version 3.0.1")
    print("=" * 50)
    print(f"Fichier: {Path(args.pdf_file).name}")
    print(f"Limite pages: {args.max_pages or 'Toutes'}")
    if not args.no_csv and CSV_EXPORT_AVAILABLE:
        print(f"Export CSV: {args.csv_dir}")
    print()
    
    # Traitement principal
    try:
        resultat = analyser_et_traiter_pdf(args.pdf_file, args.max_pages)
        
        if resultat:
            print("TRAITEMENT TERMINÉ AVEC SUCCÈS")
            print("=" * 50)
            
            if resultat.get('success', True):
                print(f"Pages de registres trouvées: {resultat['pages_registres']}")
                
                stats = resultat.get('statistiques', {})
                if 'persons' in stats:
                    print(f"Personnes extraites: {stats['persons']['total_persons']}")
                
                if 'relations' in stats:
                    rel_stats = stats['relations']
                    print(f"Relations familiales: {rel_stats['total_relations']}")
                    print(f"  - Filiations: {rel_stats['filiations']}")
                    print(f"  - Mariages: {rel_stats['mariages']}")
                    print(f"  - Parrainages: {rel_stats['parrainages']}")
                
                qualite = resultat.get('qualite_extraction', {})
                print(f"Qualité des données: {qualite.get('qualite_donnees', 'Non évaluée')}")
                
                # Performance
                performance = resultat.get('performance', {})
                if 'total_processing' in performance:
                    print(f"Temps total: {performance['total_processing']:.2f}s")
                
                # Export automatique vers CSV
                if not args.no_csv and CSV_EXPORT_AVAILABLE:
                    print(f"\nExport CSV automatique vers {args.csv_dir}")
                    print("-" * 30)
                    try:
                        fichiers_csv = exporter_vers_csv(resultat, args.csv_dir)
                        print(f"Fichiers CSV créés:")
                        for type_fichier, chemin in fichiers_csv.items():
                            filename = Path(chemin).name
                            print(f"  - {type_fichier}: {filename}")
                        
                        print(f"\nTous les fichiers sont dans le dossier: {Path(args.csv_dir).absolute()}")
                        
                    except Exception as e:
                        print(f"Erreur lors de l'export CSV: {e}")
                        if args.verbose:
                            import traceback
                            traceback.print_exc()
            else:
                print(f"TRAITEMENT PARTIEL: {resultat.get('error', 'Erreur inconnue')}")
            
            # Sauvegarde JSON (optionnelle)
            if args.output:
                try:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(resultat, f, indent=2, ensure_ascii=False)
                    print(f"Résultats JSON sauvegardés: {args.output}")
                except Exception as e:
                    print(f"Erreur sauvegarde JSON: {e}")
            
            # Statistiques détaillées
            if args.verbose or args.stats_only:
                print("\nSTATISTIQUES DÉTAILLÉES")
                print("-" * 30)
                
                if 'performance' in resultat:
                    for operation, temps in resultat['performance'].items():
                        print(f"{operation}: {temps:.2f}s")
                
                if 'analyse_pdf' in resultat:
                    resume = resultat['analyse_pdf'].get('summary', {})
                    for key, value in resume.items():
                        print(f"{key}: {value}")
        
        else:
            print("ÉCHEC DU TRAITEMENT")
            print("Vérifiez les logs pour plus de détails")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nTraitement interrompu par l'utilisateur")
        sys.exit(1)
    
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def test_analyzer():
    """Fonction de test pour valider le fonctionnement"""
    
    print("Test du Smart PDF Analyzer")
    print("=" * 30)
    
    # Test avec fichier d'exemple
    test_files = [
        r'C:\Users\Louis\Documents\CodexGenea\inventairesommai03archuoft.pdf',
        'test.pdf',
        'sample.pdf'
    ]
    
    for pdf_file in test_files:
        if Path(pdf_file).exists():
            print(f"Test avec: {Path(pdf_file).name}")
            
            try:
                resultat = analyser_et_traiter_pdf(pdf_file, max_pages=5)
                
                if resultat:
                    print("Test réussi")
                    print(f"Pages analysées: {resultat.get('pages_analysees', 0)}")
                    print(f"Pages recommandées: {resultat.get('pages_registres', 0)}")
                else:
                    print("Test échoué: Aucun résultat")
                
                return True
                
            except Exception as e:
                print(f"Test échoué: {e}")
                return False
    
    print("Aucun fichier de test trouvé")
    return False

if __name__ == "__main__":
    # Si appelé directement, lancer l'interface principale
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_analyzer()
    else:
        main()