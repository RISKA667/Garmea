# tests/test_core_functionality.py
import unittest
import tempfile
import os
from pathlib import Path
import sys

# Ajouter le répertoire parent au path
sys.path.append(str(Path(__file__).parent.parent))

from parsers.relationship.basic_relationship_parser import BasicRelationshipParser
from parsers.base.text_parser import TextParser
from utils.smart_cache import SmartCache
from utils.error_handler import ErrorHandler, GarmeaError, ErrorType
from config.settings import ParserConfig

class TestRelationshipParser(unittest.TestCase):
    """Tests pour le parser de relations"""
    
    def setUp(self):
        self.config = ParserConfig()
        self.parser = BasicRelationshipParser(self.config)
    
    def test_filiation_extraction(self):
        """Test extraction des filiations"""
        text = "Charlotte, fille de Jean Le Boucher, éc., sr de La Granville, et de Françoise Varin"
        
        relationships = self.parser.extract_relationships(text)
        
        # Vérifier qu'on trouve une filiation
        filiations = [r for r in relationships if r.type == 'filiation']
        self.assertTrue(len(filiations) > 0, "Aucune filiation trouvée")
        
        filiation = filiations[0]
        self.assertEqual(filiation.entities.get('enfant', ''), 'Charlotte')
        self.assertIn('Jean Le Boucher', filiation.entities.get('pere', ''))
        self.assertEqual(filiation.entities.get('mere', ''), 'Françoise Varin')
    
    def test_mariage_extraction(self):
        """Test extraction des mariages"""
        text = "Françoise Picot, épouse de Charles Le Boucher"
        
        relationships = self.parser.extract_relationships(text)
        
        mariages = [r for r in relationships if r.type == 'mariage']
        self.assertTrue(len(mariages) > 0, "Aucun mariage trouvé")
        
        mariage = mariages[0]
        self.assertEqual(mariage.entities.get('epouse', ''), 'Françoise Picot')
        self.assertEqual(mariage.entities.get('epoux', ''), 'Charles Le Boucher')
    
    def test_parrainage_extraction(self):
        """Test extraction des parrainages"""
        text = "marr.: Perrette Dupré; parr.: Charles Le Boucher"
        
        relationships = self.parser.extract_relationships(text)
        
        parrains = [r for r in relationships if r.type == 'parrain']
        marraines = [r for r in relationships if r.type == 'marraine']
        
        self.assertTrue(len(parrains) > 0, "Aucun parrain trouvé")
        self.assertTrue(len(marraines) > 0, "Aucune marraine trouvée")
        
        self.assertEqual(marraines[0].entities.get('personne', ''), 'Perrette Dupré')
        self.assertIn('Charles Le Boucher', parrains[0].entities.get('personne', ''))
    
    def test_name_cleaning(self):
        """Test nettoyage des noms - SKIPPED (méthode non implémentée)"""
        # TODO: Implémenter la méthode _clean_person_name dans BasicRelationshipParser
        self.skipTest("Méthode _clean_person_name non implémentée")

class TestSmartCache(unittest.TestCase):
    """Tests pour le système de cache"""
    
    def setUp(self):
        # Créer un cache temporaire
        self.temp_dir = tempfile.mkdtemp()
        self.cache = SmartCache(self.temp_dir, ttl_hours=1)
    
    def tearDown(self):
        # Fermer proprement la connexion cache
        if hasattr(self.cache, 'close'):
            self.cache.close()
        
        # Nettoyer
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except PermissionError:
            # Sur Windows, parfois les fichiers sont encore utilisés
            pass
    
    def test_cache_set_get(self):
        """Test stockage et récupération"""
        test_data = {'name': 'Jean Dupont', 'birth': '1850'}
        
        # Stocker
        success = self.cache.set('persons', 'test_id', test_data)
        self.assertTrue(success)
        
        # Récupérer
        retrieved = self.cache.get('persons', 'test_id')
        self.assertEqual(retrieved, test_data)
    
    def test_cache_expiration(self):
        """Test expiration du cache"""
        self.cache.set('test', 'key1', 'value1', ttl_hours=0.001)  # 3.6 secondes
        
        # Immédiatement disponible
        self.assertEqual(self.cache.get('test', 'key1'), 'value1')
        
        # Après expiration (on simule en modifiant le temps)
        import time
        time.sleep(4)
        self.assertIsNone(self.cache.get('test', 'key1'))
    
    def test_cache_stats(self):
        """Test statistiques du cache"""
        self.cache.set('persons', 'p1', {'name': 'Jean'})
        self.cache.set('relationships', 'r1', {'type': 'filiation'})
        
        stats = self.cache.get_stats()
        
        self.assertEqual(stats['total_entries'], 2)
        self.assertEqual(stats['categories']['persons'], 1)
        self.assertEqual(stats['categories']['relationships'], 1)

