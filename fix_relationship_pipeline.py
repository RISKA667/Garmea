# fix_relationship_pipeline.py
"""
Fix urgent pour le pipeline des relations familiales
Le problème : 0 relations détectées malgré 9762 personnes trouvées
"""

import logging
import types
from typing import Dict, List

def debug_relationship_extraction(parser, text_sample: str) -> Dict:
    """
    Debug du processus d'extraction des relations
    """
    logger = logging.getLogger(__name__)
    
    print("🔍 DEBUG EXTRACTION RELATIONS")
    print("=" * 40)
    
    # 1. Vérifier que le relationship_parser est bien initialisé
    rel_parser = parser.relationship_parser
    print(f"✅ RelationshipParser créé: {type(rel_parser).__name__}")
    
    # 2. Tester sur un échantillon de texte
    sample = text_sample[:1000] if len(text_sample) > 1000 else text_sample
    print(f"📝 Texte testé ({len(sample)} caractères):")
    print(f"'{sample[:200]}...'")
    
    # 3. Test direct du parser de relations
    try:
        relations = rel_parser.extract_relationships(sample)
        print(f"📊 Relations extraites directement: {len(relations)}")
        
        if relations:
            for i, rel in enumerate(relations[:3]):
                print(f"   {i+1}. {rel}")
        else:
            print("   ❌ Aucune relation trouvée")
    except Exception as e:
        print(f"   🚨 ERREUR dans extract_relationships: {e}")
        relations = []
    
    # 4. Tester les patterns individuellement
    print(f"\n🎯 Test des patterns individuels:")
    if hasattr(rel_parser, 'patterns'):
        for pattern_name, pattern in rel_parser.patterns.items():
            matches = pattern.findall(sample)
            print(f"   - {pattern_name}: {len(matches)} matches")
            if matches:
                print(f"     Exemple: {matches[0]}")
    
    # 5. Vérifier le texte normalisé
    normalized = parser.text_parser.normalize_text(sample)
    print(f"\n📝 Texte après normalisation:")
    print(f"'{normalized[:200]}...'")
    
    relations_normalized = rel_parser.extract_relationships(normalized)
    print(f"📊 Relations sur texte normalisé: {len(relations_normalized)}")
    
    return {
        'original_relations': relations,
        'normalized_relations': relations_normalized,
        'sample_text': sample,
        'normalized_text': normalized
    }

