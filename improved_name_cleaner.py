#!/usr/bin/env python3
"""
Améliorateur de noms avec correction des erreurs OCR et nettoyage des titres
"""

import re
import sys
import os
from pathlib import Path

# Ajouter le répertoire au PATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class NameCleaner:
    """Nettoyeur de noms avec corrections OCR et suppression des titres parasites"""
    
    def __init__(self):
        # Corrections OCR communes
        self.ocr_corrections = {
            # Lettres mal reconnues
            'ii': 'i',
            'iie': 'lle', 
            'iii': 'ill',
            'rn': 'm',
            'cl': 'd',
            'ri': 'n',
            'vv': 'w',
            
            # Corrections spécifiques vues
            'Leiiueux': 'Lelieux',
            'Cliarles': 'Charles', 
            'Heniy': 'Henry',
            'Satïrey': 'Saffrey',
            'iblanci': 'Blanche',
            'Hélèner': 'Hélène',
            'Prenpain': 'Prepain',
            'Desprès': 'Després',
            'Heiroult': 'Héroult',
            'Crevai': 'Crevail',
        }
        
        # Titres à supprimer en début de nom
        self.titres_a_supprimer = [
            r'^honnête\s+femme\s+',
            r'^damoiselle\s+',
            r'^demoiselle\s+',
            r'^noble\s+homme\s+',
            r'^noble\s+dame\s+',
            r'^maître\s+',
            r'^messire\s+',
            r'^sieur\s+',
            r'^seigneur\s+',
            r'^écuyer\s+',
            r'^veuve\s+de\s+\w+\s+',
        ]
    
    def clean_name(self, nom_complet: str) -> str:
        """Nettoie un nom complet des erreurs OCR et titres parasites"""
        
        if not nom_complet or len(nom_complet) < 3:
            return nom_complet
        
        # Étape 1: Corrections OCR
        nom_nettoye = self._correct_ocr_errors(nom_complet)
        
        # Étape 2: Suppression des titres
        nom_nettoye = self._remove_titles(nom_nettoye)
        
        # Étape 3: Nettoyage final
        nom_nettoye = self._final_cleanup(nom_nettoye)
        
        return nom_nettoye
    
    def _correct_ocr_errors(self, nom: str) -> str:
        """Corrige les erreurs OCR communes"""
        
        nom_corrige = nom
        
        # Corrections spécifiques d'abord
        for erreur, correction in self.ocr_corrections.items():
            nom_corrige = nom_corrige.replace(erreur, correction)
        
        # Corrections de patterns
        # Doubles lettres erronées
        nom_corrige = re.sub(r'([a-z])\1{2,}', r'\1\1', nom_corrige)  # iii -> ii
        
        # Majuscules en milieu de mot (souvent OCR)
        nom_corrige = re.sub(r'([a-z])([A-Z])([a-z])', r'\1\2\3', nom_corrige)
        
        return nom_corrige
    
    def _remove_titles(self, nom: str) -> str:
        """Supprime les titres en début de nom"""
        
        nom_sans_titre = nom
        
        for pattern in self.titres_a_supprimer:
            nom_sans_titre = re.sub(pattern, '', nom_sans_titre, flags=re.IGNORECASE)
        
        return nom_sans_titre.strip()
    
    def _final_cleanup(self, nom: str) -> str:
        """Nettoyage final du nom"""
        
        # Supprimer espaces multiples
        nom = re.sub(r'\s+', ' ', nom)
        
        # Supprimer caractères parasites en début/fin
        nom = nom.strip(' .,;:-_')
        
        # Capitaliser correctement
        if nom:
            mots = nom.split()
            mots_corriges = []
            
            for mot in mots:
                if len(mot) > 0:
                    # Garder les particules en minuscules
                    if mot.lower() in ['de', 'du', 'des', 'la', 'le', 'les']:
                        mots_corriges.append(mot.lower())
                    else:
                        mots_corriges.append(mot.capitalize())
            
            nom = ' '.join(mots_corriges)
        
        return nom

