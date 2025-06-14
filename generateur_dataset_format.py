# generateur_dataset_format.py
"""
Générateur de dataset au format spécialisé pour entraînement d'IA
Basé sur le format dataset.txt de l'utilisateur

Input: Résultats Smart PDF Analyzer + textes originaux
Output: Dataset.txt formaté comme les exemples fournis
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

class GenerateurDatasetFormate:
    """Générateur de dataset au format spécialisé de l'utilisateur"""
    
    def __init__(self):
        self.compteur_texte = 1
        self.instructions_ia = {
            'titres': {
                'duc': 'd',
                'comte': 'ct', 
                'sieur': 'sr',
                'seigneur': 'sgr'
            },
            'formatage': [
                "Le nom de famille doit être écrit en MAJUSCULE afin de bien le différencier des prénoms",
                "Le titre de comte a toujours un 'c' minuscule, son abréviation la plus courante est 'ct' ou 'Ct'",
                "Le titre de duc 'd' minuscule. Sieur ou sieur, abréviation 'sr'. Seigneur ou seigneur, abréviation 'sgr'",
                "Souligner en hyperlien les lieux en situant géographiquement grâce à DicoTopo"
            ]
        }
    
    def generer_dataset_complet(self, dossier_result: str = "RESULT", 
                               fichier_texte_original: str = None) -> str:
        """
        Génère un dataset au format spécialisé
        
        Args:
            dossier_result: Dossier contenant les résultats Smart PDF Analyzer
            fichier_texte_original: Texte original du PDF (optionnel)
            
        Returns:
            str: Chemin du fichier dataset généré
        """
        
        print("GÉNÉRATION DU DATASET FORMATÉ")
        print("=" * 35)
        
        # Charger les données du Smart PDF Analyzer
        donnees = self._charger_donnees_analyzer(dossier_result)
        
        if not donnees:
            print("Aucune donnée trouvée")
            return None
        
        # Créer le fichier dataset
        fichier_dataset = Path(dossier_result) / "dataset_formate.txt"
        
        with open(fichier_dataset, 'w', encoding='utf-8') as f:
            self._ecrire_entete_dataset(f)
            
            # Générer les textes formatés
            self._generer_textes_formates(donnees, f, fichier_texte_original)
            
            # Ajouter les instructions pour l'IA
            self._ecrire_instructions_ia(f)
        
        print(f"Dataset formaté créé: {fichier_dataset}")
        return str(fichier_dataset)
    
    def _charger_donnees_analyzer(self, dossier_result: str) -> Dict:
        """Charge les données du Smart PDF Analyzer"""
        
        donnees = {
            'filiations': [],
            'mariages': [],
            'parrainages': [],
            'personnes': [],
            'metadata': {}
        }
        
        dossier = Path(dossier_result)
        
        # Charger les CSV
        fichiers_csv = {
            'filiations': dossier / "filiations.csv",
            'mariages': dossier / "mariages.csv", 
            'parrainages': dossier / "parrainages.csv",
            'personnes': dossier / "personnes.csv"
        }
        
        for type_donnee, fichier in fichiers_csv.items():
            if fichier.exists():
                import csv
                with open(fichier, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    donnees[type_donnee] = list(reader)
                print(f"Chargé {len(donnees[type_donnee])} {type_donnee}")
        
        return donnees
    
    def _ecrire_entete_dataset(self, f):
        """Écrit l'en-tête du dataset"""
        f.write("DATASET D'ENTRAÎNEMENT - EXTRACTION GÉNÉALOGIQUE\n")
        f.write("=" * 55 + "\n\n")
        f.write(f"Généré automatiquement le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("Source: Smart PDF Analyzer v3.0.0\n")
        f.write("Format: Texte Original → Retranscription → Extractions structurées\n\n")
    
    def _generer_textes_formates(self, donnees: Dict, f, fichier_texte_original: str = None):
        """Génère les textes formatés selon le modèle de l'utilisateur"""
        
        # Regrouper les données par contexte/source
        contextes = self._regrouper_par_contexte(donnees)
        
        for i, contexte in enumerate(contextes, 1):
            self._ecrire_texte_formate(f, i, contexte, fichier_texte_original)
    
    def _regrouper_par_contexte(self, donnees: Dict) -> List[Dict]:
        """Regroupe les données par contexte (page, source, etc.)"""
        
        contextes = []
        
        # Analyser les sources textuelles pour regrouper
        sources_uniques = set()
        
        # Collecter toutes les sources
        for type_relation in ['filiations', 'mariages', 'parrainages']:
            for relation in donnees[type_relation]:
                source = relation.get('Source_Texte', '')
                if source and len(source) > 50:  # Sources substantielles
                    sources_uniques.add(source[:200])  # Limiter pour regroupement
        
        # Créer des contextes basés sur les sources les plus riches
        sources_triees = sorted(sources_uniques, key=len, reverse=True)
        
        for i, source in enumerate(sources_triees[:10]):  # Limiter à 10 exemples
            contexte = {
                'id': i + 1,
                'source_text': source,
                'relations': self._extraire_relations_de_source(source, donnees),
                'personnes': self._extraire_personnes_de_source(source, donnees),
                'periode': self._extraire_periode_de_source(source),
                'type_document': self._determiner_type_document(source)
            }
            
            if contexte['relations'] or contexte['personnes']:
                contextes.append(contexte)
        
        return contextes
    
    def _ecrire_texte_formate(self, f, numero: int, contexte: Dict, fichier_original: str = None):
        """Écrit un texte formaté selon le modèle"""
        
        f.write(f"TEXTE {numero}\n")
        f.write("Texte original :\n\n")
        
        # Simuler un texte original avec erreurs OCR typiques
        texte_original = self._simuler_texte_ocr(contexte['source_text'])
        f.write(f"{texte_original}\n\n")
        
        f.write("Retranscription complète :\n\n")
        
        # Retranscription corrigée
        periode = contexte.get('periode', 'XVIIe-XVIIIe siècle')
        type_doc = contexte.get('type_document', 'registre paroissial')
        
        f.write(f"[{type_doc} - {periode}]\n")
        f.write(f"{contexte['source_text']}\n\n")
        
        f.write("Format des résultats et modèles d'extractions :\n\n")
        
        # Extractions structurées
        self._ecrire_extractions_structurees(f, contexte)
        
        f.write("\n" + "="*80 + "\n\n")
    
    def _simuler_texte_ocr(self, texte_propre: str) -> str:
        """Simule des erreurs OCR typiques pour créer un 'texte original'"""
        
        erreurs_ocr = {
            'baptême': 'babtesme',
            'église': 'eglise', 
            'sieur': 'sr',
            'monsieur': 'monsr',
            'madame': 'Madame',
            'mariage': 'mariage',
            'inhumation': 'inh.',
            'présence': 'présence',
            'témoin': 'tesmoing',
            'lequel': 'lequel',
            'laquelle': 'laquelle',
            'demeurant': 'demeurant',
            'ù': 'u',
            'è': 'e',
            'é': 'e'
        }
        
        texte_ocr = texte_propre
        for correct, erreur in erreurs_ocr.items():
            # Appliquer quelques erreurs aléatoirement
            if correct in texte_ocr.lower():
                texte_ocr = texte_ocr.replace(correct, erreur)
        
        return texte_ocr
    
    def _extraire_relations_de_source(self, source: str, donnees: Dict) -> List[Dict]:
        """Extrait les relations liées à une source donnée"""
        
        relations = []
        
        for type_relation in ['filiations', 'mariages', 'parrainages']:
            for relation in donnees[type_relation]:
                if source[:100] in relation.get('Source_Texte', ''):
                    relations.append({
                        'type': type_relation[:-1],  # Enlever le 's'
                        'data': relation
                    })
        
        return relations
    
    def _extraire_personnes_de_source(self, source: str, donnees: Dict) -> List[str]:
        """Extrait les personnes mentionnées dans une source"""
        
        personnes_mentionnees = []
        
        for personne in donnees['personnes']:
            nom = personne.get('Nom_Complet', '')
            if nom and nom.lower() in source.lower():
                personnes_mentionnees.append(nom)
        
        return personnes_mentionnees[:10]  # Limiter
    
    def _extraire_periode_de_source(self, source: str) -> str:
        """Extrait la période à partir du texte source"""
        
        # Chercher des années dans le texte
        annees = re.findall(r'\b1[0-9]{3}\b', source)
        
        if annees:
            annees_int = [int(a) for a in annees]
            min_annee = min(annees_int)
            max_annee = max(annees_int)
            
            if min_annee == max_annee:
                return str(min_annee)
            else:
                return f"{min_annee}-{max_annee}"
        
        return "XVIIe-XVIIIe siècle"
    
    def _determiner_type_document(self, source: str) -> str:
        """Détermine le type de document basé sur le contenu"""
        
        indicateurs = {
            'registre paroissial': ['baptême', 'mariage', 'inhumation', 'curé', 'église', 'paroisse'],
            'acte seigneurial': ['seigneurie', 'châtellenie', 'fief', 'duc', 'comte', 'baron'],
            'acte notarié': ['notaire', 'tabellion', 'contrat', 'testament'],
            'acte judiciaire': ['bailliage', 'tribunal', 'procès', 'sentence']
        }
        
        scores = {}
        for type_doc, mots_cles in indicateurs.items():
            score = sum(1 for mot in mots_cles if mot.lower() in source.lower())
            scores[type_doc] = score
        
        return max(scores, key=scores.get) if scores else "document historique"
    
    def _ecrire_extractions_structurees(self, f, contexte: Dict):
        """Écrit les extractions structurées au format de l'utilisateur"""
        
        numero_personne = 1
        
        # Traiter les relations
        for relation in contexte['relations']:
            
            if relation['type'] == 'filiation':
                data = relation['data']
                enfant = data.get('Enfant', '')
                pere = data.get('Père', '')
                mere = data.get('Mère', '')
                
                if enfant:
                    f.write(f"{numero_personne}. {self._formater_nom(enfant)}")
                    if pere or mere:
                        parents = []
                        if pere:
                            parents.append(f"fils de {self._formater_nom(pere)}")
                        if mere:
                            parents.append(f"et de {self._formater_nom(mere)}")
                        f.write(f", {' '.join(parents)}")
                    f.write("\n")
                    numero_personne += 1
            
            elif relation['type'] == 'mariage':
                data = relation['data']
                epouse = data.get('Épouse', '')
                epoux = data.get('Époux', '')
                
                if epouse and epoux:
                    f.write(f"{numero_personne}. {self._formater_nom(epouse)}, épouse de {self._formater_nom(epoux)}\n")
                    numero_personne += 1
            
            elif relation['type'] == 'parrainage':
                data = relation['data']
                personne = data.get('Personne', '')
                type_parrainage = data.get('Type', 'parrain')
                
                if personne:
                    f.write(f"{numero_personne}. {self._formater_nom(personne)}, {type_parrainage}\n")
                    numero_personne += 1
        
        # Ajouter les personnes additionnelles
        for personne in contexte['personnes']:
            if numero_personne <= 20:  # Limiter
                f.write(f"{numero_personne}. {self._formater_nom(personne)}\n")
                numero_personne += 1
    
    def _formater_nom(self, nom: str) -> str:
        """Formate un nom selon les règles de l'utilisateur"""
        
        if not nom:
            return ""
        
        # Séparer prénoms et nom de famille
        parties = nom.split()
        
        if len(parties) >= 2:
            # Dernier mot = nom de famille en MAJUSCULES
            prenoms = ' '.join(parties[:-1])
            nom_famille = parties[-1].upper()
            return f"{prenoms} {nom_famille}"
        else:
            return nom.upper()
    
    def _ecrire_instructions_ia(self, f):
        """Écrit les instructions pour l'IA"""
        
        f.write("INSTRUCTIONS POUR L'IA :\n")
        f.write("=" * 25 + "\n\n")
        
        f.write("RÈGLES DE FORMATAGE :\n")
        for instruction in self.instructions_ia['formatage']:
            f.write(f"- {instruction}\n")
        
        f.write(f"\nABRÉVIATIONS DES TITRES :\n")
        for titre, abrev in self.instructions_ia['titres'].items():
            f.write(f"- {titre} → {abrev}\n")
        
        f.write(f"\nEXEMPLES DE FORMATAGE :\n")
        f.write("- Jean DUPONT, sieur de Montclair\n")
        f.write("- Marie LE BOUCHER, fille de Pierre LE BOUCHER et Anne MARTIN\n")
        f.write("- François d'HARCOURT, duc d'Harcourt, comte de Lillebonne\n")

def generer_dataset_formate(dossier_result: str = "RESULT") -> str:
    """
    Fonction principale pour générer le dataset formaté
    
    Args:
        dossier_result: Dossier contenant les résultats Smart PDF Analyzer
        
    Returns:
        str: Chemin du fichier dataset généré
    """
    
    generateur = GenerateurDatasetFormate()
    return generateur.generer_dataset_complet(dossier_result)

if __name__ == "__main__":
    import sys
    
    print("GÉNÉRATEUR DATASET FORMATÉ")
    print("=" * 30)
    
    dossier = sys.argv[1] if len(sys.argv) > 1 else "RESULT"
    
    if not Path(dossier).exists():
        print(f"Erreur: Dossier {dossier} non trouvé")
        sys.exit(1)
    
    fichier_dataset = generer_dataset_formate(dossier)
    
    if fichier_dataset:
        print(f"\n🎉 Dataset formaté généré !")
        print(f"📄 Fichier: {fichier_dataset}")
        print(f"\n💡 Le dataset suit le format de votre dataset.txt")
        print(f"   avec extractions structurées et instructions pour l'IA")