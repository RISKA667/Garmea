# utils/relation_debugger.py
import re
from typing import Dict, List, Tuple, Optional
import logging
from collections import Counter

class RelationshipDebugger:
    """Outil de diagnostic pour comprendre pourquoi les relations ne sont pas détectées"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Patterns de test simplifié pour diagnostic
        self.test_patterns = {
            'fils_simple': re.compile(r'(\w+)\s*,?\s*fils\s+de\s+(\w+)', re.IGNORECASE),
            'fille_simple': re.compile(r'(\w+)\s*,?\s*fille\s+de\s+(\w+)', re.IGNORECASE),
            'epouse_simple': re.compile(r'(\w+)\s*,?\s*épouse\s+de\s+(\w+)', re.IGNORECASE),
            'femme_simple': re.compile(r'(\w+)\s*,?\s*femme\s+de\s+(\w+)', re.IGNORECASE),
            'veuve_simple': re.compile(r'(\w+)\s*,?\s*veuve\s+de\s+(\w+)', re.IGNORECASE),
            'parrain_simple': re.compile(r'parr?[\.:]?\s*(\w+)', re.IGNORECASE),
            'marraine_simple': re.compile(r'marr?[\.:]?\s*(\w+)', re.IGNORECASE)
        }
        
        # Mots-clés de relation pour analyse de fréquence
        self.relation_keywords = [
            'fils', 'fille', 'filz', 'enfant',
            'père', 'mere', 'mère', 'parent',
            'épouse', 'femme', 'mari', 'époux',
            'veuve', 'veuf',
            'parrain', 'marraine', 'parr', 'marr',
            'baptême', 'bapt', 'naissance',
            'mariage', 'mar', 'union'
        ]
    
    def diagnose_document(self, text: str, sample_size: int = 2000) -> Dict:
        """Diagnostic complet d'un document"""
        
        print("🔍 DIAGNOSTIC DES RELATIONS")
        print("=" * 50)
        
        # 1. Statistiques générales
        stats = self._analyze_text_stats(text)
        print(f"📊 Statistiques du texte:")
        print(f"   - Longueur: {stats['length']:,} caractères")
        print(f"   - Lignes: {stats['lines']:,}")
        print(f"   - Mots: {stats['words']:,}")
        
        # 2. Analyse des mots-clés de relation
        keyword_analysis = self._analyze_relation_keywords(text)
        print(f"\n🔤 Mots-clés de relation trouvés:")
        for keyword, count in keyword_analysis.items():
            if count > 0:
                print(f"   - '{keyword}': {count} occurrences")
        
        # 3. Test des patterns simples
        pattern_results = self._test_simple_patterns(text)
        print(f"\n🎯 Test des patterns simples:")
        for pattern_name, matches in pattern_results.items():
            print(f"   - {pattern_name}: {len(matches)} matches")
            if matches:
                # Afficher quelques exemples
                for i, match in enumerate(matches[:3]):
                    print(f"     Exemple {i+1}: '{match[0][:80]}...'")
        
        # 4. Échantillon de texte pour inspection manuelle
        sample_text = self._extract_sample_with_relations(text, sample_size)
        print(f"\n📝 Échantillon de texte avec relations potentielles:")
        print("-" * 40)
        print(sample_text)
        print("-" * 40)
        
        # 5. Problèmes détectés
        issues = self._detect_common_issues(text, keyword_analysis, pattern_results)
        print(f"\n⚠️ Problèmes détectés:")
        for issue in issues:
            print(f"   - {issue}")
        
        # 6. Recommandations
        recommendations = self._generate_recommendations(issues, keyword_analysis)
        print(f"\n💡 Recommandations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
        
        return {
            'stats': stats,
            'keywords': keyword_analysis,
            'patterns': pattern_results,
            'sample': sample_text,
            'issues': issues,
            'recommendations': recommendations
        }
    
    def _analyze_text_stats(self, text: str) -> Dict:
        """Analyse statistique du texte"""
        return {
            'length': len(text),
            'lines': len(text.split('\n')),
            'words': len(text.split()),
            'unique_words': len(set(text.lower().split())),
            'avg_line_length': len(text) / max(1, len(text.split('\n')))
        }
    
    def _analyze_relation_keywords(self, text: str) -> Dict[str, int]:
        """Analyse la fréquence des mots-clés de relation"""
        text_lower = text.lower()
        keyword_counts = {}
        
        for keyword in self.relation_keywords:
            # Compter avec frontières de mots
            pattern = r'\b' + re.escape(keyword) + r'\b'
            count = len(re.findall(pattern, text_lower))
            keyword_counts[keyword] = count
        
        return keyword_counts
    
    def _test_simple_patterns(self, text: str) -> Dict[str, List[Tuple]]:
        """Teste des patterns simplifiés"""
        results = {}
        
        for pattern_name, pattern in self.test_patterns.items():
            matches = []
            for match in pattern.finditer(text):
                matches.append((
                    match.group(0),  # Texte complet du match
                    match.groups(),  # Groupes capturés
                    match.span()     # Position
                ))
            results[pattern_name] = matches
        
        return results
    
    def _extract_sample_with_relations(self, text: str, sample_size: int) -> str:
        """Extrait un échantillon contenant des relations potentielles"""
        
        # Chercher des segments avec mots-clés de relation
        segments_with_relations = []
        
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Vérifier si la ligne contient des mots-clés de relation
            has_relation = any(keyword in line_lower for keyword in self.relation_keywords[:10])  # Top 10 keywords
            
            if has_relation and len(line.strip()) > 20:
                # Ajouter contexte (ligne précédente et suivante)
                start_idx = max(0, i-1)
                end_idx = min(len(lines), i+2)
                context = '\n'.join(lines[start_idx:end_idx])
                segments_with_relations.append(context)
        
        # Prendre les premiers segments jusqu'à la taille demandée
        sample = ""
        for segment in segments_with_relations:
            if len(sample) + len(segment) < sample_size:
                sample += segment + "\n\n"
            else:
                break
        
        return sample[:sample_size] if sample else text[:sample_size]
    
    def _detect_common_issues(self, text: str, keywords: Dict, patterns: Dict) -> List[str]:
        """Détecte les problèmes courants"""
        issues = []
        
        # 1. Peu de mots-clés de relation
        total_relation_words = sum(keywords.values())
        if total_relation_words < 10:
            issues.append(f"Très peu de mots-clés de relation ({total_relation_words}). Le texte OCR pourrait être de mauvaise qualité.")
        
        # 2. Aucun pattern simple détecté
        total_simple_matches = sum(len(matches) for matches in patterns.values())
        if total_simple_matches == 0:
            issues.append("Aucun pattern simple détecté. Les patterns sont probablement trop stricts pour ce format de document.")
        
        # 3. Texte très long avec peu de structure
        if len(text) > 100000 and text.count('\n') < 100:
            issues.append("Texte très long avec peu de sauts de ligne. Problème possible de formatage OCR.")
        
        # 4. Caractères parasites
        weird_chars = re.findall(r'[^\w\s\-\'\.,;:()àáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]', text)
        if len(weird_chars) > len(text) * 0.01:  # Plus de 1% de caractères étranges
            issues.append(f"Nombreux caractères parasites détectés ({len(weird_chars)}). OCR de mauvaise qualité.")
        
        # 5. Mots coupés ou collés
        broken_words = re.findall(r'\b[a-z]+[A-Z][a-z]+\b', text)  # motCollés
        if len(broken_words) > 20:
            issues.append(f"Mots coupés/collés détectés ({len(broken_words)}). Problème de segmentation OCR.")
        
        return issues
    
    def _generate_recommendations(self, issues: List[str], keywords: Dict) -> List[str]:
        """Génère des recommandations basées sur les problèmes détectés"""
        recommendations = []
        
        # Recommandations générales
        if any("OCR" in issue for issue in issues):
            recommendations.append("Améliorer la préparation du texte avec un nettoyage OCR plus agressif")
            recommendations.append("Utiliser des patterns plus flexibles avec tolérance aux erreurs OCR")
        
        if any("pattern" in issue.lower() for issue in issues):
            recommendations.append("Assouplir les patterns regex (moins de contraintes de ponctuation)")
            recommendations.append("Tester d'abord avec des patterns très simples puis les complexifier")
        
        # Recommandations basées sur les mots-clés
        if keywords.get('fils', 0) > 0 or keywords.get('fille', 0) > 0:
            recommendations.append("Optimiser les patterns de filiation (fils/fille de)")
        
        if keywords.get('épouse', 0) > 0 or keywords.get('femme', 0) > 0:
            recommendations.append("Optimiser les patterns de mariage (épouse/femme de)")
        
        if keywords.get('parrain', 0) > 0 or keywords.get('marraine', 0) > 0:
            recommendations.append("Optimiser les patterns de parrainage")
        
        # Recommandations techniques
        recommendations.append("Utiliser la fonction debug_relationship_parser() pour tester des patterns spécifiques")
        recommendations.append("Commencer par des patterns très permissifs puis affiner progressivement")
        
        return recommendations

def debug_relationship_parser(text_sample: str, relationship_parser=None) -> None:
    """Fonction de debug rapide pour tester les patterns de relation"""
    
    print("🔧 DEBUG RELATIONSHIP PARSER")
    print("=" * 40)
    
    if relationship_parser is None:
        # Créer un parser de base pour test
        from config.settings import ParserConfig
        from parsers.relationship.basic_relationship_parser import RelationshipParser
        relationship_parser = RelationshipParser(ParserConfig())
    
    # Test du debug intégré si disponible
    if hasattr(relationship_parser, 'debug_text_analysis'):
        debug_info = relationship_parser.debug_text_analysis(text_sample)
        
        print("📋 Analyse des patterns:")
        for pattern_name, count in debug_info['patterns_matches'].items():
            if isinstance(count, int) and count > 0:
                print(f"   - {pattern_name}: {count} matches")
                # Afficher exemple si disponible
                example_key = f"{pattern_name}_example"
                if example_key in debug_info['patterns_matches']:
                    print(f"     Exemple: '{debug_info['patterns_matches'][example_key]}'")
        
        print(f"\n🔗 Relations trouvées: {len(debug_info['relationships_found'])}")
        for rel in debug_info['relationships_found']:
            print(f"   - {rel['type']}: {rel}")
        
        print(f"\n👥 Noms extraits: {len(debug_info['names_extracted'])}")
        for name in debug_info['names_extracted'][:10]:  # Premiers 10
            print(f"   - '{name}'")
    
    else:
        # Test manuel simple
        relationships = relationship_parser.extract_relationships(text_sample)
        print(f"Relations trouvées: {len(relationships)}")
        for rel in relationships:
            print(f"   - {rel}")

# Fonction utilitaire pour améliorer le texte OCR
def clean_ocr_text(text: str) -> str:
    """Nettoyage basique du texte OCR pour améliorer la détection de relations"""
    
    # 1. Corriger les erreurs OCR communes
    ocr_corrections = {
        r'\bl\b': 'I',  # l minuscule -> I majuscule
        r'\b1\b': 'I',  # 1 -> I
        r'\b0\b': 'O',  # 0 -> O
        r'œ': 'oe',     # œ -> oe
        r'ﬁ': 'fi',     # ligature fi
        r'ﬂ': 'fl',     # ligature fl
        r'…': '...',    # ellipse
        r'—': '-',      # tiret long
        r'"': '"',      # guillemets
        r'"': '"',
    }
    
    for pattern, replacement in ocr_corrections.items():
        text = re.sub(pattern, replacement, text)
    
    # 2. Normaliser les espaces
    text = re.sub(r'\s+', ' ', text)  # Espaces multiples -> simple
    text = re.sub(r'\n\s*\n', '\n', text)  # Lignes vides multiples
    
    # 3. Corriger la ponctuation
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # motCollé -> mot Collé
    text = re.sub(r'([.,;:])([A-Za-z])', r'\1 \2', text)  # Ajouter espace après ponctuation
    
    return text.strip()

# Script de test principal
if __name__ == "__main__":
    import sys
    
    # Exemple d'utilisation
    sample_text = """
    1651, 23 janv., inh., dans l'église, de Françoise Picot, épouse de Charles Le Boucher, 
    éc., sr du Hausey, avocat du Roi au siège de Saint-Sylvain; 24 oct., naissance, bapt., 
    et, le 21 nov., cérémonies du bapt. de Charlotte, fille de Jean Le Boucher, éc., sr de 
    La Granville, et de Françoise Varin; marr.: Perrette Dupré; parr.: Charles Le Boucher, 
    éc., sr du Hozey, conseiller et avocat du Roi à Saint-Sylvain.
    """
    
    if len(sys.argv) > 1:
        # Lire un fichier si fourni
        try:
            with open(sys.argv[1], 'r', encoding='utf-8') as f:
                sample_text = f.read()
        except Exception as e:
            print(f"Erreur lecture fichier: {e}")
            sys.exit(1)
    
    # Lancer le diagnostic
    debugger = RelationshipDebugger()
    result = debugger.diagnose_document(sample_text)
    
    print(f"\n✅ Diagnostic terminé!")
    print(f"Consultez les recommandations ci-dessus pour améliorer la détection de relations.")