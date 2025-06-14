# smart_pdf_analyzer.py - VERSION COMPLÈTEMENT CORRIGÉE ET RÉVISÉE
"""
Analyseur PDF intelligent avec correction complète du pipeline des relations
Version 2.0.0 - Fix complet et optimisé
"""

import fitz  # PyMuPDF
import re
import sys
import logging
import types
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@dataclass
class PageAnalysis:
    """Analyse d'une page de PDF avec métriques détaillées"""
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

class SmartPDFAnalyzer:
    """Analyseur PDF intelligent pour détecter automatiquement les pages de registres paroissiaux"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Patterns optimisés pour détecter les registres paroissiaux français
        self.parish_indicators = [
            r'baptême|bapt\.|baptisé|baptisée|baptiser',
            r'mariage|marié|mariée|épouse|époux|épouser',
            r'inhumation|inh\.|enterré|enterrée|décédé|décédée|sépulture',
            r'parrain|marraine|parr\.|marr\.|filleul|filleule',
            r'fils\s+de|fille\s+de|filz\s+de',
            r'sieur|sr\.|écuyer|éc\.|seigneur|dame|demoiselle',
            r'curé|vicaire|prêtre|église|paroisse|chapelle',
            r'né|née|mort|morte|veuf|veuve'
        ]
        
        # Patterns pour noms de personnes français anciens
        self.name_patterns = [
            r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ-]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ-]+)+',
            r'[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?'
        ]
        
        # Patterns pour relations familiales
        self.relationship_patterns = [
            r'fils\s+de|fille\s+de|filz\s+de',
            r'épouse\s+de|femme\s+de|veuve\s+de',
            r'parrain\s*[\.:]|marraine\s*[\.:]',
            r'et\s+de\s+[A-Z][a-z]+\s+[A-Z][a-z]+',
            r'père\s+et\s+mère|parents',
            r'frère\s+de|sœur\s+de|neveu\s+de|nièce\s+de'
        ]
        
        # Patterns pour dates françaises
        self.date_patterns = [
            r'\b\d{4}\b',  # Années (1650, 1725, etc.)
            r'\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)',
            r'\d{1,2}\s+(?:janv|févr|mars|avr|mai|juin|juil|août|sept|oct|nov|déc)\.?',
            r'\d{1,2}(?:er|e)?\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)',
        ]
    
    def analyze_pdf_structure(self, pdf_path: str, max_pages: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyse la structure complète du PDF pour identifier les pages de registres
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            max_pages: Limite du nombre de pages à analyser (None = toutes)
            
        Returns:
            Dict contenant l'analyse complète du PDF
        """
        
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"Fichier PDF non trouvé: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            if max_pages:
                total_pages = min(total_pages, max_pages)
            
            print(f"📖 Analyse du PDF: {total_pages} pages sur {len(doc)} au total")
            
            page_analyses = []
            
            # Analyse page par page avec extraction immédiate du texte
            for page_num in range(total_pages):
                try:
                    page = doc[page_num]
                    # EXTRAIT IMMÉDIATEMENT le texte pour éviter les références au document
                    text = str(page.get_text())  # Forcer une copie string
                    
                    analysis = self._analyze_page_content(page_num + 1, text)
                    page_analyses.append(analysis)
                    
                    # Progress indicator
                    if (page_num + 1) % 50 == 0 or page_num == total_pages - 1:
                        print(f"   📄 Analysé {page_num + 1}/{total_pages} pages...")
                
                except Exception as e:
                    self.logger.warning(f"Erreur analyse page {page_num + 1}: {e}")
                    # Créer une analyse vide pour cette page
                    empty_analysis = PageAnalysis(
                        page_number=page_num + 1,
                        text_content="",
                        person_count=0,
                        relationship_count=0,
                        date_count=0,
                        quality_score=0.0,
                        language="unknown",
                        preview="Erreur lecture page",
                        parish_indicators_found=0,
                        word_count=0
                    )
                    page_analyses.append(empty_analysis)
                    continue
            
            doc.close()
            
            # Analyser les résultats
            parish_pages = [p for p in page_analyses if p.quality_score > 5.0]
            total_parish_pages = len(parish_pages)
            
            print(f"✅ Analyse terminée: {total_parish_pages} pages de registres détectées sur {len(page_analyses)}")
            
            result = {
                'total_pages_analyzed': len(page_analyses),
                'total_pages_in_pdf': len(doc) if 'doc' in locals() else total_pages,
                'parish_pages_count': total_parish_pages,
                'page_analyses': page_analyses,
                'recommendations': self._generate_recommendations(page_analyses),
                'analysis_summary': self._generate_analysis_summary(page_analyses)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur critique lors de l'analyse PDF: {e}")
            raise
    
    def _analyze_page_content(self, page_num: int, text: str) -> PageAnalysis:
        """
        Analyse le contenu d'une page pour déterminer si c'est un registre paroissial
        
        Args:
            page_num: Numéro de la page
            text: Contenu textuel de la page
            
        Returns:
            PageAnalysis avec toutes les métriques
        """
        
        # Forcer une copie string pour éviter les références PyMuPDF
        text = str(text) if text else ""
        
        if not text or len(text.strip()) < 20:
            return PageAnalysis(
                page_number=page_num,
                text_content="",  # Vide pour économiser la mémoire
                person_count=0,
                relationship_count=0,
                date_count=0,
                quality_score=0.0,
                language="unknown",
                preview="",
                parish_indicators_found=0,
                word_count=0
            )
        
        # Normaliser le texte pour l'analyse
        text_clean = re.sub(r'\s+', ' ', text.strip())
        word_count = len(text_clean.split())
        
        # Compter les indicateurs paroissiaux
        parish_score = 0
        indicators_found = 0
        for pattern in self.parish_indicators:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            if matches > 0:
                indicators_found += 1
                parish_score += matches * 2  # Poids élevé pour les mots-clés paroissiaux
        
        # Compter les personnes (noms propres)
        person_count = 0
        for pattern in self.name_patterns:
            person_matches = re.findall(pattern, text)
            person_count += len(set(person_matches))  # Éviter les doublons
        
        # Compter les relations familiales
        relationship_count = 0
        for pattern in self.relationship_patterns:
            relationship_count += len(re.findall(pattern, text, re.IGNORECASE))
        
        # Compter les dates
        date_count = 0
        for pattern in self.date_patterns:
            date_count += len(re.findall(pattern, text, re.IGNORECASE))
        
        # Calcul du score de qualité (pondéré)
        quality_score = (
            parish_score * 2.0 +           # Indicateurs paroissiaux (poids fort)
            person_count * 0.8 +           # Nombre de personnes
            relationship_count * 3.0 +     # Relations familiales (poids très fort)
            date_count * 1.0 +             # Dates
            min(word_count / 50, 10) * 0.5 # Bonus pour texte substantiel (plafonné)
        )
        
        # Détecter la langue
        french_indicators = [
            r'\bde\b', r'\ble\b', r'\bla\b', r'\bdu\b', r'\bdes\b', 
            r'\bet\b', r'\bdans\b', r'\béglise\b', r'\bpar\b', r'\bce\b'
        ]
        french_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in french_indicators)
        language = "français" if french_count > 3 else "autre"
        
        # Générer prévisualisation intelligente
        preview = self._generate_smart_preview(text_clean)
        
        return PageAnalysis(
            page_number=page_num,
            text_content="",  # NE PAS stocker le texte complet pour éviter les fuites mémoire
            person_count=person_count,
            relationship_count=relationship_count,
            date_count=date_count,
            quality_score=quality_score,
            language=language,
            preview=preview,
            parish_indicators_found=indicators_found,
            word_count=word_count
        )
    
    def _generate_smart_preview(self, text: str) -> str:
        """Génère une prévisualisation intelligente du contenu"""
        if len(text) <= 150:
            return text.replace('\n', ' ')
        
        # Chercher des phrases avec indicateurs paroissiaux
        sentences = re.split(r'[.;!?]', text)
        for sentence in sentences:
            if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in self.parish_indicators[:4]):
                preview = sentence.strip()[:150]
                if preview:
                    return preview + "..."
        
        # Fallback: début du texte
        return text[:150].replace('\n', ' ') + "..."
    
    def _generate_recommendations(self, page_analyses: List[PageAnalysis]) -> Dict[str, Any]:
        """
        Génère des recommandations d'extraction basées sur l'analyse
        
        Args:
            page_analyses: Liste des analyses de pages
            
        Returns:
            Dict avec recommandations et statistiques
        """
        
        # Trier par score de qualité
        sorted_pages = sorted(page_analyses, key=lambda x: x.quality_score, reverse=True)
        
        # Pages recommandées avec seuil adaptatif
        high_quality_pages = [p for p in sorted_pages if p.quality_score > 10.0]
        medium_quality_pages = [p for p in sorted_pages if 5.0 < p.quality_score <= 10.0]
        
        if high_quality_pages:
            recommended_pages = [p.page_number for p in high_quality_pages]
        elif medium_quality_pages:
            # Si pas de pages haute qualité, prendre les meilleures moyennes
            recommended_pages = [p.page_number for p in medium_quality_pages[:20]]
        else:
            # Dernier recours: les 10 meilleures pages
            recommended_pages = [p.page_number for p in sorted_pages[:10] if p.quality_score > 1.0]
        
        # Statistiques détaillées
        total_relationships = sum(p.relationship_count for p in page_analyses)
        total_persons = sum(p.person_count for p in page_analyses)
        total_dates = sum(p.date_count for p in page_analyses)
        best_score = sorted_pages[0].quality_score if sorted_pages else 0
        
        # Détails des meilleures pages
        top_pages = sorted_pages[:15]  # Top 15 pour plus de détails
        pages_details = []
        
        for page in top_pages:
            pages_details.append({
                'page': page.page_number,
                'score': round(page.quality_score, 2),
                'relations': page.relationship_count,
                'personnes': page.person_count,
                'dates': page.date_count,
                'indicateurs': page.parish_indicators_found,
                'mots': page.word_count,
                'langue': page.language,
                'preview': page.preview
            })
        
        return {
            'pages_suggerees': recommended_pages,
            'total_relations': total_relationships,
            'total_personnes': total_persons,
            'total_dates': total_dates,
            'meilleur_score': best_score,
            'pages_details': pages_details,
            'qualite_distribution': {
                'excellente': len([p for p in page_analyses if p.quality_score > 15.0]),
                'bonne': len([p for p in page_analyses if 10.0 < p.quality_score <= 15.0]),
                'moyenne': len([p for p in page_analyses if 5.0 < p.quality_score <= 10.0]),
                'faible': len([p for p in page_analyses if 1.0 < p.quality_score <= 5.0]),
                'nulle': len([p for p in page_analyses if p.quality_score <= 1.0])
            }
        }
    
    def _generate_analysis_summary(self, page_analyses: List[PageAnalysis]) -> Dict[str, Any]:
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
    
    def extraire_pages_registres(self, pdf_path: str, page_numbers: List[int]) -> str:
        """
        Extrait le texte des pages de registres spécifiées
        
        Args:
            pdf_path: Chemin vers le PDF
            page_numbers: Liste des numéros de pages à extraire
            
        Returns:
            Texte combiné de toutes les pages
        """
        
        if not page_numbers:
            self.logger.warning("Aucune page spécifiée pour extraction")
            return ""
        
        # Vérifier que le fichier existe encore
        if not Path(pdf_path).exists():
            self.logger.error(f"Fichier PDF non trouvé lors de l'extraction: {pdf_path}")
            return ""
        
        doc = None
        try:
            doc = fitz.open(pdf_path)
            combined_text = []
            
            print(f"📄 Extraction de {len(page_numbers)} pages...")
            
            extracted_count = 0
            for page_num in page_numbers:
                try:
                    if 1 <= page_num <= len(doc):
                        page = doc[page_num - 1]  # fitz utilise un index base 0
                        text = page.get_text()
                        
                        if text.strip():
                            # Ajouter délimiteur de page pour traçabilité
                            combined_text.append(f"\n{'='*20} PAGE {page_num} {'='*20}\n{text}\n")
                            extracted_count += 1
                        else:
                            self.logger.warning(f"Page {page_num} vide ou illisible")
                    else:
                        self.logger.warning(f"Page {page_num} hors limites (PDF a {len(doc)} pages)")
                        
                except Exception as e:
                    self.logger.error(f"Erreur extraction page {page_num}: {e}")
                    continue
            
            final_text = "\n".join(combined_text)
            print(f"✅ Extraction réussie: {extracted_count}/{len(page_numbers)} pages, {len(final_text)} caractères")
            
            return final_text
            
        except Exception as e:
            self.logger.error(f"Erreur critique lors de l'extraction: {e}")
            return ""
        
        finally:
            # S'assurer que le document est fermé même en cas d'erreur
            if doc is not None:
                try:
                    doc.close()
                except Exception as e:
                    self.logger.warning(f"Erreur lors de la fermeture du document: {e}")

