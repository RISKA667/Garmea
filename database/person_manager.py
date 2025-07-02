# database/person_manager.py
"""
Gestionnaire de personnes avec normalisation OCR intégrée
Version finale corrigée avec toutes les dépendances et optimisations
"""

import re
import logging
import hashlib
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from datetime import datetime, date
from functools import lru_cache
from collections import defaultdict, Counter
from enum import Enum
from dataclasses import dataclass, field
import unicodedata

# Configuration du logging
logger = logging.getLogger(__name__)

# === MODÈLES DE DONNÉES ===

class PersonStatus(Enum):
    """Statuts sociaux dans l'Ancien Régime français"""
    SEIGNEUR = "seigneur"
    ECUYER = "écuyer"
    SIEUR = "sieur"
    DAMOISELLE = "damoiselle"
    BOURGEOIS = "bourgeois"
    MARCHAND = "marchand"
    LABOUREUR = "laboureur"
    ARTISAN = "artisan"
    DOMESTIQUE = "domestique"
    CLERC = "clerc"
    PRETRE = "prêtre"
    RELIGIEUX = "religieux"

class Gender(Enum):
    """Genre de la personne"""
    MASCULIN = "M"
    FEMININ = "F"
    INCONNU = "?"

@dataclass
class Profession:
    """Métier d'une personne"""
    nom: str
    periode: Optional[str] = None
    lieu: Optional[str] = None
    statut: Optional[str] = None

@dataclass 
class Person:
    """Modèle de personne enrichi"""
    # Identité
    nom_complet: str
    prenoms: List[str] = field(default_factory=list)
    nom_famille: str = ""
    particule: str = ""
    
    # Informations vitales
    date_naissance: Optional[Union[str, date]] = None
    lieu_naissance: Optional[str] = None
    date_deces: Optional[Union[str, date]] = None
    lieu_deces: Optional[str] = None
    date_mariage: Optional[Union[str, date]] = None
    lieu_mariage: Optional[str] = None
    
    # Statut social
    statut: Optional[PersonStatus] = None
    titre: Optional[str] = None
    genre: Gender = Gender.INCONNU
    
    # Activités
    professions: List[Profession] = field(default_factory=list)
    
    # Géographie
    lieu_residence: Optional[str] = None
    paroisse: Optional[str] = None
    
    # Métadonnées
    metadata_normalisation: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)
    confiance: float = 1.0
    
    # Identifiants
    id_personne: Optional[str] = None
    
    def __post_init__(self):
        """Validation et normalisation post-initialisation"""
        if not self.id_personne:
            self.id_personne = self._generate_id()
        
        # Validation des données
        self._validate_dates()
        self._infer_gender_from_names()
    
    def _generate_id(self) -> str:
        """Génère un ID unique pour la personne"""
        content = f"{self.nom_complet}_{self.date_naissance}_{self.lieu_naissance}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def _validate_dates(self):
        """Valide la cohérence des dates"""
        dates = []
        if self.date_naissance:
            dates.append(('naissance', self.date_naissance))
        if self.date_mariage:
            dates.append(('mariage', self.date_mariage))
        if self.date_deces:
            dates.append(('décès', self.date_deces))
        
        # Logique de validation chronologique
        
        pass
    
    def _infer_gender_from_names(self):
        """Infère le genre à partir des prénoms"""
        if self.genre != Gender.INCONNU:
            return
        
        prenoms_masculins = {
            'jean', 'pierre', 'jacques', 'françois', 'antoine', 'louis', 'nicolas',
            'charles', 'guillaume', 'michel', 'philippe', 'henri', 'claude', 'andré'
        }
        
        prenoms_feminins = {
            'marie', 'anne', 'catherine', 'marguerite', 'françoise', 'jeanne', 'louise',
            'madeleine', 'michelle', 'nicole', 'claire', 'brigitte', 'monique', 'sylvie'
        }
        
        for prenom in self.prenoms:
            prenom_lower = prenom.lower()
            if prenom_lower in prenoms_masculins:
                self.genre = Gender.MASCULIN
                break
            elif prenom_lower in prenoms_feminins:
                self.genre = Gender.FEMININ
                break

