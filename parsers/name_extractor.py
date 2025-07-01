# parsers/name_extractor.py - VERSION AMÉLIORÉE
"""
Extracteur de noms amélioré avec corrections OCR intégrées
Intègre les corrections identifiées directement dans le processus d'extraction
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from functools import lru_cache
from collections import Counter

from config.settings import ParserConfig

class NameExtractor:
    """Extracteur de noms avec corrections OCR intégrées"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Statistiques de correction intégrées
        self.stats = {
            'noms_extraits': 0,
            'corrections_ocr_appliquees': 0,
            'noms_tronques_corriges': 0,
            'erreurs_non_corrigees': 0
        }
        
        # Dictionnaire de corrections OCR découvertes
        self.corrections_ocr = {
            # === ERREURS "Aii" SYSTÉMATIQUES ===
            'Aiicelle': 'Ancelle',
            'Aiiber': 'Auber', 
            'Aiieelle': 'Ancelle',
            'Aiigotin': 'Antigotin',
            'Aiimont': 'Aumont',
            'Aiil': 'Anil',
            'Aiine-': 'Anne-',
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
            'Eléonore': 'Éléonore'
        }
        
        # Patterns de noms améliorés
        self._setup_enhanced_patterns()
        
        # Cache pour performance
        self._correction_cache = {}
    
    def _setup_enhanced_patterns(self):
        """Configure les patterns de reconnaissance de noms améliorés"""
        
        # Pattern principal plus tolérant aux erreurs OCR
        self.nom_pattern = re.compile(
            r'\b[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßĀ-ūŁł0-9]'  # Début acceptant chiffres (erreurs OCR)
            r'[a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿĀ-ūŁł\'\-\.]*'   # Corps du nom
            r'(?:\s+[a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿĀ-ūŁł\'\-\.]+)*'  # Noms composés
            r'\b',
            re.IGNORECASE
        )
        
        # Patterns spécifiques pour titres et noms
        self.patterns_titre_nom = {
            'messire': re.compile(r'\b(Messire)\s+([A-Z][a-z\-\s]+)', re.IGNORECASE),
            'damoiselle': re.compile(r'\b(Damoiselle)\s+([A-Z][a-z\-\s]+)', re.IGNORECASE),
            'sieur': re.compile(r'\b(?:sieur?|sr\.?)\s+([A-Z][a-z\-\s]+)', re.IGNORECASE),
            'ecuyer': re.compile(r'\b(?:écuyer?|éc\.?|ec\.?)\s+([A-Z][a-z\-\s]+)', re.IGNORECASE)
        }
    
    @lru_cache(maxsize=1000)
    def _corriger_nom_ocr(self, nom: str) -> Tuple[str, bool]:
        """
        Applique les corrections OCR au nom avec cache
        
        Returns:
            Tuple[str, bool]: (nom_corrigé, correction_appliquée)
        """
        if not nom or len(nom) < 2:
            return nom, False
        
        nom_original = nom
        correction_appliquee = False
        
        # 1. Corrections exactes (plus rapides)
        if nom in self.corrections_ocr:
            nom_corrige = self.corrections_ocr[nom]
            self.stats['corrections_ocr_appliquees'] += 1
            if '-' in nom_original:
                self.stats['noms_tronques_corriges'] += 1
            return nom_corrige, True
        
        # 2. Corrections partielles (patterns)
        nom_corrige = nom
        for erreur, correction in self.corrections_ocr.items():
            if erreur in nom_corrige:
                nom_corrige = nom_corrige.replace(erreur, correction)
                correction_appliquee = True
        
        # 3. Corrections contextuelles pour noms tronqués
        if '-' in nom and not correction_appliquee:
            nom_corrige = self._corriger_nom_tronque_contextuel(nom)
            if nom_corrige != nom:
                correction_appliquee = True
                self.stats['noms_tronques_corriges'] += 1
        
        if correction_appliquee:
            self.stats['corrections_ocr_appliquees'] += 1
        
        return nom_corrige, correction_appliquee
    
    def _corriger_nom_tronque_contextuel(self, nom: str) -> str:
        """Correction contextuelle des noms tronqués non mappés"""
        
        # Si se termine par "- " ou "-", tentative de completion
        if re.match(r'^[A-Z][a-z]+-?\s*$', nom):
            nom_base = nom.rstrip('- ')
            
            # Heuristiques basées sur les patterns courants
            if len(nom_base) <= 3:
                # Très courts : probablement des prénoms
                if nom_base.startswith('An'):
                    return 'Anne'
                elif nom_base.startswith('Ma'):
                    return 'Marie'
                elif nom_base.startswith('Je'):
                    return 'Jean'
            
            elif len(nom_base) >= 4:
                # Plus longs : possiblement des noms de famille
                # Conserver tel quel pour éviter les erreurs
                return nom_base
        
        return nom
    
    def extract_complete_names_with_sources(self, texte: str, source_ref: str, 
                                          page_number: int = None) -> List[Dict]:
        """
        Extraction complète avec corrections OCR intégrées
        
        Args:
            texte: Texte à analyser
            source_ref: Référence de la source
            page_number: Numéro de page
            
        Returns:
            List[Dict]: Personnes extraites avec corrections appliquées
        """
        if not texte or len(texte.strip()) < 10:
            return []
        
        personnes = []
        positions_utilisees = set()
        
        # 1. Extraction avec patterns titre + nom (priorité haute)
        for nom_pattern, pattern in self.patterns_titre_nom.items():
            for match in pattern.finditer(texte):
                if self._position_overlap(match, positions_utilisees):
                    continue
                
                titre = match.group(1) if match.lastindex >= 1 else ""
                nom_brut = match.group(2) if match.lastindex >= 2 else match.group(1)
                
                # Appliquer corrections OCR
                nom_corrige, correction_appliquee = self._corriger_nom_ocr(nom_brut)
                
                personne = {
                    'nom_complet': f"{titre} {nom_corrige}".strip(),
                    'nom': self._extraire_nom_famille(nom_corrige),
                    'prenoms': self._extraire_prenoms(nom_corrige),
                    'titre': titre,
                    'source_reference': source_ref,
                    'page': page_number,
                    'correction_ocr_appliquee': correction_appliquee,
                    'nom_original': nom_brut if correction_appliquee else None
                }
                
                personnes.append(personne)
                positions_utilisees.update(range(match.start(), match.end()))
                self.stats['noms_extraits'] += 1
        
        # 2. Extraction générale des noms restants
        for match in self.nom_pattern.finditer(texte):
            if self._position_overlap(match, positions_utilisees):
                continue
            
            nom_brut = match.group(0).strip()
            
            # Filtrer les mots trop courts ou non pertinents
            if not self._est_nom_valide(nom_brut):
                continue
            
            # Appliquer corrections OCR
            nom_corrige, correction_appliquee = self._corriger_nom_ocr(nom_brut)
            
            personne = {
                'nom_complet': nom_corrige,
                'nom': self._extraire_nom_famille(nom_corrige),
                'prenoms': self._extraire_prenoms(nom_corrige),
                'source_reference': source_ref,
                'page': page_number,
                'correction_ocr_appliquee': correction_appliquee,
                'nom_original': nom_brut if correction_appliquee else None
            }
            
            personnes.append(personne)
            positions_utilisees.update(range(match.start(), match.end()))
            self.stats['noms_extraits'] += 1
        
        # 3. Post-traitement et déduplication
        personnes_uniques = self._dedupliquer_personnes(personnes)
        
        # 4. Validation finale
        personnes_validees = self._valider_personnes_extraites(personnes_uniques)
        
        return personnes_validees
    
    def _est_nom_valide(self, nom: str) -> bool:
        """Validation améliorée des noms extraits"""
        
        if not nom or len(nom) < 2:
            return False
        
        # Filtrer mots courants non-noms
        mots_exclus = {
            'le', 'la', 'les', 'de', 'du', 'des', 'et', 'ou', 'en', 'dans',
            'pour', 'avec', 'sans', 'sur', 'sous', 'par', 'ce', 'cette',
            'son', 'sa', 'ses', 'leur', 'leurs', 'que', 'qui', 'dont',
            'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
            'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'
        }
        
        if nom.lower() in mots_exclus:
            return False
        
        # Doit commencer par une majuscule (après correction éventuelle)
        if not nom[0].isupper():
            return False
        
        # Pas uniquement des chiffres
        if nom.isdigit():
            return False
        
        # Longueur raisonnable
        if len(nom) > 50:
            return False
        
        return True
    
    def _position_overlap(self, match, positions_utilisees: Set[int]) -> bool:
        """Vérifie si un match chevauche avec des positions déjà utilisées"""
        match_range = range(match.start(), match.end())
        return any(pos in positions_utilisees for pos in match_range)
    
    def _extraire_nom_famille(self, nom_complet: str) -> str:
        """Extrait le nom de famille du nom complet"""
        # Logique simplifiée : dernier mot en majuscules
        mots = nom_complet.split()
        if mots:
            for mot in reversed(mots):
                if mot.isupper() or (mot.istitle() and len(mot) > 2):
                    return mot
            return mots[-1]  # Fallback
        return nom_complet
    
    def _extraire_prenoms(self, nom_complet: str) -> List[str]:
        """Extrait les prénoms du nom complet"""
        nom_famille = self._extraire_nom_famille(nom_complet)
        prenoms_str = nom_complet.replace(nom_famille, '').strip()
        
        if prenoms_str:
            return [p.strip() for p in prenoms_str.split() if p.strip()]
        return []
    
    def _dedupliquer_personnes(self, personnes: List[Dict]) -> List[Dict]:
        """Déduplication intelligente des personnes extraites"""
        
        personnes_uniques = {}
        
        for personne in personnes:
            # Clé de déduplication basée sur nom normalisé
            nom_normalise = re.sub(r'\s+', ' ', personne['nom_complet'].lower().strip())
            
            if nom_normalise in personnes_uniques:
                # Conserver la version avec le plus d'informations
                existante = personnes_uniques[nom_normalise]
                if (personne.get('titre') and not existante.get('titre')) or \
                   (personne.get('correction_ocr_appliquee') and not existante.get('correction_ocr_appliquee')):
                    personnes_uniques[nom_normalise] = personne
            else:
                personnes_uniques[nom_normalise] = personne
        
        return list(personnes_uniques.values())
    
    def _valider_personnes_extraites(self, personnes: List[Dict]) -> List[Dict]:
        """Validation finale des personnes extraites"""
        
        personnes_valides = []
        
        for personne in personnes:
            # Vérifications de base
            if not personne.get('nom_complet') or len(personne['nom_complet']) < 2:
                self.stats['erreurs_non_corrigees'] += 1
                continue
            
            # Vérifier que la correction n'a pas créé d'incohérence
            if personne.get('correction_ocr_appliquee'):
                nom_corrige = personne['nom_complet']
                if not self._est_nom_valide(nom_corrige):
                    self.stats['erreurs_non_corrigees'] += 1
                    continue
            
            personnes_valides.append(personne)
        
        return personnes_valides
    
    def get_enhanced_statistics(self) -> Dict:
        """Statistiques enrichies avec informations de correction"""
        
        stats_base = {
            'noms_extraits': self.stats['noms_extraits'],
            'corrections_ocr_appliquees': self.stats['corrections_ocr_appliquees'],
            'noms_tronques_corriges': self.stats['noms_tronques_corriges'],
            'erreurs_non_corrigees': self.stats['erreurs_non_corrigees'],
            'taux_correction': 0.0,
            'qualite_estimee': 0.0
        }
        
        if stats_base['noms_extraits'] > 0:
            stats_base['taux_correction'] = (
                stats_base['corrections_ocr_appliquees'] / stats_base['noms_extraits']
            ) * 100
            
            stats_base['qualite_estimee'] = (
                (stats_base['noms_extraits'] - stats_base['erreurs_non_corrigees']) /
                stats_base['noms_extraits']
            ) * 100
        
        return stats_base
    
    def reset_statistics(self):
        """Remet à zéro les statistiques"""
        self.stats = {
            'noms_extraits': 0,
            'corrections_ocr_appliquees': 0,
            'noms_tronques_corriges': 0,
            'erreurs_non_corrigees': 0
        }
        self._correction_cache.clear()