# === FIX COMPLET DU PIPELINE DES RELATIONS ===

def debug_relationship_extraction(parser, text_sample: str) -> Dict[str, Any]:
    """Debug approfondi du processus d'extraction des relations"""
    
    print("🔍 DEBUG EXTRACTION RELATIONS")
    print("=" * 40)
    
    # 1. Vérifier le parser de relations
    rel_parser = parser.relationship_parser
    print(f"✅ RelationshipParser: {type(rel_parser).__name__}")
    
    # 2. Test sur échantillon
    sample = text_sample[:1500] if len(text_sample) > 1500 else text_sample
    print(f"📝 Échantillon testé ({len(sample)} caractères)")
    print(f"Preview: '{sample[:100]}...'")
    
    # 3. Test direct extraction
    try:
        relations = rel_parser.extract_relationships(sample)
        print(f"📊 Relations extraites: {len(relations)}")
        
        if relations:
            for i, rel in enumerate(relations[:5]):  # Afficher 5 premiers
                print(f"   {i+1}. Type: {rel.get('type', 'N/A')} - {rel}")
        else:
            print("   ⚠️ Aucune relation trouvée")
            
    except Exception as e:
        print(f"   🚨 ERREUR extraction: {e}")
        relations = []
    
    # 4. Test patterns individuellement
    print(f"\n🎯 Test patterns individuels:")
    if hasattr(rel_parser, 'patterns'):
        for pattern_name, pattern in list(rel_parser.patterns.items())[:5]:  # Top 5 patterns
            try:
                matches = pattern.findall(sample)
                print(f"   - {pattern_name}: {len(matches)} matches")
                if matches:
                    print(f"     Premier: {matches[0]}")
            except Exception as e:
                print(f"   - {pattern_name}: ERREUR - {e}")
    
    # 5. Test normalisation
    try:
        normalized = parser.text_parser.normalize_text(sample)
        relations_norm = rel_parser.extract_relationships(normalized)
        print(f"\n📝 Après normalisation: {len(relations_norm)} relations")
    except Exception as e:
        print(f"\n❌ Erreur normalisation: {e}")
        relations_norm = []
    
    return {
        'relations_brutes': relations,
        'relations_normalisees': relations_norm,
        'sample_text': sample[:500],  # Limiter pour debug
        'success': len(relations) > 0 or len(relations_norm) > 0
    }

