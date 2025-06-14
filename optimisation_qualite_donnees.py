# optimisation_qualite_donnees.py
"""
Script d'optimisation pour améliorer la qualité des données extraites
Applicable après un traitement réussi pour raffiner les résultats
"""

import json
import re
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Set

class OptimisateurQualiteDonnees:
    """Optimise la qualité des données extraites par le Smart PDF Analyzer"""
    
    def __init__(self):
        self.stats_optimisation = {
            'relations_filtrees': 0,
            'doublons_supprimes': 0,
            'noms_normalises': 0,
            'faux_positifs_detectes': 0
        }
    
    def optimiser_resultats(self, resultats: Dict) -> Dict:
        """
        Optimise les résultats d'extraction pour améliorer la qualité
        
        Args:
            resultats: Résultats du Smart PDF Analyzer
            
        Returns:
            Dict: Résultats optimisés
        """
        
        print("Optimisation de la qualité des données")
        print("=" * 40)
        
        # Extraire les données généalogiques
        genealogique = resultats.get('resultats_genealogiques', {})
        
        # 1. Filtrer et nettoyer les relations
        filiations_optimisees = self._optimiser_filiations(genealogique.get('filiations', []))
        mariages_optimises = self._optimiser_mariages(genealogique.get('mariages', []))
        parrainages_optimises = self._optimiser_parrainages(genealogique.get('parrainages', []))
        
        # 2. Normaliser les noms de personnes
        personnes_optimisees = self._optimiser_personnes(genealogique.get('personnes_extraites', []))
        
        # 3. Détecter et supprimer les doublons
        relations_dedupliquees = self._supprimer_doublons_relations(
            filiations_optimisees, mariages_optimises, parrainages_optimises
        )
        
        # 4. Recalculer la validation
        nouvelle_validation = self._recalculer_validation(
            relations_dedupliquees, personnes_optimisees
        )
        
        # 5. Construire les résultats optimisés
        resultats_optimises = resultats.copy()
        resultats_optimises['resultats_genealogiques'] = {
            'relations_count': sum(len(r) for r in relations_dedupliquees.values()),
            'filiations': relations_dedupliquees['filiations'],
            'mariages': relations_dedupliquees['mariages'],
            'parrainages': relations_dedupliquees['parrainages'],
            'personnes_extraites': personnes_optimisees,
            'validation': nouvelle_validation
        }
        
        # Mettre à jour les statistiques
        resultats_optimises['qualite_extraction'] = {
            'relations_extraites': sum(len(r) for r in relations_dedupliquees.values()),
            'qualite_donnees': nouvelle_validation['data_quality'],
            'taux_validation': nouvelle_validation['validation_rate'],
            'optimisation_appliquee': True,
            'stats_optimisation': self.stats_optimisation
        }
        
        self._afficher_resume_optimisation()
        
        return resultats_optimises
    
    def _optimiser_filiations(self, filiations: List[Dict]) -> List[Dict]:
        """Optimise les relations de filiation"""
        
        filiations_valides = []
        
        for filiation in filiations:
            enfant = filiation.get('enfant', '').strip()
            pere = filiation.get('pere', '').strip()
            mere = filiation.get('mere', '').strip()
            
            # Filtres de qualité
            if not enfant or len(enfant) < 3:
                continue
            
            # Éviter les relations impossibles
            if enfant.lower() == pere.lower() or enfant.lower() == mere.lower():
                self.stats_optimisation['faux_positifs_detectes'] += 1
                continue
            
            # Normaliser les noms
            filiation_optimisee = {
                'type': 'filiation',
                'enfant': self._normaliser_nom(enfant),
                'pere': self._normaliser_nom(pere) if pere else None,
                'mere': self._normaliser_nom(mere) if mere else None,
                'source_text': filiation.get('source_text', ''),
                'confiance': self._calculer_confiance_filiation(filiation)
            }
            
            filiations_valides.append(filiation_optimisee)
        
        self.stats_optimisation['relations_filtrees'] += len(filiations) - len(filiations_valides)
        
        return filiations_valides
    
    def _optimiser_mariages(self, mariages: List[Dict]) -> List[Dict]:
        """Optimise les relations de mariage"""
        
        mariages_valides = []
        
        for mariage in mariages:
            epouse = mariage.get('epouse', '').strip()
            epoux = mariage.get('epoux', '').strip()
            
            # Filtres de qualité
            if not epouse or not epoux or len(epouse) < 3 or len(epoux) < 3:
                continue
            
            # Éviter les auto-mariages
            if epouse.lower() == epoux.lower():
                self.stats_optimisation['faux_positifs_detectes'] += 1
                continue
            
            mariage_optimise = {
                'type': 'mariage',
                'epouse': self._normaliser_nom(epouse),
                'epoux': self._normaliser_nom(epoux),
                'statut': mariage.get('statut', 'mariée'),
                'source_text': mariage.get('source_text', ''),
                'confiance': self._calculer_confiance_mariage(mariage)
            }
            
            mariages_valides.append(mariage_optimise)
        
        self.stats_optimisation['relations_filtrees'] += len(mariages) - len(mariages_valides)
        
        return mariages_valides
    
    def _optimiser_parrainages(self, parrainages: List[Dict]) -> List[Dict]:
        """Optimise les relations de parrainage"""
        
        parrainages_valides = []
        
        for parrainage in parrainages:
            personne = parrainage.get('personne', '').strip()
            type_relation = parrainage.get('type', '')
            
            # Filtres de qualité
            if not personne or len(personne) < 3:
                continue
            
            if type_relation not in ['parrain', 'marraine']:
                continue
            
            parrainage_optimise = {
                'type': type_relation,
                'personne': self._normaliser_nom(personne),
                'source_text': parrainage.get('source_text', ''),
                'confiance': self._calculer_confiance_parrainage(parrainage)
            }
            
            parrainages_valides.append(parrainage_optimise)
        
        self.stats_optimisation['relations_filtrees'] += len(parrainages) - len(parrainages_valides)
        
        return parrainages_valides
    
    def _optimiser_personnes(self, personnes: List[Dict]) -> List[Dict]:
        """Optimise la liste des personnes extraites"""
        
        personnes_uniques = {}
        
        for personne in personnes:
            nom_original = personne.get('nom_complet', '')
            nom_normalise = self._normaliser_nom(nom_original)
            
            if len(nom_normalise) < 3:
                continue
            
            # Déduplication par nom normalisé
            if nom_normalise not in personnes_uniques:
                personnes_uniques[nom_normalise] = {
                    'nom_complet': nom_normalise,
                    'nom_original': nom_original,
                    'occurrences': personne.get('occurrences', 1),
                    'variantes': [nom_original]
                }
                self.stats_optimisation['noms_normalises'] += 1
            else:
                # Fusionner les occurrences
                personnes_uniques[nom_normalise]['occurrences'] += personne.get('occurrences', 1)
                if nom_original not in personnes_uniques[nom_normalise]['variantes']:
                    personnes_uniques[nom_normalise]['variantes'].append(nom_original)
                self.stats_optimisation['doublons_supprimes'] += 1
        
        return list(personnes_uniques.values())
    
    def _normaliser_nom(self, nom: str) -> str:
        """Normalise un nom de personne"""
        if not nom:
            return ""
        
        # Nettoyage de base
        nom_clean = re.sub(r'\s+', ' ', nom.strip())
        
        # Capitalisation appropriée
        mots = nom_clean.split()
        mots_normalises = []
        
        for mot in mots:
            if len(mot) > 1:
                # Particules restent en minuscules
                if mot.lower() in ['de', 'du', 'des', 'le', 'la', 'les', 'von', 'van', 'von']:
                    mots_normalises.append(mot.lower())
                else:
                    mots_normalises.append(mot.capitalize())
            else:
                mots_normalises.append(mot.upper())
        
        return ' '.join(mots_normalises)
    
    def _calculer_confiance_filiation(self, filiation: Dict) -> float:
        """Calcule un score de confiance pour une filiation"""
        score = 0.5  # Score de base
        
        # Bonus si père et mère présents
        if filiation.get('pere') and filiation.get('mere'):
            score += 0.3
        elif filiation.get('pere') or filiation.get('mere'):
            score += 0.2
        
        # Bonus si contexte riche
        source = filiation.get('source_text', '')
        if len(source) > 50:
            score += 0.1
        
        # Malus si noms trop courts ou suspects
        enfant = filiation.get('enfant', '')
        if len(enfant) < 5:
            score -= 0.2
        
        return max(0.1, min(1.0, score))
    
    def _calculer_confiance_mariage(self, mariage: Dict) -> float:
        """Calcule un score de confiance pour un mariage"""
        score = 0.6  # Score de base plus élevé
        
        # Bonus si statut précisé
        if mariage.get('statut') in ['mariée', 'veuve']:
            score += 0.2
        
        # Malus si noms trop similaires
        epouse = mariage.get('epouse', '').lower()
        epoux = mariage.get('epoux', '').lower()
        
        if epouse and epoux:
            # Vérifier similarité excessive
            mots_epouse = set(epouse.split())
            mots_epoux = set(epoux.split())
            similarite = len(mots_epouse.intersection(mots_epoux)) / max(len(mots_epouse), len(mots_epoux))
            
            if similarite > 0.7:
                score -= 0.3
        
        return max(0.1, min(1.0, score))
    
    def _calculer_confiance_parrainage(self, parrainage: Dict) -> float:
        """Calcule un score de confiance pour un parrainage"""
        score = 0.4  # Score de base
        
        # Bonus selon le type
        if parrainage.get('type') in ['parrain', 'marraine']:
            score += 0.3
        
        # Bonus si nom substantiel
        personne = parrainage.get('personne', '')
        if len(personne) > 10:
            score += 0.2
        
        return max(0.1, min(1.0, score))
    
    def _supprimer_doublons_relations(self, filiations: List[Dict], 
                                    mariages: List[Dict], parrainages: List[Dict]) -> Dict:
        """Supprime les doublons entre les relations"""
        
        # Créer des signatures uniques pour chaque relation
        relations_uniques = {
            'filiations': [],
            'mariages': [],
            'parrainages': []
        }
        
        # Filiations
        signatures_filiations = set()
        for filiation in filiations:
            signature = f"{filiation['enfant']}|{filiation.get('pere', '')}|{filiation.get('mere', '')}"
            if signature not in signatures_filiations:
                signatures_filiations.add(signature)
                relations_uniques['filiations'].append(filiation)
            else:
                self.stats_optimisation['doublons_supprimes'] += 1
        
        # Mariages
        signatures_mariages = set()
        for mariage in mariages:
            signature = f"{mariage['epouse']}|{mariage['epoux']}"
            signature_inverse = f"{mariage['epoux']}|{mariage['epouse']}"
            
            if signature not in signatures_mariages and signature_inverse not in signatures_mariages:
                signatures_mariages.add(signature)
                relations_uniques['mariages'].append(mariage)
            else:
                self.stats_optimisation['doublons_supprimes'] += 1
        
        # Parrainages
        signatures_parrainages = set()
        for parrainage in parrainages:
            signature = f"{parrainage['type']}|{parrainage['personne']}"
            if signature not in signatures_parrainages:
                signatures_parrainages.add(signature)
                relations_uniques['parrainages'].append(parrainage)
            else:
                self.stats_optimisation['doublons_supprimes'] += 1
        
        return relations_uniques
    
    def _recalculer_validation(self, relations: Dict, personnes: List[Dict]) -> Dict:
        """Recalcule la validation avec les données optimisées"""
        
        total_relations = sum(len(r) for r in relations.values())
        total_personnes = len(personnes)
        
        # Calculer cohérence
        personnes_dans_relations = set()
        
        for filiation in relations['filiations']:
            if filiation.get('enfant'):
                personnes_dans_relations.add(filiation['enfant'].lower())
            if filiation.get('pere'):
                personnes_dans_relations.add(filiation['pere'].lower())
            if filiation.get('mere'):
                personnes_dans_relations.add(filiation['mere'].lower())
        
        for mariage in relations['mariages']:
            if mariage.get('epouse'):
                personnes_dans_relations.add(mariage['epouse'].lower())
            if mariage.get('epoux'):
                personnes_dans_relations.add(mariage['epoux'].lower())
        
        for parrainage in relations['parrainages']:
            if parrainage.get('personne'):
                personnes_dans_relations.add(parrainage['personne'].lower())
        
        personnes_extraites = {p['nom_complet'].lower() for p in personnes}
        
        validation_rate = 0.0
        if personnes_extraites:
            validation_rate = len(personnes_dans_relations.intersection(personnes_extraites)) / len(personnes_extraites) * 100
        
        # Calculer confiance moyenne
        confidences = []
        for relations_type in relations.values():
            for relation in relations_type:
                if 'confiance' in relation:
                    confidences.append(relation['confiance'])
        
        confiance_moyenne = sum(confidences) / len(confidences) if confidences else 0.5
        
        # Ajuster le score de qualité
        if validation_rate > 80 and confiance_moyenne > 0.7:
            quality = "Excellente"
        elif validation_rate > 60 and confiance_moyenne > 0.6:
            quality = "Bonne"
        elif validation_rate > 40 and confiance_moyenne > 0.5:
            quality = "Moyenne"
        else:
            quality = "Faible"
        
        return {
            'validation_rate': round(validation_rate, 1),
            'data_quality': quality,
            'total_persons': total_personnes,
            'total_relations': total_relations,
            'coherence_score': round(validation_rate / 100, 2),
            'confidence_moyenne': round(confiance_moyenne, 2)
        }
    
    def _afficher_resume_optimisation(self):
        """Affiche un résumé de l'optimisation"""
        print("\nRésumé de l'optimisation:")
        print("-" * 30)
        for key, value in self.stats_optimisation.items():
            print(f"{key.replace('_', ' ').title()}: {value}")