# === TESTS ET VALIDATION ===

if __name__ == "__main__":
    from config.settings import ParserConfig
    
    # Test du NameExtractor amélioré
    config = ParserConfig()
    extractor = NameExtractor(config)
    
    # Texte de test avec erreurs OCR
    test_text = """
    942,Jean Aiicelle,Jean,Aiicelle,1,Jean Aiicelle,Jean Aiicelle
    8835,Jaeques- Roch Adam,Jaeques- Roch,Adam,1,Jaeques- Roch Adam
    12412,Marguerite Ade-,Marguerite,Ade-,1,Marguerite Ade-
    9311,Messire Henry Acher,Messire Henry,Acher,1,Messire Henry Acher
    Catlierhie Aiimont et Franteois Guillaïune, parents de Marie- An
    """
    
    print("=== TEST NAME EXTRACTOR AMÉLIORÉ ===")
    print(f"Texte de test:\n{test_text}\n")
    
    # Extraction avec corrections
    personnes = extractor.extract_complete_names_with_sources(
        test_text, "Test OCR", 1
    )
    
    print(f"=== RÉSULTATS ({len(personnes)} personnes) ===")
    for i, personne in enumerate(personnes, 1):
        print(f"{i}. {personne['nom_complet']}")
        if personne.get('correction_ocr_appliquee'):
            print(f"   ✅ Corrigé de: '{personne['nom_original']}'")
        if personne.get('titre'):
            print(f"   Titre: {personne['titre']}")
    
    # Statistiques
    stats = extractor.get_enhanced_statistics()
    print(f"\n=== STATISTIQUES ===")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:.1f}%")
        else:
            print(f"{key}: {value}")