def corriger_personnes_extraites():
    """Corrige les personnes déjà extraites et relance le traitement"""
    
    print("🧹 CORRECTION DES NOMS EXTRAITS")
    print("=" * 35)
    
    # Noms problématiques détectés dans les logs
    noms_problematiques = [
        "honnête femme Anne Torcapel",
        "damoiselle iblanci Le Maistre", 
        "Marie Leiiueux",
        "Cliarles Chalopin",
        "Heniy Baudart",
        "Hélèner de La Ménardière",
        "Guillaume Satïrey",
        "Jeanne Desprès",
    ]
    
    cleaner = NameCleaner()
    
    print("🔧 Exemples de corrections :")
    for nom_problematique in noms_problematiques:
        nom_corrige = cleaner.clean_name(nom_problematique)
        print(f"  '{nom_problematique}' → '{nom_corrige}'")
    
    return cleaner

def relancer_traitement_avec_corrections():
    """Relance le traitement avec les corrections de noms"""
    
    print(f"\n🚀 RELANCE AVEC CORRECTIONS DE NOMS")
    print("=" * 40)
    
    try:
        # Utiliser les pages déjà identifiées comme bonnes
        bonnes_pages = [314, 258, 118, 301, 577, 471, 304, 326, 69, 400]
        
        # Extraire le contenu
        from smart_pdf_analyzer import SmartPDFAnalyzer
        
        analyseur = SmartPDFAnalyzer()
        pdf_file = "inventairesommai03archuoft.pdf"
        
        if not Path(pdf_file).exists():
            print(f"❌ PDF non trouvé: {pdf_file}")
            return False
        
        print(f"📝 Extraction du contenu des {len(bonnes_pages)} meilleures pages...")
        texte_registres = analyseur.extraire_pages_registres(pdf_file, bonnes_pages)
        
        if not texte_registres:
            print("❌ Aucun texte extrait")
            return False
        
        print(f"✅ Extraction réussie: {len(texte_registres)} caractères")
        
        # Traitement généalogique avec nettoyage des noms
        print(f"\n⚙️  TRAITEMENT AVEC CORRECTION DES NOMS")
        print("=" * 45)
        
        # Patcher temporairement le name_extractor pour appliquer les corrections
        from parsers.name_extractor import NameExtractor
        
        # Créer le cleaner
        cleaner = NameCleaner()
        
        # Patcher la méthode d'extraction
        original_extract_method = NameExtractor.extract_complete_names
        
        def extract_with_cleaning(self, text):
            """Version avec nettoyage des noms"""
            # Appeler la méthode originale
            persons = original_extract_method(self, text)
            
            # Nettoyer chaque nom
            for person in persons:
                if 'nom_complet' in person:
                    original_name = person['nom_complet']
                    cleaned_name = cleaner.clean_name(original_name)
                    
                    if cleaned_name != original_name:
                        print(f"    CORRECTION: '{original_name}' → '{cleaned_name}'")
                        person['nom_complet'] = cleaned_name
                        
                        # Mettre à jour prénom et nom
                        if ' ' in cleaned_name:
                            parts = cleaned_name.split(' ', 1)
                            person['prenom'] = parts[0]
                            person['nom'] = parts[1]
                        else:
                            person['prenom'] = cleaned_name
                            person['nom'] = "Inconnu"
            
            return persons
        
        # Appliquer le patch
        NameExtractor.extract_complete_names = extract_with_cleaning
        
        # Traitement principal
        from main import GenealogyParser
        from exporters.report_generator import ReportGenerator
        
        parser = GenealogyParser()
        resultat = parser.process_document(texte_registres, "Archives du Calvados")
        
        print(f"\n🎉 RÉSULTATS AVEC NOMS CORRIGÉS")
        print("=" * 35)
        ReportGenerator.print_formatted_results(resultat)
        
        # Statistiques finales
        stats = parser.get_global_statistics()
        print(f"\n📊 STATISTIQUES FINALES")
        print("=" * 25)
        print(f"Personnes identifiées: {stats['persons']['total_persons']}")
        print(f"Actes créés: {stats['actes']['total_actes']}")
        print(f"Relations familiales: {len(resultat.get('filiations', []))}")
        print(f"Parrainages: {len(resultat.get('parrainages', []))}")
        print(f"Corrections de genre: {stats['persons']['gender_corrections']}")
        print(f"Homonymes détectés: {stats['persons']['homonym_detections']}")
        
        # Sauvegarder les résultats finaux
        sauvegarder_resultats_finaux(resultat, stats)
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur relance: {e}")
        import traceback
        traceback.print_exc()
        return False

