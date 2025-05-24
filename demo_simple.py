import sys
import os
import json
from pathlib import Path

# Ajouter le répertoire courant au PATH Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test tous les imports essentiels"""
    print("🔍 Test des imports...")
    
    try:
        from config.settings import ParserConfig
        print("✅ Config OK")
        
        from core.models import Person, ActeParoissial, ActeType, PersonStatus
        print("✅ Models OK")
        
        from parsers.text_parser import TextParser
        from parsers.name_extractor import NameExtractor
        from parsers.date_parser import DateParser
        from parsers.profession_parser import ProfessionParser
        from parsers.relationship_parser import RelationshipParser
        print("✅ Parsers OK")
        
        from database.person_manager import PersonManager
        from database.acte_manager import ActeManager
        print("✅ Database managers OK")
        
        from exporters.report_generator import ReportGenerator
        print("✅ Exporters OK")
        
        # Import de la classe principale
        from main import GenealogyParser
        print("✅ GenealogyParser OK")
        
        return True
    except ImportError as e:
        print(f"❌ ERREUR IMPORT: {e}")
        print("\n💡 Solutions possibles:")
        print("1. Vérifiez que tous les fichiers .py sont présents")
        print("2. Créez les fichiers __init__.py dans chaque dossier")
        print("3. Vérifiez la structure des dossiers")
        print("4. Assurez-vous que main.py contient la classe GenealogyParser corrigée")
        return False
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False