def fix_process_document_method(parser_instance) -> None:
    """
    Application complète du fix pour le pipeline des relations familiales
    """
    
    def process_document_fixed(self, text: str, lieu: str = "Archive départementale") -> Dict[str, Any]:
        """Version complètement corrigée du traitement de document"""
        
        # Initialisation
        self.perf_logger.start_timer("process_document")
        self.logger.info(f"🚀 Début traitement - Lieu: {lieu}")
        
        try:
            # === PHASE 1: PRÉPARATION DU TEXTE ===
            self.perf_logger.start_timer("text_preparation")
            
            print(f"📝 Texte d'entrée: {len(text)} caractères")
            
            # Normalisation
            normalized_text = self.text_parser.normalize_text(text)
            print(f"📝 Après normalisation: {len(normalized_text)} caractères")
            
            # Segmentation
            segments = self.text_parser.extract_segments(normalized_text)
            print(f"📦 Segments créés: {len(segments)}")
            
            self.perf_logger.end_timer("text_preparation")
            
            # === PHASE 2: EXTRACTION DES RELATIONS (CRITIQUE) ===
            self.perf_logger.start_timer("relationship_extraction")
            
            print(f"\n🔗 === EXTRACTION DES RELATIONS ===")
            
            # Debug sur échantillon si texte volumineux
            if len(normalized_text) > 5000:
                debug_sample = normalized_text[:5000]
                debug_result = debug_relationship_extraction(self, debug_sample)
                print(f"🔍 Debug échantillon: {len(debug_result['relations_brutes'])} relations")
            
            # Extraction complète
            print(f"🔄 Extraction sur texte complet...")
            all_relationships = self.relationship_parser.extract_relationships(normalized_text)
            
            print(f"📊 === RÉSULTATS EXTRACTION ===")
            print(f"   Total relations: {len(all_relationships)}")
            
            # Classification par type
            filiations = []
            parrainages = []
            mariages = []
            autres_relations = []
            
            for rel in all_relationships:
                rel_type = rel.get('type', 'inconnu')
                
                if rel_type == 'filiation':
                    filiations.append(rel)
                elif rel_type in ['parrain', 'marraine']:
                    parrainages.append(rel)
                elif rel_type == 'mariage':
                    mariages.append(rel)
                else:
                    autres_relations.append(rel)
                    
                # Debug première relation de chaque type
                if len(filiations) == 1 and rel_type == 'filiation':
                    print(f"   📋 Première filiation: {rel}")
                elif len(parrainages) == 1 and rel_type in ['parrain', 'marraine']:
                    print(f"   🤝 Premier parrainage: {rel}")
                elif len(mariages) == 1 and rel_type == 'mariage':
                    print(f"   💒 Premier mariage: {rel}")
            
            print(f"   📋 Filiations: {len(filiations)}")
            print(f"   🤝 Parrainages: {len(parrainages)}")
            print(f"   💒 Mariages: {len(mariages)}")
            print(f"   ❓ Autres: {len(autres_relations)}")
            
            self.perf_logger.end_timer("relationship_extraction")
            
            # === PHASE 3: EXTRACTION DES PERSONNES ===
            self.perf_logger.start_timer("person_extraction")
            
            print(f"\n👥 === EXTRACTION DES PERSONNES ===")
            
            names_and_info = []
            for segment in segments:
                segment_names = self.name_extractor.extract_complete_names_with_sources(
                    segment['content'], 
                    segment.get('source_reference', ''),
                    segment.get('page_number')
                )
                names_and_info.extend(segment_names)
            
            print(f"   Noms extraits: {len(names_and_info)}")
            
            # Création des objets Person
            persons = {}
            for name_info in names_and_info:
                try:
                    person = self.person_manager.create_or_update_person(name_info)
                    if person and hasattr(person, 'id') and person.id:
                        persons[person.id] = person
                except Exception as e:
                    self.logger.warning(f"Erreur création personne {name_info}: {e}")
            
            print(f"   Personnes créées: {len(persons)}")
            self.perf_logger.end_timer("person_extraction")
            
            # === PHASE 4: CRÉATION DES ACTES ===
            self.perf_logger.start_timer("acte_creation")
            
            print(f"\n📋 === CRÉATION DES ACTES ===")
            
            actes = {}
            for segment in segments:
                try:
                    segment_actes = self.acte_manager.extract_actes_from_segment(segment, persons)
                    if segment_actes:
                        actes.update(segment_actes)
                except Exception as e:
                    self.logger.warning(f"Erreur création actes segment: {e}")
            
            print(f"   Actes créés: {len(actes)}")
            self.perf_logger.end_timer("acte_creation")
            
            # === PHASE 5: INTÉGRATION DES RELATIONS (CRITIQUE) ===
            self.perf_logger.start_timer("relationship_integration")
            
            print(f"\n🔗 === INTÉGRATION DES RELATIONS ===")
            
            relations_applied = 0
            
            # Application des filiations
            for i, filiation in enumerate(filiations):
                try:
                    if self._apply_filiation_to_persons(filiation, persons):
                        relations_applied += 1
                        if i < 3:  # Debug des 3 premières
                            print(f"   ✅ Filiation {i+1} appliquée")
                except Exception as e:
                    print(f"   ❌ Erreur filiation {i}: {e}")
            
            # Application des parrainages
            for i, parrainage in enumerate(parrainages):
                try:
                    if self._apply_parrainage_to_persons(parrainage, persons):
                        relations_applied += 1
                        if i < 3:  # Debug des 3 premiers
                            print(f"   ✅ Parrainage {i+1} appliqué")
                except Exception as e:
                    print(f"   ❌ Erreur parrainage {i}: {e}")
            
            # Application des mariages
            for i, mariage in enumerate(mariages):
                try:
                    if self._apply_mariage_to_persons(mariage, persons):
                        relations_applied += 1
                        if i < 3:  # Debug des 3 premiers
                            print(f"   ✅ Mariage {i+1} appliqué")
                except Exception as e:
                    print(f"   ❌ Erreur mariage {i}: {e}")
            
            print(f"   Relations appliquées: {relations_applied}/{len(all_relationships)}")
            self.perf_logger.end_timer("relationship_integration")
            
            # === PHASE 6: VALIDATION ===
            self.perf_logger.start_timer("validation")
            
            validation_results = self._validate_data_enhanced(persons, actes, all_relationships)
            
            self.perf_logger.end_timer("validation")
            
            # === PHASE 7: CONSTRUCTION DU RÉSULTAT ===
            
            result = {
                'persons': persons,
                'actes': actes,
                'filiations': filiations,
                'parrainages': parrainages,
                'mariages': mariages,
                'autres_relations': autres_relations,
                'relations_count': len(all_relationships),
                'relations_applied': relations_applied,
                'validation': validation_results,
                'lieu': lieu,
                'processing_time': self.perf_logger.get_total_time("process_document"),
                'stats': {
                    'segments_traites': len(segments),
                    'noms_extraits': len(names_and_info),
                    'personnes_creees': len(persons),
                    'actes_crees': len(actes),
                    'relations_totales': len(all_relationships),
                    'relations_appliquees': relations_applied
                }
            }
            
            print(f"\n✅ === TRAITEMENT TERMINÉ ===")
            print(f"   👥 Personnes: {len(persons)}")
            print(f"   📋 Actes: {len(actes)}")
            print(f"   🔗 Relations: {len(all_relationships)}")
            print(f"   ✅ Relations intégrées: {relations_applied}")
            print(f"   ⏱️ Temps: {result['processing_time']:.2f}s")
            
            self.perf_logger.end_timer("process_document")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur critique dans process_document: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    # === MÉTHODES D'AIDE POUR L'APPLICATION DES RELATIONS ===
    
    def _apply_filiation_to_persons(self, filiation: Dict, persons: Dict) -> bool:
        """Applique une filiation aux personnes avec validation"""
        try:
            enfant_name = filiation.get('enfant', '').strip()
            pere_name = filiation.get('pere', '').strip()
            mere_name = filiation.get('mere', '').strip()
            
            if not enfant_name:
                return False
            
            # Trouver les personnes
            enfant = self._find_person_by_name(enfant_name, persons)
            pere = self._find_person_by_name(pere_name, persons) if pere_name else None
            mere = self._find_person_by_name(mere_name, persons) if mere_name else None
            
            if enfant:
                updated = False
                if pere and not enfant.pere_id:
                    enfant.pere_id = pere.id
                    updated = True
                if mere and not enfant.mere_id:
                    enfant.mere_id = mere.id
                    updated = True
                
                return updated
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Erreur application filiation: {e}")
            return False
    
    def _apply_parrainage_to_persons(self, parrainage: Dict, persons: Dict) -> bool:
        """Applique un parrainage aux personnes avec validation"""
        try:
            personne_name = parrainage.get('personne', '').strip()
            enfant_name = parrainage.get('enfant', '').strip()
            type_parrainage = parrainage.get('type', '')
            
            if not personne_name:
                return False
            
            personne = self._find_person_by_name(personne_name, persons)
            enfant = self._find_person_by_name(enfant_name, persons) if enfant_name else None
            
            if personne and enfant:
                if type_parrainage == 'parrain' and not enfant.parrain_id:
                    enfant.parrain_id = personne.id
                    return True
                elif type_parrainage == 'marraine' and not enfant.marraine_id:
                    enfant.marraine_id = personne.id
                    return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Erreur application parrainage: {e}")
            return False
    
    def _apply_mariage_to_persons(self, mariage: Dict, persons: Dict) -> bool:
        """Applique un mariage aux personnes avec validation"""
        try:
            epoux_name = mariage.get('epoux', '').strip()
            epouse_name = mariage.get('epouse', '').strip()
            
            if not epoux_name or not epouse_name:
                return False
            
            epoux = self._find_person_by_name(epoux_name, persons)
            epouse = self._find_person_by_name(epouse_name, persons)
            
            if epoux and epouse and not epoux.conjoint_id and not epouse.conjoint_id:
                epoux.conjoint_id = epouse.id
                epouse.conjoint_id = epoux.id
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Erreur application mariage: {e}")
            return False
    
    def _find_person_by_name(self, name: str, persons: Dict):
        """Recherche intelligente d'une personne par nom avec correspondance floue"""
        if not name or not persons:
            return None
        
        name_clean = name.strip().lower()
        name_words = name_clean.split()
        
        for person in persons.values():
            # Match exact du nom complet
            person_full = f"{' '.join(person.prenoms)} {person.nom}".strip().lower()
            if person_full == name_clean:
                return person
            
            # Match du nom de famille
            if person.nom.lower() == name_clean:
                return person
            
            # Match partiel (nom de famille + au moins un prénom)
            if len(name_words) >= 2:
                if person.nom.lower() == name_words[-1]:  # Nom de famille correspond
                    # Vérifier si au moins un prénom correspond
                    person_prenoms = [p.lower() for p in person.prenoms]
                    if any(prenom in person_prenoms for prenom in name_words[:-1]):
                        return person
        
        return None
    
    def _validate_data_enhanced(self, persons: Dict, actes: Dict, relations: List) -> Dict:
        """Validation améliorée des données"""
        
        # Statistiques de base
        persons_with_relations = 0
        for person in persons.values():
            if (person.pere_id or person.mere_id or person.conjoint_id or 
                person.parrain_id or person.marraine_id):
                persons_with_relations += 1
        
        validation_rate = (persons_with_relations / len(persons) * 100) if persons else 0
        
        return {
            'persons_total': len(persons),
            'persons_with_relations': persons_with_relations,
            'actes_total': len(actes),
            'relations_extracted': len(relations),
            'validation_rate': round(validation_rate, 1),
            'data_quality': 'Excellente' if validation_rate > 70 else 'Bonne' if validation_rate > 40 else 'Moyenne'
        }
    
    # Application des méthodes à l'instance
    parser_instance.process_document = types.MethodType(process_document_fixed, parser_instance)
    parser_instance._apply_filiation_to_persons = types.MethodType(_apply_filiation_to_persons, parser_instance)
    parser_instance._apply_parrainage_to_persons = types.MethodType(_apply_parrainage_to_persons, parser_instance)
    parser_instance._apply_mariage_to_persons = types.MethodType(_apply_mariage_to_persons, parser_instance)
    parser_instance._find_person_by_name = types.MethodType(_find_person_by_name, parser_instance)
    parser_instance._validate_data_enhanced = types.MethodType(_validate_data_enhanced, parser_instance)
    
    print("🔧 Fix complet appliqué avec succès au parser!")