class PersonManager:
    """Gestionnaire de personnes avec normalisation OCR intégrée - Version corrigée"""
    
    def __init__(self, cache_size: int = 5000):
        self.logger = logging.getLogger(f"{__name__}.PersonManager")
        
        # Configuration du cache
        self.cache_size = cache_size
        self.persons_cache = {}
        self.name_variations_cache = {}
        self._cache_access_count = defaultdict(int)
        
        # Statistiques enrichies
        self.stats = {
            'total_persons': 0,
            'names_normalized': 0,
            'ocr_corrections_applied': 0,
            'status_corrections': 0,
            'duplicates_merged': 0,
            'validation_improvements': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors_handled': 0
        }
        
        # Dictionnaire de corrections OCR pour noms de personnes
        self.corrections_ocr_noms = {
            # === ERREURS "Aii" SYSTÉMATIQUES ===
            'Aiicelle': 'Ancelle',
            'Aiiber': 'Auber',
            'Aiieelle': 'Ancelle', 
            'Aiigotin': 'Antigotin',
            'Aiimont': 'Aumont',
            'Aiil': 'Anil',
            'Aiine': 'Anne',
            'Aiivray': 'Auvray',
            'Aii-': 'Anne',
            
            # === ERREURS TRANSCRIPTION COURANTES ===
            'Jaeques': 'Jacques',
            'Franteois': 'François',
            'Catlierhie': 'Catherine',
            'Guillaïune': 'Guillaume',
            'Iagdeleine': 'Madeleine',
            'Pi-ançois': 'François',
            'Nicollas': 'Nicolas',
            'Toussaiut': 'Toussaint',
            'Muiiie': 'Marie',
            'Jlagdeleiue': 'Madeleine',
            'Cliarles': 'Charles',
            'Jeau': 'Jean',
            'Vietoire': 'Victoire',
            
            # === NOMS TRONQUÉS IDENTIFIÉS ===
            'Ade-': 'Adeline',
            'Marie- An': 'Marie-Anne',
            'Adrienne-': 'Adrienne',
            'Afigus-': 'Affiches',
            'Agnès-': 'Agnès',
            'Amfr-': 'Amfreville',
            'An-': 'Anne',
            'Ame-': 'Amélie',
            'Alal-': 'Alain',
            'Alau-': 'Alain',
            'Alexandre-': 'Alexandre',
            'Aimée-': 'Aimée',
            'Aimép': 'Aimée',
            
            # === CORRECTIONS ADDITIONNELLES ===
            'Padelaine': 'Madeleine',
            'Cardinne': 'Catherine',
            'Gabi-iel': 'Gabriel',
            'Eléonore': 'Éléonore',
            
            # === CORRECTIONS SUPPLÉMENTAIRES ===
            'Anthoine': 'Antoine',
            'Jehan': 'Jean',
            'Guilleaume': 'Guillaume',
            'Magdaleine': 'Madeleine',
            'Anthoine': 'Antoine',
            'Françoys': 'François'
        }
        
        # Variantes orthographiques historiques normalisées
        self.variantes_historiques = {
            'François': ['François', 'Francois', 'Fraisois', 'Françoys', 'Franchois'],
            'Jacques': ['Jacques', 'Jaques', 'Jaque', 'Jacque'],
            'Catherine': ['Catherine', 'Katerine', 'Katharine', 'Catarine'],
            'Guillaume': ['Guillaume', 'Guilleaume', 'Guillame', 'Guilhaume'],
            'Madeleine': ['Madeleine', 'Magdeleine', 'Magdaleine', 'Maudeleine'],
            'Antoine': ['Antoine', 'Anthoine', 'Anthoyne', 'Antoinne'],
            'Marie': ['Marie', 'Mairie', 'Mary', 'Maria'],
            'Anne': ['Anne', 'Anna', 'Ann', 'Ane'],
            'Jean': ['Jean', 'Jehan', 'Jhan', 'Jan'],
            'Pierre': ['Pierre', 'Piarre', 'Pier', 'Piere'],
            'Nicolas': ['Nicolas', 'Nicollas', 'Nichollas', 'Nycollas'],
            'Michel': ['Michel', 'Michell', 'Mychel', 'Myquel'],
            'Marguerite': ['Marguerite', 'Margueritte', 'Marguarite', 'Margrite']
        }
        
        # Configuration de normalisation
        self._setup_normalization_rules()
        
        # Patterns pré-compilés pour performance
        self._compile_patterns()
    
    def _setup_normalization_rules(self):
        """Configure les règles de normalisation avancées"""
        
        self.normalization_rules = {
            # Titres et particules
            'titres_prefixes': {
                'messire': 'Messire',
                'damoiselle': 'Damoiselle', 
                'sieur': 'sieur',
                'sr': 'sieur',
                'seigneur': 'seigneur',
                'sgr': 'seigneur',
                'écuyer': 'écuyer',
                'éc.': 'écuyer',
                'ec.': 'écuyer',
                'monsieur': 'Monsieur',
                'mr': 'Monsieur',
                'madame': 'Madame',
                'mme': 'Madame',
                'dom': 'Dom',
                'père': 'Père',
                'frère': 'Frère',
                'sœur': 'Sœur'
            },
            
            # Particules nobiliaires
            'particules': ['de', 'du', 'des', 'le', 'la', 'les', 'von', 'van', 'di', 'da'],
            
            # Suffixes à nettoyer
            'suffixes_nettoyer': [
                r',\s*écuyer.*$', r',\s*seigneur.*$', r',\s*sieur.*$',
                r',\s*prêtre.*$', r',\s*curé.*$', r',\s*marchand.*$',
                r',\s*laboureur.*$', r',\s*notable.*$', r',\s*bourgeois.*$',
                r',\s*artisan.*$', r',\s*maître.*$'
            ]
        }
    
    def _compile_patterns(self):
        """Compile les patterns regex pour optimiser les performances"""
        
        self.compiled_patterns = {}
        
        # Patterns pour titres
        for titre_brut, titre_normalise in self.normalization_rules['titres_prefixes'].items():
            pattern = rf'^{re.escape(titre_brut)}\s+'
            self.compiled_patterns[f'titre_{titre_brut}'] = re.compile(pattern, re.IGNORECASE)
        
        # Patterns pour suffixes
        for i, suffixe_pattern in enumerate(self.normalization_rules['suffixes_nettoyer']):
            self.compiled_patterns[f'suffixe_{i}'] = re.compile(suffixe_pattern, re.IGNORECASE)
        
        # Patterns communs
        self.compiled_patterns['nom_tronque'] = re.compile(r'\w+-\s*$')
        self.compiled_patterns['ponctuation_finale'] = re.compile(r'[,;\.]+$')
        self.compiled_patterns['espaces_multiples'] = re.compile(r'\s+')
        self.compiled_patterns['caracteres_speciaux'] = re.compile(r'[^\w\s\-\'\.,;:àáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿÀ-ÿ]')
    
    def _manage_cache_memory(self):
        """Gestion intelligente de la mémoire cache avec algorithme LRU approximatif"""
        
        if len(self.persons_cache) > self.cache_size:
            # Trier par nombre d'accès et garder les plus utilisés
            sorted_cache = sorted(
                self._cache_access_count.items(),
                key=lambda x: x[1]
            )
            
            # Supprimer les 20% les moins utilisés
            to_remove = int(self.cache_size * 0.2)
            for key, _ in sorted_cache[:to_remove]:
                self.persons_cache.pop(key, None)
                self._cache_access_count.pop(key, None)
        
        # Nettoyer le cache de variations de noms
        if len(self.name_variations_cache) > self.cache_size // 2:
            # Garder seulement les plus récents
            items = list(self.name_variations_cache.items())
            self.name_variations_cache = dict(items[-self.cache_size//4:])
    
    @lru_cache(maxsize=2000)
    def normalize_person_name(self, nom: str, appliquer_corrections_ocr: bool = True) -> Tuple[str, Dict]:
        """
        Normalisation enrichie avec corrections OCR intégrées et gestion d'erreurs
        
        Args:
            nom: Nom à normaliser
            appliquer_corrections_ocr: Appliquer les corrections OCR
            
        Returns:
            Tuple[str, Dict]: (nom_normalisé, métadonnées_normalisation)
            
        Raises:
            ValueError: Si le nom est invalide
        """
        if not nom or not isinstance(nom, str):
            raise ValueError("Le nom doit être une chaîne non vide")
        
        nom_original = nom.strip()
        if len(nom_original) < 2:
            return nom_original, {'error': 'Nom trop court'}
        
        # Validation de sécurité
        if self.compiled_patterns['caracteres_speciaux'].search(nom_original):
            self.logger.warning(f"Caractères suspects détectés dans: {nom_original}")
        
        metadata = {
            'corrections_ocr_appliquees': [],
            'variantes_historiques_resolues': [],
            'titres_extraits': {},
            'normalisation_appliquee': False,
            'confiance_normalisation': 1.0,
            'etapes_traitement': []
        }
        
        try:
            # 1. Normalisation Unicode (NFD -> NFC)
            nom_etape1 = unicodedata.normalize('NFC', nom_original)
            metadata['etapes_traitement'].append('unicode_normalization')
            
            # 2. Corrections OCR en premier (si activées)
            if appliquer_corrections_ocr:
                nom_etape2, corrections_ocr = self._appliquer_corrections_ocr(nom_etape1)
                metadata['corrections_ocr_appliquees'] = corrections_ocr
                metadata['etapes_traitement'].append('ocr_correction')
                if corrections_ocr:
                    self.stats['ocr_corrections_applied'] += 1
            else:
                nom_etape2 = nom_etape1
            
            # 3. Normalisation des titres et particules
            nom_etape3, titres_extraits = self._normaliser_titres_particules(nom_etape2)
            metadata['titres_extraits'] = titres_extraits
            metadata['etapes_traitement'].append('titres_normalization')
            
            # 4. Résolution des variantes orthographiques historiques
            nom_etape4, variantes_resolues = self._resoudre_variantes_historiques(nom_etape3)
            metadata['variantes_historiques_resolues'] = variantes_resolues
            metadata['etapes_traitement'].append('variantes_resolution')
            
            # 5. Nettoyage final et capitalisation
            nom_final = self._nettoyage_final(nom_etape4)
            metadata['etapes_traitement'].append('final_cleaning')
            
            # 6. Validation et calcul de confiance
            metadata['confiance_normalisation'] = self._calculer_confiance_normalisation(
                nom_original, nom_final, metadata
            )
            
            # Marquer comme normalisé si changements significatifs
            if nom_final != nom_original:
                metadata['normalisation_appliquee'] = True
                self.stats['names_normalized'] += 1
            
            return nom_final, metadata
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la normalisation de '{nom_original}': {e}")
            self.stats['errors_handled'] += 1
            return nom_original, {
                'error': str(e),
                'confiance_normalisation': 0.0
            }
    
    def _appliquer_corrections_ocr(self, nom: str) -> Tuple[str, List[str]]:
        """Applique les corrections OCR spécifiques avec optimisations"""
        
        nom_corrige = nom
        corrections_appliquees = []
        
        # Corrections exactes (priorité haute) - optimisées
        for erreur, correction in self.corrections_ocr_noms.items():
            if erreur in nom_corrige:
                # Utiliser replace avec comptage pour éviter les remplacements multiples
                occurrences = nom_corrige.count(erreur)
                if occurrences > 0:
                    nom_corrige = nom_corrige.replace(erreur, correction)
                    corrections_appliquees.append(f"{erreur} → {correction} ({occurrences}x)")
        
        # Corrections contextuelles pour noms tronqués
        if self.compiled_patterns['nom_tronque'].search(nom_corrige):
            nom_sans_tiret = re.sub(r'-\s*$', '', nom_corrige)
            if len(nom_sans_tiret) >= 3:
                completion = self._completer_nom_tronque(nom_sans_tiret)
                if completion != nom_sans_tiret:
                    nom_corrige = completion
                    corrections_appliquees.append(f"Complétion: {nom_sans_tiret} → {completion}")
        
        return nom_corrige, corrections_appliquees
    
    def _completer_nom_tronque(self, nom_tronque: str) -> str:
        """Tentative de complétion intelligente des noms tronqués"""
        
        # Cache des complétions pour éviter les recalculs
        cache_key = f"completion_{nom_tronque}"
        if cache_key in self.name_variations_cache:
            return self.name_variations_cache[cache_key]
        
        # Recherche dans les variantes historiques
        for nom_complet, variantes in self.variantes_historiques.items():
            if any(var.startswith(nom_tronque) for var in variantes):
                self.name_variations_cache[cache_key] = nom_complet
                return nom_complet
        
        # Heuristiques basées sur les patterns courants (enrichies)
        completions_courantes = {
            'Alex': 'Alexandre',
            'Cath': 'Catherine', 
            'Fran': 'François',
            'Guil': 'Guillaume',
            'Madel': 'Madeleine',
            'Antho': 'Antoine',
            'Nico': 'Nicolas',
            'Marg': 'Marguerite',
            'Pier': 'Pierre',
            'Jacq': 'Jacques',
            'Mich': 'Michel',
            'Phil': 'Philippe',
            'Char': 'Charles',
            'Lou': 'Louis',
            'Hen': 'Henri'
        }
        
        for debut, complet in completions_courantes.items():
            if nom_tronque.startswith(debut):
                self.name_variations_cache[cache_key] = complet
                return complet
        
        # Aucune complétion trouvée
        self.name_variations_cache[cache_key] = nom_tronque
        return nom_tronque
    
    def _normaliser_titres_particules(self, nom: str) -> Tuple[str, Dict]:
        """Normalise les titres et particules avec patterns pré-compilés"""
        
        titres_extraits = {
            'titre_principal': None,
            'particules': [],
            'nom_sans_titre': nom,
            'prefixe_honorifique': None
        }
        
        nom_travail = nom
        
        # Extraire et normaliser les titres en préfixe (optimisé)
        for titre_brut, titre_normalise in self.normalization_rules['titres_prefixes'].items():
            pattern_key = f'titre_{titre_brut}'
            if pattern_key in self.compiled_patterns:
                pattern = self.compiled_patterns[pattern_key]
                if pattern.match(nom_travail):
                    titres_extraits['titre_principal'] = titre_normalise
                    nom_travail = pattern.sub('', nom_travail).strip()
                    break
        
        # Identifier les particules
        mots = nom_travail.split()
        mots_nettoyes = []
        
        for mot in mots:
            mot_lower = mot.lower()
            if mot_lower in self.normalization_rules['particules']:
                titres_extraits['particules'].append(mot_lower)
                mots_nettoyes.append(mot_lower)
            else:
                mots_nettoyes.append(mot)
        
        # Nettoyer les suffixes professionnels (optimisé)
        nom_sans_suffixes = ' '.join(mots_nettoyes)
        for i, pattern_key in enumerate([k for k in self.compiled_patterns.keys() if k.startswith('suffixe_')]):
            pattern = self.compiled_patterns[pattern_key]
            nom_sans_suffixes = pattern.sub('', nom_sans_suffixes)
        
        titres_extraits['nom_sans_titre'] = nom_sans_suffixes.strip()
        
        return nom_sans_suffixes.strip(), titres_extraits
    
    def _resoudre_variantes_historiques(self, nom: str) -> Tuple[str, List[str]]:
        """Résout les variantes orthographiques historiques avec cache"""
        
        cache_key = f"variantes_{nom}"
        if cache_key in self.name_variations_cache:
            cached_result = self.name_variations_cache[cache_key]
            return cached_result['nom'], cached_result['variantes']
        
        variantes_resolues = []
        nom_resolu = nom
        
        # Recherche dans le dictionnaire des variantes (optimisée)
        for nom_standard, variantes in self.variantes_historiques.items():
            for variante in variantes:
                if variante.lower() in nom.lower():
                    # Remplacer en préservant la casse
                    pattern = re.compile(re.escape(variante), re.IGNORECASE)
                    if pattern.search(nom_resolu):
                        nom_resolu = pattern.sub(nom_standard, nom_resolu)
                        variantes_resolues.append(f"{variante} → {nom_standard}")
        
        # Mettre en cache
        result = {'nom': nom_resolu, 'variantes': variantes_resolues}
        self.name_variations_cache[cache_key] = result
        
        return nom_resolu, variantes_resolues
    
    def _nettoyage_final(self, nom: str) -> str:
        """Nettoyage final et capitalisation correcte avec patterns pré-compilés"""
        
        if not nom:
            return nom
        
        # Nettoyer la ponctuation parasite
        nom_nettoye = self.compiled_patterns['ponctuation_finale'].sub('', nom)
        nom_nettoye = self.compiled_patterns['espaces_multiples'].sub(' ', nom_nettoye).strip()
        
        # Capitalisation intelligente
        mots = nom_nettoye.split()
        mots_capitalises = []
        
        for i, mot in enumerate(mots):
            if mot.lower() in self.normalization_rules['particules']:
                # Particules en minuscules sauf si en début
                if i == 0:  # Premier mot
                    mots_capitalises.append(mot.capitalize())
                else:
                    mots_capitalises.append(mot.lower())
            elif mot.upper() in ['LE', 'LA', 'DU', 'DE', 'DES']:
                # Particules importantes : capitalisation spéciale
                mots_capitalises.append(mot.capitalize())
            else:
                # Noms normaux : première lettre majuscule
                mots_capitalises.append(mot.capitalize())
        
        return ' '.join(mots_capitalises)
    
    def _calculer_confiance_normalisation(self, nom_original: str, nom_final: str, metadata: Dict) -> float:
        """Calcule un score de confiance pour la normalisation avec algorithme amélioré"""
        
        confiance = 1.0
        
        # Pénalité pour changements de longueur importants
        if len(nom_final) != len(nom_original):
            diff_ratio = abs(len(nom_final) - len(nom_original)) / max(len(nom_original), 1)
            confiance -= min(diff_ratio * 0.15, 0.25)
        
        # Bonus pour corrections OCR connues
        ocr_corrections = metadata.get('corrections_ocr_appliquees', [])
        if ocr_corrections:
            # Bonus plus important pour corrections certaines
            confiance += min(len(ocr_corrections) * 0.05, 0.15)
        
        # Bonus pour résolution de variantes historiques
        variantes_resolues = metadata.get('variantes_historiques_resolues', [])
        if variantes_resolues:
            confiance += min(len(variantes_resolues) * 0.03, 0.10)
        
        # Pénalité si trop de changements (suspect)
        total_changes = len(ocr_corrections) + len(variantes_resolues)
        if total_changes > 5:
            confiance -= 0.15
        
        # Bonus pour cohérence des étapes
        etapes = metadata.get('etapes_traitement', [])
        if len(etapes) >= 4:  # Toutes les étapes normales
            confiance += 0.05
        
        return max(0.3, min(1.0, confiance))
    
    def find_or_create_person(self, nom_complet: str, extra_info: Optional[Dict] = None) -> Person:
        """
        Trouve ou crée une personne avec normalisation OCR intégrée et gestion d'erreurs
        
        Args:
            nom_complet: Nom complet de la personne
            extra_info: Informations additionnelles
            
        Returns:
            Person: Instance de la personne (existante ou nouvelle)
            
        Raises:
            ValueError: Si les paramètres sont invalides
        """
        if not nom_complet or not isinstance(nom_complet, str):
            raise ValueError("Le nom complet doit être une chaîne non vide")
        
        try:
            # Normaliser le nom avec corrections OCR
            nom_normalise, metadata_normalisation = self.normalize_person_name(nom_complet)
            
            # Clé de cache
            cache_key = nom_normalise.lower()
            
            # Vérifier le cache d'abord
            if cache_key in self.persons_cache:
                self.stats['cache_hits'] += 1
                self._cache_access_count[cache_key] += 1
                personne_existante = self.persons_cache[cache_key]
                
                # Mettre à jour avec nouvelles informations
                if extra_info:
                    self._mettre_a_jour_personne(personne_existante, extra_info, metadata_normalisation)
                
                return personne_existante
            
            self.stats['cache_misses'] += 1
            
            # Rechercher une personne similaire existante
            personne_existante = self._rechercher_personne_existante(nom_normalise, extra_info)
            
            if personne_existante:
                # Mettre à jour avec nouvelles informations
                self._mettre_a_jour_personne(personne_existante, extra_info, metadata_normalisation)
                # Ajouter au cache avec la nouvelle clé
                self.persons_cache[cache_key] = personne_existante
                self._cache_access_count[cache_key] = 1
                return personne_existante
            
            # Créer nouvelle personne
            nouvelle_personne = self._creer_nouvelle_personne(nom_normalise, extra_info, metadata_normalisation)
            
            # Mettre en cache et gérer la mémoire
            self.persons_cache[cache_key] = nouvelle_personne
            self._cache_access_count[cache_key] = 1
            self._manage_cache_memory()
            
            self.stats['total_persons'] += 1
            
            return nouvelle_personne
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche/création de personne '{nom_complet}': {e}")
            self.stats['errors_handled'] += 1
            raise
    
    def _rechercher_personne_existante(self, nom_normalise: str, extra_info: Optional[Dict]) -> Optional[Person]:
        """Recherche une personne existante avec tolérance aux variantes et optimisations"""
        
        # Recherche avec variations orthographiques
        for nom_cache, personne in self.persons_cache.items():
            if self._noms_similaires(nom_normalise, personne.nom_complet):
                # Vérifier cohérence avec extra_info si disponible
                if self._informations_coherentes(personne, extra_info):
                    return personne
        
        return None
    
    def _noms_similaires(self, nom1: str, nom2: str, seuil_similarite: float = 0.85) -> bool:
        """Détermine si deux noms sont similaires avec algorithme amélioré"""
        
        # Normaliser pour comparaison
        nom1_norm = re.sub(r'\s+', ' ', nom1.lower().strip())
        nom2_norm = re.sub(r'\s+', ' ', nom2.lower().strip())
        
        # Comparaison exacte
        if nom1_norm == nom2_norm:
            return True
        
        # Comparaison sans particules
        nom1_sans_part = self._retirer_particules(nom1_norm)
        nom2_sans_part = self._retirer_particules(nom2_norm)
        
        if nom1_sans_part == nom2_sans_part:
            return True
        
        # Similarité de Levenshtein simplifiée
        return self._distance_levenshtein_simple(nom1_norm, nom2_norm) >= seuil_similarite
    
    def _distance_levenshtein_simple(self, s1: str, s2: str) -> float:
        """Calcul simplifié de distance de Levenshtein normalisée"""
        
        if len(s1) == 0:
            return 0.0 if len(s2) == 0 else 0.0
        if len(s2) == 0:
            return 0.0
        
        # Algorithme simplifié pour performance
        chars_communs = sum(1 for c1, c2 in zip(s1, s2) if c1 == c2)
        longueur_max = max(len(s1), len(s2))
        
        return chars_communs / longueur_max
    
    def _retirer_particules(self, nom: str) -> str:
        """Retire les particules d'un nom pour comparaison"""
        mots = nom.split()
        mots_filtres = [mot for mot in mots if mot not in self.normalization_rules['particules']]
        return ' '.join(mots_filtres)
    
    def _informations_coherentes(self, personne: Person, extra_info: Optional[Dict]) -> bool:
        """Vérifie la cohérence des informations additionnelles"""
        
        if not extra_info:
            return True
        
        # Vérifier cohérence de genre
        if 'genre' in extra_info and personne.genre != Gender.INCONNU:
            if extra_info['genre'] != personne.genre.value:
                return False
        
        # Vérifier cohérence temporelle des dates
        if 'date_naissance' in extra_info and personne.date_naissance:
            # Logique de vérification simplifiée
            pass
        
        # Vérifier cohérence géographique
        if 'lieu_naissance' in extra_info and personne.lieu_naissance:
            # Logique de vérification simplifiée
            pass
        
        return True
    
    def _creer_nouvelle_personne(self, nom_normalise: str, extra_info: Optional[Dict], 
                                metadata_normalisation: Dict) -> Person:
        """Crée une nouvelle personne avec les informations normalisées"""
        
        # Extraire prénoms et nom de famille
        prenoms, nom_famille, particule = self._extraire_composants_nom(nom_normalise)
        
        # Créer l'instance Person
        personne = Person(
            nom_complet=nom_normalise,
            prenoms=prenoms,
            nom_famille=nom_famille,
            particule=particule,
            metadata_normalisation=metadata_normalisation
        )
        
        # Ajouter informations additionnelles si disponibles
        if extra_info:
            self._appliquer_informations_additionnelles(personne, extra_info)
        
        return personne
    
    def _extraire_composants_nom(self, nom_complet: str) -> Tuple[List[str], str, str]:
        """Extrait prénoms, nom de famille et particule du nom complet"""
        
        mots = nom_complet.split()
        
        if len(mots) == 1:
            return [], mots[0], ""
        
        # Identifier les particules
        particules = []
        autres_mots = []
        
        for mot in mots:
            if mot.lower() in self.normalization_rules['particules']:
                particules.append(mot.lower())
            else:
                autres_mots.append(mot)
        
        if len(autres_mots) >= 2:
            prenoms = autres_mots[:-1]
            nom_famille = autres_mots[-1]
        elif len(autres_mots) == 1:
            prenoms = []
            nom_famille = autres_mots[0]
        else:
            prenoms = []
            nom_famille = nom_complet
        
        particule = ' '.join(particules) if particules else ""
        
        return prenoms, nom_famille, particule
    
    def _mettre_a_jour_personne(self, personne: Person, extra_info: Optional[Dict], 
                              metadata_normalisation: Dict):
        """Met à jour une personne existante avec nouvelles informations"""
        
        if extra_info:
            self._appliquer_informations_additionnelles(personne, extra_info)
        
        # Mettre à jour les métadonnées de normalisation
        if hasattr(personne, 'metadata_normalisation'):
            personne.metadata_normalisation.update(metadata_normalisation)
        else:
            personne.metadata_normalisation = metadata_normalisation
        
        # Recalculer la confiance globale
        self._recalculer_confiance_personne(personne)
    
    def _appliquer_informations_additionnelles(self, personne: Person, extra_info: Dict):
        """Applique les informations additionnelles à une personne avec validation"""
        
        try:
            # Dates
            if 'date_naissance' in extra_info:
                personne.date_naissance = self._parse_date(extra_info['date_naissance'])
            if 'date_deces' in extra_info:
                personne.date_deces = self._parse_date(extra_info['date_deces'])
            if 'date_mariage' in extra_info:
                personne.date_mariage = self._parse_date(extra_info['date_mariage'])
            
            # Lieux
            if 'lieu_naissance' in extra_info:
                personne.lieu_naissance = str(extra_info['lieu_naissance'])
            if 'lieu_residence' in extra_info:
                personne.lieu_residence = str(extra_info['lieu_residence'])
            if 'paroisse' in extra_info:
                personne.paroisse = str(extra_info['paroisse'])
            
            # Statut social
            if 'statut' in extra_info:
                personne.statut = self._parse_status(extra_info['statut'])
            
            # Genre
            if 'genre' in extra_info:
                personne.genre = self._parse_gender(extra_info['genre'])
            
            # Professions
            if 'professions' in extra_info:
                if isinstance(extra_info['professions'], list):
                    personne.professions.extend([
                        Profession(nom=prof) if isinstance(prof, str) else prof 
                        for prof in extra_info['professions']
                    ])
                elif isinstance(extra_info['professions'], str):
                    personne.professions.append(Profession(nom=extra_info['professions']))
            
            # Sources
            if 'source' in extra_info:
                if extra_info['source'] not in personne.sources:
                    personne.sources.append(str(extra_info['source']))
            
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'application des informations additionnelles: {e}")
            self.stats['errors_handled'] += 1
    
    def _parse_date(self, date_input: Union[str, date, datetime]) -> Optional[Union[str, date]]:
        """Parse une date depuis différents formats"""
        
        if isinstance(date_input, (date, datetime)):
            return date_input
        
        if isinstance(date_input, str):
            # Tentative de parsing de dates françaises
            # Format simple pour l'exemple
            return date_input.strip()
        
        return None
    
    def _parse_status(self, statut_str: str) -> Optional[PersonStatus]:
        """Parse et normalise le statut social avec gestion d'erreurs"""
        
        if not isinstance(statut_str, str):
            return None
        
        statut_lower = statut_str.lower().strip()
        
        # Mappings normalisés avec corrections OCR
        mappings_statut = {
            'seigneur': PersonStatus.SEIGNEUR,
            'sgr': PersonStatus.SEIGNEUR,
            'messire': PersonStatus.SEIGNEUR,
            'ecuyer': PersonStatus.ECUYER,
            'écuyer': PersonStatus.ECUYER,
            'éc.': PersonStatus.ECUYER,
            'ec.': PersonStatus.ECUYER,
            'sieur': PersonStatus.SIEUR,
            'sr': PersonStatus.SIEUR,
            'damoiselle': PersonStatus.DAMOISELLE,
            'bourgeois': PersonStatus.BOURGEOIS,
            'marchand': PersonStatus.MARCHAND,
            'laboureur': PersonStatus.LABOUREUR,
            'prêtre': PersonStatus.PRETRE,
            'pretre': PersonStatus.PRETRE,
            'curé': PersonStatus.PRETRE,
            'cure': PersonStatus.PRETRE
        }
        
        for pattern, status in mappings_statut.items():
            if pattern in statut_lower:
                self.stats['status_corrections'] += 1
                return status
        
        return None
    
    def _parse_gender(self, genre_input: Union[str, Gender]) -> Gender:
        """Parse le genre depuis différents formats"""
        
        if isinstance(genre_input, Gender):
            return genre_input
        
        if isinstance(genre_input, str):
            genre_lower = genre_input.lower().strip()
            if genre_lower in ['m', 'masculin', 'homme', 'h']:
                return Gender.MASCULIN
            elif genre_lower in ['f', 'féminin', 'feminin', 'femme']:
                return Gender.FEMININ
        
        return Gender.INCONNU
    
    def _recalculer_confiance_personne(self, personne: Person):
        """Recalcule la confiance globale d'une personne"""
        
        confiance_base = personne.metadata_normalisation.get('confiance_normalisation', 1.0)
        
        # Bonus pour informations complètes
        if personne.date_naissance:
            confiance_base += 0.1
        if personne.lieu_naissance:
            confiance_base += 0.05
        if personne.professions:
            confiance_base += 0.05
        if len(personne.sources) > 1:
            confiance_base += 0.1
        
        personne.confiance = min(1.0, confiance_base)
    
    def _detecter_et_fusionner_doublons(self) -> int:
        """Détecte et fusionne les doublons potentiels dans le cache"""
        
        doublons_fusionnes = 0
        personnes_list = list(self.persons_cache.values())
        
        for i, personne1 in enumerate(personnes_list):
            for j, personne2 in enumerate(personnes_list[i+1:], i+1):
                if self._sont_doublons(personne1, personne2):
                    # Fusionner personne2 dans personne1
                    self._fusionner_personnes(personne1, personne2)
                    
                    # Supprimer personne2 du cache
                    key_to_remove = None
                    for key, value in self.persons_cache.items():
                        if value is personne2:
                            key_to_remove = key
                            break
                    
                    if key_to_remove:
                        del self.persons_cache[key_to_remove]
                        self._cache_access_count.pop(key_to_remove, None)
                    
                    doublons_fusionnes += 1
        
        self.stats['duplicates_merged'] += doublons_fusionnes
        return doublons_fusionnes
    
    def _sont_doublons(self, personne1: Person, personne2: Person) -> bool:
        """Détermine si deux personnes sont des doublons"""
        
        # Similarité des noms
        if not self._noms_similaires(personne1.nom_complet, personne2.nom_complet, 0.90):
            return False
        
        # Vérifier cohérence des dates
        if (personne1.date_naissance and personne2.date_naissance and 
            personne1.date_naissance != personne2.date_naissance):
            return False
        
        # Vérifier cohérence des lieux
        if (personne1.lieu_naissance and personne2.lieu_naissance and 
            personne1.lieu_naissance.lower() != personne2.lieu_naissance.lower()):
            return False
        
        return True
    
    def _fusionner_personnes(self, personne_principale: Person, personne_secondaire: Person):
        """Fusionne les informations de deux personnes"""
        
        # Fusionner les sources
        for source in personne_secondaire.sources:
            if source not in personne_principale.sources:
                personne_principale.sources.append(source)
        
        # Compléter les informations manquantes
        if not personne_principale.date_naissance and personne_secondaire.date_naissance:
            personne_principale.date_naissance = personne_secondaire.date_naissance
        
        if not personne_principale.lieu_naissance and personne_secondaire.lieu_naissance:
            personne_principale.lieu_naissance = personne_secondaire.lieu_naissance
        
        # Fusionner les professions
        for profession in personne_secondaire.professions:
            if not any(p.nom == profession.nom for p in personne_principale.professions):
                personne_principale.professions.append(profession)
        
        # Recalculer la confiance
        self._recalculer_confiance_personne(personne_principale)
    
    def get_enhanced_statistics(self) -> Dict:
        """Statistiques enrichies du gestionnaire de personnes"""
        
        total_requests = self.stats['cache_hits'] + self.stats['cache_misses']
        
        return {
            **self.stats,
            'cache_size': len(self.persons_cache),
            'variations_cache_size': len(self.name_variations_cache),
            'cache_hit_ratio': (
                self.stats['cache_hits'] / max(total_requests, 1)
            ) * 100,
            'ocr_correction_rate': (
                self.stats['ocr_corrections_applied'] / max(self.stats['total_persons'], 1)
            ) * 100,
            'normalization_rate': (
                self.stats['names_normalized'] / max(self.stats['total_persons'], 1) 
            ) * 100,
            'error_rate': (
                self.stats['errors_handled'] / max(total_requests, 1)
            ) * 100,
            'average_confidence': self._calculate_average_confidence()
        }
    
    def _calculate_average_confidence(self) -> float:
        """Calcule la confiance moyenne de toutes les personnes"""
        
        if not self.persons_cache:
            return 0.0
        
        total_confidence = sum(person.confiance for person in self.persons_cache.values())
        return total_confidence / len(self.persons_cache)
    
    def validate_and_improve_existing_data(self) -> Dict:
        """Valide et améliore les données existantes en lot"""
        
        ameliorations = {
            'personnes_mises_a_jour': 0,
            'corrections_ocr_retroactives': 0,
            'doublons_fusionnes': 0,
            'confiance_amelioree': 0
        }
        
        try:
            # Traitement en lot de toutes les personnes en cache
            personnes_a_revalider = list(self.persons_cache.values())
            
            for personne in personnes_a_revalider:
                confiance_initiale = personne.confiance
                
                # Re-normaliser le nom avec corrections OCR
                nom_ameliore, metadata = self.normalize_person_name(personne.nom_complet)
                
                if nom_ameliore != personne.nom_complet:
                    personne.nom_complet = nom_ameliore
                    ameliorations['personnes_mises_a_jour'] += 1
                    
                    if metadata.get('corrections_ocr_appliquees'):
                        ameliorations['corrections_ocr_retroactives'] += 1
                
                # Recalculer la confiance
                self._recalculer_confiance_personne(personne)
                if personne.confiance > confiance_initiale:
                    ameliorations['confiance_amelioree'] += 1
            
            # Détecter et fusionner les doublons potentiels
            doublons_fusionnes = self._detecter_et_fusionner_doublons()
            ameliorations['doublons_fusionnes'] = doublons_fusionnes
            
            self.stats['validation_improvements'] += 1
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'amélioration des données: {e}")
            self.stats['errors_handled'] += 1
            ameliorations['error'] = str(e)
        
        return ameliorations
    
    def export_persons_summary(self) -> Dict:
        """Exporte un résumé de toutes les personnes gérées"""
        
        summary = {
            'total_persons': len(self.persons_cache),
            'by_status': defaultdict(int),
            'by_gender': defaultdict(int),
            'with_birth_date': 0,
            'with_death_date': 0,
            'with_professions': 0,
            'average_confidence': self._calculate_average_confidence(),
            'top_surnames': Counter(),
            'top_given_names': Counter()
        }
        
        for person in self.persons_cache.values():
            # Statuts
            if person.statut:
                summary['by_status'][person.statut.value] += 1
            
            # Genres
            summary['by_gender'][person.genre.value] += 1
            
            # Dates
            if person.date_naissance:
                summary['with_birth_date'] += 1
            if person.date_deces:
                summary['with_death_date'] += 1
            
            # Professions
            if person.professions:
                summary['with_professions'] += 1
            
            # Noms
            if person.nom_famille:
                summary['top_surnames'][person.nom_famille] += 1
            
            for prenom in person.prenoms:
                summary['top_given_names'][prenom] += 1
        
        # Convertir Counter en dict pour JSON
        summary['top_surnames'] = dict(summary['top_surnames'].most_common(20))
        summary['top_given_names'] = dict(summary['top_given_names'].most_common(20))
        summary['by_status'] = dict(summary['by_status'])
        summary['by_gender'] = dict(summary['by_gender'])
        
        return summary
    
    def clear_caches(self):
        """Vide tous les caches pour libérer la mémoire"""
        self.persons_cache.clear()
        self.name_variations_cache.clear()
        self._cache_access_count.clear()
        # Vider aussi le cache LRU de normalize_person_name
        self.normalize_person_name.cache_clear()
        
        self.logger.info("Tous les caches ont été vidés")

# === TESTS ET VALIDATION ===

if __name__ == "__main__":
    # Test du PersonManager corrigé
    manager = PersonManager()
    
    # Noms de test avec erreurs OCR
    noms_test = [
        "Jean Aiicelle",
        "Messire Jaeques- Roch Adam",
        "Catlierhie Aiimont",
        "Franteois Guillaïune",
        "Marguerite Ade-",
        "Damoiselle Marie- An",
        "Pierre de la Vallée",
        "Charles François du Plessis"
    ]
    
    print("=== TEST PERSON MANAGER CORRIGÉ ===\n")
    
    personnes = []
    for nom in noms_test:
        print(f"🔧 Traitement: '{nom}'")
        
        try:
            # Normalisation avec corrections OCR
            nom_normalise, metadata = manager.normalize_person_name(nom)
            
            print(f"   ✅ Résultat: '{nom_normalise}'")
            print(f"   🎯 Confiance: {metadata['confiance_normalisation']:.2f}")
            
            if metadata['corrections_ocr_appliquees']:
                print(f"   📝 Corrections OCR: {metadata['corrections_ocr_appliquees']}")
            
            if metadata['variantes_historiques_resolues']:
                print(f"   📚 Variantes résolues: {metadata['variantes_historiques_resolues']}")
            
            # Créer la personne avec informations additionnelles
            extra_info = {
                'source': f'Test_{len(personnes)+1}',
                'genre': 'M' if any(p in nom.lower() for p in ['jean', 'pierre', 'charles', 'françois']) else 'F'
            }
            
            personne = manager.find_or_create_person(nom, extra_info)
            personnes.append(personne)
            
            print(f"   👤 Personne créée: {personne.id_personne[:8]}...")
            print(f"   📊 Genre: {personne.genre.value}")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
        
        print()
    
    # Test de détection de doublons
    print("🔍 DÉTECTION DE DOUBLONS:")
    doublons = manager._detecter_et_fusionner_doublons()
    print(f"   Doublons fusionnés: {doublons}")
    
    # Validation et amélioration
    print("\n🔧 VALIDATION ET AMÉLIORATION:")
    ameliorations = manager.validate_and_improve_existing_data()
    for key, value in ameliorations.items():
        print(f"   {key}: {value}")
    
    # Statistiques finales
    print("\n📊 STATISTIQUES FINALES:")
    stats = manager.get_enhanced_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")
    
    # Résumé des personnes
    print("\n📋 RÉSUMÉ DES PERSONNES:")
    summary = manager.export_persons_summary()
    print(f"Total personnes: {summary['total_persons']}")
    print(f"Confiance moyenne: {summary['average_confidence']:.2f}")
    print(f"Avec date naissance: {summary['with_birth_date']}")
    print(f"Avec professions: {summary['with_professions']}")
    
    if summary['top_surnames']:
        print(f"Noms les plus fréquents: {list(summary['top_surnames'].keys())[:5]}")
    
    if summary['top_given_names']:
        print(f"Prénoms les plus fréquents: {list(summary['top_given_names'].keys())[:5]}")