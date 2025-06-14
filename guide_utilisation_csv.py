# guide_utilisation_csv.py
"""
Guide d'utilisation du Smart PDF Analyzer avec export CSV automatique
Instructions complètes pour obtenir vos données dans RESULT/
"""

def afficher_guide():
    """Affiche le guide d'utilisation complet"""
    
    print("""
SMART PDF ANALYZER - GUIDE D'UTILISATION CSV
============================================

ÉTAPE 1: PRÉPARATION
-------------------
1. Assurez-vous d'avoir ces fichiers:
   - smart_pdf_analyzer.py (version corrigée)
   - fix_document_closed.py
   - csv_exporter.py

2. Installez les dépendances si nécessaire:
   pip install pandas

ÉTAPE 2: UTILISATION SIMPLE
---------------------------
Commande de base (export CSV automatique):

python smart_pdf_analyzer.py votre_fichier.pdf

Résultat: Dossier RESULT/ créé avec tous les fichiers CSV

ÉTAPE 3: OPTIONS AVANCÉES
-------------------------
Avec limitation de pages:
python smart_pdf_analyzer.py votre_fichier.pdf --max-pages 100

Avec dossier personnalisé:
python smart_pdf_analyzer.py votre_fichier.pdf --csv-dir MON_DOSSIER

Avec sauvegarde JSON en plus:
python smart_pdf_analyzer.py votre_fichier.pdf --output resultats.json

Mode verbeux pour debug:
python smart_pdf_analyzer.py votre_fichier.pdf --verbose

ÉTAPE 4: FICHIERS CRÉÉS
-----------------------
Dans le dossier RESULT/, vous trouverez:

📄 filiations.csv
   Colonnes: ID, Enfant, Père, Mère, Source_Texte, Confiance
   Trié par: Nom de l'enfant puis du père

📄 mariages.csv
   Colonnes: ID, Épouse, Époux, Statut, Source_Texte, Confiance
   Trié par: Nom de l'épouse puis de l'époux

📄 parrainages.csv
   Colonnes: ID, Type, Personne, Source_Texte, Confiance
   Trié par: Type (parrain/marraine) puis nom

📄 personnes.csv
   Colonnes: ID, Nom_Complet, Prénoms, Nom_Famille, Occurrences
   Trié par: Nom de famille puis prénoms

📄 relations_consolidees.csv
   Toutes les relations dans un seul fichier
   Colonnes: ID, Type_Relation, Personne_Principale, etc.

📄 resume_general.csv
   Statistiques et métriques du traitement

📄 INDEX.txt
   Liste de tous les fichiers créés avec descriptions

ÉTAPE 5: EXPORT UNIQUEMENT (si vous avez déjà des résultats)
------------------------------------------------------------
Si vous avez un fichier JSON de résultats:

python csv_exporter.py resultats.json

Ou vers un dossier spécifique:
python csv_exporter.py resultats.json MON_DOSSIER

ÉTAPE 6: EXEMPLE COMPLET
------------------------
""")

def exemple_utilisation_complete():
    """Exemple d'utilisation complète"""
    
    print("""
EXEMPLE PRATIQUE
================

1. Lancer l'analyse:
   python smart_pdf_analyzer.py inventaire.pdf --max-pages 50

2. Résultat attendu:
   Smart PDF Analyzer - Version 3.0.0
   ==================================================
   Fichier: inventaire.pdf
   Limite pages: 50
   Export CSV: RESULT
   
   [... traitement ...]
   
   TRAITEMENT TERMINÉ AVEC SUCCÈS
   ==================================================
   Pages de registres trouvées: 35
   Personnes extraites: 1247
   Relations familiales: 892
     - Filiations: 245
     - Mariages: 67
     - Parrainages: 580
   
   Export CSV automatique vers RESULT
   ------------------------------
   Fichiers CSV créés:
     - filiations: filiations.csv
     - mariages: mariages.csv
     - parrainages: parrainages.csv
     - personnes: personnes.csv
     - consolide: relations_consolidees.csv
     - resume: resume_general.csv
   
   Tous les fichiers sont dans le dossier: C:\\...\\RESULT

3. Ouvrir les fichiers:
   - Excel: Ouvrir directement les fichiers .csv
   - LibreOffice: Importer avec séparateur virgule, UTF-8
   - Google Sheets: Importer les fichiers CSV

STRUCTURE DES DONNÉES
====================

filiations.csv - Exemple:
ID,Enfant,Père,Mère,Source_Texte,Confiance
1,Marie Dupont,Jean Dupont,Anne Martin,"Marie fille de Jean Dupont et Anne Martin",0.85
2,Pierre Martin,Louis Martin,,"Pierre fils de Louis Martin",0.65

mariages.csv - Exemple:
ID,Épouse,Époux,Statut,Source_Texte,Confiance
1,Marie Leblanc,Jean Dupont,mariée,"Marie Leblanc épouse de Jean Dupont",0.90
2,Anne Durand,Pierre Martin,veuve,"Anne Durand veuve de Pierre Martin",0.75

personnes.csv - Exemple:
ID,Nom_Complet,Prénoms,Nom_Famille,Occurrences
1,Jean Dupont,Jean,Dupont,15
2,Marie Martin,Marie,Martin,8

CONSEILS D'UTILISATION
======================

🎯 Pour de meilleurs résultats:
   - Limitez à 50-100 pages pour les premiers tests
   - Utilisez --verbose pour comprendre le processus
   - Vérifiez le fichier INDEX.txt pour un résumé

📊 Pour analyser les données:
   - Ouvrez relations_consolidees.csv pour une vue d'ensemble
   - Utilisez filiations.csv pour construire des arbres généalogiques
   - Filtrez les données par confiance (>0.7 recommandé)

🔧 En cas de problème:
   - Vérifiez que tous les fichiers .py sont dans le même dossier
   - Utilisez --verbose pour voir les détails
   - Consultez INDEX.txt pour vérifier les exports

🚀 Pour aller plus loin:
   - Importez les CSV dans votre logiciel de généalogie
   - Utilisez Excel/LibreOffice pour créer des graphiques
   - Croisez les données entre les différents fichiers
""")

def tester_systeme():
    """Test rapide du système"""
    
    print("TEST DU SYSTÈME CSV")
    print("=" * 25)
    
    # Vérifier les modules
    modules_requis = [
        'smart_pdf_analyzer.py',
        'fix_document_closed.py', 
        'csv_exporter.py'
    ]
    
    from pathlib import Path
    
    print("Vérification des fichiers:")
    for module in modules_requis:
        if Path(module).exists():
            print(f"  ✅ {module}")
        else:
            print(f"  ❌ {module} - MANQUANT")
    
    # Vérifier les imports
    print("\nVérification des imports:")
    try:
        import pandas
        print("  ✅ pandas")
    except ImportError:
        print("  ⚠️ pandas - Optionnel mais recommandé")
    
    try:
        import fitz
        print("  ✅ PyMuPDF")
    except ImportError:
        print("  ❌ PyMuPDF - REQUIS")
    
    print("\nPour installer les dépendances manquantes:")
    print("pip install PyMuPDF pandas")
    
    print(f"\nSystème prêt ! Lancez:")
    print(f"python smart_pdf_analyzer.py votre_fichier.pdf")

if __name__ == "__main__":
    afficher_guide()
    print("\n" + "="*60)
    exemple_utilisation_complete()
    print("\n" + "="*60)
    tester_systeme()