def sauvegarder_resultats_finaux(resultat, stats):
    """Sauvegarde les résultats finaux corrigés"""
    
    try:
        import json
        from datetime import datetime
        
        output_dir = Path("resultats_finaux")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Rapport généalogique complet
        rapport_file = output_dir / f"rapport_genealogique_final_{timestamp}.txt"
        with open(rapport_file, 'w', encoding='utf-8') as f:
            import contextlib, io
            f_buffer = io.StringIO()
            
            try:
                from exporters.report_generator import ReportGenerator
                with contextlib.redirect_stdout(f_buffer):
                    ReportGenerator.print_formatted_results(resultat)
                f.write(f_buffer.getvalue())
            except:
                f.write("Erreur génération rapport formaté\n")
                f.write(str(resultat))
        
        # Statistiques complètes
        stats_file = output_dir / f"statistiques_finales_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False, default=str)
        
        # Liste des personnes pour analyse
        personnes_file = output_dir / f"personnes_extraites_{timestamp}.txt"
        with open(personnes_file, 'w', encoding='utf-8') as f:
            f.write("PERSONNES EXTRAITES DES REGISTRES PAROISSIAUX\n")
            f.write("=" * 50 + "\n\n")
            
            personnes = resultat.get('personnes', [])
            for i, personne in enumerate(personnes, 1):
                f.write(f"{i:3d}. {personne.get('nom_complet', 'N/A')}\n")
                f.write(f"     Dates: {personne.get('dates', 'N/A')}\n")
                f.write(f"     Professions: {personne.get('professions', 'N/A')}\n")
                f.write(f"     Titres: {personne.get('titres', 'N/A')}\n")
                f.write(f"     Notabilité: {personne.get('notabilite', 'N/A')}\n")
                f.write("\n")
        
        print(f"\n💾 RÉSULTATS FINAUX SAUVEGARDÉS")
        print("=" * 35)
        print(f"📋 Rapport: {rapport_file}")
        print(f"📊 Stats: {stats_file}")
        print(f"👥 Personnes: {personnes_file}")
        
    except Exception as e:
        print(f"⚠️  Erreur sauvegarde: {e}")

def main():
    """Fonction principale"""
    
    print("🎯 AMÉLIORATION ET FINALISATION DU TRAITEMENT")
    print("=" * 50)
    
    # Étape 1: Montrer les corrections possibles
    cleaner = corriger_personnes_extraites()
    
    # Étape 2: Relancer avec corrections
    print(f"\n🚀 Voulez-vous relancer le traitement avec ces corrections ? (o/n) [o]: ", end="")
    response = input().strip().lower() or 'o'
    
    if response == 'o':
        success = relancer_traitement_avec_corrections()
        
        if success:
            print(f"\n🎉 TRAITEMENT FINALISÉ AVEC SUCCÈS!")
            print("Les résultats finaux sont maintenant disponibles dans le dossier 'resultats_finaux/'")
        else:
            print(f"\n❌ Erreur durant le traitement final")
    else:
        print(f"\n👋 À bientôt ! Les résultats partiels sont déjà très prometteurs.")

if __name__ == "__main__":
    main()