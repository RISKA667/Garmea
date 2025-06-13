import re
import fitz
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import logging
from dataclasses import dataclass

@dataclass
class PageAnalysis:
    """
    Classe de données pour stocker les résultats de l'analyse d'une page PDF.
    
    Attributs:
        page_num (int): Numéro de la page analysée
        score_paroissial (float): Score indiquant la probabilité que la page contienne un registre paroissial
        langue (str): Langue détectée dans le texte
        contient_registre (bool): Indique si la page contient un registre paroissial
        indicateurs_trouvés (List[str]): Liste des motifs trouvés qui ont contribué au score
        texte_extrait (str): Extrait du texte de la page (limité à 300 caractères)
        longueur (int): Longueur totale du texte de la page
        relations_detectees (int): Nombre de relations familiales détectées
    """
    page_num: int
    score_paroissial: float
    langue: str
    contient_registre: bool
    indicateurs_trouvés: List[str]
    texte_extrait: str
    longueur: int
    relations_detectees: int

class SmartPDFAnalyzer:
    """Analyseur PDF optimisé pour la détection de registres paroissiaux historiques."""
    
    def __init__(self):
        """Initialise l'analyseur avec les motifs de recherche et la configuration."""
        self.logger = logging.getLogger(__name__)
        
        # Patterns pour détecter le contenu paroissial en français
        self.patterns_registres = {
            'actes_paroissiaux': [
                r'\bbapt[êe]mes?\b', r'\bbaptême\b', r'\bbapt\.\b',
                r'\bmariages?\b', r'\bmar\.\b', r'\bépouse\b',
                r'\binhumations?\b', r'\binh\.\b', r'\bdécès\b',
                r'\bnaissance\b', r'\benterrement\b'
            ],
            'relations_familiales': [
                r'\bfille\s+de\b', r'\bfils\s+de\b', r'\bfilz\s+de\b',
                r'\bépouse\s+de\b', r'\bfemme\s+de\b', r'\bveuve\s+de\b',
                r'\bparrain\b', r'\bmarraine\b', r'\bparr\.\b', r'\bmarr\.\b',
                r'\bpère\b', r'\bmère\b', r'\bet\s+de\b'
            ],
            'dates_historiques': [
                r'\bl\'an\s+de\s+grâce\s+1[4-8]\d{2}\b',
                r'\b1[4-8]\d{2}\b',  # Années 1400-1899
                r'\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+1[4-8]\d{2}',
                r'\d{1,2}e?\s+jour\s+de\s+\w+\s+1[4-8]\d{2}'
            ],
            'professions_titres': [
                r'\bcur[ée]s?\b', r'\bpr[êe]stres?\b',
                r'\b[ée]cuyers?\b', r'\b[ée]c\.\b',
                r'\bseigneurs?\b', r'\bsgr\b',
                r'\bsieurs?\b', r'\bsr\b',
                r'\bavocat\s+du\s+roi\b', r'\bconseiller\b',
                r'\bmarchand\b', r'\bnotaire\b'
            ],
            'lieux_religieux': [
                r'\béglise\b', r'\bchapelle\b', r'\bparoisse\b',
                r'\bbénéfice\b', r'\bautel\b', r'\bchœur\b'
            ],
            'structure_registre': [
                r'—\s*«', r'»\s*—',  # Guillemets typiques
                r'\d{4}-\d{4}\.\s*—',  # Format période
                r'Bapt\.,\s*mar\.,\s*inh\.'  # Abréviations typiques
            ]
        }
        
        # Patterns pour exclure les pages non pertinentes
        self.patterns_negatifs = [
            r'\buniversity\b', r'\blibrary\b', r'\bdepartment\b',
            r'\beducation\b', r'\bpurchased\b', r'\bfor\s+the\b',
            r'\btable\s+of\s+contents\b', r'\bindex\b', r'\bpreface\b',
            r'\bintroduction\b', r'\bchapter\b', r'\bsection\b'
        ]
    
    def analyser_pdf_complet(self, pdf_path: str, max_pages: int = None) -> Dict:
        """
        Analyse un fichier PDF complet pour détecter les pages contenant des registres paroissiaux.
        
        Args:
            pdf_path (str): Chemin vers le fichier PDF à analyser
            max_pages (int, optional): Nombre maximum de pages à analyser
            
        Returns:
            Dict: Dictionnaire contenant les résultats de l'analyse
        """
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            if max_pages:
                total_pages = min(total_pages, max_pages)
            
            print(f"Analyse de {total_pages} pages pour détecter les registres paroissiaux...")
            
            analyses = []
            pages_pertinentes = []
            
            for page_num in range(total_pages):
                if page_num % 50 == 0:
                    print(f"Progression: {page_num}/{total_pages} pages analysées...")
                
                page = doc[page_num]
                texte = page.get_text()
                
                analyse = self._analyser_page(page_num + 1, texte)
                analyses.append(analyse)
                
                if analyse.contient_registre:
                    pages_pertinentes.append(analyse)
            
            doc.close()
            
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
        """
        Analyse une page individuelle pour détecter la présence de registres paroissiaux.
        
        Args:
            page_num (int): Numéro de la page
            texte (str): Texte extrait de la page
            
        Returns:
            PageAnalysis: Objet contenant les résultats de l'analyse
        """
        if not texte or len(texte.strip()) < 50:
            return PageAnalysis(
                page_num=page_num,
                score_paroissial=0.0,
                langue='indéterminée',
                contient_registre=False,
                indicateurs_trouvés=[],
                texte_extrait="",
                longueur=0,
                relations_detectees=0
            )
        
        texte_lower = texte.lower()
        indicateurs_trouvés = []
        score = 0.0
        relations_count = 0
        
        # Calcul du score basé sur les motifs positifs
        for categorie, patterns in self.patterns_registres.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, texte_lower))
                if matches > 0:
                    if categorie == 'actes_paroissiaux':
                        score += matches * 3.0
                    elif categorie == 'relations_familiales':
                        score += matches * 4.0
                        relations_count += matches
                    elif categorie == 'dates_historiques':
                        score += matches * 2.0
                    elif categorie == 'structure_registre':
                        score += matches * 5.0
                    else:
                        score += matches * 1.0
                    
                    indicateurs_trouvés.append(f"{categorie}:{pattern}({matches})")
        
        # Application des pénalités pour motifs négatifs
        for pattern in self.patterns_negatifs:
            matches = len(re.findall(pattern, texte_lower))
            if matches > 0:
                score -= matches * 2.0
                indicateurs_trouvés.append(f"NÉGATIF:{pattern}")
        
        # Détection de la langue
        langue = self._detecter_langue(texte_lower)
        if langue != 'français':
            score *= 0.5
        
        # Bonus pour longueur appropriée
        if 200 <= len(texte) <= 5000:
            score += 1.0
        elif len(texte) > 5000:
            score += 2.0
        
        # Décision finale
        contient_registre = (score >= 4.0 and 
                           langue == 'français' and
                           len(texte.strip()) > 100)
        
        return PageAnalysis(
            page_num=page_num,
            score_paroissial=score,
            langue=langue,
            contient_registre=contient_registre,
            indicateurs_trouvés=indicateurs_trouvés,
            texte_extrait=texte[:300] if contient_registre else "",
            longueur=len(texte),
            relations_detectees=relations_count
        )
    
    def _detecter_langue(self, texte: str) -> str:
        """
        Détecte la langue du texte avec un focus sur le français historique.
        
        Args:
            texte (str): Texte à analyser
            
        Returns:
            str: Langue détectée ('français', 'indéterminée')
        """
        mots_francais_registres = [
            'le', 'la', 'les', 'de', 'du', 'des', 'et', 'dans', 'avec',
            'pour', 'par', 'sur', 'sous', 'sans', 'son', 'sa', 'ses',
            'qui', 'que', 'dont', 'où', 'ont', 'est', 'sont'
        ]
        
        count_francais = sum(len(re.findall(rf'\b{mot}\b', texte)) for mot in mots_francais_registres)
        
        mots_anglais = ['the', 'and', 'or', 'in', 'on', 'with', 'for', 'of', 'to', 'is', 'are']
        count_anglais = sum(len(re.findall(rf'\b{mot}\b', texte)) for mot in mots_anglais)
        
        mots_latin = ['sancti', 'domini', 'anno', 'die', 'mensis']
        count_latin = sum(len(re.findall(rf'\b{mot}\b', texte)) for mot in mots_latin)
        
        if count_francais > max(count_anglais, count_latin) * 1.5:
            return 'français'
        return 'indéterminée'
    
    def _generer_recommandation(self, pages_pertinentes: List[PageAnalysis]) -> Dict:
        """
        Génère une recommandation d'action basée sur les pages détectées.
        
        Args:
            pages_pertinentes (List[PageAnalysis]): Liste des pages détectées
            
        Returns:
            Dict: Dictionnaire contenant la recommandation et les détails
        """
        if not pages_pertinentes:
            return {
                'action': 'aucune_page_trouvee',
                'message': "Aucune page contenant des registres paroissiaux détectée",
                'pages_suggérées': []
            }
        
        pages_triees = sorted(pages_pertinentes, 
                             key=lambda p: (p.score_paroissial, p.relations_detectees), 
                             reverse=True)
        
        total_pages = len(pages_pertinentes)
        pages_a_traiter = [p.page_num for p in pages_triees]
        
        if total_pages > 500:
            print(f"Attention: {total_pages} pages détectées, limitation à 500 pour performance")
            pages_a_traiter = pages_a_traiter[:500]
        
        return {
            'action': 'extraire_toutes_pages',
            'message': f"{total_pages} pages avec registres détectées - TRAITEMENT COMPLET",
            'pages_suggérées': pages_a_traiter,
            'meilleur_score': pages_triees[0].score_paroissial,
            'total_relations': sum(p.relations_detectees for p in pages_pertinentes),
            'pages_details': [
                {
                    'page': p.page_num,
                    'score': p.score_paroissial,
                    'langue': p.langue,
                    'relations': p.relations_detectees,
                    'preview': p.texte_extrait[:100] + "..." if len(p.texte_extrait) > 100 else p.texte_extrait
                }
                for p in pages_triees[:10]
            ]
        }
    
    def extraire_pages_registres(self, pdf_path: str, pages_a_extraire: List[int]) -> str:
        """
        Extrait le texte des pages spécifiées avec optimisation mémoire.
        
        Args:
            pdf_path (str): Chemin vers le fichier PDF
            pages_a_extraire (List[int]): Liste des numéros de pages à extraire
            
        Returns:
            str: Texte concaténé des pages extraites
        """
        texte_complet = ""
        
        try:
            doc = fitz.open(pdf_path)
            
            print(f"Extraction de {len(pages_a_extraire)} pages de registres...")
            
            batch_size = 50
            for i in range(0, len(pages_a_extraire), batch_size):
                batch = pages_a_extraire[i:i+batch_size]
                
                for page_num in batch:
                    if page_num <= len(doc):
                        page = doc[page_num - 1]
                        texte_page = page.get_text()
                        
                        if texte_page.strip():
                            texte_complet += f"\n--- PAGE {page_num} ---\n"
                            texte_complet += texte_page + "\n"
                
                if len(pages_a_extraire) > 100 and i % 100 == 0:
                    print(f"Progression extraction: {i+batch_size}/{len(pages_a_extraire)} pages")
            
            doc.close()
            
            print(f"Extraction terminée: {len(texte_complet):,} caractères")
            return texte_complet
            
        except Exception as e:
            self.logger.error(f"Erreur extraction pages: {e}")
            return ""

