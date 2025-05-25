#!/usr/bin/env python3
"""
Analyseur PDF intelligent pour détecter et extraire automatiquement 
les pages contenant des registres paroissiaux français
"""

import re
import fitz  # PyMuPDF
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import logging
from dataclasses import dataclass

@dataclass
class PageAnalysis:
    """Résultat d'analyse d'une page"""
    page_num: int
    score_paroissial: float
    langue: str
    contient_registre: bool
    indicateurs_trouvés: List[str]
    texte_extrait: str
    longueur: int

class SmartPDFAnalyzer:
    """Analyseur PDF intelligent pour registres paroissiaux"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Patterns pour détecter du contenu paroissial français
        self.patterns_registres = {
            'actes_paroissiaux': [
                r'\bbapt[êe]mes?\b', r'\bbaptême\b', r'\bbapt\.\b',
                r'\bmariages?\b', r'\bmar\.\b', r'\bépouse\b',
                r'\binhumations?\b', r'\binh\.\b', r'\bdécès\b',
                r'\bnaissance\b', r'\benterrement\b'
            ],
            'dates_historiques': [
                r'\bl\'an\s+de\s+grâce\s+1[4-8]\d{2}\b',
                r'\b1[4-8]\d{2}\b',  # Années 1400-1899
                r'\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+1[4-8]\d{2}',
                r'\d{1,2}e?\s+jour\s+de\s+\w+\s+1[4-8]\d{2}'
            ],
            'relations_familiales': [
                r'\bfille\s+de\b', r'\bfils\s+de\b',
                r'\bépouse\s+de\b', r'\bmari\s+de\b',
                r'\bveuve\s+de\b', r'\bparrain\b', r'\bmarraine\b',
                r'\bpère\b', r'\bmère\b'
            ],
            'professions_titres': [
                r'\bcur[ée]s?\b', r'\bpr[êe]stres?\b',
                r'\b[ée]cuyers?\b', r'\b[ée]c\.\b',
                r'\bseigneurs?\b', r'\bsgr\b',
                r'\bsieurs?\b', r'\bsr\b',
                r'\bavocat\s+du\s+roi\b', r'\bconseiller\b'
            ],
            'lieux_religieux': [
                r'\béglise\b', r'\bchapelle\b', r'\bparoisse\b',
                r'\bbénéfice\b', r'\bautel\b', r'\bchœur\b'
            ],
            'structure_registre': [
                r'—\s*«', r'»\s*—',  # Guillemets typiques des registres
                r'\d{4}-\d{4}\.\s*—',  # Format période : "1643-1687. —"
                r'Bapt\.,\s*mar\.,\s*inh\.'  # Abréviations typiques
            ]
        }
        
        # Patterns négatifs (indiquent que ce n'est PAS un registre)
        self.patterns_negatifs = [
            r'\buniversity\b', r'\blibrary\b', r'\bdepartment\b',
            r'\beducation\b', r'\bpurchased\b', r'\bfor\s+the\b',
            r'\btable\s+of\s+contents\b', r'\bindex\b', r'\bpreface\b',
            r'\bintroduction\b', r'\bchapter\b', r'\bsection\b'
        ]
    
    def analyser_pdf_complet(self, pdf_path: str, max_pages: int = None) -> Dict:
        """Analyse complète du PDF pour identifier les pages de registres"""
        
        try:
            # Ouvrir le PDF
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            if max_pages:
                total_pages = min(total_pages, max_pages)
            
            print(f"📖 Analyse de {total_pages} pages pour détecter les registres paroissiaux...")
            
            # Analyser chaque page
            analyses = []
            pages_pertinentes = []
            
            for page_num in range(total_pages):
                if page_num % 50 == 0:
                    print(f"   Progression: {page_num}/{total_pages} pages analysées...")
                
                page = doc[page_num]
                texte = page.get_text()
                
                # Analyser cette page
                analyse = self._analyser_page(page_num + 1, texte)
                analyses.append(analyse)
                
                # Si la page contient un registre, l'ajouter
                if analyse.contient_registre:
                    pages_pertinentes.append(analyse)
            
            doc.close()
            
            # Résumé de l'analyse
            resultat = {
                'pdf_path': pdf_path,
                'total_pages_analysees': total_pages,
                'pages_avec_registres': len(pages_pertinentes),
                'pages_pertinentes': pages_pertinentes,
                'toutes_analyses': analyses,
                'recommandation': self._generer_recommandation(pages_pertinentes)
            }
            
            return resultat
            
        except Exception as e:
            self.logger.error(f"Erreur analyse PDF: {e}")
            return {'erreur': str(e)}
    
    def _analyser_page(self, page_num: int, texte: str) -> PageAnalysis:
        """Analyse une page individuelle"""
        
        if not texte or len(texte.strip()) < 50:
            return PageAnalysis(
                page_num=page_num,
                score_paroissial=0.0,
                langue='indéterminée',
                contient_registre=False,
                indicateurs_trouvés=[],
                texte_extrait="",
                longueur=0
            )
        
        texte_lower = texte.lower()
        indicateurs_trouvés = []
        score = 0.0
        
        # Calculer le score positif
        for categorie, patterns in self.patterns_registres.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, texte_lower))
                if matches > 0:
                    if categorie == 'actes_paroissiaux':
                        score += matches * 3.0  # Poids fort
                    elif categorie == 'dates_historiques':
                        score += matches * 2.0
                    elif categorie == 'structure_registre':
                        score += matches * 4.0  # Poids très fort
                    else:
                        score += matches * 1.0
                    
                    indicateurs_trouvés.append(f"{categorie}:{pattern}")
        
        # Appliquer les pénalités négatives
        for pattern in self.patterns_negatifs:
            matches = len(re.findall(pattern, texte_lower))
            if matches > 0:
                score -= matches * 2.0
                indicateurs_trouvés.append(f"NÉGATIF:{pattern}")
        
        # Détecter la langue
        langue = self._detecter_langue(texte_lower)
        if langue != 'français':
            score *= 0.5  # Pénalité si pas français
        
        # Décision : contient un registre ?
        contient_registre = (score >= 5.0 and 
                           langue == 'français' and
                           len(texte.strip()) > 200)
        
        return PageAnalysis(
            page_num=page_num,
            score_paroissial=score,
            langue=langue,
            contient_registre=contient_registre,
            indicateurs_trouvés=indicateurs_trouvés,
            texte_extrait=texte[:500] if contient_registre else "",
            longueur=len(texte)
        )
    
    def _detecter_langue(self, texte: str) -> str:
        """Détection simple de langue française"""
        
        # Mots français très caractéristiques des registres paroissiaux
        mots_francais_registres = [
            'le', 'la', 'les', 'de', 'du', 'des', 'et', 'dans', 'avec',
            'pour', 'par', 'sur', 'sous', 'sans', 'son', 'sa', 'ses'
        ]
        
        # Compter les occurrences
        count_francais = sum(len(re.findall(rf'\b{mot}\b', texte)) for mot in mots_francais_registres)
        
        # Mots anglais typiques
        mots_anglais = ['the', 'and', 'or', 'in', 'on', 'with', 'for', 'of', 'to']
        count_anglais = sum(len(re.findall(rf'\b{mot}\b', texte)) for mot in mots_anglais)
        
        if count_francais > count_anglais * 2:
            return 'français'
        elif count_anglais > count_francais * 2:
            return 'anglais'
        else:
            return 'indéterminée'
    
    def _generer_recommandation(self, pages_pertinentes: List[PageAnalysis]) -> Dict:
        """Génère une recommandation basée sur l'analyse"""
        
        if not pages_pertinentes:
            return {
                'action': 'aucune_page_trouvee',
                'message': "Aucune page contenant des registres paroissiaux détectée",
                'pages_suggérées': []
            }
        
        # Trier par score décroissant
        pages_triees = sorted(pages_pertinentes, key=lambda p: p.score_paroissial, reverse=True)
        
        # Prendre les meilleures pages
        meilleures_pages = pages_triees[:20]  # Max 20 pages
        
        return {
            'action': 'extraire_pages',
            'message': f"{len(pages_pertinentes)} pages avec registres détectées",
            'pages_suggérées': [p.page_num for p in meilleures_pages],
            'meilleur_score': pages_triees[0].score_paroissial,
            'pages_details': [
                {
                    'page': p.page_num,
                    'score': p.score_paroissial,
                    'langue': p.langue,
                    'preview': p.texte_extrait[:100] + "..." if len(p.texte_extrait) > 100 else p.texte_extrait
                }
                for p in meilleures_pages[:5]  # Détails des 5 meilleures
            ]
        }
    
    def extraire_pages_registres(self, pdf_path: str, pages_a_extraire: List[int]) -> str:
        """Extrait le texte des pages spécifiées"""
        
        texte_complet = ""
        
        try:
            doc = fitz.open(pdf_path)
            
            print(f"📝 Extraction de {len(pages_a_extraire)} pages de registres...")
            
            for page_num in pages_a_extraire:
                if page_num <= len(doc):
                    page = doc[page_num - 1]  # fitz utilise index 0
                    texte_page = page.get_text()
                    
                    if texte_page.strip():
                        texte_complet += f"\n--- PAGE {page_num} ---\n"
                        texte_complet += texte_page + "\n"
            
            doc.close()
            
            print(f"✅ Extraction terminée: {len(texte_complet)} caractères")
            return texte_complet
            
        except Exception as e:
            self.logger.error(f"Erreur extraction pages: {e}")
            return ""

