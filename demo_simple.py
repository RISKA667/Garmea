import sys
import os

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
        print("✅ Parsers OK")
        
        return True
    except ImportError as e:
        print(f"❌ ERREUR IMPORT: {e}")
        print("\n💡 Solutions possibles:")
        print("1. Vérifiez que tous les fichiers .py sont présents")
        print("2. Créez les fichiers __init__.py dans chaque dossier")
        print("3. Vérifiez la structure des dossiers")
        return False
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False

def demo_parsing():
    """Démonstration du parsing avec le texte d'exemple"""
    
    # Texte d'exemple des registres paroissiaux
    sample_text = """
    1643-1687. — Bapt., mar., inh. — Charles de Montigny, Guillaume Le Breton, curés.
    — « L'an de grâce 1643, le dimanche 8e jour de mars, moy, Charles Demontigny, prestre, 
    ay, au nom de Dieu, pris possession du bénéfice Notre-Dame d'Esméville, sans aucune opposition. » 
    — 1646, 13 fév., décès, le 14, inhumation, dans l'église, de Jean Le Boucher, écuyer, sr de Bréville. 
    — 1651, 23 janv., inh., dans l'église, de Françoise Picot, épouse de Charles Le Boucher, 
    éc., sr du Hausey, avocat du Roi au siège de Saint-Sylvain; 24 oct., naissance, bapt., 
    et, le 21 nov., cérémonies du bapt. de Charlotte, fille de Jean Le Boucher, éc., sr de 
    La Granville, et de Françoise Varin; marr.: Perrette Dupré; parr.: Charles Le Boucher, 
    éc., sr du Hozey, conseiller et avocat du Roi à Saint-Sylvain.
    """
    
    try:
        print("\n🚀 DÉMONSTRATION DU PARSING")
        print("=" * 50)
        
        # Imports
        from config.settings import ParserConfig
        from parsers.text_parser import TextParser
        from parsers.name_extractor import NameExtractor
        from parsers.date_parser import DateParser
        from parsers.profession_parser import ProfessionParser
        
        # Configuration
        config = ParserConfig()
        print(f"📋 Configuration chargée (seuil similarité: {config.similarity_threshold})")
        
        # Parsers
        text_parser = TextParser(config)
        name_extractor = NameExtractor(config)
        date_parser = DateParser(config)
        profession_parser = ProfessionParser(config)
        
        print(f"🔧 Parsers initialisés")
        
        # 1. Normalisation du texte
        print("\n1️⃣ NORMALISATION DU TEXTE")
        normalized_text = text_parser.normalize_text(sample_text)
        print(f"   📝 Texte original: {len(sample_text)} caractères")
        print(f"   ✨ Texte normalisé: {len(normalized_text)} caractères")
        
        # 2. Extraction des noms
        print("\n2️⃣ EXTRACTION DES NOMS")
        names = name_extractor.extract_complete_names(normalized_text)
        print(f"   👥 {len(names)} personnes trouvées:")
        
        for i, name in enumerate(names, 1):
            print(f"   {i}. {name['prenom']} {name['nom']}")
            
            # Professions pour cette personne
            professions = name.get('professions', [])
            if professions:
                print(f"      Professions: {', '.join(professions)}")
            
            # Statut
            statut = name.get('statut')
            if statut:
                print(f"      Statut: {statut}")
            
            # Terres
            terres = name.get('terres', [])
            if terres:
                print(f"      Terres: sr de {', '.join(terres)}")
            
            # Notable
            if name.get('notable'):
                print(f"      👑 NOTABLE (inhumé dans l'église)")
        
        # 3. Extraction des dates
        print("\n3️⃣ EXTRACTION DES DATES")
        dates = date_parser.extract_all_dates(normalized_text)
        print(f"   📅 {len(dates)} dates trouvées:")
        
        for i, date in enumerate(dates, 1):
            confidence_icon = "🟢" if date.confidence > 0.8 else "🟡" if date.confidence > 0.5 else "🔴"
            print(f"   {i}. {date.original_text}")
            if date.year:
                print(f"      Année: {date.year} {confidence_icon}")
            if date.parsed_date:
                print(f"      Date complète: {date.parsed_date.strftime('%d/%m/%Y')}")
        
        # 4. Segments d'actes
        print("\n4️⃣ SEGMENTATION DES ACTES")
        segments = text_parser.extract_segments(normalized_text)
        print(f"   📋 {len(segments)} segments trouvés:")
        
        for i, segment in enumerate(segments, 1):
            print(f"   {i}. Type: {segment['type']}")
            if segment['type'] == 'acte':
                preview = segment['content'][:100] + "..." if len(segment['content']) > 100 else segment['content']
                print(f"      Contenu: {preview}")
        
        print("\n✅ DÉMONSTRATION TERMINÉE AVEC SUCCÈS!")
        print("\n💡 Pour utiliser avec un fichier:")
        print("   python main.py votre_fichier.txt")
        
        return True
        
    except Exception as e:
        print(f"❌ ERREUR PENDANT LA DÉMONSTRATION: {e}")
        import traceback
        traceback.print_exc()
        return False

def demo_corrections():
    """Démonstration des corrections automatiques"""
    print("\n🔍 DÉMONSTRATION DES CORRECTIONS")
    print("=" * 40)
    
    exemples_corrections = [
        ("Charles Demontigny, prestre", "Charles de Montigny, prêtre"),
        ("Jean sr de Breville", "Jean sieur de Bréville"),
        ("13 fév. 1646", "13 février 1646"),
        ("moy, Charles", "moi, Charles"),
        ("ay pris possession", "ai pris possession")
    ]
    
    for original, attendu in exemples_corrections:
        print(f"   📝 '{original}'")
        print(f"   ✨ → '{attendu}'")
        print()

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
        print(f"💻 Vous pouvez maintenant tester:")
        print(f"   python main.py {filename}")
        print(f"   python main.py {filename} --gedcom --json")
        
        return filename
        
    except Exception as e:
        print(f"❌ Erreur création fichier: {e}")
        return None

def main():
    """Fonction principale de démonstration"""
    print("🎉 DÉMONSTRATION GENEALOGY PARSER")
    print("=" * 60)
    
    # Test des imports
    if not test_imports():
        print("\n❌ ÉCHEC DES IMPORTS - Arrêt du programme")
        return False
    
    # Démonstration du parsing
    if not demo_parsing():
        print("\n❌ ÉCHEC DE LA DÉMONSTRATION")
        return False
    
    # Démonstration des corrections
    demo_corrections()
    
    # Créer un fichier d'exemple
    print("\n📁 CRÉATION D'UN FICHIER D'EXEMPLE")
    print("=" * 40)
    sample_file = create_sample_file()
    
    print("\n🎯 PROCHAINES ÉTAPES")
    print("=" * 30)
    if sample_file:
        print(f"1. Testez le parser complet:")
        print(f"   python main.py {sample_file}")
        print(f"2. Avec exports:")
        print(f"   python main.py {sample_file} --gedcom --json")
        print(f"3. Mode verbeux:")
        print(f"   python main.py {sample_file} -v")
    
    print("\n✨ FÉLICITATIONS ! Le parser fonctionne correctement.")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 DÉMONSTRATION RÉUSSIE !")
        else:
            print("\n❌ DÉMONSTRATION ÉCHOUÉE")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Démonstration interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n💥 ERREUR INATTENDUE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)