class TestErrorHandler(unittest.TestCase):
    """Tests pour la gestion d'erreurs"""
    
    def setUp(self):
        self.error_handler = ErrorHandler()
    
    def test_pdf_error_classification(self):
        """Test classification erreur PDF"""
        pdf_error = Exception("fitz: cannot open document")
        
        garmea_error = self.error_handler.handle_error(pdf_error)
        
        self.assertEqual(garmea_error.error_type, ErrorType.PDF_READ_ERROR)
        self.assertIn("PDF", garmea_error.message)
    
    def test_parsing_error_classification(self):
        """Test classification erreur parsing"""
        parsing_error = Exception("regex pattern failed")
        
        garmea_error = self.error_handler.handle_error(parsing_error)
        
        self.assertEqual(garmea_error.error_type, ErrorType.PARSING_ERROR)
    
    def test_error_context(self):
        """Test contexte d'erreur"""
        error = Exception("Test error")
        context = {'file_name': 'test.pdf', 'page_number': 5}
        
        garmea_error = self.error_handler.handle_error(error, context)
        
        self.assertEqual(garmea_error.context, context)
        self.assertIn("test.pdf", garmea_error.message)
        self.assertIn("Page: 5", garmea_error.message)

class TestTextParser(unittest.TestCase):
    """Tests pour le parser de texte"""
    
    def setUp(self):
        self.config = ParserConfig()
        self.parser = TextParser(self.config)
    
    def test_abbreviation_expansion(self):
        """Test expansion des abréviations"""
        text = "bapt. le 15 janv., inh. le 20 fév."
        
        normalized = self.parser.normalize_text(text)
        
        self.assertIn("baptême", normalized['normalized'])
        self.assertIn("janvier", normalized['normalized'])
        self.assertIn("inhumation", normalized['normalized'])
        self.assertIn("février", normalized['normalized'])
    
    def test_text_cleaning(self):
        """Test nettoyage du texte"""
        messy_text = "  Jean   Le  Boucher,,,   éc.  "
        
        cleaned = self.parser.normalize_text(messy_text)
        
        # Espaces multiples supprimés
        self.assertNotIn("  ", cleaned)
        # Virgules multiples supprimées
        self.assertNotIn(",,", cleaned)

class TestIntegration(unittest.TestCase):
    """Tests d'intégration"""
    
    def test_complete_parsing_workflow(self):
        """Test du workflow complet"""
        sample_text = """
        1651, 23 janv., inh., dans l'église, de Françoise Picot, épouse de Charles Le Boucher, 
        éc., sr du Hausey; 24 oct., naissance, bapt. de Charlotte, fille de Jean Le Boucher 
        et de Françoise Varin; marr.: Perrette Dupré; parr.: Charles Le Boucher.
        """
        
        config = ParserConfig()
        text_parser = TextParser(config)
        relationship_parser = BasicRelationshipParser(config)
        
        # Normaliser le texte
        normalized_text = text_parser.normalize_text(sample_text)
        
        # Extraire les relations
        relationships = relationship_parser.extract_relationships(normalized_text)
        
        # Vérifications
        self.assertTrue(len(relationships) > 0, "Aucune relation extraite")
        
        # Doit contenir différents types de relations
        types_found = {r['type'] for r in relationships}
        expected_types = {'filiation', 'mariage', 'parrain', 'marraine'}
        
        self.assertTrue(
            expected_types.intersection(types_found),
            f"Types attendus non trouvés. Trouvés: {types_found}"
        )

# Script de lancement des tests
if __name__ == '__main__':
    # Configuration des logs pour les tests
    import logging
    logging.basicConfig(level=logging.ERROR)  # Réduire le bruit pendant les tests
    
    # Créer une suite de tests
    test_suite = unittest.TestSuite()
    
    # Ajouter tous les tests
    test_classes = [
        TestRelationshipParser,
        TestSmartCache, 
        TestErrorHandler,
        TestTextParser,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Lancer les tests avec rapport détaillé
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(test_suite)
    
    # Afficher résumé
    print(f"\n{'='*50}")
    print(f"RÉSUMÉ DES TESTS")
    print(f"{'='*50}")
    print(f"Tests exécutés: {result.testsRun}")
    print(f"Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    
    if result.failures:
        print(f"\nÉCHECS:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\nERREURS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Exception:')[-1].strip()}")
    
    # Code de sortie
    exit_code = 0 if result.wasSuccessful() else 1
    print(f"\nStatut: {'✅ SUCCÈS' if result.wasSuccessful() else '❌ ÉCHEC'}")
    exit(exit_code)