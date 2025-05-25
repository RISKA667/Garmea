#!/usr/bin/env python3
"""
Script de correction rapide pour les noms incomplets et relance de l'analyse
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire au PATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def corriger_person_manager():
    """Applique le correctif temporaire au PersonManager"""
    
    try:
        # Import dynamique pour patcher la méthode
        from database.person_manager import PersonManager
        from core.models import Person
        from typing import Dict, Optional
        import logging
        
        # Méthode corrigée
        def get_or_create_person_fixed(self, nom: str, prenom: str, 
                                     extra_info: Optional[Dict] = None) -> Person:
            """Version corrigée pour gérer les noms incomplets"""
            
            if extra_info is None:
                extra_info = {}
            
            try:
                if not isinstance(nom, str) or not isinstance(prenom, str):
                    error_msg = f"nom et prenom doivent être des strings, reçu: nom={type(nom)}, prenom={type(prenom)}"
                    self.logger.error(error_msg)
                    self.stats['validation_errors'] += 1
                    raise TypeError(error_msg)
                
                # CORRECTION: Gestion des noms incomplets
                nom = nom.strip() if nom else ""
                prenom = prenom.strip() if prenom else ""
                
                # Si le nom est vide, essayer de le déduire
                if not nom and prenom:
                    if len(prenom) >= 3:
                        context = extra_info.get('context', '')
                        if 'fille de' in context.lower():
                            nom = "fille"
                        else:
                            nom = "Inconnu"
                        self.logger.info(f"CORRECTION: Nom manquant pour '{prenom}', utilisation de '{nom}'")
                    else:
                        raise ValueError(f"Prénom trop court sans nom: '{prenom}'")
                
                # Si le prénom est vide
                elif not prenom and nom:
                    if len(nom) >= 3:
                        prenom = "Inconnu"
                        self.logger.info(f"CORRECTION: Prénom manquant pour '{nom}', utilisation de '{prenom}'")
                    else:
                        raise ValueError(f"Nom trop court sans prénom: '{nom}'")
                
                # Validation finale avec extraction depuis nom_complet si nécessaire
                if not nom or not prenom or len(nom) < 2 or len(prenom) < 2:
                    nom_complet = extra_info.get('nom_complet', '')
                    if nom_complet and len(nom_complet) > 4:
                        parties = nom_complet.split()
                        if len(parties) >= 2:
                            prenom = parties[0]
                            nom = ' '.join(parties[1:])
                            self.logger.info(f"CORRECTION: Extraction depuis nom_complet '{nom_complet}'")
                        else:
                            prenom = parties[0]
                            nom = "Inconnu"
                            self.logger.info(f"CORRECTION: Prénom seul '{nom_complet}' -> nom générique")
                    else:
                        # Dernière chance : valeurs par défaut
                        if not prenom or len(prenom) < 2:
                            prenom = "Inconnu"
                        if not nom or len(nom) < 2:
                            nom = "Inconnu"
                        self.logger.warning(f"CORRECTION ULTIME: {prenom} {nom}")
                
                # Nettoyer extra_info
                clean_extra_info = self._clean_extra_info(extra_info)
                
                # Continuer avec le traitement normal
                candidates = self._find_similar_persons(nom, prenom, clean_extra_info)
                
                if candidates:
                    best_candidate = self._select_best_candidate(candidates, clean_extra_info)
                    if best_candidate:
                        self._merge_person_info(best_candidate, clean_extra_info)
                        self.stats['persons_merged'] += 1
                        return best_candidate
                
                # Créer nouvelle personne
                person = self._create_new_person(nom, prenom, clean_extra_info)
                self.stats['persons_created'] += 1
                return person
                
            except Exception as e:
                self.logger.error(f"Erreur get_or_create_person pour {prenom} {nom}: {e}")
                
                # Création fallback
                try:
                    fallback_nom = nom if nom and len(nom) >= 2 else "Inconnu"
                    fallback_prenom = prenom if prenom and len(prenom) >= 2 else "Inconnu"
                    
                    person = Person(
                        id=self.person_id_counter,
                        nom=fallback_nom,
                        prenom=fallback_prenom,
                        confidence_score=0.3
                    )
                    
                    self.persons[self.person_id_counter] = person
                    self._add_to_index(person)
                    self.person_id_counter += 1
                    
                    self.logger.info(f"CRÉATION FALLBACK: {person.full_name}")
                    return person
                    
                except Exception as fallback_error:
                    self.logger.error(f"Échec création fallback: {fallback_error}")
                    raise e
        
        # Patcher la méthode
        PersonManager.get_or_create_person = get_or_create_person_fixed
        print("✅ Correctif appliqué avec succès")
        return True
        
    except Exception as e:
        print(f"❌ Erreur application correctif: {e}")
        return False

def relancer_analyse_pages_extraites():
    """Relance l'analyse sur les pages déjà identifiées comme bonnes"""
    
    print("🔄 RELANCE DE L'ANALYSE AVEC CORRECTIF")
    print("=" * 45)
    
    try:
        # Appliquer le correctif
        if not corriger_person_manager():
            return False
        
        # Pages identifiées comme ayant du bon contenu (from previous run)
        bonnes_pages = [314, 258, 118, 301, 577, 471, 304, 326, 69, 400, 
                       502, 176, 533, 520, 91, 317, 569, 580, 324, 299]
        
        # Extraire le contenu de ces pages
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
        
        # Traitement généalogique avec correctif
        from main import GenealogyParser
        from exporters.report_generator import ReportGenerator
        
        print(f"\n⚙️  TRAITEMENT GÉNÉALOGIQUE AVEC CORRECTIF")
        print("=" * 45)
        
        parser = GenealogyParser()
        resultat = parser.process_document(texte_registres, "Archives du Calvados")
        
        print(f"\n🎉 RÉSULTATS CORRIGÉS")
        print("=" * 25)
        ReportGenerator.print_formatted_results(resultat)
        
        # Statistiques détaillées
        stats = parser.get_global_statistics()
        print(f"\n📊 STATISTIQUES FINALES")
        print("=" * 25)
        print(f"Pages traitées: {len(bonnes_pages)}")
        print(f"Personnes identifiées: {stats['persons']['total_persons']}")
        print(f"Actes créés: {stats['actes']['total_actes']}")
        print(f"Relations familiales: {len(resultat.get('filiations', []))}")
        print(f"Parrainages: {len(resultat.get('parrainages', []))}")
        print(f"Corrections appliquées: {stats['persons']['gender_corrections']}")
        
        # Sauvegarder les résultats
        sauvegarder_resultats_corriges(resultat, stats)
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur relance: {e}")
        import traceback
        traceback.print_exc()
        return False

def sauvegarder_resultats_corriges(resultat, stats):
    """Sauvegarde les résultats corrigés"""
    
    try:
        import json
        from datetime import datetime
        
        output_dir = Path("resultats_corriges")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Rapport complet
        rapport_file = output_dir / f"rapport_genealogique_corrige_{timestamp}.txt"
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
        
        # Statistiques JSON
        stats_file = output_dir / f"statistiques_corriges_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 RÉSULTATS SAUVEGARDÉS")
        print("=" * 25)
        print(f"📋 Rapport: {rapport_file}")
        print(f"📊 Stats: {stats_file}")
        
    except Exception as e:
        print(f"⚠️  Erreur sauvegarde: {e}")

if __name__ == "__main__":
    print("🔧 CORRECTIF ET RELANCE DE L'ANALYSE")
    print("=" * 40)
    
    success = relancer_analyse_pages_extraites()
    
    if success:
        print(f"\n🎉 ANALYSE TERMINÉE AVEC SUCCÈS!")
        print("Les résultats corrigés sont maintenant disponibles.")
    else:
        print(f"\n❌ Erreur durant l'analyse corrigée")