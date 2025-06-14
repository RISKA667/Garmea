# integration_csv_patch.py
"""
Patch pour intégrer l'export CSV automatique dans smart_pdf_analyzer.py
Applique automatiquement les modifications nécessaires
"""

import re
from pathlib import Path

def appliquer_patch_csv():
    """Applique le patch CSV au smart_pdf_analyzer.py existant"""
    
    fichier_analyzer = "smart_pdf_analyzer.py"
    fichier_backup = "smart_pdf_analyzer_BACKUP_CSV.py"
    
    if not Path(fichier_analyzer).exists():
        print(f"❌ Fichier {fichier_analyzer} non trouvé")
        return False
    
    try:
        # Lire le fichier
        with open(fichier_analyzer, 'r', encoding='utf-8') as f:
            contenu = f.read()
        
        # Créer un backup
        with open(fichier_backup, 'w', encoding='utf-8') as f:
            f.write(contenu)
        print(f"✅ Backup créé: {fichier_backup}")
        
        # Vérifier si le patch est déjà appliqué
        if "csv_exporter" in contenu:
            print("⚠️ Le patch CSV semble déjà appliqué")
            return True
        
        # Modifications à appliquer
        print("🔧 Application du patch CSV...")
        
        # 1. Ajouter l'import du csv_exporter après les autres imports
        import_csv = '''
# === IMPORT CSV EXPORTER ===
try:
    from csv_exporter import exporter_vers_csv
    CSV_EXPORT_AVAILABLE = True
except ImportError:
    CSV_EXPORT_AVAILABLE = False
    print("Module csv_exporter non disponible - export CSV désactivé")
'''
        
        # Trouver la fin des imports pour insérer l'import CSV
        lines = contenu.split('\n')
        import_end = 0
        for i, line in enumerate(lines):
            if (line.startswith('import ') or line.startswith('from ')) and 'import' in line:
                import_end = i + 1
        
        lines.insert(import_end, import_csv)
        
        # 2. Modifier la fonction main() pour ajouter les arguments CSV
        contenu_modifie = '\n'.join(lines)
        
        # Trouver et remplacer la section des arguments dans main()
        pattern_args = r'(parser\.add_argument\(\s*\'--output\'.*?\))'
        
        nouveaux_args = '''parser.add_argument(
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
        help='Désactiver l\\'export CSV automatique'
    )'''
        
        contenu_modifie = re.sub(pattern_args, nouveaux_args, contenu_modifie, flags=re.DOTALL)
        
        # 3. Ajouter la section d'export CSV dans main()
        section_export_csv = '''
            # Export automatique vers CSV
            if not args.no_csv and CSV_EXPORT_AVAILABLE:
                print(f"\\nExport CSV automatique vers {args.csv_dir}")
                print("-" * 30)
                try:
                    fichiers_csv = exporter_vers_csv(resultat, args.csv_dir)
                    print(f"Fichiers CSV créés:")
                    for type_fichier, chemin in fichiers_csv.items():
                        filename = Path(chemin).name
                        print(f"  - {type_fichier}: {filename}")
                    
                    print(f"\\nTous les fichiers sont dans le dossier: {Path(args.csv_dir).absolute()}")
                    
                except Exception as e:
                    print(f"Erreur lors de l\\'export CSV: {e}")
                    if args.verbose:
                        import traceback
                        traceback.print_exc()'''
        
        # Trouver où insérer la section CSV (après l'affichage des résultats)
        pattern_insertion = r'(# Sauvegarde des résultats.*?if args\.output:)'
        
        contenu_modifie = re.sub(
            pattern_insertion,
            section_export_csv + '\\n\\n            \\1',
            contenu_modifie,
            flags=re.DOTALL
        )
        
        # 4. Modifier l'affichage initial pour mentionner l'export CSV
        pattern_affichage = r'(print\(f"Limite pages: \{args\.max_pages or \'Toutes\'\}"\))'
        
        nouvel_affichage = '''print(f"Limite pages: {args.max_pages or 'Toutes'}")
    if not args.no_csv and CSV_EXPORT_AVAILABLE:
        print(f"Export CSV: {args.csv_dir}")'''
        
        contenu_modifie = re.sub(pattern_affichage, nouvel_affichage, contenu_modifie)
        
        # Sauvegarder le fichier modifié
        with open(fichier_analyzer, 'w', encoding='utf-8') as f:
            f.write(contenu_modifie)
        
        print("✅ Patch CSV appliqué avec succès!")
        print(f"💡 Votre ancien fichier est sauvegardé dans: {fichier_backup}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'application du patch: {e}")
        
        # Restaurer le backup en cas d'erreur
        if Path(fichier_backup).exists():
            with open(fichier_backup, 'r', encoding='utf-8') as f:
                contenu_backup = f.read()
            with open(fichier_analyzer, 'w', encoding='utf-8') as f:
                f.write(contenu_backup)
            print(f"🔄 Fichier restauré depuis le backup")
        
        return False

