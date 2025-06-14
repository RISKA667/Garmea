# parser_entraineur.py
"""
Système d'entraînement et d'amélioration des parsers basé sur dataset.txt
Utilise les exemples de référence pour corriger et améliorer la qualité des extractions

Version 1.0.0 - Apprentissage supervisé des patterns généalogiques
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass
import logging

@dataclass
class ExempleReference:
    """Exemple de référence extrait du dataset.txt"""
    texte_original: str
    texte_corrige: str
    extractions: List[Dict]
    periode: str
    type_document: str
    numero_texte: int

@dataclass
class PatternAppris:
    """Pattern appris à partir des exemples"""
    regex: str
    type_relation: str
    confiance: float
    exemples: List[str]
    description: str

class DatasetParser:
    """Parse le fichier dataset.txt pour extraire les exemples de référence"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def parser_dataset(self, fichier_dataset: str) -> List[ExempleReference]:
        """
        Parse le fichier dataset.txt et extrait tous les exemples
        
        Args:
            fichier_dataset: Chemin vers dataset.txt
            
        Returns:
            List[ExempleReference]: Liste des exemples parsés
        """
        
        if not Path(fichier_dataset).exists():
            self.logger.error(f"Fichier dataset non trouvé: {fichier_dataset}")
            return []
        
        with open(fichier_dataset, 'r', encoding='utf-8') as f:
            contenu = f.read()
        
        # Diviser en sections TEXTE
        sections = re.split(r'TEXTE \d+', contenu)[1:]  # Ignorer avant le premier TEXTE
        
        exemples = []
        for i, section in enumerate(sections, 1):
            exemple = self._parser_section_texte(section, i)
            if exemple:
                exemples.append(exemple)
        
        self.logger.info(f"Parsé {len(exemples)} exemples du dataset")
        return exemples
    
    def _parser_section_texte(self, section: str, numero: int) -> Optional[ExempleReference]:
        """Parse une section TEXTE individuelle"""
        
        try:
            # Extraire texte original
            match_original = re.search(r'Texte original\s*:(.*?)Retranscription complète', section, re.DOTALL)
            texte_original = match_original.group(1).strip() if match_original else ""
            
            # Extraire retranscription
            match_retrans = re.search(r'Retranscription complète\s*:(.*?)Format des résultats', section, re.DOTALL)
            texte_corrige = match_retrans.group(1).strip() if match_retrans else ""
            
            # Extraire période et type
            periode = self._extraire_periode(texte_corrige)
            type_document = self._extraire_type_document(texte_corrige)
            
            # Extraire les numérotations des personnes
            match_extractions = re.search(r'Format des résultats.*?:(.*?)(?=Notes à prendre|$)', section, re.DOTALL)
            extractions_text = match_extractions.group(1) if match_extractions else ""
            
            extractions = self._parser_extractions_numerotees(extractions_text)
            
            return ExempleReference(
                texte_original=texte_original,
                texte_corrige=texte_corrige,
                extractions=extractions,
                periode=periode,
                type_document=type_document,
                numero_texte=numero
            )
            
        except Exception as e:
            self.logger.warning(f"Erreur parsing section {numero}: {e}")
            return None
    
    def _extraire_periode(self, texte: str) -> str:
        """Extrait la période du texte"""
        # Chercher des patterns comme [Acte entre 1770-1778] ou années
        match_periode = re.search(r'\[.*?(\d{4}[-–]\d{4}|\d{4}).*?\]', texte)
        if match_periode:
            return match_periode.group(1)
        
        # Chercher des années isolées
        annees = re.findall(r'\b1[0-9]{3}\b', texte)
        if annees:
            return f"{min(annees)}-{max(annees)}" if len(set(annees)) > 1 else annees[0]
        
        return "période indéterminée"
    
    def _extraire_type_document(self, texte: str) -> str:
        """Détermine le type de document"""
        if any(word in texte.lower() for word in ['baptême', 'mariage', 'inhumation', 'curé']):
            return "registre_paroissial"
        elif any(word in texte.lower() for word in ['seigneurie', 'châtellenie', 'fief', 'duc']):
            return "acte_seigneurial"
        elif any(word in texte.lower() for word in ['notaire', 'tabellion', 'contrat']):
            return "acte_notarie"
        else:
            return "document_historique"
    
    def _parser_extractions_numerotees(self, extractions_text: str) -> List[Dict]:
        """Parse les extractions numérotées du format utilisateur"""
        
        extractions = []
        
        # Chercher les lignes numérotées (1., 2., etc.)
        lignes = re.findall(r'(\d+)\.\s*([^\n]+)', extractions_text)
        
        for numero, contenu in lignes:
            extraction = self._analyser_ligne_extraction(contenu.strip(), int(numero))
            if extraction:
                extractions.append(extraction)
        
        return extractions
    
    def _analyser_ligne_extraction(self, ligne: str, numero: int) -> Optional[Dict]:
        """Analyse une ligne d'extraction pour identifier le type de relation"""
        
        extraction = {
            'numero': numero,
            'texte_original': ligne,
            'type': 'personne',
            'entites': {},
            'metadata': {}
        }
        
        # Patterns pour différents types de relations
        
        # Filiation: "X, fils de Y" ou "X, fille de Y et Z"
        filiation_pattern = r'([^,]+),\s*(?:fils|fille)\s+de\s+([^,]+?)(?:\s+et\s+(?:de\s+)?([^,\[]+))?'
        match_filiation = re.search(filiation_pattern, ligne, re.IGNORECASE)
        
        if match_filiation:
            extraction['type'] = 'filiation'
            extraction['entites'] = {
                'enfant': self._nettoyer_nom(match_filiation.group(1)),
                'pere': self._nettoyer_nom(match_filiation.group(2)),
                'mere': self._nettoyer_nom(match_filiation.group(3)) if match_filiation.group(3) else None
            }
            return extraction
        
        # Mariage: "X, épouse de Y" ou "X, femme de Y"
        mariage_pattern = r'([^,]+),\s*(?:épouse|femme|veuve)\s+de\s+([^,\[]+)'
        match_mariage = re.search(mariage_pattern, ligne, re.IGNORECASE)
        
        if match_mariage:
            extraction['type'] = 'mariage'
            extraction['entites'] = {
                'epouse': self._nettoyer_nom(match_mariage.group(1)),
                'epoux': self._nettoyer_nom(match_mariage.group(2))
            }
            return extraction
        
        # Parrainage: "X, parrain" ou "X, marraine"
        parrainage_pattern = r'([^,]+),\s*(parrain|marraine)'
        match_parrainage = re.search(parrainage_pattern, ligne, re.IGNORECASE)
        
        if match_parrainage:
            extraction['type'] = 'parrainage'
            extraction['entites'] = {
                'personne': self._nettoyer_nom(match_parrainage.group(1)),
                'role': match_parrainage.group(2).lower()
            }
            return extraction
        
        # Personne simple avec informations
        # Extraire le nom principal
        nom_principal = ligne.split(',')[0].strip()
        if nom_principal:
            extraction['entites'] = {'nom': self._nettoyer_nom(nom_principal)}
            
            # Extraire métadonnées (titres, professions, dates, lieux)
            metadata = self._extraire_metadata_personne(ligne)
            extraction['metadata'] = metadata
        
        return extraction
    
    def _nettoyer_nom(self, nom: str) -> str:
        """Nettoie un nom selon les règles du dataset"""
        if not nom:
            return ""
        
        # Supprimer les informations entre crochets et parenthèses
        nom = re.sub(r'\[.*?\]|\(.*?\)', '', nom)
        
        # Nettoyer les espaces multiples
        nom = re.sub(r'\s+', ' ', nom).strip()
        
        return nom
    
    def _extraire_metadata_personne(self, ligne: str) -> Dict:
        """Extrait les métadonnées d'une personne (titres, professions, dates, lieux)"""
        
        metadata = {}
        
        # Titres
        titres = re.findall(r'\b(?:duc|comte|baron|sieur|seigneur|écuyer|chevalier)\b', ligne, re.IGNORECASE)
        if titres:
            metadata['titres'] = list(set(titres))
        
        # Professions
        professions = re.findall(r'\b(?:curé|prêtre|avocat|greffier|tabellion|meunier|sage-femme|matrone)\b', ligne, re.IGNORECASE)
        if professions:
            metadata['professions'] = list(set(professions))
        
        # Dates
        dates = re.findall(r'\b\d{2}-\d{2}-\d{4}\b|\b\d{4}\b', ligne)
        if dates:
            metadata['dates'] = dates
        
        # Lieux
        lieux = re.findall(r'\b(?:de|à|en)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', ligne)
        if lieux:
            metadata['lieux'] = [lieu[0] if isinstance(lieu, tuple) else lieu for lieu in lieux]
        
        return metadata