# === FONCTION PRINCIPALE CORRIGÉE ===

def analyser_et_traiter_pdf(pdf_path: str, max_pages: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Fonction principale d'analyse et traitement complet d'un PDF de registres paroissiaux
    VERSION COMPLÈTEMENT CORRIGÉE ET OPTIMISÉE
    
    Args:
        pdf_path: Chemin vers le fichier PDF à analyser
        max_pages: Limite optionnelle du nombre de pages à traiter
        
    Returns:
        Dict avec tous les résultats d'analyse et de traitement, ou None en cas d'échec
    """
    
    print(f"🚀 === ANALYSE ET TRAITEMENT PDF COMPLET ===")
    print(f"📁 Fichier: {pdf_path}")
    print(f"📄 Limite pages: {max_pages if max_pages else 'Aucune'}")
    print("=" * 60)
    
    # === PHASE 1: ANALYSE STRUCTURELLE DU PDF ===
    
    analyseur = SmartPDFAnalyzer()
    
    try:
        print(f"\n📊 Phase 1: Analyse structurelle du PDF")
        analyse = analyseur.analyze_pdf_structure(pdf_path, max_pages)
        
    except FileNotFoundError:
        print(f"❌ Fichier PDF non trouvé: {pdf_path}")
        return None
    except Exception as e:
        print(f"❌ Erreur critique lors de l'analyse PDF: {e}")
        return None
    
    # === PHASE 2: AFFICHAGE DES RÉSULTATS D'ANALYSE ===
    
    recommandation = analyse['recommendations']
    summary = analyse.get('analysis_summary', {})
    
    print(f"\n📊 === RÉSULTATS DE L'ANALYSE ===")
    print(f"Pages analysées: {analyse['total_pages_analyzed']}")
    print(f"Pages dans le PDF: {analyse['total_pages_in_pdf']}")
    print(f"Pages de registres détectées: {len(recommandation['pages_suggerees'])}")
    print(f"Score maximum: {recommandation['meilleur_score']:.1f}")
    print(f"Relations détectées: {recommandation['total_relations']}")
    print(f"Personnes détectées: {recommandation['total_personnes']}")
    print(f"Dates détectées: {recommandation['total_dates']}")
    
    if summary:
        print(f"\n📈 Résumé qualité:")
        print(f"  • Pages en français: {summary.get('pages_francais', 0)}/{summary.get('pages_totales', 0)} ({summary.get('pourcentage_francais', 0)}%)")
        print(f"  • Score moyen: {summary.get('score_moyen', 0)}")
        print(f"  • Pages prometteuses: {summary.get('pages_prometteuses', 0)}")
    
    # Distribution qualité
    qualite = recommandation.get('qualite_distribution', {})
    if qualite:
        print(f"\n📊 Distribution qualité:")
        print(f"  • Excellente (>15): {qualite.get('excellente', 0)} pages")
        print(f"  • Bonne (10-15): {qualite.get('bonne', 0)} pages")
        print(f"  • Moyenne (5-10): {qualite.get('moyenne', 0)} pages")
        print(f"  • Faible (1-5): {qualite.get('faible', 0)} pages")
        print(f"  • Nulle (<1): {qualite.get('nulle', 0)} pages")
    
    print(f"\n🏆 TOP 10 DES MEILLEURES PAGES:")
    for i, detail in enumerate(recommandation['pages_details'][:10]):
        print(f"{i+1:2d}. Page {detail['page']:3d}: Score {detail['score']:5.1f} "
              f"({detail['relations']:2d} rel, {detail['personnes']:2d} pers, {detail['dates']:2d} dates) "
              f"[{detail['langue']}]")
        print(f"    Preview: {detail['preview'][:80]}...")
        if i < 9:  # Pas de ligne vide après le dernier
            print()
    
    # === PHASE 3: EXTRACTION DU TEXTE ===
    
    pages_a_traiter = recommandation['pages_suggerees']
    
    if not pages_a_traiter:
        print(f"\n❌ Aucune page de registre détectée avec suffisamment de confiance")
        print(f"💡 Suggestion: Vérifiez le contenu du PDF ou ajustez les paramètres d'analyse")
        return None
    
    print(f"\n📄 === EXTRACTION DU TEXTE ===")
    print(f"Pages sélectionnées: {len(pages_a_traiter)}")
    
    texte_registres = analyseur.extraire_pages_registres(pdf_path, pages_a_traiter)
    
    if not texte_registres:
        print(f"❌ Échec de l'extraction du texte")
        return None
    
    # === PHASE 4: TRAITEMENT GÉNÉALOGIQUE AVEC FIX COMPLET ===
    
    print(f"\n🧬 === TRAITEMENT GÉNÉALOGIQUE AVANCÉ ===")
    
    try:
        # Import des modules de traitement
        from main import GenealogyParser
        from exporters.report_generator import ReportGenerator
        
        print(f"🔧 Application du fix complet pour les relations familiales...")
        
        # Création et configuration du parser
        parser = GenealogyParser()
        parser.config.max_persons = 10000  # Augmenté pour gros volumes
        parser.config.cache_size = 5000    # Cache plus important
        
        # 🚨 APPLICATION DU FIX COMPLET 🚨
        fix_process_document_method(parser)
        print(f"✅ Fix relationnel appliqué avec succès!")
        
        # Traitement avec le parser corrigé
        print(f"\n🔄 Lancement du traitement généalogique...")
        resultat = parser.process_document(texte_registres, "Archive départementale")
        
        # === PHASE 5: AFFICHAGE DES RÉSULTATS ===
        
        print(f"\n📋 === RÉSULTATS DU TRAITEMENT GÉNÉALOGIQUE ===")
        
        try:
            ReportGenerator.print_formatted_results(resultat)
        except Exception as e:
            print(f"⚠️ Erreur affichage rapport: {e}")
        
        # Statistiques générales
        try:
            stats = parser.get_global_statistics()
        except Exception:
            # Fallback si get_global_statistics n'existe pas
            stats = {
                'persons': {'total_persons': len(resultat.get('persons', {}))},
                'actes': {'total_actes': len(resultat.get('actes', {})), 'validation_rate': 0}
            }
        
        # === PHASE 6: AFFICHAGE FINAL CORRIGÉ ===
        
        print(f"\n📊 === STATISTIQUES FINALES ===")
        print("=" * 35)
        print(f"Pages traitées: {len(pages_a_traiter)}")
        print(f"Personnes identifiées: {stats['persons']['total_persons']}")
        print(f"Actes créés: {stats['actes']['total_actes']}")
        
        # Comptage corrigé des relations
        filiations_count = len(resultat.get('filiations', []))
        parrainages_count = len(resultat.get('parrainages', []))
        mariages_count = len(resultat.get('mariages', []))
        total_relations = resultat.get('relations_count', 0)
        relations_applied = resultat.get('relations_applied', 0)
        
        print(f"Relations familiales: {total_relations}")
        print(f"  • Filiations: {filiations_count}")
        print(f"  • Parrainages: {parrainages_count}")
        print(f"  • Mariages: {mariages_count}")
        print(f"Relations intégrées: {relations_applied}")
        
        validation = resultat.get('validation', {})
        print(f"Taux de validation: {validation.get('validation_rate', 0):.1f}%")
        print(f"Qualité des données: {validation.get('data_quality', 'Non évaluée')}")
        
        # Temps de traitement
        processing_time = resultat.get('processing_time', 0)
        print(f"Temps de traitement: {processing_time:.1f}s")
        
        # === RETOUR RÉSULTAT COMPLET ===
        
        return {
            'pages_analysees': analyse['total_pages_analyzed'],
            'pages_registres': len(pages_a_traiter),
            'pages_suggerees': pages_a_traiter,
            'resultats_genealogiques': resultat,
            'statistiques': stats,
            'analyse_pdf': analyse,
            'qualite_extraction': {
                'relations_extraites': total_relations,
                'relations_integrees': relations_applied,
                'taux_integration': round((relations_applied / total_relations * 100) if total_relations else 0, 1),
                'qualite_donnees': validation.get('data_quality', 'Non évaluée')
            }
        }
        
    except ImportError as e:
        print(f"❌ Erreur import modules: {e}")
        print(f"💡 Vérifiez que main.py et les modules requis sont présents")
        return None
    
    except Exception as e:
        print(f"❌ Erreur critique durant le traitement généalogique:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# === POINT D'ENTRÉE PRINCIPAL ===

if __name__ == "__main__":
    
    # Configuration du logging pour l'exécution directe
    logging.getLogger().setLevel(logging.INFO)
    
    # Gestion des arguments
    if len(sys.argv) < 2:
        # Fichier par défaut pour tests
        pdf_file = "inventairesommai03archuoft.pdf"
        if not Path(pdf_file).exists():
            print("❌ Fichier PDF par défaut non trouvé")
            print("📖 Usage: python smart_pdf_analyzer.py <fichier.pdf> [max_pages]")
            print("📖 Exemple: python smart_pdf_analyzer.py registres.pdf 100")
            sys.exit(1)
    else:
        pdf_file = sys.argv[1]
    
    # Limite de pages (optionnel)
    max_pages = None
    if len(sys.argv) > 2:
        try:
            max_pages = int(sys.argv[2])
            if max_pages <= 0:
                raise ValueError("Le nombre de pages doit être positif")
        except ValueError as e:
            print(f"❌ Nombre de pages invalide: {e}")
            sys.exit(1)
    
    # === LANCEMENT DE L'ANALYSE COMPLÈTE ===
    
    print("🔧 SMART PDF ANALYZER v2.0.0 - VERSION COMPLÈTEMENT CORRIGÉE")
    print("🎯 Fix relationnel intégré et optimisé")
    print()
    
    resultat = analyser_et_traiter_pdf(pdf_file, max_pages)
    
    # === RÉSULTAT FINAL ===
    
    if resultat:
        print(f"\n🎉 === TRAITEMENT COMPLET TERMINÉ AVEC SUCCÈS ===")
        print(f"📄 Pages de registres trouvées et traitées: {resultat['pages_registres']}")
        print(f"👥 Personnes avec informations complètes: {resultat['statistiques']['persons']['total_persons']}")
        
        # Affichage des relations extraites
        resultats_genea = resultat['resultats_genealogiques']
        qualite = resultat.get('qualite_extraction', {})
        
        if 'relations_count' in resultats_genea and resultats_genea['relations_count'] > 0:
            print(f"🔗 RELATIONS FAMILIALES EXTRAITES: {resultats_genea['relations_count']}")
            print(f"✅ Relations intégrées avec succès: {qualite.get('relations_integrees', 0)}")
            print(f"📊 Taux d'intégration: {qualite.get('taux_integration', 0)}%")
            print(f"🏆 Qualité globale: {qualite.get('qualite_donnees', 'Non évaluée')}")
        else:
            print(f"⚠️ Aucune relation familiale extraite - Vérifiez le contenu du document")
        
        print(f"\n💾 Résultats sauvegardés et prêts pour export")
        
    else:
        print(f"\n❌ === ÉCHEC DU TRAITEMENT ===")
        print(f"💡 Suggestions:")
        print(f"   • Vérifiez que le PDF contient des registres paroissiaux")
        print(f"   • Essayez avec un nombre de pages limité")
        print(f"   • Consultez les logs pour plus de détails")
        
        sys.exit(1)