def verification_post_patch():
    """Vérifie que le patch a été correctement appliqué"""
    
    print("🔍 Vérification post-patch...")
    
    fichier_analyzer = "smart_pdf_analyzer.py"
    
    if not Path(fichier_analyzer).exists():
        print("❌ Fichier smart_pdf_analyzer.py non trouvé")
        return False
    
    with open(fichier_analyzer, 'r', encoding='utf-8') as f:
        contenu = f.read()
    
    verifications = [
        ("Import CSV", "csv_exporter"),
        ("Variable CSV_EXPORT_AVAILABLE", "CSV_EXPORT_AVAILABLE"),
        ("Argument --csv-dir", "--csv-dir"),
        ("Argument --no-csv", "--no-csv"),
        ("Section export CSV", "Export CSV automatique")
    ]
    
    tout_ok = True
    for nom, pattern in verifications:
        if pattern in contenu:
            print(f"  ✅ {nom}")
        else:
            print(f"  ❌ {nom} - MANQUANT")
            tout_ok = False
    
    if tout_ok:
        print("🎉 Patch correctement appliqué!")
        return True
    else:
        print("⚠️ Certains éléments du patch sont manquants")
        return False

def test_integration_complete():
    """Test complet de l'intégration CSV"""
    
    print("🧪 TEST D'INTÉGRATION COMPLÈTE")
    print("=" * 35)
    
    # 1. Vérifier les fichiers requis
    fichiers_requis = [
        "smart_pdf_analyzer.py",
        "fix_document_closed.py",
        "csv_exporter.py"
    ]
    
    print("1. Vérification des fichiers:")
    for fichier in fichiers_requis:
        if Path(fichier).exists():
            print(f"   ✅ {fichier}")
        else:
            print(f"   ❌ {fichier} - MANQUANT")
            print(f"      Assurez-vous que ce fichier existe dans le répertoire")
    
    # 2. Test d'import
    print("\n2. Test des imports:")
    try:
        import csv_exporter
        print("   ✅ csv_exporter importé")
    except ImportError as e:
        print(f"   ❌ Erreur import csv_exporter: {e}")
        return False
    
    try:
        from csv_exporter import exporter_vers_csv
        print("   ✅ fonction exporter_vers_csv disponible")
    except ImportError as e:
        print(f"   ❌ Erreur import fonction: {e}")
        return False
    
    # 3. Test de création du dossier RESULT
    print("\n3. Test création dossier RESULT:")
    try:
        result_dir = Path("RESULT")
        result_dir.mkdir(exist_ok=True)
        print(f"   ✅ Dossier RESULT créé/vérifié: {result_dir.absolute()}")
    except Exception as e:
        print(f"   ❌ Erreur création dossier: {e}")
        return False
    
    print("\n🎉 Intégration CSV prête!")
    print(f"💡 Lancez maintenant: python smart_pdf_analyzer.py votre_fichier.pdf")
    
    return True

if __name__ == "__main__":
    print("INTÉGRATION CSV POUR SMART PDF ANALYZER")
    print("=" * 45)
    
    # Appliquer le patch
    if appliquer_patch_csv():
        print()
        # Vérifier le patch
        if verification_post_patch():
            print()
            # Test complet
            test_integration_complete()
    
    print(f"\n📖 INSTRUCTIONS FINALES:")
    print(f"1. Assurez-vous que csv_exporter.py est dans le même dossier")
    print(f"2. Lancez: python smart_pdf_analyzer.py votre_fichier.pdf")
    print(f"3. Les résultats seront dans le dossier RESULT/")
    print(f"4. Pour désactiver l'export CSV: ajoutez --no-csv")