def optimiser_resultats_smart_analyzer(fichier_resultats: str = None, 
                                     resultats_dict: Dict = None) -> Dict:
    """
    Fonction principale d'optimisation
    
    Args:
        fichier_resultats: Chemin vers un fichier JSON de résultats
        resultats_dict: Dictionnaire de résultats directement
        
    Returns:
        Dict: Résultats optimisés
    """
    
    if fichier_resultats:
        with open(fichier_resultats, 'r', encoding='utf-8') as f:
            resultats = json.load(f)
    elif resultats_dict:
        resultats = resultats_dict
    else:
        raise ValueError("Fournissez soit un fichier soit un dictionnaire de résultats")
    
    optimisateur = OptimisateurQualiteDonnees()
    resultats_optimises = optimisateur.optimiser_resultats(resultats)
    
    return resultats_optimises

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        fichier = sys.argv[1]
        resultats_optimises = optimiser_resultats_smart_analyzer(fichier_resultats=fichier)
        
        # Sauvegarder les résultats optimisés
        fichier_optimise = fichier.replace('.json', '_optimise.json')
        with open(fichier_optimise, 'w', encoding='utf-8') as f:
            json.dump(resultats_optimises, f, indent=2, ensure_ascii=False)
        
        print(f"\nRésultats optimisés sauvegardés: {fichier_optimise}")
    else:
        print("Usage: python optimisation_qualite_donnees.py resultats.json")