class ParserEntraineur:
    """Système d'entraînement qui améliore les parsers basé sur les exemples de référence"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.patterns_appris = []
        self.regles_correction = {}
        self.dictionnaire_noms = set()
        self.titres_normalises = {}
        
    def entrainer_sur_dataset(self, fichier_dataset: str) -> Dict:
        """
        Entraîne le système sur le dataset de référence
        
        Args:
            fichier_dataset: Chemin vers dataset.txt
            
        Returns:
            Dict: Statistiques d'entraînement
        """
        
        print("ENTRAÎNEMENT DES PARSERS SUR DATASET")
        print("=" * 40)
        
        # Parser le dataset
        dataset_parser = DatasetParser()
        exemples = dataset_parser.parser_dataset(fichier_dataset)
        
        if not exemples:
            print("Aucun exemple trouvé dans le dataset")
            return {}
        
        print(f"Exemples chargés: {len(exemples)}")
        
        # Apprendre les patterns
        self._apprendre_patterns_filiation(exemples)
        self._apprendre_patterns_mariage(exemples)
        self._apprendre_patterns_parrainage(exemples)
        
        # Construire le dictionnaire de noms
        self._construire_dictionnaire_noms(exemples)
        
        # Apprendre les règles de normalisation
        self._apprendre_regles_normalisation(exemples)
        
        # Construire les règles de correction OCR
        self._apprendre_corrections_ocr(exemples)
        
        stats = {
            'exemples_traites': len(exemples),
            'patterns_appris': len(self.patterns_appris),
            'noms_dictionnaire': len(self.dictionnaire_noms),
            'regles_correction': len(self.regles_correction)
        }
        
        self._afficher_statistiques_entrainement(stats)
        
        return stats
    
    def _apprendre_patterns_filiation(self, exemples: List[ExempleReference]):
        """Apprend les patterns de filiation des exemples"""
        
        patterns_filiation = []
        
        for exemple in exemples:
            for extraction in exemple.extractions:
                if extraction['type'] == 'filiation':
                    # Analyser le texte original pour créer des patterns
                    texte_ref = extraction['texte_original']
                    
                    # Créer des variants du pattern
                    pattern_variants = self._generer_variants_filiation(texte_ref)
                    patterns_filiation.extend(pattern_variants)
        
        # Consolider les patterns similaires
        patterns_consolides = self._consolider_patterns(patterns_filiation, 'filiation')
        
        self.patterns_appris.extend(patterns_consolides)
        print(f"Patterns filiation appris: {len(patterns_consolides)}")
    
    def _apprendre_patterns_mariage(self, exemples: List[ExempleReference]):
        """Apprend les patterns de mariage des exemples"""
        
        patterns_mariage = []
        
        for exemple in exemples:
            for extraction in exemple.extractions:
                if extraction['type'] == 'mariage':
                    texte_ref = extraction['texte_original']
                    pattern_variants = self._generer_variants_mariage(texte_ref)
                    patterns_mariage.extend(pattern_variants)
        
        patterns_consolides = self._consolider_patterns(patterns_mariage, 'mariage')
        self.patterns_appris.extend(patterns_consolides)
        print(f"Patterns mariage appris: {len(patterns_consolides)}")
    
    def _apprendre_patterns_parrainage(self, exemples: List[ExempleReference]):
        """Apprend les patterns de parrainage des exemples"""
        
        patterns_parrainage = []
        
        for exemple in exemples:
            for extraction in exemple.extractions:
                if extraction['type'] == 'parrainage':
                    texte_ref = extraction['texte_original']
                    pattern_variants = self._generer_variants_parrainage(texte_ref)
                    patterns_parrainage.extend(pattern_variants)
        
        patterns_consolides = self._consolider_patterns(patterns_parrainage, 'parrainage')
        self.patterns_appris.extend(patterns_consolides)
        print(f"Patterns parrainage appris: {len(patterns_consolides)}")
    
    def _generer_variants_filiation(self, texte_ref: str) -> List[Dict]:
        """Génère des variants de patterns pour les filiations"""
        
        variants = []
        
        # Pattern de base pour "X, fils de Y"
        base_pattern = r'([A-Z][a-zA-Z\s\-]+),\s*(?:fils|fille)\s+de\s+([A-Z][a-zA-Z\s\-]+)'
        
        variants.append({
            'regex': base_pattern,
            'type': 'filiation',
            'exemple': texte_ref,
            'description': 'Filiation simple père'
        })
        
        # Pattern avec mère "X, fils de Y et de Z"
        pattern_avec_mere = r'([A-Z][a-zA-Z\s\-]+),\s*(?:fils|fille)\s+de\s+([A-Z][a-zA-Z\s\-]+)\s+et\s+(?:de\s+)?([A-Z][a-zA-Z\s\-]+)'
        
        variants.append({
            'regex': pattern_avec_mere,
            'type': 'filiation',
            'exemple': texte_ref,
            'description': 'Filiation avec père et mère'
        })
        
        return variants
    
    def _generer_variants_mariage(self, texte_ref: str) -> List[Dict]:
        """Génère des variants de patterns pour les mariages"""
        
        variants = []
        
        # Patterns de mariage
        patterns_mariage = [
            r'([A-Z][a-zA-Z\s\-]+),\s*épouse\s+de\s+([A-Z][a-zA-Z\s\-]+)',
            r'([A-Z][a-zA-Z\s\-]+),\s*femme\s+de\s+([A-Z][a-zA-Z\s\-]+)',
            r'([A-Z][a-zA-Z\s\-]+),\s*veuve\s+de\s+([A-Z][a-zA-Z\s\-]+)'
        ]
        
        for pattern in patterns_mariage:
            variants.append({
                'regex': pattern,
                'type': 'mariage',
                'exemple': texte_ref,
                'description': 'Relation matrimoniale'
            })
        
        return variants
    
    def _generer_variants_parrainage(self, texte_ref: str) -> List[Dict]:
        """Génère des variants de patterns pour les parrainages"""
        
        variants = []
        
        patterns_parrainage = [
            r'([A-Z][a-zA-Z\s\-]+),\s*parrain',
            r'([A-Z][a-zA-Z\s\-]+),\s*marraine',
            r'parrain[:\s]*([A-Z][a-zA-Z\s\-]+)',
            r'marraine[:\s]*([A-Z][a-zA-Z\s\-]+)'
        ]
        
        for pattern in patterns_parrainage:
            variants.append({
                'regex': pattern,
                'type': 'parrainage',
                'exemple': texte_ref,
                'description': 'Relation de parrainage'
            })
        
        return variants
    
    def _consolider_patterns(self, patterns: List[Dict], type_relation: str) -> List[PatternAppris]:
        """Consolide les patterns similaires"""
        
        # Grouper par regex similaire
        groupes = defaultdict(list)
        for pattern in patterns:
            groupes[pattern['regex']].append(pattern)
        
        patterns_consolides = []
        for regex, groupe in groupes.items():
            exemples = [p['exemple'] for p in groupe]
            confiance = len(groupe) / len(patterns)  # Plus fréquent = plus de confiance
            
            pattern_appris = PatternAppris(
                regex=regex,
                type_relation=type_relation,
                confiance=confiance,
                exemples=exemples[:5],  # Garder 5 exemples max
                description=groupe[0]['description']
            )
            
            patterns_consolides.append(pattern_appris)
        
        return patterns_consolides
    
    def _construire_dictionnaire_noms(self, exemples: List[ExempleReference]):
        """Construit un dictionnaire des noms corrects"""
        
        for exemple in exemples:
            for extraction in exemple.extractions:
                entites = extraction.get('entites', {})
                
                for key, nom in entites.items():
                    if nom and isinstance(nom, str) and len(nom) > 2:
                        # Nettoyer et ajouter au dictionnaire
                        nom_clean = re.sub(r'[^\w\s\-]', '', nom).strip()
                        if nom_clean:
                            self.dictionnaire_noms.add(nom_clean)
        
        print(f"Dictionnaire de noms: {len(self.dictionnaire_noms)} entrées")
    
    def _apprendre_regles_normalisation(self, exemples: List[ExempleReference]):
        """Apprend les règles de normalisation des noms et titres"""
        
        # Analyser les titres
        titres_trouves = defaultdict(list)
        
        for exemple in exemples:
            for extraction in exemple.extractions:
                texte = extraction['texte_original']
                
                # Chercher les abréviations et leur forme complète
                abreviations = {
                    'sr': 'sieur', 'Sr': 'sieur',
                    'sgr': 'seigneur', 'Sgr': 'seigneur',
                    'ct': 'comte', 'Ct': 'comte',
                    'd': 'duc', 'éc': 'écuyer', 'ec': 'écuyer'
                }
                
                for abrév, complet in abreviations.items():
                    if abrév in texte:
                        titres_trouves[abrév].append(complet)
        
        # Consolider les règles
        for abrév, formes in titres_trouves.items():
            self.titres_normalises[abrév] = Counter(formes).most_common(1)[0][0]
        
        print(f"Règles titres: {len(self.titres_normalises)}")
    
    def _apprendre_corrections_ocr(self, exemples: List[ExempleReference]):
        """Apprend les corrections OCR à partir des exemples"""
        
        for exemple in exemples:
            if exemple.texte_original and exemple.texte_corrige:
                # Comparer texte original vs corrigé pour apprendre les corrections
                corrections = self._extraire_corrections(exemple.texte_original, exemple.texte_corrige)
                self.regles_correction.update(corrections)
        
        print(f"Règles correction OCR: {len(self.regles_correction)}")
    
    def _extraire_corrections(self, original: str, corrige: str) -> Dict[str, str]:
        """Extrait les corrections entre deux textes"""
        
        corrections = {}
        
        # Corrections simples mot par mot
        mots_originaux = original.split()
        mots_corriges = corrige.split()
        
        # Alignement approximatif
        for i, mot_orig in enumerate(mots_originaux):
            if i < len(mots_corriges):
                mot_corr = mots_corriges[i]
                
                # Si différent et pas trop différent (même longueur environ)
                if (mot_orig != mot_corr and 
                    abs(len(mot_orig) - len(mot_corr)) <= 2 and
                    len(mot_orig) > 2):
                    corrections[mot_orig] = mot_corr
        
        return corrections
    
    def _afficher_statistiques_entrainement(self, stats: Dict):
        """Affiche les statistiques d'entraînement"""
        
        print(f"\nSTATISTIQUES D'ENTRAÎNEMENT:")
        print(f"  Exemples traités: {stats['exemples_traites']}")
        print(f"  Patterns appris: {stats['patterns_appris']}")
        print(f"  Noms référence: {stats['noms_dictionnaire']}")
        print(f"  Règles correction: {stats['regles_correction']}")
    
    def sauvegarder_modele_entraine(self, fichier_sortie: str):
        """Sauvegarde le modèle entraîné"""
        
        modele = {
            'patterns_appris': [
                {
                    'regex': p.regex,
                    'type_relation': p.type_relation,
                    'confiance': p.confiance,
                    'description': p.description,
                    'exemples': p.exemples
                }
                for p in self.patterns_appris
            ],
            'dictionnaire_noms': list(self.dictionnaire_noms),
            'titres_normalises': self.titres_normalises,
            'regles_correction': self.regles_correction,
            'metadata': {
                'date_entrainement': str(datetime.now()),
                'nb_patterns': len(self.patterns_appris),
                'nb_noms': len(self.dictionnaire_noms)
            }
        }
        
        with open(fichier_sortie, 'w', encoding='utf-8') as f:
            json.dump(modele, f, indent=2, ensure_ascii=False)
        
        print(f"Modèle sauvegardé: {fichier_sortie}")

