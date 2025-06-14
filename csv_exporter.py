# csv_exporter.py
"""
Exporteur CSV complet pour les résultats du Smart PDF Analyzer
Crée des fichiers CSV organisés et triés dans le dossier RESULT

Version 1.0.0
Auteur: Smart PDF Analyzer Team
"""

import csv
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd

class CSVExporter:
    """Exporteur CSV pour les résultats généalogiques"""
    
    def __init__(self, output_dir: str = "RESULT"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Statistiques d'export
        self.export_stats = {
            'filiations_exportees': 0,
            'mariages_exportes': 0,
            'parrainages_exportes': 0,
            'personnes_exportees': 0,
            'fichiers_crees': []
        }
        
        print(f"Exporteur CSV initialisé - Dossier: {self.output_dir.absolute()}")
    
    def exporter_resultats_complets(self, resultats: Dict) -> Dict[str, str]:
        """
        Exporte tous les résultats en fichiers CSV organisés
        
        Args:
            resultats: Résultats du Smart PDF Analyzer
            
        Returns:
            Dict: Chemins des fichiers créés
        """
        
        print("Export des résultats en CSV")
        print("=" * 30)
        
        fichiers_crees = {}
        
        # Extraire les données généalogiques
        genealogique = resultats.get('resultats_genealogiques', {})
        
        # 1. Export des filiations
        filiations = genealogique.get('filiations', [])
        if filiations:
            fichier_filiations = self._exporter_filiations(filiations)
            fichiers_crees['filiations'] = fichier_filiations
            print(f"Filiations exportées: {len(filiations)} -> {fichier_filiations}")
        
        # 2. Export des mariages
        mariages = genealogique.get('mariages', [])
        if mariages:
            fichier_mariages = self._exporter_mariages(mariages)
            fichiers_crees['mariages'] = fichier_mariages
            print(f"Mariages exportés: {len(mariages)} -> {fichier_mariages}")
        
        # 3. Export des parrainages
        parrainages = genealogique.get('parrainages', [])
        if parrainages:
            fichier_parrainages = self._exporter_parrainages(parrainages)
            fichiers_crees['parrainages'] = fichier_parrainages
            print(f"Parrainages exportés: {len(parrainages)} -> {fichier_parrainages}")
        
        # 4. Export des personnes
        personnes = genealogique.get('personnes_extraites', [])
        if personnes:
            fichier_personnes = self._exporter_personnes(personnes)
            fichiers_crees['personnes'] = fichier_personnes
            print(f"Personnes exportées: {len(personnes)} -> {fichier_personnes}")
        
        # 5. Export du résumé général
        fichier_resume = self._exporter_resume_general(resultats)
        fichiers_crees['resume'] = fichier_resume
        print(f"Résumé exporté: {fichier_resume}")
        
        # 6. Export consolidé (toutes les relations dans un fichier)
        fichier_consolide = self._exporter_consolide(genealogique)
        fichiers_crees['consolide'] = fichier_consolide
        print(f"Fichier consolidé créé: {fichier_consolide}")
        
        # 7. Créer un index des fichiers
        self._creer_index_fichiers(fichiers_crees, resultats)
        
        print(f"\nExport terminé - {len(fichiers_crees)} fichiers créés")
        return fichiers_crees
    
    def _exporter_filiations(self, filiations: List[Dict]) -> str:
        """Exporte les filiations en CSV trié"""
        
        filename = self.output_dir / "filiations.csv"
        
        # Préparation des données
        rows = []
        for i, filiation in enumerate(filiations, 1):
            row = {
                'ID': i,
                'Enfant': filiation.get('enfant', ''),
                'Père': filiation.get('pere', ''),
                'Mère': filiation.get('mere', ''),
                'Source_Texte': self._nettoyer_texte(filiation.get('source_text', '')),
                'Position_Debut': filiation.get('position', [0, 0])[0] if filiation.get('position') else 0,
                'Position_Fin': filiation.get('position', [0, 0])[1] if filiation.get('position') else 0,
                'Confiance': filiation.get('confiance', 0.5)
            }
            rows.append(row)
        
        # Tri par nom de l'enfant, puis du père
        rows.sort(key=lambda x: (x['Enfant'].lower(), x['Père'].lower()))
        
        # Écriture CSV
        fieldnames = ['ID', 'Enfant', 'Père', 'Mère', 'Source_Texte', 'Position_Debut', 'Position_Fin', 'Confiance']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        self.export_stats['filiations_exportees'] = len(rows)
        self.export_stats['fichiers_crees'].append(str(filename))
        
        return str(filename)
    
    def _exporter_mariages(self, mariages: List[Dict]) -> str:
        """Exporte les mariages en CSV trié"""
        
        filename = self.output_dir / "mariages.csv"
        
        rows = []
        for i, mariage in enumerate(mariages, 1):
            row = {
                'ID': i,
                'Épouse': mariage.get('epouse', ''),
                'Époux': mariage.get('epoux', ''),
                'Statut': mariage.get('statut', 'mariée'),
                'Source_Texte': self._nettoyer_texte(mariage.get('source_text', '')),
                'Position_Debut': mariage.get('position', [0, 0])[0] if mariage.get('position') else 0,
                'Position_Fin': mariage.get('position', [0, 0])[1] if mariage.get('position') else 0,
                'Confiance': mariage.get('confiance', 0.6)
            }
            rows.append(row)
        
        # Tri par nom de l'épouse, puis de l'époux
        rows.sort(key=lambda x: (x['Épouse'].lower(), x['Époux'].lower()))
        
        fieldnames = ['ID', 'Épouse', 'Époux', 'Statut', 'Source_Texte', 'Position_Debut', 'Position_Fin', 'Confiance']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        self.export_stats['mariages_exportes'] = len(rows)
        self.export_stats['fichiers_crees'].append(str(filename))
        
        return str(filename)
    
    def _exporter_parrainages(self, parrainages: List[Dict]) -> str:
        """Exporte les parrainages en CSV trié"""
        
        filename = self.output_dir / "parrainages.csv"
        
        rows = []
        for i, parrainage in enumerate(parrainages, 1):
            row = {
                'ID': i,
                'Type': parrainage.get('type', ''),
                'Personne': parrainage.get('personne', ''),
                'Source_Texte': self._nettoyer_texte(parrainage.get('source_text', '')),
                'Position_Debut': parrainage.get('position', [0, 0])[0] if parrainage.get('position') else 0,
                'Position_Fin': parrainage.get('position', [0, 0])[1] if parrainage.get('position') else 0,
                'Confiance': parrainage.get('confiance', 0.4)
            }
            rows.append(row)
        
        # Tri par type puis par nom de personne
        rows.sort(key=lambda x: (x['Type'], x['Personne'].lower()))
        
        fieldnames = ['ID', 'Type', 'Personne', 'Source_Texte', 'Position_Debut', 'Position_Fin', 'Confiance']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        self.export_stats['parrainages_exportes'] = len(rows)
        self.export_stats['fichiers_crees'].append(str(filename))
        
        return str(filename)
    
    def _exporter_personnes(self, personnes: List[Dict]) -> str:
        """Exporte la liste des personnes en CSV trié"""
        
        filename = self.output_dir / "personnes.csv"
        
        rows = []
        for i, personne in enumerate(personnes, 1):
            # Analyser le nom pour séparer prénom(s) et nom de famille
            nom_complet = personne.get('nom_complet', '')
            prenoms, nom_famille = self._analyser_nom_complet(nom_complet)
            
            row = {
                'ID': i,
                'Nom_Complet': nom_complet,
                'Prénoms': prenoms,
                'Nom_Famille': nom_famille,
                'Occurrences': personne.get('occurrences', 1),
                'Nom_Original': personne.get('nom_original', nom_complet),
                'Variantes': ', '.join(personne.get('variantes', [nom_complet]))
            }
            rows.append(row)
        
        # Tri par nom de famille puis prénoms
        rows.sort(key=lambda x: (x['Nom_Famille'].lower(), x['Prénoms'].lower()))
        
        fieldnames = ['ID', 'Nom_Complet', 'Prénoms', 'Nom_Famille', 'Occurrences', 'Nom_Original', 'Variantes']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        self.export_stats['personnes_exportees'] = len(rows)
        self.export_stats['fichiers_crees'].append(str(filename))
        
        return str(filename)
    
    def _exporter_consolide(self, genealogique: Dict) -> str:
        """Exporte toutes les relations dans un fichier consolidé"""
        
        filename = self.output_dir / "relations_consolidees.csv"
        
        rows = []
        relation_id = 1
        
        # Filiations
        for filiation in genealogique.get('filiations', []):
            row = {
                'ID': relation_id,
                'Type_Relation': 'Filiation',
                'Personne_Principale': filiation.get('enfant', ''),
                'Personne_Liée_1': filiation.get('pere', ''),
                'Personne_Liée_2': filiation.get('mere', ''),
                'Rôle_1': 'Père',
                'Rôle_2': 'Mère',
                'Source_Texte': self._nettoyer_texte(filiation.get('source_text', '')),
                'Confiance': filiation.get('confiance', 0.5)
            }
            rows.append(row)
            relation_id += 1
        
        # Mariages
        for mariage in genealogique.get('mariages', []):
            row = {
                'ID': relation_id,
                'Type_Relation': 'Mariage',
                'Personne_Principale': mariage.get('epouse', ''),
                'Personne_Liée_1': mariage.get('epoux', ''),
                'Personne_Liée_2': '',
                'Rôle_1': 'Époux',
                'Rôle_2': '',
                'Source_Texte': self._nettoyer_texte(mariage.get('source_text', '')),
                'Confiance': mariage.get('confiance', 0.6)
            }
            rows.append(row)
            relation_id += 1
        
        # Parrainages
        for parrainage in genealogique.get('parrainages', []):
            row = {
                'ID': relation_id,
                'Type_Relation': 'Parrainage',
                'Personne_Principale': parrainage.get('personne', ''),
                'Personne_Liée_1': '',
                'Personne_Liée_2': '',
                'Rôle_1': parrainage.get('type', ''),
                'Rôle_2': '',
                'Source_Texte': self._nettoyer_texte(parrainage.get('source_text', '')),
                'Confiance': parrainage.get('confiance', 0.4)
            }
            rows.append(row)
            relation_id += 1
        
        # Tri par type de relation puis par personne principale
        rows.sort(key=lambda x: (x['Type_Relation'], x['Personne_Principale'].lower()))
        
        fieldnames = ['ID', 'Type_Relation', 'Personne_Principale', 'Personne_Liée_1', 'Personne_Liée_2', 
                     'Rôle_1', 'Rôle_2', 'Source_Texte', 'Confiance']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        self.export_stats['fichiers_crees'].append(str(filename))
        
        return str(filename)
    
    def _exporter_resume_general(self, resultats: Dict) -> str:
        """Exporte un résumé général des résultats"""
        
        filename = self.output_dir / "resume_general.csv"
        
        # Préparer les statistiques
        genealogique = resultats.get('resultats_genealogiques', {})
        statistiques = resultats.get('statistiques', {})
        qualite = resultats.get('qualite_extraction', {})
        performance = resultats.get('performance', {})
        
        rows = [
            {'Métrique': 'Pages analysées', 'Valeur': resultats.get('pages_analysees', 0)},
            {'Métrique': 'Pages de registres', 'Valeur': resultats.get('pages_registres', 0)},
            {'Métrique': 'Total relations', 'Valeur': genealogique.get('relations_count', 0)},
            {'Métrique': 'Filiations', 'Valeur': len(genealogique.get('filiations', []))},
            {'Métrique': 'Mariages', 'Valeur': len(genealogique.get('mariages', []))},
            {'Métrique': 'Parrainages', 'Valeur': len(genealogique.get('parrainages', []))},
            {'Métrique': 'Personnes extraites', 'Valeur': len(genealogique.get('personnes_extraites', []))},
            {'Métrique': 'Qualité des données', 'Valeur': qualite.get('qualite_donnees', 'Non évaluée')},
            {'Métrique': 'Taux de validation (%)', 'Valeur': qualite.get('taux_validation', 0)},
            {'Métrique': 'Temps total (s)', 'Valeur': performance.get('total_processing', 0)},
            {'Métrique': 'Date export', 'Valeur': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['Métrique', 'Valeur'])
            writer.writeheader()
            writer.writerows(rows)
        
        self.export_stats['fichiers_crees'].append(str(filename))
        
        return str(filename)
    
    def _creer_index_fichiers(self, fichiers_crees: Dict[str, str], resultats: Dict):
        """Crée un fichier index listant tous les fichiers créés"""
        
        filename = self.output_dir / "INDEX.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("INDEX DES FICHIERS EXPORTÉS\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Date d'export: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source: Smart PDF Analyzer v3.0.0\n\n")
            
            f.write("FICHIERS CRÉÉS:\n")
            f.write("-" * 20 + "\n")
            
            for type_fichier, chemin in fichiers_crees.items():
                filename_only = Path(chemin).name
                f.write(f"{type_fichier.upper()}: {filename_only}\n")
            
            f.write(f"\nSTATISTIQUES D'EXPORT:\n")
            f.write("-" * 25 + "\n")
            for key, value in self.export_stats.items():
                if key != 'fichiers_crees':
                    f.write(f"{key.replace('_', ' ').title()}: {value}\n")
            
            genealogique = resultats.get('resultats_genealogiques', {})
            f.write(f"\nSTATISTIQUES GÉNÉRALES:\n")
            f.write("-" * 28 + "\n")
            f.write(f"Total relations extraites: {genealogique.get('relations_count', 0)}\n")
            f.write(f"Pages analysées: {resultats.get('pages_analysees', 0)}\n")
            f.write(f"Pages de registres: {resultats.get('pages_registres', 0)}\n")
            
            f.write(f"\nDESCRIPTION DES FICHIERS:\n")
            f.write("-" * 30 + "\n")
            f.write("filiations.csv: Relations parent-enfant triées par nom\n")
            f.write("mariages.csv: Relations matrimoniales triées par épouse\n")
            f.write("parrainages.csv: Relations de parrainage triées par type\n")
            f.write("personnes.csv: Liste des personnes triées par nom de famille\n")
            f.write("relations_consolidees.csv: Toutes les relations dans un fichier\n")
            f.write("resume_general.csv: Statistiques et métriques générales\n")
    
    def _nettoyer_texte(self, texte: str) -> str:
        """Nettoie un texte pour l'export CSV"""
        if not texte:
            return ""
        
        # Supprimer les retours à la ligne et caractères problématiques
        clean = texte.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        clean = ' '.join(clean.split())  # Normaliser les espaces
        
        # Limiter la longueur pour lisibilité
        if len(clean) > 200:
            clean = clean[:197] + "..."
        
        return clean
    
    def _analyser_nom_complet(self, nom_complet: str) -> tuple:
        """Analyse un nom complet pour séparer prénoms et nom de famille"""
        if not nom_complet:
            return "", ""
        
        parts = nom_complet.split()
        if len(parts) == 1:
            return parts[0], ""
        elif len(parts) == 2:
            return parts[0], parts[1]
        else:
            # Assumer que le dernier mot est le nom de famille
            prenoms = ' '.join(parts[:-1])
            nom_famille = parts[-1]
            return prenoms, nom_famille

def exporter_vers_csv(resultats: Dict, dossier_output: str = "RESULT") -> Dict[str, str]:
    """
    Fonction principale d'export vers CSV
    
    Args:
        resultats: Résultats du Smart PDF Analyzer
        dossier_output: Dossier de destination
        
    Returns:
        Dict: Chemins des fichiers créés
    """
    
    exporter = CSVExporter(dossier_output)
    fichiers_crees = exporter.exporter_resultats_complets(resultats)
    
    return fichiers_crees

def exporter_depuis_json(fichier_json: str, dossier_output: str = "RESULT") -> Dict[str, str]:
    """
    Exporte vers CSV depuis un fichier JSON de résultats
    
    Args:
        fichier_json: Chemin vers le fichier JSON des résultats
        dossier_output: Dossier de destination
        
    Returns:
        Dict: Chemins des fichiers créés
    """
    
    with open(fichier_json, 'r', encoding='utf-8') as f:
        resultats = json.load(f)
    
    return exporter_vers_csv(resultats, dossier_output)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Mode fichier JSON
        fichier_json = sys.argv[1]
        dossier_output = sys.argv[2] if len(sys.argv) > 2 else "RESULT"
        
        if not Path(fichier_json).exists():
            print(f"Erreur: Fichier {fichier_json} non trouvé")
            sys.exit(1)
        
        print(f"Export CSV depuis {fichier_json}")
        fichiers_crees = exporter_depuis_json(fichier_json, dossier_output)
        
        print(f"\nExport terminé:")
        for type_fichier, chemin in fichiers_crees.items():
            print(f"  {type_fichier}: {chemin}")
    
    else:
        print("Usage:")
        print("  python csv_exporter.py resultats.json [dossier_output]")
        print("  python csv_exporter.py resultats.json RESULT")