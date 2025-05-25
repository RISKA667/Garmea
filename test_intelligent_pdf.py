#!/usr/bin/env python3
"""
Script de test pour analyser intelligemment le PDF de 614 pages
et extraire automatiquement les registres paroissiaux
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire au PATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def tester_pdf_intelligent():
    """Test de l'analyse intelligente du PDF"""
    
    pdf_file = "inventairesommai03archuoft.pdf"
    
    if not Path(pdf_file).exists():
        print(f"❌ Fichier PDF non trouvé: {pdf_file}")
        print("Assurez-vous que le fichier est dans le même répertoire")
        return False
    
    print("🤖 ANALYSE INTELLIGENTE DU PDF")
    print("=" * 50)
    print(f"Fichier: {pdf_file}")
    print(f"Objectif: Détecter automatiquement les registres paroissiaux")
    print()
    
    try:
        # Importer l'analyseur intelligent
        from smart_pdf_analyzer import analyser_et_traiter_pdf
        
        # Option 1: Analyse complète (peut être long)
        print("⚠️  Ce PDF fait 614 pages. Options:")
        print("1. Analyse rapide (100 premières pages)")
        print("2. Analyse complète (toutes les pages - plus long)")
        print("3. Analyse moyenne (300 pages)")
        
        choix = input("\nChoisissez (1/2/3) [1]: ").strip() or "1"
        
        if choix == "1":
            max_pages = 100
            print(f"🚀 Analyse rapide des 100 premières pages...")
        elif choix == "3":
            max_pages = 300
            print(f"🚀 Analyse de 300 pages...")
        else:
            max_pages = None
            print(f"🚀 Analyse complète des 614 pages (cela peut prendre quelques minutes)...")
        
        # Lancer l'analyse intelligente
        resultat = analyser_et_traiter_pdf(pdf_file, max_pages)
        
        if resultat:
            print(f"\n🎉 SUCCÈS!")
            print("=" * 15)
            print(f"✅ Pages de registres trouvées: {resultat['pages_registres']}")
            print(f"✅ Personnes identifiées: {resultat['statistiques']['persons']['total_persons']}")
            print(f"✅ Actes détectés: {resultat['statistiques']['actes']['total_actes']}")
            
            # Sauvegarder les résultats
            sauvegarder_resultats(resultat)
            
        else:
            print(f"\n⚠️  RÉSULTAT MITIGÉ")
            print("=" * 20)
            print("Possible que les registres paroissiaux soient:")
            print("• Dans les pages non analysées (si analyse partielle)")
            print("• Dans un format très différent")
            print("• Absents de ce document")
            print("\nEssayez une analyse plus complète ou vérifiez le contenu manuellement")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        print("Assurez-vous que PyMuPDF est installé: pip install PyMuPDF")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def sauvegarder_resultats(resultat):
    """Sauvegarde les résultats dans des fichiers"""
    
    try:
        import json
        from datetime import datetime
        
        # Créer un dossier de résultats
        output_dir = Path("resultats_pdf")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sauvegarder les statistiques
        stats_file = output_dir / f"statistiques_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(resultat['statistiques'], f, indent=2, ensure_ascii=False)
        
        # Sauvegarder le rapport généalogique
        rapport_file = output_dir / f"rapport_genealogique_{timestamp}.txt"
        with open(rapport_file, 'w', encoding='utf-8') as f:
            # Rediriger l'output du rapport vers le fichier
            import contextlib, io
            f_buffer = io.StringIO()
            
            try:
                from exporters.report_generator import ReportGenerator
                with contextlib.redirect_stdout(f_buffer):
                    ReportGenerator.print_formatted_results(resultat['resultats_genealogiques'])
                f.write(f_buffer.getvalue())
            except:
                f.write("Erreur génération rapport formaté\n")
                f.write(str(resultat['resultats_genealogiques']))
        
        print(f"\n💾 RÉSULTATS SAUVEGARDÉS")
        print("=" * 25)
        print(f"📊 Statistiques: {stats_file}")
        print(f"📋 Rapport: {rapport_file}")
        
    except Exception as e:
        print(f"⚠️  Erreur sauvegarde: {e}")

def mode_demo():
    """Mode démo avec exemple simple"""
    
    print("🎭 MODE DÉMO - TEST AVEC EXEMPLE")
    print("=" * 40)
    
    # Créer un fichier exemple avec vrai contenu paroissial
    exemple_registre = """1643-1687. — Bapt., mar., inh. — Charles de Montigny, Guillaume Le Breton, curés.
— « L'an de grâce 1643, le dimanche 8e jour de mars, moy, Charles Demontigny, prestre, 
ay, au nom de Dieu, pris possession du bénéfice Notre-Dame d'Esméville, sans aucune opposition. » 
— 1646, 13 fév., décès, le 14, inhumation, dans l'église, de Jean Le Boucher, écuyer, sr de Bréville. 
— 1651, 23 janv., inh., dans l'église, de Françoise Picot, épouse de Charles Le Boucher, 
éc., sr du Hausey, avocat du Roi au siège de Saint-Sylvain; 24 oct., naissance, bapt., 
et, le 21 nov., cérémonies du bapt. de Charlotte, fille de Jean Le Boucher, éc., sr de 
La Granville, et de Françoise Varin; marr.: Perrette Dupré; parr.: Charles Le Boucher, 
éc., sr du Hozey, conseiller et avocat du Roi à Saint-Sylvain."""
    
    try:
        from main import GenealogyParser
        from exporters.report_generator import ReportGenerator
        
        parser = GenealogyParser()
        resultat = parser.process_document(exemple_registre, "Notre-Dame d'Esméville")
        
        print("✅ EXEMPLE DE RÉSULTAT ATTENDU:")
        print("=" * 35)
        ReportGenerator.print_formatted_results(resultat)
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur mode démo: {e}")
        return False

def main():
    """Menu principal"""
    
    print("🔍 ANALYSEUR PDF INTELLIGENT POUR REGISTRES PAROISSIAUX")
    print("=" * 65)
    print()
    print("Options:")
    print("1. Analyser le PDF complet (intelligent)")
    print("2. Mode démo avec exemple")
    print("3. Quitter")
    print()
    
    choix = input("Choisissez une option (1/2/3) [1]: ").strip() or "1"
    
    if choix == "1":
        success = tester_pdf_intelligent()
    elif choix == "2":
        success = mode_demo()
    else:
        print("Au revoir!")
        return
    
    if success:
        print(f"\n✨ TERMINÉ AVEC SUCCÈS!")
    else:
        print(f"\n⚠️  Voir les erreurs ci-dessus")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"\n💥 Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()