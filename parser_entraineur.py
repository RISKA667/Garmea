#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dataset Trainer Enhanced - Entraîneur de parser généalogique avancé
Version vectorisée avec validation automatique et cache intelligent

Version: 2.0.0 - Garméa Enhanced Training System
Auteur: Système d'IA Garméa
"""

import re
import json
import hashlib
import logging
import time
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Set, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter
from functools import lru_cache, wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from abc import ABC, abstractmethod

# Imports pour la vectorisation
try:
    import numpy as np
    from scipy.spatial.distance import cosine
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    VECTORIZATION_AVAILABLE = True
except ImportError:
    VECTORIZATION_AVAILABLE = False
    print("⚠️ Vectorisation non disponible. Installez: pip install numpy scipy scikit-learn")

# ============================================================================
# MODÈLES DE DONNÉES AMÉLIORÉS
# ============================================================================

@dataclass
class PersonneExtraite:
    """Modèle pour une personne extraite du dataset"""
    nom_complet: str
    nom_famille: str
    prenoms: List[str]
    titres: List[str] = field(default_factory=list)
    professions: List[str] = field(default_factory=list)
    lieux: List[str] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    relations: List[Dict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    source_texte: str = ""
    confiance: float = 1.0
    
    # Nouveaux champs pour l'analyse avancée
    particule: str = ""
    variantes_nom: List[str] = field(default_factory=list)
    scores_validation: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-traitement après initialisation"""
        if not self.metadata:
            self.metadata = {
                'timestamp_extraction': datetime.now().isoformat(),
                'version_parser': '2.0.0'
            }

@dataclass
class ValidationResult:
    """Résultat de validation d'une extraction"""
    score_confiance: float
    erreurs_detectees: List[str] = field(default_factory=list)
    avertissements: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    valide: bool = True
    details_scoring: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class MetriquesEntrainement:
    """Métriques complètes de l'entraînement"""
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    nombre_extractions: int = 0
    temps_traitement: float = 0.0
    patterns_nouveaux: int = 0
    corrections_nouvelles: int = 0
    score_qualite_global: float = 0.0
    taux_validation: float = 0.0
    efficacite_cache: float = 0.0

@dataclass
class ExempleReference:
    """Exemple de référence enrichi du dataset"""
    numero: int
    texte_original: str
    texte_corrige: str
    personnes_extraites: List[PersonneExtraite]
    corrections_ocr: Dict[str, str] = field(default_factory=dict)
    patterns_identifies: List[str] = field(default_factory=list)
    
    # Nouveaux champs
    type_document: str = "inconnu"
    periode_historique: str = ""
    region_geographique: str = ""
    difficulte_extraction: str = "normale"  # facile, normale, difficile
    tags: List[str] = field(default_factory=list)

# ============================================================================
# CACHE INTELLIGENT ET VECTORISATION
# ============================================================================

class CacheIntelligent:
    """Cache intelligent avec gestion vectorisée"""
    
    def __init__(self, taille_max: int = 10000):
        self.cache = {}
        self.taille_max = taille_max
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache"""
        with self.lock:
            if key in self.cache:
                self.stats['hits'] += 1
                # Mettre à jour l'ordre d'accès
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            else:
                self.stats['misses'] += 1
                return None
    
    def set(self, key: str, value: Any):
        """Stocke une valeur dans le cache"""
        with self.lock:
            if len(self.cache) >= self.taille_max:
                # Éviction LRU - supprimer le plus ancien
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.stats['evictions'] += 1
            
            self.cache[key] = value
    
    def get_efficacite(self) -> float:
        """Calcule l'efficacité du cache"""
        total = self.stats['hits'] + self.stats['misses']
        return self.stats['hits'] / total if total > 0 else 0.0
    
    def clear(self):
        """Vide le cache"""
        with self.lock:
            self.cache.clear()
            self.stats = {'hits': 0, 'misses': 0, 'evictions': 0}