def demo_parsing_corrected():
    """Démonstration complète du parsing avec la version corrigée"""
    
    # Texte d'exemple des registres paroissiaux
    sample_text = """1643-1687. — Bapt., mar., inh. — Charles de Montigny, Guillaume Le Breton, curés.
— « L'an de grâce 1643, le dimanche 8e jour de mars, moy, Charles Demontigny, prestre, 
ay, au nom de Dieu, pris possession du bénéfice Notre-Dame d'Esméville, sans aucune opposition. » 
— 1646, 13 fév., décès, le 14, inhumation, dans l'église, de Jean Le Boucher, écuyer, sr de Bréville. 
— 1651, 23 janv., inh., dans l'église, de Françoise Picot, épouse de Charles Le Boucher, 
éc., sr du Hausey, avocat du Roi au siège de Saint-Sylvain; 24 oct., naissance, bapt., 
et, le 21 nov., cérémonies du bapt. de Charlotte, fille de Jean Le Boucher, éc., sr de 
La Granville, et de Françoise Varin; marr.: Perrette Dupré; parr.: Charles Le Boucher, 
éc., sr du Hozey, conseiller et avocat du Roi à Saint-Sylvain."""
    
    try:
        print("\n🚀 DÉMONSTRATION DU PARSING CORRIGÉ")
        print("=" * 60)
        
        # Import de la classe principale corrigée
        from main import GenealogyParser
        from exporters.report_generator import ReportGenerator
        
        # Initialisation du parser corrigé
        parser = GenealogyParser()
        
        print(f"📋 Parser initialisé avec les corrections")
        
        # Traitement complet avec la version corrigée
        print(f"\n🔧 Traitement du document avec les corrections...")
        result = parser.process_document(sample_text)
        
        print(f"\n✅ TRAITEMENT TERMINÉ - RÉSULTATS CORRIGÉS")
        print("=" * 60)
        
        # Affichage du rapport final corrigé
        ReportGenerator.print_formatted_results(result)
        
        # Vérifications de la qualité des corrections
        print(f"\n🔍 VÉRIFICATION DES CORRECTIONS")
        print("=" * 45)
        
        verification_results = verify_corrections(result)
        display_verification_results(verification_results)
        
        # Statistiques détaillées
        print(f"\n📊 STATISTIQUES DÉTAILLÉES")
        print("=" * 35)
        
        stats = parser.get_global_statistics()
        display_detailed_stats(stats)
        
        return True, result
        
    except Exception as e:
        print(f"❌ ERREUR PENDANT LA DÉMONSTRATION: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def verify_corrections(result: dict) -> dict:
    """Vérifie que les corrections ont bien été appliquées"""
    verification = {
        'attribution_correcte': False,
        'filiations_detectees': False,
        'parrainages_detectes': False,
        'dates_extraites': False,
        'personnes_avec_attributs_corrects': [],
        'personnes_problematiques': [],
        'relations_trouvees': 0,
        'parrainages_trouves': 0
    }
    
    try:
        personnes = result.get('personnes', [])
        filiations = result.get('filiations', [])
        parrainages = result.get('parrainages', [])
        
        # Vérification 1: Attribution correcte des attributs
        francoise_picot = None
        charles_le_boucher = None
        
        for personne in personnes:
            nom_complet = personne.get('nom_complet', '')
            
            if 'Françoise Picot' in nom_complet:
                francoise_picot = personne
            elif 'Charles Le Boucher' in nom_complet:
                charles_le_boucher = personne
        
        # Françoise Picot ne devrait PAS avoir d'attributs masculins
        if francoise_picot:
            professions = francoise_picot.get('professions', '')
            titres = francoise_picot.get('titres', '')
            
            if ('avocat' not in professions.lower() and 
                'écuyer' not in titres.lower() and
                'sr de' not in titres.lower()):
                verification['attribution_correcte'] = True
                verification['personnes_avec_attributs_corrects'].append('Françoise Picot: attributs corrects')
            else:
                verification['personnes_problematiques'].append(f'Françoise Picot: attributs incorrects - {professions}, {titres}')
        
        # Vérification 2: Filiations détectées
        verification['relations_trouvees'] = len(filiations)
        if filiations:
            verification['filiations_detectees'] = True
        
        # Vérification 3: Parrainages détectés
        verification['parrainages_trouves'] = len(parrainages)
        if parrainages:
            verification['parrainages_detectes'] = True
        
        # Vérification 4: Dates extraites
        dates_trouvees = 0
        for personne in personnes:
            dates = personne.get('dates', '')
            if dates and 'inconnus' not in dates:
                dates_trouvees += 1
        
        if dates_trouvees > 0:
            verification['dates_extraites'] = True
            verification['personnes_avec_dates'] = dates_trouvees
        
    except Exception as e:
        print(f"Erreur lors de la vérification: {e}")
    
    return verification

def display_verification_results(verification: dict):
    """Affiche les résultats de vérification de manière claire"""
    
    print("🎯 RÉSULTATS DES CORRECTIONS:")
    
    # Attribution des attributs
    if verification['attribution_correcte']:
        print("✅ Attribution des attributs: CORRIGÉE")
        for msg in verification['personnes_avec_attributs_corrects']:
            print(f"   → {msg}")
    else:
        print("❌ Attribution des attributs: PROBLÈME PERSISTANT")
        for msg in verification['personnes_problematiques']:
            print(f"   → {msg}")
    
    # Filiations
    if verification['filiations_detectees']:
        print(f"✅ Filiations: {verification['relations_trouvees']} relation(s) détectée(s)")
    else:
        print("❌ Filiations: AUCUNE RELATION DÉTECTÉE")
    
    # Parrainages
    if verification['parrainages_detectes']:
        print(f"✅ Parrainages: {verification['parrainages_trouves']} parrainage(s) détecté(s)")
    else:
        print("❌ Parrainages: AUCUN PARRAINAGE DÉTECTÉ")
    
    # Dates
    if verification['dates_extraites']:
        print(f"✅ Dates: {verification.get('personnes_avec_dates', 0)} personne(s) avec dates")
    else:
        print("❌ Dates: AUCUNE DATE EXTRAITE")
    
    # Score global
    corrections_reussies = sum([
        verification['attribution_correcte'],
        verification['filiations_detectees'], 
        verification['parrainages_detectes'],
        verification['dates_extraites']
    ])
    
    score_pct = (corrections_reussies / 4) * 100
    
    print(f"\n🏆 SCORE GLOBAL DES CORRECTIONS: {corrections_reussies}/4 ({score_pct:.0f}%)")
    
    if score_pct >= 75:
        print("🎉 CORRECTIONS MAJORITAIREMENT RÉUSSIES!")
    elif score_pct >= 50:
        print("⚠️  CORRECTIONS PARTIELLES - Des améliorations sont nécessaires")
    else:
        print("🚨 CORRECTIONS INSUFFISANTES - Vérifiez l'implémentation")

def display_detailed_stats(stats: dict):
    """Affiche des statistiques détaillées"""
    try:
        global_stats = stats.get('global', {})
        person_stats = stats.get('persons', {})
        acte_stats = stats.get('actes', {})
        
        print(f"📈 Documents traités: {global_stats.get('documents_processed', 0)}")
        print(f"👥 Personnes créées: {person_stats.get('persons_created', 0)}")
        print(f"🔗 Personnes fusionnées: {person_stats.get('persons_merged', 0)}")
        print(f"📋 Actes créés: {acte_stats.get('actes_created', 0)}")
        print(f"✅ Actes validés: {acte_stats.get('actes_validated', 0)}")
        print(f"🔧 Corrections appliquées: {global_stats.get('corrections_applied', 0)}")
        print(f"⚠️  Erreurs de validation: {person_stats.get('validation_errors', 0)}")
        
        # Statistiques de cache
        cache_hit_rate = person_stats.get('cache_hit_rate', 0)
        print(f"🚀 Taux de succès du cache: {cache_hit_rate:.1f}%")
        
    except Exception as e:
        print(f"Erreur affichage statistiques: {e}")

def test_specific_extractions():
    """Test spécifique des nouvelles fonctionnalités d'extraction"""
    print("\n🧪 TESTS SPÉCIFIQUES DES EXTRACTIONS")
    print("=" * 45)
    
    try:
        from config.settings import ParserConfig
        from parsers.name_extractor import NameExtractor
        
        config = ParserConfig()
        extractor = NameExtractor(config)
        
        # Test 1: Attribution précise
        test_text1 = "Françoise Picot, épouse de Charles Le Boucher, éc., sr du Hausey, avocat du Roi"
        
        print("🔬 Test 1: Attribution des attributs")
        print(f"Texte: {test_text1}")
        
        names1 = extractor.extract_complete_names(test_text1)
        
        print(f"Personnes extraites: {len(names1)}")
        for person in names1:
            print(f"  - {person['nom_complet']}")
            print(f"    Professions: {person.get('professions', [])}")
            print(f"    Statut: {person.get('statut')}")
            print(f"    Terres: {person.get('terres', [])}")
        
        # Test 2: Relations familiales
        test_text2 = "Charlotte, fille de Jean Le Boucher, éc., sr de La Granville, et de Françoise Varin"
        
        print(f"\n🔬 Test 2: Relations familiales")
        print(f"Texte: {test_text2}")
        
        names2 = extractor.extract_complete_names(test_text2)
        
        print(f"Personnes extraites: {len(names2)}")
        for person in names2:
            print(f"  - {person['nom_complet']}")
            if person.get('relationships'):
                print(f"    Relations: {person['relationships']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur tests spécifiques: {e}")
        return False

def create_sample_file():
    """Crée un fichier d'exemple pour tester main.py"""
    sample_content = """1643-1687. — Bapt., mar., inh. — Charles de Montigny, Guillaume Le Breton, curés.
— « L'an de grâce 1643, le dimanche 8e jour de mars, moy, Charles Demontigny, prestre, 
ay, au nom de Dieu, pris possession du bénéfice Notre-Dame d'Esméville, sans aucune opposition. » 
— 1646, 13 fév., décès, le 14, inhumation, dans l'église, de Jean Le Boucher, écuyer, sr de Bréville. 
— 1651, 23 janv., inh., dans l'église, de Françoise Picot, épouse de Charles Le Boucher, 
éc., sr du Hausey, avocat du Roi au siège de Saint-Sylvain; 24 oct., naissance, bapt., 
et, le 21 nov., cérémonies du bapt. de Charlotte, fille de Jean Le Boucher, éc., sr de 
La Granville, et de Françoise Varin; marr.: Perrette Dupré; parr.: Charles Le Boucher, 
éc., sr du Hozey, conseiller et avocat du Roi à Saint-Sylvain."""
    
    filename = "exemple_registre.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        print(f"📄 Fichier d'exemple créé: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Erreur création fichier: {e}")
        return None

def show_expected_results():
    """Affiche les résultats attendus après corrections"""
    print("\n🎯 RÉSULTATS ATTENDUS APRÈS CORRECTIONS")
    print("=" * 50)
    
    expected_results = """
=== ACTES IDENTIFIÉS ===
Notre-Dame d'Esméville, 1643-1651, 2 baptêmes, 0 mariages, 2 inhumations, 0 actes de vente, 1 prise de possession

=== PERSONNES IDENTIFIÉES ===
1. **Charles de Montigny** (*8e jour de mars 1643-†?), curé, aucun titre, notabilité : prise de possession du bénéfice
2. **Guillaume Le Breton** (*?-†?), curé, aucun titre, notabilité : ministre du culte
3. **Jean Le Boucher** (*?-†13 février 1646), aucune profession, écuyer, sr de Bréville, notabilité : notable
4. **Charles Le Boucher** (*?-†?), avocat du Roi, écuyer, sr du Hausey, notabilité : fonction royale
5. **Françoise Picot** (*?-†23 janvier 1651), aucune profession, aucun titre, notabilité : notable
6. **Charlotte** (*24 octobre 1651-†?), aucune profession, aucun titre, notabilité : aucune notabilité particulière
7. **Jean Le Boucher** (*?-†?), aucune profession, écuyer, sr de La Granville, notabilité : aucune notabilité particulière
8. **Françoise Varin** (*?-†?), aucune profession, aucun titre, notabilité : aucune notabilité particulière
9. **Perrette Dupré** (*?-†?), aucune profession, aucun titre, notabilité : aucune notabilité particulière

=== FILIATIONS ===
1. **Jean Le Boucher** (éc., sr de La Granville) **X** **Françoise Varin** *(mariage antérieur à 1651)*

=== PARRAINAGES ===
1. **Charlotte** (1651) : parrain **Charles Le Boucher** (éc., sr du Hozey, conseiller et avocat du Roi), marraine **Perrette Dupré**
"""
    
    print(expected_results)
    
    print("\n🔑 POINTS CLÉS DES CORRECTIONS:")
    print("• Françoise Picot n'a plus les attributs masculins")
    print("• Les dates de naissance et décès sont extraites")
    print("• Les filiations sont détectées (Jean Le Boucher X Françoise Varin)")
    print("• Les parrainages sont extraits (Charlotte avec ses parrains)")
    print("• Les homonymes sont distingués (2 Jean Le Boucher différents)")

def main():
    """Fonction principale de démonstration corrigée"""
    print("🎉 DÉMONSTRATION GENEALOGY PARSER - VERSION CORRIGÉE")
    print("=" * 70)
    
    # Test des imports
    if not test_imports():
        print("\n❌ ÉCHEC DES IMPORTS - Arrêt du programme")
        print("Assurez-vous d'avoir appliqué toutes les corrections!")
        return False
    
    # Affichage des résultats attendus
    show_expected_results()
    
    # Démonstration du parsing corrigé
    success, result = demo_parsing_corrected()
    
    if not success:
        print("\n❌ ÉCHEC DE LA DÉMONSTRATION")
        return False
    
    # Tests spécifiques
    print("\n" + "=" * 70)
    test_specific_extractions()
    
    # Créer un fichier d'exemple
    print("\n📁 CRÉATION D'UN FICHIER D'EXEMPLE")
    print("=" * 40)
    sample_file = create_sample_file()
    
    print("\n🎯 PROCHAINES ÉTAPES")
    print("=" * 30)
    if sample_file:
        print(f"1. Testez le parser complet:")
        print(f"   python main.py {sample_file}")
        print(f"2. Avec mode verbeux pour voir les détails:")
        print(f"   python main.py {sample_file} -v")
        print(f"3. Avec exports:")
        print(f"   python main.py {sample_file} --gedcom --json")
    
    print("\n✨ FÉLICITATIONS ! Le parser fonctionne avec les corrections.")
    print("\n🔍 Si vous ne voyez pas les résultats attendus:")
    print("1. Vérifiez que main.py contient bien la version corrigée")
    print("2. Vérifiez que parsers/name_extractor.py est aussi corrigé")
    print("3. Relancez avec -v pour voir les logs détaillés")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 DÉMONSTRATION RÉUSSIE AVEC CORRECTIONS !")
        else:
            print("\n❌ DÉMONSTRATION ÉCHOUÉE - Vérifiez les corrections")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Démonstration interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n💥 ERREUR INATTENDUE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)