def analyser_et_traiter_pdf(pdf_path: str, max_pages_analyse: int = None):
    """Fonction principale : analyse et traitement automatique"""
    
    print(f"🔍 ANALYSE INTELLIGENTE DU PDF")
    print(f"Fichier: {pdf_path}")
    print("=" * 60)
    
    # Initialiser l'analyseur
    analyseur = SmartPDFAnalyzer()
    
    # 1. Analyser le PDF complet
    print("Phase 1: Analyse des pages pour détecter les registres...")
    analyse = analyseur.analyser_pdf_complet(pdf_path, max_pages_analyse)
    
    if 'erreur' in analyse:
        print(f"❌ Erreur: {analyse['erreur']}")
        return None
    
    # 2. Afficher les résultats de l'analyse
    print(f"\n📊 RÉSULTATS DE L'ANALYSE")
    print("=" * 30)
    print(f"Pages analysées: {analyse['total_pages_analysees']}")
    print(f"Pages avec registres: {analyse['pages_avec_registres']}")
    
    recommandation = analyse['recommandation']
    
    if recommandation['action'] == 'aucune_page_trouvee':
        print(f"❌ {recommandation['message']}")
        
        # Montrer quelques pages d'exemple pour debug
        print(f"\n🔍 DEBUG - Contenu des premières pages:")
        for i, analysis in enumerate(analyse['toutes_analyses'][:3]):
            print(f"  Page {analysis.page_num}: Score={analysis.score_paroissial:.1f}, Langue={analysis.langue}")
            if analysis.texte_extrait:
                print(f"    Extrait: {analysis.texte_extrait[:100]}...")
        
        return None
    
    # 3. Montrer les meilleures pages trouvées
    print(f"\n✅ {recommandation['message']}")
    print(f"Meilleur score: {recommandation['meilleur_score']:.1f}")
    print(f"\n🎯 TOP 5 DES MEILLEURES PAGES:")
    
    for detail in recommandation['pages_details']:
        print(f"  📄 Page {detail['page']}: Score {detail['score']:.1f} ({detail['langue']})")
        print(f"     Preview: {detail['preview']}")
        print()
    
    # 4. Demander confirmation ou procéder automatiquement
    pages_a_traiter = recommandation['pages_suggérées']
    
    print(f"🚀 EXTRACTION ET TRAITEMENT")
    print("=" * 35)
    print(f"Pages sélectionnées: {pages_a_traiter[:10]}..." if len(pages_a_traiter) > 10 else f"Pages sélectionnées: {pages_a_traiter}")
    
    # 5. Extraire le texte
    texte_registres = analyseur.extraire_pages_registres(pdf_path, pages_a_traiter)
    
    if not texte_registres:
        print("❌ Aucun texte extrait")
        return None
    
    # 6. Traiter avec le parser généalogique
    print(f"\n⚙️  TRAITEMENT GÉNÉALOGIQUE")
    print("=" * 30)
    
    try:
        from main import GenealogyParser
        from exporters.report_generator import ReportGenerator
        
        parser = GenealogyParser()
        resultat = parser.process_document(texte_registres, "Archive départementale")
        
        print(f"\n📋 RÉSULTATS DU PARSING")
        print("=" * 25)
        ReportGenerator.print_formatted_results(resultat)
        
        # Statistiques
        stats = parser.get_global_statistics()
        print(f"\n📊 STATISTIQUES FINALES")
        print("=" * 25)
        print(f"Pages traitées: {len(pages_a_traiter)}")
        print(f"Personnes identifiées: {stats['persons']['total_persons']}")
        print(f"Actes créés: {stats['actes']['total_actes']}")
        print(f"Relations familiales: {len(resultat.get('filiations', []))}")
        print(f"Parrainages: {len(resultat.get('parrainages', []))}")
        
        return {
            'pages_analysees': analyse['total_pages_analysees'],
            'pages_registres': len(pages_a_traiter),
            'resultats_genealogiques': resultat,
            'statistiques': stats
        }
        
    except Exception as e:
        print(f"❌ Erreur traitement généalogique: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        # Test avec le fichier par défaut
        pdf_file = "inventairesommai03archuoft.pdf"
        if not Path(pdf_file).exists():
            print("❌ Fichier PDF non trouvé")
            print("Usage: python smart_pdf_analyzer.py <fichier.pdf> [max_pages]")
            sys.exit(1)
    else:
        pdf_file = sys.argv[1]
    
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    # Lancer l'analyse intelligente
    resultat = analyser_et_traiter_pdf(pdf_file, max_pages)
    
    if resultat:
        print(f"\n🎉 TRAITEMENT TERMINÉ AVEC SUCCÈS!")
        print(f"Pages de registres trouvées et traitées: {resultat['pages_registres']}")
    else:
        print(f"\n❌ Aucun registre paroissial trouvé dans ce document")