def analyser_et_traiter_pdf(pdf_path: str, max_pages_analyse: int = None):
    """
    Fonction principale pour analyser et traiter un fichier PDF complet.
    
    Args:
        pdf_path (str): Chemin vers le fichier PDF
        max_pages_analyse (int, optional): Nombre maximum de pages à analyser
        
    Returns:
        Optional[Dict]: Résultats de l'analyse ou None en cas d'erreur
    """
    print(f"ANALYSE INTELLIGENTE DU PDF")
    print(f"Fichier: {pdf_path}")
    print("=" * 60)
    
    analyseur = SmartPDFAnalyzer()
    
    # Phase 1: Analyse complète du PDF
    print("Phase 1: Analyse des pages pour détecter les registres...")
    analyse = analyseur.analyser_pdf_complet(pdf_path, max_pages_analyse)
    
    if 'erreur' in analyse:
        print(f"Erreur: {analyse['erreur']}")
        return None
    
    # Affichage des résultats
    print(f"\nRESULTATS DE L'ANALYSE")
    print("=" * 30)
    print(f"Pages analysées: {analyse['total_pages_analysees']}")
    print(f"Pages avec registres: {analyse['pages_avec_registres']}")
    
    recommandation = analyse['recommandation']
    
    if recommandation['action'] == 'aucune_page_trouvee':
        print(f"{recommandation['message']}")
        
        # Debug: affichage des premières pages
        print(f"\nDEBUG - Contenu des premières pages:")
        for i, analysis in enumerate(analyse['toutes_analyses'][:3]):
            print(f"Page {analysis.page_num}: Score={analysis.score_paroissial:.1f}, Langue={analysis.langue}")
            if analysis.texte_extrait:
                print(f"Extrait: {analysis.texte_extrait[:100]}...")
        
        return None
    
    # Affichage des meilleures pages
    print(f"\n{recommandation['message']}")
    print(f"Meilleur score: {recommandation['meilleur_score']:.1f}")
    print(f"Relations familiales détectées: {recommandation['total_relations']}")
    print(f"\nTOP 10 DES MEILLEURES PAGES:")
    
    for detail in recommandation['pages_details']:
        print(f"Page {detail['page']}: Score {detail['score']:.1f} ({detail['langue']}) - {detail['relations']} relations")
        print(f"Preview: {detail['preview']}")
        print()
    
    # Extraction des pages détectées
    pages_a_traiter = recommandation['pages_suggérées']
    
    print(f"EXTRACTION ET TRAITEMENT COMPLET")
    print("=" * 40)
    print(f"Pages à traiter: {len(pages_a_traiter)}")
    
    # Extraction du texte
    texte_registres = analyseur.extraire_pages_registres(pdf_path, pages_a_traiter)
    
    if not texte_registres:
        print("Aucun texte extrait")
        return None
    
    # Traitement généalogique
    print(f"\nTRAITEMENT GENEALOGIQUE COMPLET")
    print("=" * 35)
    
    try:
        from main import GenealogyParser
        from exporters.report_generator import ReportGenerator
        
        parser = GenealogyParser()
        parser.config.max_persons = 5000
        parser.config.cache_size = 2000
        
        resultat = parser.process_document(texte_registres, "Archive départementale")
        
        print(f"\nRESULTATS DU PARSING COMPLET")
        print("=" * 30)
        ReportGenerator.print_formatted_results(resultat)
        
        stats = parser.get_global_statistics()
        print(f"\nSTATISTIQUES FINALES")
        print("=" * 25)
        print(f"Pages traitées: {len(pages_a_traiter)}")
        print(f"Personnes identifiées: {stats['persons']['total_persons']}")
        print(f"Actes créés: {stats['actes']['total_actes']}")
        print(f"Relations familiales: {len(resultat.get('filiations', []))}")
        print(f"Parrainages: {len(resultat.get('parrainages', []))}")
        print(f"Taux de validation: {stats['actes'].get('validation_rate', 0):.1f}%")
        print(f"Homonymes détectés: {stats['persons'].get('homonym_groups', 0)}")
        
        return {
            'pages_analysees': analyse['total_pages_analysees'],
            'pages_registres': len(pages_a_traiter),
            'resultats_genealogiques': resultat,
            'statistiques': stats
        }
        
    except Exception as e:
        print(f"Erreur traitement généalogique: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        # Test avec fichier par défaut
        pdf_file = "inventairesommai03archuoft.pdf"
        if not Path(pdf_file).exists():
            print("Fichier PDF non trouvé")
            print("Usage: python smart_pdf_analyzer.py <fichier.pdf> [max_pages]")
            sys.exit(1)
    else:
        pdf_file = sys.argv[1]
    
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    # Lancement de l'analyse
    resultat = analyser_et_traiter_pdf(pdf_file, max_pages)
    
    if resultat:
        print(f"\nTRAITEMENT COMPLET TERMINE AVEC SUCCES!")
        print(f"Pages de registres trouvées et traitées: {resultat['pages_registres']}")
        print(f"Personnes avec informations complètes: {resultat['statistiques']['persons']['total_persons']}")
    else:
        print(f"\nAucun registre paroissial trouvé dans ce document")