class VectorisateurTexte:
    """Gestionnaire de vectorisation pour l'analyse de similarité"""
    
    def __init__(self):
        self.vectorizer = None
        self.corpus_vectors = None
        self.corpus_texts = []
        self.is_fitted = False
        
        if VECTORIZATION_AVAILABLE:
            self.vectorizer = TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 3),
                stop_words=None,  # Pas de stop words pour le français historique
                lowercase=True
            )
    
    def fit(self, textes: List[str]):
        """Entraîne le vectoriseur sur un corpus"""
        if not VECTORIZATION_AVAILABLE:
            return
        
        self.corpus_texts = textes
        if len(textes) > 0:
            self.corpus_vectors = self.vectorizer.fit_transform(textes)
            self.is_fitted = True
    
    def trouver_similaires(self, texte: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Trouve les textes les plus similaires"""
        if not VECTORIZATION_AVAILABLE or not self.is_fitted:
            return []
        
        # Vectoriser le texte query
        query_vector = self.vectorizer.transform([texte])
        
        # Calculer les similarités
        similarities = cosine_similarity(query_vector, self.corpus_vectors)[0]
        
        # Obtenir les indices des plus similaires
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Seuil de similarité
                results.append((self.corpus_texts[idx], similarities[idx]))
        
        return results

# ============================================================================
# SYSTÈME DE VALIDATION AVANCÉ
# ============================================================================

class ValidateurExtraction:
    """Système de validation avancé pour les extractions"""
    
    def __init__(self):
        self.regles = self._initialiser_regles()
        self.seuils = {
            'score_minimum': 0.6,
            'score_excellent': 0.9,
            'nombre_max_erreurs': 2
        }
        
        # Bases de données de référence
        self.noms_famille_connus = {
            'HARCOURT', 'BERTHAULT', 'VAILLANT', 'HARIVEL', 'MAZURIER', 
            'PATRY', 'GUILLEBERT', 'BLAIS', 'EULDE', 'CHEVAL', 'PELLERIN',
            'JEAN', 'LORME', 'BOREL', 'JEHENNE', 'BOURGEOIS', 'HEBERT'
        }
        
        self.prenoms_historiques = {
            'Jean', 'Pierre', 'Marie', 'Anne', 'François', 'Henri', 
            'Louis', 'Antoine', 'Michel', 'Jacques', 'Nicolas',
            'Jean-Baptiste', 'Jean-François', 'Anne-Pierre', 'Henri-François',
            'Louis-François', 'Thomas', 'Perrine', 'Guillemette'
        }
        
        self.particules_nobles = {
            'de', 'du', 'des', 'le', 'la', 'les', 'von', 'van', 'd\''
        }
        
        self.patterns_suspects = [
            r'[0-9]{3,}',  # Trop de chiffres
            r'[!@#$%^&*()+=]',  # Caractères spéciaux
            r'^[a-z]+$',  # Tout en minuscules
            r'\b[A-Z]{1,2}\b',  # Initiales isolées
            r'[àâäéèêëïîôùûüÿ]{3,}',  # Trop d'accents consécutifs
        ]
    
    def _initialiser_regles(self) -> Dict[str, callable]:
        """Initialise les règles de validation"""
        return {
            'nom_famille_majuscule': self._valider_nom_famille_majuscule,
            'prenoms_historiques': self._valider_prenoms_historiques,
            'particules_correctes': self._valider_particules,
            'caracteres_suspects': self._detecter_caracteres_suspects,
            'longueur_raisonnable': self._valider_longueur,
            'coherence_historique': self._valider_coherence_historique,
            'structure_nom': self._valider_structure_nom,
            'contexte_textuel': self._valider_contexte_textuel
        }
    
    def valider(self, personne: PersonneExtraite, contexte: str = "") -> ValidationResult:
        """Valide une extraction avec scoring détaillé"""
        
        resultat = ValidationResult(score_confiance=0.5)
        scores_detailles = {}
        
        # Appliquer chaque règle
        for nom_regle, fonction_regle in self.regles.items():
            try:
                score, erreurs, avertissements, suggestions = fonction_regle(personne, contexte)
                
                # Pondération selon l'importance
                poids = self._obtenir_poids_regle(nom_regle)
                score_pondere = score * poids
                
                # Mise à jour du score global
                resultat.score_confiance += score_pondere
                scores_detailles[nom_regle] = score_pondere
                
                # Collecte des retours
                resultat.erreurs_detectees.extend(erreurs)
                resultat.avertissements.extend(avertissements)
                resultat.suggestions.extend(suggestions)
                
            except Exception as e:
                logging.warning(f"Erreur dans règle {nom_regle}: {e}")
                resultat.avertissements.append(f"Erreur validation {nom_regle}")
        
        # Normalisation du score
        resultat.score_confiance = max(0.0, min(1.0, resultat.score_confiance))
        resultat.details_scoring = scores_detailles
        
        # Détermination de la validité
        resultat.valide = (
            resultat.score_confiance >= self.seuils['score_minimum'] and
            len(resultat.erreurs_detectees) <= self.seuils['nombre_max_erreurs']
        )
        
        return resultat
    
    def _obtenir_poids_regle(self, nom_regle: str) -> float:
        """Retourne le poids d'une règle"""
        poids = {
            'nom_famille_majuscule': 0.20,
            'prenoms_historiques': 0.18,
            'particules_correctes': 0.12,
            'caracteres_suspects': 0.25,
            'longueur_raisonnable': 0.08,
            'coherence_historique': 0.10,
            'structure_nom': 0.15,
            'contexte_textuel': 0.07
        }
        return poids.get(nom_regle, 0.05)
    
    def _valider_nom_famille_majuscule(self, personne: PersonneExtraite, contexte: str) -> Tuple[float, List[str], List[str], List[str]]:
        """Valide que le nom de famille est en majuscules"""
        if personne.nom_famille.isupper():
            return 0.25, [], [], []
        else:
            return (
    -0.15, 
    [f"Nom de famille '{personne.nom_famille}' devrait être en MAJUSCULES"], 
    [], 
    [f"Suggestion: {personne.nom_famille.upper()}"]
)
    
    def _valider_prenoms_historiques(self, personne: PersonneExtraite, contexte: str) -> Tuple[float, List[str], List[str], List[str]]:
        """Valide la cohérence historique des prénoms"""
        score = 0.0
        erreurs, avertissements, suggestions = [], [], []
        
        for prenom in personne.prenoms:
            if prenom in self.prenoms_historiques:
                score += 0.08
            elif prenom.lower().title() in self.prenoms_historiques:
                score += 0.04
                avertissements.append(f"Prénom '{prenom}' - casse inhabituelle")
            else:
                # Recherche de prénoms similaires
                similaires = self._trouver_prenoms_similaires(prenom)
                if similaires:
                    avertissements.append(f"Prénom '{prenom}' non reconnu")
                    suggestions.extend([f"Similaire: {s}" for s in similaires[:2]])
                else:
                    erreurs.append(f"Prénom '{prenom}' totalement inconnu")
                    score -= 0.05
        
        return score, erreurs, avertissements, suggestions
    
    def _valider_particules(self, personne: PersonneExtraite, contexte: str) -> Tuple[float, List[str], List[str], List[str]]:
        """Valide la gestion des particules nobiliaires"""
        score = 0.0
        erreurs, avertissements, suggestions = [], [], []
        
        # Détecter les particules dans le nom complet
        mots = personne.nom_complet.lower().split()
        particules_trouvees = [mot for mot in mots if mot in self.particules_nobles]
        
        if particules_trouvees:
            score += 0.08
            
            # Vérifier que la particule n'est pas dans le nom de famille
            for particule in particules_trouvees:
                if particule in personne.nom_famille.lower():
                    erreurs.append(f"Particule '{particule}' incluse dans nom de famille")
                    suggestions.append("Séparer particule du nom de famille")
                    score -= 0.10
        
        return score, erreurs, avertissements, suggestions
    
    def _detecter_caracteres_suspects(self, personne: PersonneExtraite, contexte: str) -> Tuple[float, List[str], List[str], List[str]]:
        """Détecte les caractères suspects (erreurs OCR)"""
        score = 0.08  # Score de base si pas de problème
        erreurs, avertissements, suggestions = [], [], []
        
        nom_complet = personne.nom_complet
        
        for pattern in self.patterns_suspects:
            matches = re.findall(pattern, nom_complet)
            if matches:
                if pattern == r'[0-9]{3,}':
                    erreurs.append(f"Chiffres suspects: {matches}")
                    score -= 0.20
                elif pattern == r'[!@#$%^&*()+=]':
                    erreurs.append(f"Caractères spéciaux: {matches}")
                    score -= 0.25
                elif pattern == r'^[a-z]+$' and personne.nom_famille.islower():
                    erreurs.append("Nom famille tout en minuscules")
                    score -= 0.15
                elif pattern == r'\b[A-Z]{1,2}\b':
                    avertissements.append(f"Initiales isolées: {matches}")
                    score -= 0.05
        
        return score, erreurs, avertissements, suggestions
    
    def _valider_longueur(self, personne: PersonneExtraite, contexte: str) -> Tuple[float, List[str], List[str], List[str]]:
        """Valide la longueur des noms"""
        score = 0.0
        erreurs, avertissements, suggestions = [], [], []
        
        longueur = len(personne.nom_complet)
        
        if 8 <= longueur <= 45:
            score = 0.06
        elif longueur < 8:
            avertissements.append(f"Nom très court: {longueur} caractères")
            score = -0.02
        elif longueur > 45:
            erreurs.append(f"Nom très long: {longueur} caractères")
            score = -0.08
        
        return score, erreurs, avertissements, suggestions
    
    def _valider_coherence_historique(self, personne: PersonneExtraite, contexte: str) -> Tuple[float, List[str], List[str], List[str]]:
        """Valide la cohérence historique globale"""
        score = 0.0
        erreurs, avertissements, suggestions = [], [], []
        
        # Bonus pour nom de famille connu
        if personne.nom_famille in self.noms_famille_connus:
            score += 0.04
        
        # Bonus professions historiques
        professions_historiques = {
            'curé', 'prêtre', 'avocat', 'greffier', 'tabellion', 
            'meunier', 'sage-femme', 'matrone', 'domestique'
        }
        
        professions_trouvees = [p.lower() for p in personne.professions]
        if any(prof in professions_historiques for prof in professions_trouvees):
            score += 0.03
        
        # Bonus titres nobiliaires
        titres_nobles = {'duc', 'comte', 'baron', 'sieur', 'seigneur', 'écuyer'}
        titres_trouves = [t.lower() for t in personne.titres]
        if any(titre in titres_nobles for titre in titres_trouves):
            score += 0.02
        
        return score, erreurs, avertissements, suggestions
    
    def _valider_structure_nom(self, personne: PersonneExtraite, contexte: str) -> Tuple[float, List[str], List[str], List[str]]:
        """Valide la structure générale du nom"""
        score = 0.0
        erreurs, avertissements, suggestions = [], [], []
        
        # Vérifier la cohérence prénom(s) + nom
        if len(personne.prenoms) == 0:
            erreurs.append("Aucun prénom détecté")
            score -= 0.15
        elif len(personne.prenoms) > 4:
            avertissements.append(f"Beaucoup de prénoms: {len(personne.prenoms)}")
            score -= 0.05
        else:
            score += 0.05
        
        # Vérifier la cohérence du nom complet
        prenoms_concatenes = " ".join(personne.prenoms)
        if prenoms_concatenes not in personne.nom_complet:
            erreurs.append("Incohérence prénom/nom complet")
            score -= 0.10
        
        return score, erreurs, avertissements, suggestions
    
    def _valider_contexte_textuel(self, personne: PersonneExtraite, contexte: str) -> Tuple[float, List[str], List[str], List[str]]:
        """Valide la cohérence avec le contexte textuel"""
        score = 0.0
        erreurs, avertissements, suggestions = [], [], []
        
        if contexte and personne.nom_famille in contexte:
            score += 0.03
        
        # Vérifier que le nom apparaît bien dans le contexte
        if contexte and personne.nom_complet not in contexte:
            # Chercher des variantes
            nom_sans_particule = personne.nom_complet
            for particule in self.particules_nobles:
                nom_sans_particule = nom_sans_particule.replace(f" {particule} ", " ")
            
            if nom_sans_particule not in contexte:
                avertissements.append("Nom non trouvé dans le contexte")
                score -= 0.02
        
        return score, erreurs, avertissements, suggestions
    
    def _trouver_prenoms_similaires(self, prenom: str) -> List[str]:
        """Trouve des prénoms similaires par distance d'édition"""
        similaires = []
        prenom_lower = prenom.lower()
        
        for prenom_ref in self.prenoms_historiques:
            # Distance simplifiée (Hamming approximative)
            if abs(len(prenom) - len(prenom_ref)) <= 2:
                if (prenom_lower[:min(3, len(prenom_lower))] == 
                    prenom_ref.lower()[:min(3, len(prenom_ref))] or
                    prenom_lower[-3:] == prenom_ref.lower()[-3:]):
                    similaires.append(prenom_ref)
        
        return similaires[:3]

# ============================================================================
# DATASET TRAINER ENHANCED PRINCIPAL
# ============================================================================

class DatasetTrainerEnhanced:
    """Entraîneur de parser généalogique avancé avec vectorisation"""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialise l'entraîneur avec configuration optionnelle"""
        
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Composants principaux
        self.cache = CacheIntelligent(taille_max=self.config.get('cache_size', 10000))
        self.validateur = ValidateurExtraction()
        self.vectoriseur = VectorisateurTexte()
        
        # Dataset et apprentissage
        self.dataset_examples = self._load_dataset_examples()
        self.corrections_ocr_apprises = {}
        self.patterns_noms_apprises = []
        self.patterns_relations_apprises = []
        self.patterns_titres_apprises = {}
        self.patterns_dates_apprises = []
        
        # Métriques et statistiques
        self.metriques = MetriquesEntrainement()
        self.stats = {
            'exemples_traites': 0,
            'corrections_ocr_decouvertes': 0,
            'patterns_noms_appris': 0,
            'patterns_relations_appris': 0,
            'personnes_extraites': 0,
            'validations_effectuees': 0,
            'erreurs_detectees': 0
        }
        
        # Configuration avancée
        self.parallel_processing = self.config.get('parallel_processing', True)
        self.max_workers = self.config.get('max_workers', 4)
        self.vectorization_enabled = VECTORIZATION_AVAILABLE and self.config.get('vectorization', True)
        
        self.logger.info("🎓 DatasetTrainerEnhanced v2.0 initialisé")
        if self.vectorization_enabled:
            self.logger.info("✅ Vectorisation activée")
        
    def _load_dataset_examples(self) -> List[ExempleReference]:
        """Charge les exemples enrichis du dataset"""
        
        exemples = []
        
        # === EXEMPLE 1: PLEDS DE SEIGNEURIE ===
        texte1_original = """1770-1778. -- Semblables pleds de la seigneurie et châtellenie de Clécy et verge du marquisat de la Motte aud. Clécy, appartenant à Anne-Pierre d'Har-court, duc d'Harcourt, pair de France, comte de Lill-bonne, garde de l'Oriflamme, chevalier des ordres du Roi, lieutenant général de ses armées, gouverneur général de la province de Normandie, tenus : en 1770, en l'auditoire du bailliage d'Harcourt, par Jean-Bap-tiste Berthault, avocat postulant aud. bailliage, pour l'absence du bailli sénéchal, en présence de Louis-François Le Harivel, greffier ; aux années suivantes, par le même. -- 1770. Tenants noblement, les héritiers d'Henri-François Le Vaillant, écuyer, fils Fran-cois, par acquêt de Jean Le Mazurier, fils François, lui par décret de Jean-François Patry, sr de St-Lambert, tenu en 1682, pour le noble fief de Montfort. quart de fief de chevalier, avec la prairie assise à St-Laurent ;"""
        
        texte1_corrige = """[Actes entre 1770-1778]
Semblables pleds de la seigneurie et châtellenie de Clécy et vergé du marquisat de La Motte audit Clécy, appartenant à Anne-Pierre d'Harcourt, duc d'Harcourt, pair de France, comte de Lillebonne, garde de l'Oriflamme, chevalier des ordres du Roi, lieutenant général de ses armées, gouverneur général de la province de Normandie, tenus : en 1770, en l'auditoire du bailliage d'Harcourt, par Jean-Baptiste Berthault, avocat postulant audit bailliage, pour l'absence du bailli sénéchal, en présence de Louis François Le Harivel, greffier ; aux années suivantes, par le même.
[1770]
Tenants noblement, les héritiers d'Henri-François Le Vaillant, écuyer, fils François, par acquêt de Jean Le Mazurier, fils François, lui par décret de Jean-François Patry, sieur de Saint-Lambert, tenu en 1682, pour le noble fief de Montfort."""
        
        personnes1 = [
            PersonneExtraite(
                nom_complet="Anne-Pierre d'HARCOURT",
                nom_famille="HARCOURT",
                prenoms=["Anne-Pierre"],
                particule="d'",
                titres=["duc d'Harcourt", "pair de France", "comte de Lillebonne", "garde de l'Oriflamme", "chevalier des ordres du Roi", "lieutenant général", "gouverneur général de Normandie"],
                lieux=["Clécy", "Lillebonne", "Normandie"],
                dates=["1770-1778"],
                notes=["seigneur et châtelain de Clécy", "vivant entre 1770-1778, estimation naissance vers 1740"],
                variantes_nom=["Anne-Pierre d'Har-court", "d'HARCOURT"]
            ),
            PersonneExtraite(
                nom_complet="Jean-Baptiste BERTHAULT",
                nom_famille="BERTHAULT", 
                prenoms=["Jean-Baptiste"],
                professions=["avocat postulant au bailliage d'Harcourt"],
                dates=["1770-1778"],
                notes=["vivant entre 1770-1778, estimation naissance vers 1740"],
                variantes_nom=["Jean-Bap-tiste BERTHAULT"]
            ),
            PersonneExtraite(
                nom_complet="Louis François LE HARIVEL",
                nom_famille="LE HARIVEL",
                prenoms=["Louis", "François"],
                professions=["greffier"],
                dates=["1770-1778"],
                notes=["vivant entre 1770-1778, estimation naissance vers 1740"]
            ),
            PersonneExtraite(
                nom_complet="Henri-François LE VAILLANT",
                nom_famille="LE VAILLANT",
                prenoms=["Henri-François"],
                titres=["écuyer"],
                relations=[{"type": "filiation", "fils_de": "François LE VAILLANT"}],
                dates=["1770"]
            ),
            PersonneExtraite(
                nom_complet="Jean LE MAZURIER",
                nom_famille="LE MAZURIER",
                prenoms=["Jean"],
                relations=[{"type": "filiation", "fils_de": "François LE MAZURIER"}],
                dates=["1770"]
            ),
            PersonneExtraite(
                nom_complet="Jean-François PATRY",
                nom_famille="PATRY",
                prenoms=["Jean-François"],
                titres=["sieur de Saint-Lambert"],
                dates=["1682"],
                variantes_nom=["sr de St-Lambert"]
            )
        ]
        
        exemple1 = ExempleReference(
            numero=1,
            texte_original=texte1_original,
            texte_corrige=texte1_corrige,
            personnes_extraites=personnes1,
            corrections_ocr={
                "d'Har-court": "d'Harcourt",
                "Lill-bonne": "Lillebonne", 
                "aud.": "audit",
                "Jean-Bap-tiste": "Jean-Baptiste",
                "sr": "sieur",
                "St-Lambert": "Saint-Lambert"
            },
            type_document="pleds_seigneurie",
            periode_historique="XVIII_siecle",
            region_geographique="Normandie",
            difficulte_extraction="normale",
            tags=["noblesse", "juridique", "normandie"]
        )
        
        # === EXEMPLE 2: REGISTRES PAROISSIAUX ===
        texte2_original = """1644-1674. -- Actes de baptêmes, mariages, sépultures et administrations de sacrements, procla-mations de bans, fiançailles, par le curé Pellerin, Thomas Jean, prêtre, etc. -- Le 6 février 1646, inh. de Jacques Guillebert, fils de Pierre, tabellion royal, au hameau de Coupigny. -- Le 16 mai 1649, inh. en l'église de Valmeray de Michel Blais, meunier du moulin du sr d'Airan; "la charité d'Airen leva son corps et le porta au lieu de sa sépulture". -- " Le mercredy au soir, demy heure de nuict, jour et feste des Roys, Perrine Eulde, femme de Matin de Lorme, jurée matrone et sage-femme de ceste paroisse d'Airen, sixiesme du mois de janvier 1655, assistée de Marie Cheval...... (blanc) et de Guillemette Borel, femme de Anthoisne Jehenne, Anne Le Chevalier, femme de Jean Le Bourgeois, Jeune Hébert, servante de la dicte Borel, m'a présenté une fille estant malade, pour estre honorée comme les autres chrestiens du st babtesme, ce que par crainte qu'il ne luy arrivast mort nous avons faict, laquelle Marie Cheval nous a dit estre de la paroisse de Beaumontel", etc.,. ,n'avoir père ni mère, et de là estre venue demerer chés Monsr le baron de la Rivière en la paroisse de Rabodange, évesché de Séez en qualité de domestique et fille de chambre de feu Madame de La Rivière"""
        
        texte2_corrige = """[Acte entre 1644-1674]
Actes de baptêmes, mariages, sépultures et administrations de sacrements, proclamations de bans, fiançailles, par le curé Pellerin, Thomas Jean, prêtre, etc. Le 6 février 1646, inhumation de Jacques Guillebert, fils de Pierre, tabellion royal, au hameau de Coupigny. Le 16 mai 1649, inhumation en l'église de Valmeray de Michel Blais, meunier du moulin du sieur d'Airan; "la charité d'Airan leva son corps et le porta au lieu de sa sépulture". Le mercredi au soir, demi-heure de nuit, jour et fête des Rois, Perrine Eulde, femme de Matin de Lorme, jurée matrone et sage-femme de cette paroisse d'Airan, sixième jour du mois de janvier 1655, assistée de Marie Cheval et de Guillemette Borel, femme de Antoine Jehenne, Anne Le Chevalier, femme de Jean Le Bourgeois, Jeune Hébert, servante de la dite Borel"""
        
        personnes2 = [
            PersonneExtraite(
                nom_complet="Jean PELLERIN",
                nom_famille="PELLERIN",
                prenoms=["Jean"],
                professions=["curé d'Airan"],
                dates=["1644-1674"]
            ),
            PersonneExtraite(
                nom_complet="Thomas JEAN",
                nom_famille="JEAN",
                prenoms=["Thomas"],
                professions=["prêtre", "curé d'Airan"],
                dates=["1644-1674"]
            ),
            PersonneExtraite(
                nom_complet="Jacques GUILLEBERT",
                nom_famille="GUILLEBERT",
                prenoms=["Jacques"],
                professions=["tabellion royal"],
                lieux=["hameau de Coupigny"],
                relations=[{"type": "filiation", "fils_de": "Pierre GUILLEBERT"}],
                dates=["06-02-1646"],
                notes=["inhumé le 06-02-1646 à Airan"]
            ),
            PersonneExtraite(
                nom_complet="Michel BLAIS",
                nom_famille="BLAIS", 
                prenoms=["Michel"],
                professions=["meunier du sieur d'Airan"],
                dates=["16-05-1649"],
                notes=["inhumé le 16-05-1649 dans l'église de Valmeray"]
            ),
            PersonneExtraite(
                nom_complet="Perrine EULDE",
                nom_famille="EULDE",
                prenoms=["Perrine"],
                professions=["jurée matrone", "sage-femme"],
                lieux=["paroisse d'Airan"],
                relations=[{"type": "mariage", "epouse_de": "Matin de LORME"}],
                dates=["1655"]
            ),
            PersonneExtraite(
                nom_complet="Marie CHEVAL",
                nom_famille="CHEVAL",
                prenoms=["Marie"],
                professions=["domestique", "fille de chambre"],
                lieux=["Beaumontel", "Rabodange"],
                notes=["domestique du baron de la Rivière", "n'avoir père ni mère"]
            )
        ]
        
        exemple2 = ExempleReference(
            numero=2,
            texte_original=texte2_original,
            texte_corrige=texte2_corrige,
            personnes_extraites=personnes2,
            corrections_ocr={
                "procla-mations": "proclamations",
                "inh.": "inhumation",
                "sr": "sieur",
                "mercredy": "mercredi",
                "demy": "demi",
                "nuict": "nuit",
                "feste": "fête",
                "Roys": "Rois",
                "ceste": "cette",
                "sixiesme": "sixième",
                "Anthoisne": "Antoine",
                "estant": "étant",
                "estre": "être",
                "chrestiens": "chrétiens",
                "babtesme": "baptême",
                "faict": "fait",
                "père": "père",
                "mère": "mère",
                "demerer": "demeurer",
                "chés": "chez",
                "Monsr": "Monsieur",
                "évesché": "évêché"
            },
            type_document="registres_paroissiaux",
            periode_historique="XVII_siecle",
            region_geographique="Normandie",
            difficulte_extraction="difficile",
            tags=["bapteme", "mariage", "sepulture", "religieux"]
        )
        
        exemples.append(exemple1)
        exemples.append(exemple2)
        
        return exemples
    
    def entrainer_sur_dataset(self) -> Dict[str, Any]:
        """Entraîne le système sur le dataset avec traitement parallèle"""
        
        start_time = time.time()
        self.logger.info("🎓 Début de l'entraînement vectorisé")
        
        # Préparation du corpus pour la vectorisation
        if self.vectorization_enabled:
            corpus_textes = [ex.texte_corrige for ex in self.dataset_examples]
            self.vectoriseur.fit(corpus_textes)
            self.logger.info("📊 Vectoriseur entraîné sur le corpus")
        
        # Traitement parallèle ou séquentiel
        if self.parallel_processing and len(self.dataset_examples) > 1:
            self._entrainer_parallele()
        else:
            self._entrainer_sequentiel()
        
        # Consolidation finale
        self._consolider_apprentissages()
        
        # Calcul des métriques
        self.metriques.temps_traitement = time.time() - start_time
        self.metriques.efficacite_cache = self.cache.get_efficacite()
        
        return self._generer_rapport_complet()
    
    def _entrainer_parallele(self):
        """Entraînement avec traitement parallèle"""
        
        self.logger.info(f"🔄 Traitement parallèle sur {self.max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Soumission des tâches
            futures = []
            for exemple in self.dataset_examples:
                future = executor.submit(self._traiter_exemple_complet, exemple)
                futures.append(future)
            
            # Collecte des résultats
            for future in as_completed(futures):
                try:
                    resultats = future.result()
                    self._integrer_resultats_exemple(resultats)
                except Exception as e:
                    self.logger.error(f"Erreur traitement parallèle: {e}")
    
    def _entrainer_sequentiel(self):
        """Entraînement séquentiel"""
        
        self.logger.info("🔄 Traitement séquentiel")
        
        for exemple in self.dataset_examples:
            self.logger.info(f"📖 Traitement exemple {exemple.numero}")
            resultats = self._traiter_exemple_complet(exemple)
            self._integrer_resultats_exemple(resultats)
    
    def _traiter_exemple_complet(self, exemple: ExempleReference) -> Dict[str, Any]:
        """Traite un exemple de manière complète avec toutes les analyses"""
        
        resultats = {
            'exemple_numero': exemple.numero,
            'corrections_ocr': {},
            'patterns_noms': [],
            'patterns_relations': [],
            'patterns_titres': {},
            'patterns_dates': [],
            'validations': [],
            'personnes_extraites': len(exemple.personnes_extraites)
        }
        
        # 1. Apprentissage des corrections OCR
        corrections = self._apprendre_corrections_ocr_avancees(exemple)
        resultats['corrections_ocr'] = corrections
        
        # 2. Analyse des patterns de noms
        patterns_noms = self._analyser_patterns_noms_vectorises(exemple)
        resultats['patterns_noms'] = patterns_noms
        
        # 3. Extraction des relations
        patterns_relations = self._extraire_patterns_relations_avances(exemple)
        resultats['patterns_relations'] = patterns_relations
        
        # 4. Normalisation des titres
        patterns_titres = self._normaliser_titres_intelligents(exemple)
        resultats['patterns_titres'] = patterns_titres
        
        # 5. Analyse des dates
        patterns_dates = self._analyser_patterns_dates_avances(exemple)
        resultats['patterns_dates'] = patterns_dates
        
        # 6. Validation de toutes les extractions
        validations = []
        for personne in exemple.personnes_extraites:
            validation = self.validateur.valider(personne, exemple.texte_corrige)
            validations.append(validation)
        resultats['validations'] = validations
        
        return resultats
    
    def _integrer_resultats_exemple(self, resultats: Dict[str, Any]):
        """Intègre les résultats d'un exemple dans le modèle global"""
        
        # Mise à jour des corrections OCR
        self.corrections_ocr_apprises.update(resultats['corrections_ocr'])
        
        # Ajout des patterns
        self.patterns_noms_apprises.extend(resultats['patterns_noms'])
        self.patterns_relations_apprises.extend(resultats['patterns_relations'])
        self.patterns_titres_apprises.update(resultats['patterns_titres'])
        self.patterns_dates_apprises.extend(resultats['patterns_dates'])
        
        # Mise à jour des statistiques
        self.stats['exemples_traites'] += 1
        self.stats['personnes_extraites'] += resultats['personnes_extraites']
        self.stats['corrections_ocr_decouvertes'] += len(resultats['corrections_ocr'])
        self.stats['patterns_noms_appris'] += len(resultats['patterns_noms'])
        self.stats['patterns_relations_appris'] += len(resultats['patterns_relations'])
        self.stats['validations_effectuees'] += len(resultats['validations'])
        
        # Calcul des erreurs détectées
        erreurs_total = sum(len(v.erreurs_detectees) for v in resultats['validations'])
        self.stats['erreurs_detectees'] += erreurs_total
    
    def _apprendre_corrections_ocr_avancees(self, exemple: ExempleReference) -> Dict[str, str]:
        """Apprentissage avancé des corrections OCR avec analyse contextuelle"""
        
        corrections = {}
        
        # 1. Corrections explicites du dataset
        corrections.update(exemple.corrections_ocr)
        
        # 2. Découverte automatique par comparaison texte original/corrigé
        if self.vectorization_enabled:
            corrections_auto = self._detecter_corrections_automatiques(
                exemple.texte_original, 
                exemple.texte_corrige
            )
            corrections.update(corrections_auto)
        
        # 3. Corrections basées sur les patterns connus
        corrections_patterns = self._appliquer_corrections_patterns(exemple.texte_original)
        corrections.update(corrections_patterns)
        
        return corrections
    
    def _detecter_corrections_automatiques(self, texte_original: str, texte_corrige: str) -> Dict[str, str]:
        """Détecte automatiquement les corrections par diff intelligent"""
        
        corrections = {}
        
        # Tokenisation simple
        mots_originaux = re.findall(r'\b\w+\b', texte_original)
        mots_corriges = re.findall(r'\b\w+\b', texte_corrige)
        
        # Alignement approximatif (méthode simple)
        for i, mot_orig in enumerate(mots_originaux):
            if i < len(mots_corriges):
                mot_corr = mots_corriges[i]
                
                # Si différent et longueur similaire, probablement une correction
                if (mot_orig != mot_corr and 
                    abs(len(mot_orig) - len(mot_corr)) <= 3 and
                    len(mot_orig) >= 3):
                    
                    # Vérifier que c'est une vraie correction utile
                    if self._est_correction_utile(mot_orig, mot_corr):
                        corrections[mot_orig] = mot_corr
        
        return corrections
    
    def _est_correction_utile(self, original: str, corrige: str) -> bool:
        """Détermine si une correction est utile à retenir"""
        
        # Éviter les corrections trop courtes
        if len(original) < 3 or len(corrige) < 3:
            return False
        
        # Éviter les corrections de nombres
        if original.isdigit() or corrige.isdigit():
            return False
        
        # Éviter les corrections qui changent complètement le mot
        similarite = len(set(original.lower()) & set(corrige.lower())) / max(len(original), len(corrige))
        if similarite < 0.4:
            return False
        
        return True
    
    def _appliquer_corrections_patterns(self, texte: str) -> Dict[str, str]:
        """Applique les patterns de correction connus"""
        
        corrections_patterns = {
            # Abréviations courantes
            'sr': 'sieur', 'sgr': 'seigneur', 'éc.': 'écuyer', 'ec.': 'écuyer',
            'ct': 'comte', 'Ct': 'comte', 'inh.': 'inhumation', 'bapt.': 'baptême',
            'mar.': 'mariage', 'aud.': 'audit', 'lad.': 'ladite', 'lesd.': 'lesdits',
            
            # Orthographe ancienne
            'mercredy': 'mercredi', 'demy': 'demi', 'nuict': 'nuit', 'feste': 'fête',
            'ceste': 'cette', 'estre': 'être', 'faict': 'fait', 'chés': 'chez',
            
            # Coupures OCR
            'procla-mations': 'proclamations', 'administra-tions': 'administrations',
            'd\'Har-court': 'd\'Harcourt', 'Jean-Bap-tiste': 'Jean-Baptiste'
        }
        
        corrections_trouvees = {}
        for pattern, correction in corrections_patterns.items():
            if pattern in texte:
                corrections_trouvees[pattern] = correction
        
        return corrections_trouvees
    
    def _analyser_patterns_noms_vectorises(self, exemple: ExempleReference) -> List[Dict[str, Any]]:
        """Analyse vectorisée des patterns de noms"""
        
        patterns = []
        
        for personne in exemple.personnes_extraites:
            pattern = {
                'nom_complet': personne.nom_complet,
                'nom_famille': personne.nom_famille,
                'prenoms': personne.prenoms,
                'particule': personne.particule,
                'format': 'PRENOMS [PARTICULE] NOM_FAMILLE_MAJUSCULE',
                'score_qualite': self._calculer_score_qualite_nom(personne),
                'variantes': personne.variantes_nom,
                'contexte_extraction': personne.source_texte
            }
            
            # Analyse vectorielle si disponible
            if self.vectorization_enabled:
                pattern['similarites'] = self._trouver_noms_similaires_vectorises(personne.nom_complet)
            
            patterns.append(pattern)
        
        return patterns
    
    def _calculer_score_qualite_nom(self, personne: PersonneExtraite) -> float:
        """Calcule un score de qualité pour un nom extrait"""
        
        score = 0.5  # Base
        
        # Bonus nom famille en majuscules
        if personne.nom_famille.isupper():
            score += 0.2
        
        # Bonus prénoms valides
        prenoms_valides = sum(1 for p in personne.prenoms if p in self.validateur.prenoms_historiques)
        score += (prenoms_valides / len(personne.prenoms)) * 0.2 if personne.prenoms else 0
        
        # Bonus particule détectée
        if personne.particule:
            score += 0.1
        
        # Malus caractères suspects
        if re.search(r'[0-9@#$%]', personne.nom_complet):
            score -= 0.3
        
        return max(0.0, min(1.0, score))
    
    def _trouver_noms_similaires_vectorises(self, nom: str) -> List[Tuple[str, float]]:
        """Trouve des noms similaires via vectorisation"""
        
        if not self.vectorization_enabled:
            return []
        
        # Utiliser le vectoriseur pour trouver des noms similaires
        similaires = self.vectoriseur.trouver_similaires(nom, top_k=3)
        
        # Filtrer pour ne garder que les noms de personnes
        noms_similaires = []
        for texte_similaire, score in similaires:
            # Extraire les noms du texte similaire
            noms_extraits = re.findall(r'([A-Z][a-zA-ZÀ-ÿ\-]+(?:\s+[A-Z][a-zA-ZÀ-ÿ\-]+)*)\s+([A-Z]{2,})', texte_similaire)
            for prenoms, nom_famille in noms_extraits:
                nom_complet = f"{prenoms} {nom_famille}"
                if nom_complet != nom:  # Éviter le nom lui-même
                    noms_similaires.append((nom_complet, score))
        
        return noms_similaires[:3]
    
    def _extraire_patterns_relations_avances(self, exemple: ExempleReference) -> List[Dict[str, Any]]:
        """Extraction avancée des patterns de relations"""
        
        patterns = []
        
        for personne in exemple.personnes_extraites:
            for relation in personne.relations:
                pattern = {
                    'type_relation': relation['type'],
                    'personne_source': personne.nom_complet,
                    'personne_cible': relation.get('fils_de') or relation.get('epouse_de'),
                    'pattern_textuel': self._extraire_pattern_textuel_avance(relation, exemple.texte_corrige),
                    'contexte': self._extraire_contexte_relation(relation, exemple.texte_corrige),
                    'confiance': self._calculer_confiance_relation(relation, exemple.texte_corrige)
                }
                
                patterns.append(pattern)
        
        return patterns
    
    def _extraire_pattern_textuel_avance(self, relation: Dict, texte: str) -> str:
        """Extraction avancée du pattern textuel d'une relation"""
        
        patterns_recherche = {
            'filiation': [
                r'(\w+(?:\s+\w+)*),?\s*fils de\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*),?\s*fille de\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*),?\s*enfant de\s+(\w+(?:\s+\w+)*)'
            ],
            'mariage': [
                r'(\w+(?:\s+\w+)*),?\s*(?:femme|épouse) de\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*),?\s*(?:mari|époux) de\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*)\s+et\s+(\w+(?:\s+\w+)*),?\s*(?:mariés|unis)'
            ]
        }
        
        type_relation = relation['type']
        if type_relation in patterns_recherche:
            for pattern in patterns_recherche[type_relation]:
                match = re.search(pattern, texte, re.IGNORECASE)
                if match:
                    return match.group(0)
        
        return ""
    
    def _extraire_contexte_relation(self, relation: Dict, texte: str) -> str:
        """Extrait le contexte autour d'une relation"""
        
        # Chercher la relation dans le texte et extraire le contexte (±50 caractères)
        pattern_relation = self._extraire_pattern_textuel_avance(relation, texte)
        
        if pattern_relation:
            index = texte.find(pattern_relation)
            if index != -1:
                debut = max(0, index - 50)
                fin = min(len(texte), index + len(pattern_relation) + 50)
                return texte[debut:fin].strip()
        
        return ""
    
    def _calculer_confiance_relation(self, relation: Dict, texte: str) -> float:
        """Calcule la confiance d'une relation extraite"""
        
        confiance = 0.5
        
        # Bonus si pattern textuel trouvé
        pattern = self._extraire_pattern_textuel_avance(relation, texte)
        if pattern:
            confiance += 0.3
        
        # Bonus selon le type de relation
        if relation['type'] in ['filiation', 'mariage']:
            confiance += 0.1
        
        # Bonus si noms cohérents
        personne_cible = relation.get('fils_de') or relation.get('epouse_de')
        if personne_cible and personne_cible.isupper():
            confiance += 0.1
        
        return min(1.0, confiance)
    
    def _normaliser_titres_intelligents(self, exemple: ExempleReference) -> Dict[str, str]:
        """Normalisation intelligente des titres avec contexte"""
        
        normalisations = {}
        
        for personne in exemple.personnes_extraites:
            for titre in personne.titres:
                titre_normalise = self._normaliser_titre_contextuel(titre, personne, exemple)
                if titre_normalise and titre_normalise != titre:
                    normalisations[titre] = titre_normalise
        
        return normalisations
    
    def _normaliser_titre_contextuel(self, titre: str, personne: PersonneExtraite, exemple: ExempleReference) -> str:
        """Normalise un titre en tenant compte du contexte"""
        
        # Règles de base
        regles_base = {
            'duc': 'duc', 'comte': 'comte', 'baron': 'baron',
            'sieur': 'sieur', 'seigneur': 'seigneur', 'écuyer': 'écuyer',
            'sr': 'sieur', 'sgr': 'seigneur', 'ct': 'comte', 'Ct': 'comte'
        }
        
        titre_lower = titre.lower().strip()
        
        # Recherche dans les règles de base
        for pattern, normalise in regles_base.items():
            if pattern in titre_lower:
                # Analyser le contexte pour affiner
                if 'de' in titre.lower() and normalise in ['duc', 'comte', 'baron']:
                    # Garder la forme complète pour les titres territoriaux
                    return titre.lower()
                return normalise
        
        return titre
    
    def _analyser_patterns_dates_avances(self, exemple: ExempleReference) -> List[Dict[str, Any]]:
        """Analyse avancée des patterns de dates"""
        
        patterns = []
        
        for personne in exemple.personnes_extraites:
            for date in personne.dates:
                pattern = {
                    'date_originale': date,
                    'format_detecte': self._detecter_format_date_avance(date),
                    'date_normalisee': self._normaliser_date(date),
                    'precision': self._evaluer_precision_date(date),
                    'contexte': 'genealogique',
                    'epoque_estimee': self._estimer_epoque(date),
                    'validite': self._valider_coherence_date(date, exemple.periode_historique)
                }
                
                patterns.append(pattern)
        
        return patterns
    
    def _detecter_format_date_avance(self, date: str) -> str:
        """Détection avancée du format de date"""
        
        formats = {
            r'\d{4}-\d{4}': 'periode_annees',
            r'\d{2}-\d{2}-\d{4}': 'jj-mm-aaaa',
            r'\d{4}': 'annee',
            r'\d{1,2}\s+\w+\s+\d{4}': 'jour_mois_annee',
            r'\w+\s+\d{4}': 'mois_annee',
            r'vers\s+\d{4}': 'estimation_annee',
            r'avant\s+\d{4}': 'ante_date',
            r'après\s+\d{4}': 'post_date'
        }
        
        for pattern, format_type in formats.items():
            if re.match(pattern, date):
                return format_type
        
        return 'format_inconnu'
    
    def _normaliser_date(self, date: str) -> str:
        """Normalise une date selon les standards"""
        
        # Remplacements courants
        remplacements = {
            'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
            'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
            'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
        }
        
        date_norm = date.lower()
        for ancien, nouveau in remplacements.items():
            date_norm = date_norm.replace(ancien, nouveau)
        
        return date_norm
    
    def _evaluer_precision_date(self, date: str) -> str:
        """Évalue la précision d'une date"""
        
        if re.match(r'\d{2}-\d{2}-\d{4}', date):
            return 'jour'
        elif re.match(r'\d{2}-\d{4}', date):
            return 'mois'
        elif re.match(r'\d{4}', date):
            return 'annee'
        elif re.match(r'\d{4}-\d{4}', date):
            return 'periode'
        else:
            return 'approximative'
    
    def _estimer_epoque(self, date: str) -> str:
        """Estime l'époque historique d'une date"""
        
        # Extraire l'année
        annee_match = re.search(r'\d{4}', date)
        if annee_match:
            annee = int(annee_match.group())
            
            if annee < 1600:
                return 'moyen_age_tardif'
            elif annee < 1700:
                return 'XVII_siecle'
            elif annee < 1800:
                return 'XVIII_siecle'
            elif annee < 1900:
                return 'XIX_siecle'
            else:
                return 'epoque_moderne'
        
        return 'indeterminee'
    
    def _valider_coherence_date(self, date: str, periode_document: str) -> bool:
        """Valide la cohérence d'une date avec la période du document"""
        
        if not periode_document:
            return True
        
        epoque_date = self._estimer_epoque(date)
        
        # Vérification de cohérence simple
        if periode_document in epoque_date or epoque_date in periode_document:
            return True
        
        return False
    
    def _consolider_apprentissages(self):
        """Consolidation avancée des apprentissages"""
        
        self.logger.info("📊 Consolidation des apprentissages...")
        
        # 1. Déduplication intelligente des corrections OCR
        self.corrections_ocr_apprises = self._dedupliquer_corrections_ocr()
        
        # 2. Clustering des patterns de noms similaires
        if self.vectorization_enabled:
            self.patterns_noms_apprises = self._clusteriser_patterns_noms()
        
        # 3. Optimisation des patterns de relations
        self.patterns_relations_apprises = self._optimiser_patterns_relations()
        
        # 4. Calcul des métriques finales
        self._calculer_metriques_finales()
        
        # 5. Nettoyage du cache si nécessaire
        if self.cache.get_efficacite() < 0.3:
            self.cache.clear()
            self.logger.info("🧹 Cache nettoyé (faible efficacité)")
    
    def _dedupliquer_corrections_ocr(self) -> Dict[str, str]:
        """Déduplication intelligente des corrections OCR"""
        
        corrections_filtrees = {}
        
        for erreur, correction in self.corrections_ocr_apprises.items():
            # Filtres de qualité
            if (len(erreur) >= 2 and len(correction) >= 2 and
                not erreur.isdigit() and not correction.isdigit() and
                erreur != correction):
                
                # Éviter les corrections en chaîne (A->B et B->C)
                if correction not in self.corrections_ocr_apprises:
                    corrections_filtrees[erreur] = correction
        
        return corrections_filtrees
    
    def _clusteriser_patterns_noms(self) -> List[Dict[str, Any]]:
        """Clustering des patterns de noms similaires"""
        
        if not self.patterns_noms_apprises:
            return []
        
        # Grouper par score de qualité
        patterns_groupes = defaultdict(list)
        
        for pattern in self.patterns_noms_apprises:
            score_qualite = pattern.get('score_qualite', 0.5)
            
            if score_qualite >= 0.8:
                categorie = 'excellent'
            elif score_qualite >= 0.6:
                categorie = 'bon'
            else:
                categorie = 'moyen'
            
            patterns_groupes[categorie].append(pattern)
        
        # Retourner les patterns triés par qualité
        patterns_tries = []
        for categorie in ['excellent', 'bon', 'moyen']:
            patterns_tries.extend(patterns_groupes[categorie])
        
        return patterns_tries
    
    def _optimiser_patterns_relations(self) -> List[Dict[str, Any]]:
        """Optimise les patterns de relations par fréquence et confiance"""
        
        if not self.patterns_relations_apprises:
            return []
        
        # Trier par confiance décroissante
        patterns_tries = sorted(
            self.patterns_relations_apprises,
            key=lambda p: p.get('confiance', 0.5),
            reverse=True
        )
        
        # Regrouper par type de relation
        patterns_optimises = []
        relations_vues = set()
        
        for pattern in patterns_tries:
            # Éviter les doublons exacts
            cle_unique = (pattern['type_relation'], pattern.get('pattern_textuel', ''))
            
            if cle_unique not in relations_vues:
                relations_vues.add(cle_unique)
                patterns_optimises.append(pattern)
        
        return patterns_optimises
    
    def _calculer_metriques_finales(self):
        """Calcule les métriques finales de l'entraînement"""
        
        if self.stats['personnes_extraites'] > 0:
            # Taux de validation
            self.metriques.taux_validation = (
                (self.stats['validations_effectuees'] - self.stats['erreurs_detectees']) /
                self.stats['validations_effectuees']
                if self.stats['validations_effectuees'] > 0 else 0
            )
            
            # Score de qualité global
            self.metriques.score_qualite_global = (
                len(self.corrections_ocr_apprises) * 0.3 +
                len(self.patterns_noms_apprises) * 0.25 +
                len(self.patterns_relations_apprises) * 0.25 +
                self.metriques.taux_validation * 0.2
            ) / 4
            
            # Patterns nouveaux
            self.metriques.patterns_nouveaux = (
                len(self.patterns_noms_apprises) +
                len(self.patterns_relations_apprises) +
                len(self.patterns_titres_apprises)
            )
            
            # Corrections nouvelles
            self.metriques.corrections_nouvelles = len(self.corrections_ocr_apprises)
    
    def _generer_rapport_complet(self) -> Dict[str, Any]:
        """Génère un rapport complet et détaillé"""
        
        rapport = {
            'version': '2.0.0',
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'vectorisation_activee': self.vectorization_enabled,
                'traitement_parallele': self.parallel_processing,
                'max_workers': self.max_workers,
                'taille_cache': self.cache.taille_max
            },
            'statistiques_base': self.stats.copy(),
            'metriques_avancees': {
                'temps_traitement': self.metriques.temps_traitement,
                'score_qualite_global': self.metriques.score_qualite_global,
                'taux_validation': self.metriques.taux_validation,
                'efficacite_cache': self.metriques.efficacite_cache,
                'patterns_nouveaux': self.metriques.patterns_nouveaux,
                'corrections_nouvelles': self.metriques.corrections_nouvelles
            },
            'apprentissages': {
                'corrections_ocr': {
                    'total': len(self.corrections_ocr_apprises),
                    'exemples': dict(list(self.corrections_ocr_apprises.items())[:10]),
                    'qualite_moyenne': self._evaluer_qualite_corrections()
                },
                'patterns_noms': {
                    'total': len(self.patterns_noms_apprises),
                    'distribution_qualite': self._analyser_distribution_qualite_noms(),
                    'format_standard': 'PRENOMS [PARTICULE] NOM_FAMILLE_MAJUSCULE'
                },
                'patterns_relations': {
                    'total': len(self.patterns_relations_apprises),
                    'types': list(set(p['type_relation'] for p in self.patterns_relations_apprises)),
                    'confiance_moyenne': self._calculer_confiance_moyenne_relations()
                },
                'patterns_titres': {
                    'total': len(self.patterns_titres_apprises),
                    'exemples': dict(list(self.patterns_titres_apprises.items())[:5])
                }
            },
            'recommandations': self._generer_recommandations_avancees(),
            'cache_stats': self.cache.stats.copy(),
            'seuils_qualite': {
                'score_minimum_extraction': 0.6,
                'confiance_minimum_relation': 0.7,
                'taux_validation_cible': 0.85
            }
        }
        
        return rapport
    
    def _evaluer_qualite_corrections(self) -> float:
        """Évalue la qualité moyenne des corrections OCR"""
        
        if not self.corrections_ocr_apprises:
            return 0.0
        
        score_total = 0
        for erreur, correction in self.corrections_ocr_apprises.items():
            # Score basé sur la longueur et la similarité
            score = 0.5
            
            if len(erreur) >= 3 and len(correction) >= 3:
                score += 0.2
            
            if not erreur.isdigit() and not correction.isdigit():
                score += 0.2
            
            if abs(len(erreur) - len(correction)) <= 2:
                score += 0.1
            
            score_total += score
        
        return score_total / len(self.corrections_ocr_apprises)
    
    def _analyser_distribution_qualite_noms(self) -> Dict[str, int]:
        """Analyse la distribution de qualité des noms"""
        
        distribution = {'excellent': 0, 'bon': 0, 'moyen': 0, 'faible': 0}
        
        for pattern in self.patterns_noms_apprises:
            score = pattern.get('score_qualite', 0.5)
            
            if score >= 0.9:
                distribution['excellent'] += 1
            elif score >= 0.7:
                distribution['bon'] += 1
            elif score >= 0.5:
                distribution['moyen'] += 1
            else:
                distribution['faible'] += 1
        
        return distribution
    
    def _calculer_confiance_moyenne_relations(self) -> float:
        """Calcule la confiance moyenne des relations"""
        
        if not self.patterns_relations_apprises:
            return 0.0
        
        confiances = [p.get('confiance', 0.5) for p in self.patterns_relations_apprises]
        return sum(confiances) / len(confiances)
    
    def _generer_recommandations_avancees(self) -> List[str]:
        """Génère des recommandations avancées basées sur l'analyse"""
        
        recommandations = []
        
        # Recommandations basées sur la qualité
        if self.metriques.score_qualite_global < 0.7:
            recommandations.append("⚠️ Score de qualité faible - réviser les exemples du dataset")
        
        if self.metriques.taux_validation < 0.8:
            recommandations.append("🔍 Taux de validation bas - améliorer les règles de validation")
        
        if len(self.corrections_ocr_apprises) > 50:
            recommandations.append("📚 Intégrer les corrections OCR dans le TextParser principal")
        
        if len(self.patterns_relations_apprises) > 10:
            recommandations.append("🔗 Enrichir le RelationshipParser avec les nouveaux patterns")
        
        # Recommandations techniques
        if not self.vectorization_enabled:
            recommandations.append("⚡ Installer les dépendances de vectorisation pour de meilleures performances")
        
        if self.cache.get_efficacite() < 0.5:
            recommandations.append("💾 Optimiser la stratégie de cache (taille ou TTL)")
        
        # Recommandations spécifiques
        recommandations.extend([
            "🎯 Implémenter la validation automatique en production",
            "📊 Créer un tableau de bord de monitoring de la qualité",
            "🔄 Planifier un réentraînement périodique avec nouveaux exemples",
            "🌐 Intégrer avec DicoTopo pour la géolocalisation",
            "📱 Exposer les métriques via API pour le frontend"
        ])
        
        return recommandations
    
    # =========================================================================
    # MÉTHODES D'INTERFACE PUBLIQUE
    # =========================================================================
    
    def extraire_avec_validation(self, texte: str) -> List[Tuple[PersonneExtraite, ValidationResult]]:
        """Interface publique pour extraction avec validation"""
        
        # Vérifier le cache
        cache_key = hashlib.md5(texte.encode()).hexdigest()
        resultats_cache = self.cache.get(cache_key)
        
        if resultats_cache:
            return resultats_cache
        
        # Extraction
        personnes = self.extraire_personnes_format_dataset(texte)
        
        # Validation
        resultats = []
        for personne in personnes:
            validation = self.validateur.valider(personne, texte)
            resultats.append((personne, validation))
        
        # Mise en cache
        self.cache.set(cache_key, resultats)
        
        return resultats
    
    def appliquer_corrections_sur_texte(self, texte: str) -> Tuple[str, List[str]]:
        """Applique les corrections OCR apprises"""
        
        texte_corrige = texte
        corrections_appliquees = []
        
        for erreur, correction in self.corrections_ocr_apprises.items():
            if erreur in texte_corrige:
                texte_corrige = texte_corrige.replace(erreur, correction)
                corrections_appliquees.append(f"{erreur} → {correction}")
        
        return texte_corrige, corrections_appliquees
    
    def extraire_personnes_format_dataset(self, texte: str) -> List[PersonneExtraite]:
        """Extraction de personnes avec le format du dataset"""
        
        personnes = []
        noms_extraits = set()
        
        # Patterns avancés avec particules
        patterns = [
            # Pattern avec particules nobiliaires
            r"([A-Z][a-zA-ZÀ-ÿ\-']+(?:\s+[A-Z][a-zA-ZÀ-ÿ\-']+)*)\s+((?:d'|de\s+|du\s+|des\s+|le\s+|la\s+|les\s+|Le\s+|La\s+|Les\s+|De\s+|Du\s+|Des\s+)?)\s*([A-Z]{2,})",
            # Pattern simple
            r"([A-Z][a-zA-ZÀ-ÿ\-']+(?:\s+[A-Z][a-zA-ZÀ-ÿ\-']+)*)\s+([A-Z]{3,})"
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, texte):
                try:
                    if len(match.groups()) >= 3:  # Pattern avec particules
                        prenoms_str = match.group(1).strip()
                        particule = match.group(2).strip() if match.group(2) else ""
                        nom_famille = match.group(3).strip()
                    else:  # Pattern simple
                        prenoms_str = match.group(1).strip()
                        particule = ""
                        nom_famille = match.group(2).strip()
                    
                    # Nettoyage de la particule
                    if particule:
                        particule = particule.lower().strip()
                        if particule.endswith(' '):
                            particule = particule.rstrip()
                    
                    # Extraction des prénoms
                    prenoms = [p.strip() for p in prenoms_str.split() if p.strip()]
                    
                    # Construction du nom complet
                    if particule:
                        nom_complet = f"{prenoms_str} {particule}{nom_famille}" if particule.endswith("'") else f"{prenoms_str} {particule} {nom_famille}"
                    else:
                        nom_complet = f"{prenoms_str} {nom_famille}"
                    
                    # Éviter les doublons
                    if nom_complet not in noms_extraits and len(prenoms) > 0:
                        personne = PersonneExtraite(
                            nom_complet=nom_complet,
                            nom_famille=nom_famille,
                            prenoms=prenoms,
                            particule=particule,
                            source_texte=match.group(0),
                            confiance=self._calculer_score_qualite_extraction(nom_complet, texte)
                        )
                        
                        personnes.append(personne)
                        noms_extraits.add(nom_complet)
                
                except Exception as e:
                    self.logger.warning(f"Erreur extraction nom: {e}")
                    continue
        
        return personnes
    
    def _calculer_score_qualite_extraction(self, nom: str, contexte: str) -> float:
        """Calcule un score de qualité pour une extraction"""
        
        score = 0.5
        
        # Bonus si nom bien formé
        if re.match(r'^[A-Z][a-zA-ZÀ-ÿ\-\s\']+\s+[A-Z]{2,}$', nom):
            score += 0.2
        
        # Bonus si présent dans le contexte
        if nom in contexte:
            score += 0.2
        
        # Malus pour caractères suspects
        if re.search(r'[0-9@#$%&*()+=]', nom):
            score -= 0.3
        
        # Bonus longueur raisonnable
        if 8 <= len(nom) <= 45:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def sauvegarder_modele_entraine(self, chemin_sortie: str):
        """Sauvegarde complète du modèle entraîné"""
        
        modele_complet = {
            'version': '2.0.0',
            'date_entrainement': datetime.now().isoformat(),
            'configuration': {
                'vectorisation': self.vectorization_enabled,
                'traitement_parallele': self.parallel_processing,
                'max_workers': self.max_workers
            },
            'dataset_info': {
                'nombre_exemples': len(self.dataset_examples),
                'types_documents': list(set(ex.type_document for ex in self.dataset_examples)),
                'periodes_historiques': list(set(ex.periode_historique for ex in self.dataset_examples))
            },
            'apprentissages': {
                'corrections_ocr': self.corrections_ocr_apprises,
                'patterns_noms': self.patterns_noms_apprises,
                'patterns_relations': self.patterns_relations_apprises,
                'patterns_titres': self.patterns_titres_apprises,
                'patterns_dates': self.patterns_dates_apprises
            },
            'metriques': {
                'temps_traitement': self.metriques.temps_traitement,
                'score_qualite_global': self.metriques.score_qualite_global,
                'taux_validation': self.metriques.taux_validation,
                'efficacite_cache': self.metriques.efficacite_cache
            },
            'statistiques': self.stats,
            'config_recommandee': self._generer_config_production(),
            'seuils_validation': self.validateur.seuils
        }
        
        # Sauvegarde avec gestion d'erreurs
        try:
            with open(chemin_sortie, 'w', encoding='utf-8') as f:
                json.dump(modele_complet, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"💾 Modèle complet sauvegardé: {chemin_sortie}")
            
            # Sauvegarde des métriques séparément pour monitoring
            chemin_metriques = chemin_sortie.replace('.json', '_metriques.json')
            with open(chemin_metriques, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'metriques': self.metriques.__dict__,
                    'stats': self.stats
                }, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde modèle: {e}")
            raise
    
    def _generer_config_production(self) -> Dict[str, Any]:
        """Génère une configuration optimisée pour la production"""
        
        return {
            'version': '2.0.0',
            'corrections_ocr': {
                'actives': True,
                'dictionnaire': self.corrections_ocr_apprises,
                'seuil_confiance': 0.8
            },
            'extraction_noms': {
                'format_standard': 'PRENOMS [PARTICULE] NOM_FAMILLE_MAJUSCULE',
                'particules_supportees': ['de', 'du', 'des', 'le', 'la', 'les', "d'"],
                'validation_automatique': True,
                'score_minimum': 0.6
            },
            'relations_familiales': {
                'patterns_actifs': [p['pattern_textuel'] for p in self.patterns_relations_apprises if p.get('confiance', 0) > 0.7],
                'types_supportes': ['filiation', 'mariage', 'parrainage'],
                'confiance_minimum': 0.7
            },
            'normalisation_titres': {
                'regles': self.patterns_titres_apprises,
                'format_sortie': 'minuscule',
                'conservation_forme_complete': True
            },
            'dates': {
                'formats_detectes': list(set(p['format_detecte'] for p in self.patterns_dates_apprises)),
                'normalisation_automatique': True,
                'validation_coherence': True
            },
            'cache': {
                'actif': True,
                'taille_max': 10000,
                'ttl_heures': 24
            },
            'monitoring': {
                'metriques_activees': True,
                'seuils_alerte': {
                    'score_qualite_minimum': 0.7,
                    'taux_validation_minimum': 0.8,
                    'efficacite_cache_minimum': 0.5
                }
            }
        }


# ============================================================================
# FONCTION PRINCIPALE ET TESTS
# ============================================================================

def main():
    """Fonction principale d'entraînement enhanced"""
    
    print("🎓 DATASET TRAINER ENHANCED v2.0")
    print("=" * 55)
    print("Entraîneur vectorisé avec validation automatique")
    print()
    
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configuration
    config = {
        'cache_size': 5000,
        'parallel_processing': True,
        'max_workers': 4,
        'vectorization': True
    }
    
    # Création de l'entraîneur
    print("🔧 Initialisation de l'entraîneur...")
    trainer = DatasetTrainerEnhanced(config)
    
    print(f"📚 Dataset chargé: {len(trainer.dataset_examples)} exemples")
    print(f"⚡ Vectorisation: {'✅ Activée' if trainer.vectorization_enabled else '❌ Désactivée'}")
    print(f"🔄 Traitement parallèle: {'✅ Activé' if trainer.parallel_processing else '❌ Désactivé'}")
    print()
    
    # Entraînement
    print("🚀 Début de l'entraînement enhanced...")
    debut = time.time()
    
    try:
        rapport = trainer.entrainer_sur_dataset()
        duree = time.time() - debut
        
        # Affichage des résultats
        print(f"\n📊 RÉSULTATS DE L'ENTRAÎNEMENT (en {duree:.2f}s):")
        print("=" * 50)
        
        # Statistiques de base
        stats = rapport['statistiques_base']
        print(f"📖 Exemples traités: {stats['exemples_traites']}")
        print(f"👥 Personnes extraites: {stats['personnes_extraites']}")
        print(f"🔧 Corrections OCR: {stats['corrections_ocr_decouvertes']}")
        print(f"📝 Patterns noms: {stats['patterns_noms_appris']}")
        print(f"🔗 Patterns relations: {stats['patterns_relations_appris']}")
        print(f"✅ Validations: {stats['validations_effectuees']}")
        
        # Métriques avancées
        metriques = rapport['metriques_avancees']
        print(f"\n🎯 MÉTRIQUES DE QUALITÉ:")
        print(f"   • Score global: {metriques['score_qualite_global']:.2f}/1.0")
        print(f"   • Taux validation: {metriques['taux_validation']:.1%}")
        print(f"   • Efficacité cache: {metriques['efficacite_cache']:.1%}")
        print(f"   • Patterns nouveaux: {metriques['patterns_nouveaux']}")
        
        # Apprentissages
        apprentissages = rapport['apprentissages']
        print(f"\n🧠 APPRENTISSAGES:")
        
        print(f"   🔤 Corrections OCR ({apprentissages['corrections_ocr']['total']}):")
        for erreur, correction in list(apprentissages['corrections_ocr']['exemples'].items())[:5]:
            print(f"      • {erreur} → {correction}")
        
        print(f"   👤 Noms ({apprentissages['patterns_noms']['total']}):")
        distrib = apprentissages['patterns_noms']['distribution_qualite']
        print(f"      • Excellent: {distrib['excellent']}, Bon: {distrib['bon']}, Moyen: {distrib['moyen']}")
        
        print(f"   🔗 Relations ({apprentissages['patterns_relations']['total']}):")
        print(f"      • Types: {', '.join(apprentissages['patterns_relations']['types'])}")
        print(f"      • Confiance moyenne: {apprentissages['patterns_relations']['confiance_moyenne']:.2f}")
        
        # Recommandations
        print(f"\n💡 RECOMMANDATIONS:")
        for i, rec in enumerate(rapport['recommandations'][:5], 1):
            print(f"   {i}. {rec}")
        
        # Tests de validation
        print(f"\n🧪 TESTS DE VALIDATION:")
        print("-" * 30)
        
        textes_test = [
            "Jean-Baptiste BERTHAULT, avocat, et Henri-François LE VAILLANT, sr de Montfort",
            "Anne-Pierre d'HARCOURT, duc d'Harcourt, pair de France",
            "Marie CHEVAL, domestique, fille de chambre"
        ]
        
        for i, texte in enumerate(textes_test, 1):
            print(f"\n🔍 Test {i}: {texte[:50]}...")
            
            resultats = trainer.extraire_avec_validation(texte)
            
            for personne, validation in resultats:
                statut = "✅" if validation.valide else "❌"
                print(f"   {statut} {personne.nom_complet} (score: {validation.score_confiance:.2f})")
                
                if validation.erreurs_detectees:
                    print(f"      🚨 Erreurs: {len(validation.erreurs_detectees)}")
                
                if validation.suggestions:
                    print(f"      💡 Suggestions: {len(validation.suggestions)}")
        
        # Sauvegarde
        print(f"\n💾 SAUVEGARDE:")
        chemin_modele = "modele_entraine_enhanced_v2.json"
        trainer.sauvegarder_modele_entraine(chemin_modele)
        print(f"   • Modèle: {chemin_modele}")
        print(f"   • Métriques: {chemin_modele.replace('.json', '_metriques.json')}")
        
        # Configuration de production
        print(f"\n⚙️ CONFIGURATION DE PRODUCTION:")
        config_prod = trainer._generer_config_production()
        print(f"   • Version: {config_prod['version']}")
        print(f"   • Corrections OCR: {len(config_prod['corrections_ocr']['dictionnaire'])} règles")
        print(f"   • Patterns relations: {len(config_prod['relations_familiales']['patterns_actifs'])} patterns")
        print(f"   • Validation automatique: {'✅' if config_prod['extraction_noms']['validation_automatique'] else '❌'}")
        print(f"   • Cache activé: {'✅' if config_prod['cache']['actif'] else '❌'}")
        
        # Résumé final
        print(f"\n🎉 RÉSUMÉ FINAL:")
        print("=" * 30)
        print(f"   ⏱️  Temps d'entraînement: {duree:.2f}s")
        print(f"   📊 Score de qualité: {metriques['score_qualite_global']:.1%}")
        print(f"   🎯 Taux de validation: {metriques['taux_validation']:.1%}")
        print(f"   🚀 Améliorations détectées: {metriques['patterns_nouveaux']} patterns")
        print(f"   💾 Efficacité cache: {metriques['efficacite_cache']:.1%}")
        
        # Niveau de qualité atteint
        if metriques['score_qualite_global'] >= 0.9:
            niveau = "🏆 EXCELLENT"
        elif metriques['score_qualite_global'] >= 0.8:
            niveau = "🥇 TRÈS BON"
        elif metriques['score_qualite_global'] >= 0.7:
            niveau = "🥈 BON"
        elif metriques['score_qualite_global'] >= 0.6:
            niveau = "🥉 ACCEPTABLE"
        else:
            niveau = "⚠️ À AMÉLIORER"
        
        print(f"\n🎖️ NIVEAU DE QUALITÉ ATTEINT: {niveau}")
        
        print(f"\n✅ Entraînement terminé avec succès!")
        print(f"📦 Le modèle peut maintenant être intégré dans les parsers Garméa.")
        print(f"🔧 Fichiers générés prêts pour la production.")
        
    except Exception as e:
        print(f"\n❌ ERREUR DURANT L'ENTRAÎNEMENT:")
        print(f"   🚨 {type(e).__name__}: {str(e)}")
        print(f"   📋 Vérifiez les logs pour plus de détails")
        
        # Sauvegarde partielle en cas d'erreur
        try:
            chemin_erreur = "modele_partiel_erreur.json"
            trainer.sauvegarder_modele_entraine(chemin_erreur)
            print(f"   💾 Modèle partiel sauvegardé: {chemin_erreur}")
        except:
            print(f"   ⚠️ Impossible de sauvegarder le modèle partiel")
        
        raise
    
    finally:
        # Nettoyage et statistiques finales
        if 'trainer' in locals():
            print(f"\n📈 STATISTIQUES CACHE:")
            cache_stats = trainer.cache.stats
            print(f"   • Hits: {cache_stats['hits']}")
            print(f"   • Misses: {cache_stats['misses']}")
            print(f"   • Évictions: {cache_stats['evictions']}")
            
            if trainer.vectorization_enabled:
                print(f"   • Vectorisation: ✅ Utilisée")
            else:
                print(f"   • Vectorisation: ❌ Non disponible")


def test_trainer_enhanced():
    """Fonction de test pour le trainer enhanced"""
    
    print("🧪 TESTS DU DATASET TRAINER ENHANCED")
    print("=" * 45)
    
    # Test de base
    try:
        trainer = DatasetTrainerEnhanced({'cache_size': 100, 'parallel_processing': False})
        
        # Test extraction simple
        texte_test = "Jean-Baptiste BERTHAULT, avocat du roi"
        resultats = trainer.extraire_avec_validation(texte_test)
        
        print(f"✅ Test extraction: {len(resultats)} personnes trouvées")
        
        # Test corrections OCR
        texte_ocr = "sr Jean, avocat aud. bailliage"
        texte_corrige, corrections = trainer.appliquer_corrections_sur_texte(texte_ocr)
        
        print(f"✅ Test corrections OCR: {len(corrections)} corrections appliquées")
        
        # Test validation
        if resultats:
            personne, validation = resultats[0]
            print(f"✅ Test validation: score {validation.score_confiance:.2f}")
        
        print("🎉 Tous les tests passés avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur durant les tests: {e}")
        return False
    
    return True


if __name__ == "__main__":
    # Choix du mode d'exécution
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Mode test
        success = test_trainer_enhanced()
        sys.exit(0 if success else 1)
    else:
        # Mode normal
        main()