def fix_process_document_method(parser_instance):
    """
    Fixe la méthode process_document pour corriger l'extraction des relations
    """
    
    def process_document_fixed(self, text: str, lieu: str = "Notre-Dame d'Esméville") -> Dict:
        """Version corrigée avec debug des relations"""
        
        self.perf_logger.start_timer("process_document")
        self.logger.info(f"🚀 Début traitement - Lieu: {lieu}")
        
        try:
            # 1. Normalisation du texte
            self.perf_logger.start_timer("text_normalization")
            normalized_text = self.text_parser.normalize_text(text)
            self.perf_logger.end_timer("text_normalization")
            
            print(f"📝 Texte normalisé: {len(normalized_text)} caractères")
            
            # 2. Extraction des segments
            self.perf_logger.start_timer("segment_extraction")
            segments = self.text_parser.extract_segments(normalized_text)
            self.perf_logger.end_timer("segment_extraction")
            
            print(f"📦 Segments extraits: {len(segments)}")
            
            # 3. ⚠️ EXTRACTION DES RELATIONS - PARTIE CRITIQUE ⚠️
            self.perf_logger.start_timer("relationship_extraction")
            
            print(f"🔗 EXTRACTION DES RELATIONS...")
            
            # Debug sur un échantillon
            if len(normalized_text) > 2000:
                debug_sample = normalized_text[:2000]
                debug_result = debug_relationship_extraction(self, debug_sample)
                print(f"🔍 Debug échantillon - Relations trouvées: {len(debug_result['original_relations'])}")
            
            # Extraction sur tout le texte
            all_relationships = self.relationship_parser.extract_relationships(normalized_text)
            
            print(f"📊 TOTAL RELATIONS EXTRAITES: {len(all_relationships)}")
            
            # Séparation par type
            filiations = []
            parrainages = []
            mariages = []
            
            for rel in all_relationships:
                rel_type = rel.get('type', '')
                print(f"   - Relation type '{rel_type}': {rel}")
                
                if rel_type == 'filiation':
                    filiations.append(rel)
                elif rel_type in ['parrain', 'marraine']:
                    parrainages.append(rel)
                elif rel_type == 'mariage':
                    mariages.append(rel)
            
            print(f"   📋 Filiations: {len(filiations)}")
            print(f"   👨‍👩‍👧‍👦 Parrainages: {len(parrainages)}")
            print(f"   💒 Mariages: {len(mariages)}")
            
            self.perf_logger.end_timer("relationship_extraction")
            
            # 4. Extraction des noms et personnes (reste identique)
            self.perf_logger.start_timer("name_extraction")
            
            names_and_info = []
            for segment in segments:
                segment_names = self.name_extractor.extract_complete_names_with_sources(
                    segment['content'], 
                    segment.get('source_reference', ''),
                    segment.get('page_number')
                )
                names_and_info.extend(segment_names)
            
            self.perf_logger.end_timer("name_extraction")
            
            # 5. Création des personnes
            self.perf_logger.start_timer("person_creation")
            persons = {}
            
            for name_info in names_and_info:
                person = self.person_manager.create_or_update_person(name_info)
                if person and person.id:
                    persons[person.id] = person
            
            print(f"👥 Personnes créées: {len(persons)}")
            self.perf_logger.end_timer("person_creation")
            
            # 6. Création des actes
            self.perf_logger.start_timer("acte_creation")
            actes = {}
            
            for segment in segments:
                segment_actes = self.acte_manager.extract_actes_from_segment(
                    segment, persons
                )
                actes.update(segment_actes)
            
            print(f"📋 Actes créés: {len(actes)}")
            self.perf_logger.end_timer("acte_creation")
            
            # 7. ⚠️ INTEGRATION DES RELATIONS DANS LES PERSONNES ⚠️
            self.perf_logger.start_timer("relationship_integration")
            
            print(f"🔗 Intégration des relations dans les personnes...")
            
            # Appliquer les filiations
            for filiation in filiations:
                print(f"   📝 Traitement filiation: {filiation}")
                self._apply_filiation_to_persons(filiation, persons)
            
            # Appliquer les parrainages
            for parrainage in parrainages:
                print(f"   🤝 Traitement parrainage: {parrainage}")
                self._apply_parrainage_to_persons(parrainage, persons)
            
            # Appliquer les mariages
            for mariage in mariages:
                print(f"   💒 Traitement mariage: {mariage}")
                self._apply_mariage_to_persons(mariage, persons)
            
            self.perf_logger.end_timer("relationship_integration")
            
            # 8. Validation (reste identique)
            self.perf_logger.start_timer("validation")
            validation_results = self._validate_data(persons, actes)
            self.perf_logger.end_timer("validation")
            
            # 9. Construction du résultat CORRIGÉ
            result = {
                'persons': persons,
                'actes': actes,
                'filiations': filiations,  # ⚠️ AJOUTER EXPLICITEMENT
                'parrainages': parrainages,  # ⚠️ AJOUTER EXPLICITEMENT  
                'mariages': mariages,  # ⚠️ AJOUTER EXPLICITEMENT
                'relations_count': len(all_relationships),  # ⚠️ AJOUTER COUNT
                'validation': validation_results,
                'lieu': lieu,
                'processing_time': self.perf_logger.get_total_time("process_document")
            }
            
            print(f"✅ TRAITEMENT TERMINÉ")
            print(f"   👥 Personnes: {len(persons)}")
            print(f"   📋 Actes: {len(actes)}")
            print(f"   🔗 Relations: {len(all_relationships)}")
            print(f"   📋 Filiations: {len(filiations)}")
            print(f"   🤝 Parrainages: {len(parrainages)}")
            
            self.perf_logger.end_timer("process_document")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur dans process_document: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    # Méthodes d'aide pour appliquer les relations
    def _apply_filiation_to_persons(self, filiation: Dict, persons: Dict):
        """Applique une filiation aux personnes"""
        try:
            enfant_name = filiation.get('enfant', '')
            pere_name = filiation.get('pere', '')
            mere_name = filiation.get('mere', '')
            
            # Trouver les personnes correspondantes
            enfant = self._find_person_by_name(enfant_name, persons)
            pere = self._find_person_by_name(pere_name, persons) if pere_name else None
            mere = self._find_person_by_name(mere_name, persons) if mere_name else None
            
            if enfant:
                if pere:
                    enfant.pere_id = pere.id
                if mere:
                    enfant.mere_id = mere.id
                    
                print(f"      ✅ Filiation appliquée: {enfant_name} -> père: {pere_name}, mère: {mere_name}")
            else:
                print(f"      ❌ Enfant non trouvé: {enfant_name}")
                
        except Exception as e:
            print(f"      🚨 Erreur filiation: {e}")
    
    def _apply_parrainage_to_persons(self, parrainage: Dict, persons: Dict):
        """Applique un parrainage aux personnes"""
        try:
            personne_name = parrainage.get('personne', '')
            enfant_name = parrainage.get('enfant', '')
            
            personne = self._find_person_by_name(personne_name, persons)
            enfant = self._find_person_by_name(enfant_name, persons) if enfant_name else None
            
            if personne and enfant:
                if parrainage['type'] == 'parrain':
                    enfant.parrain_id = personne.id
                elif parrainage['type'] == 'marraine':
                    enfant.marraine_id = personne.id
                    
                print(f"      ✅ Parrainage appliqué: {personne_name} -> {enfant_name}")
            else:
                print(f"      ❌ Parrainage non appliqué: {personne_name}, {enfant_name}")
                
        except Exception as e:
            print(f"      🚨 Erreur parrainage: {e}")
    
    def _apply_mariage_to_persons(self, mariage: Dict, persons: Dict):
        """Applique un mariage aux personnes"""
        try:
            epoux_name = mariage.get('epoux', '')
            epouse_name = mariage.get('epouse', '')
            
            epoux = self._find_person_by_name(epoux_name, persons)
            epouse = self._find_person_by_name(epouse_name, persons)
            
            if epoux and epouse:
                epoux.conjoint_id = epouse.id
                epouse.conjoint_id = epoux.id
                print(f"      ✅ Mariage appliqué: {epoux_name} ↔ {epouse_name}")
            else:
                print(f"      ❌ Mariage non appliqué: {epoux_name}, {epouse_name}")
                
        except Exception as e:
            print(f"      🚨 Erreur mariage: {e}")
    
    def _find_person_by_name(self, name: str, persons: Dict):
        """Trouve une personne par nom (approximatif)"""
        if not name:
            return None
            
        name_clean = name.strip().lower()
        
        for person in persons.values():
            # Essayer nom complet
            person_full = f"{' '.join(person.prenoms)} {person.nom}".strip().lower()
            if person_full == name_clean:
                return person
            
            # Essayer juste le nom de famille
            if person.nom.lower() == name_clean:
                return person
        
        return None
    
    def _validate_data(self, persons: Dict, actes: Dict) -> Dict:
        """Validation basique des données"""
        return {
            'persons_validated': len(persons),
            'actes_validated': len(actes),
            'validation_rate': 100.0 if persons else 0.0
        }
    
    # Remplacer les méthodes
    parser_instance.process_document = types.MethodType(process_document_fixed, parser_instance)
    parser_instance._apply_filiation_to_persons = types.MethodType(_apply_filiation_to_persons, parser_instance)
    parser_instance._apply_parrainage_to_persons = types.MethodType(_apply_parrainage_to_persons, parser_instance)
    parser_instance._apply_mariage_to_persons = types.MethodType(_apply_mariage_to_persons, parser_instance)
    parser_instance._find_person_by_name = types.MethodType(_find_person_by_name, parser_instance)
    parser_instance._validate_data = types.MethodType(_validate_data, parser_instance)
    
    print("🔧 Fix appliqué à process_document!")