def entrainer_parsers_sur_dataset(fichier_dataset: str = "dataset.txt", 
                                 fichier_modele: str = "modele_entraine.json") -> Dict:
    """
    Fonction principale d'entraînement
    
    Args:
        fichier_dataset: Chemin vers dataset.txt
        fichier_modele: Fichier de sortie du modèle
        
    Returns:
        Dict: Statistiques d'entraînement
    """
    
    entraineur = ParserEntraineur()
    stats = entraineur.entrainer_sur_dataset(fichier_dataset)
    
    if stats:
        entraineur.sauvegarder_modele_entraine(fichier_modele)
    
    return stats

if __name__ == "__main__":
    import sys
    from datetime import datetime
    
    print("ENTRAÎNEUR DE PARSERS GÉNÉALOGIQUES")
    print("=" * 45)
    
    fichier_dataset = sys.argv[1] if len(sys.argv) > 1 else "dataset.txt"
    
    if not Path(fichier_dataset).exists():
        print(f"Erreur: Dataset {fichier_dataset} non trouvé")
        print("Créez d'abord votre dataset.txt avec des exemples de référence")
        sys.exit(1)
    
    print(f"Entraînement sur: {fichier_dataset}")
    
    stats = entrainer_parsers_sur_dataset(fichier_dataset)
    
    if stats:
        print(f"\n🎉 Entraînement terminé avec succès!")
        print(f"📄 Modèle sauvegardé: modele_entraine.json")
        print(f"💡 Utilisez ce modèle pour améliorer vos extractions")
    else:
        print(f"❌ Échec de l'entraînement")