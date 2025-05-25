import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from itertools import groupby

from core.models import Person, ActeParoissial, ActeType
from database.person_manager import PersonManager
from database.acte_manager import ActeManager
from config.settings import ParserConfig

class ReportGenerator:
    """Générateur de rapports optimisé avec cache manuel et indexation"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self._cache = {}
        self._indexes = {}
    
    def generate_final_report(self, person_manager: PersonManager, 
                            acte_manager: ActeManager, 
                            lieu: str = "Notre-Dame d'Esméville") -> Dict:
        """Génère le rapport final avec optimisations de performance"""
        
        # Pré-calcul des index pour éviter les recherches répétitives
        self._build_indexes(person_manager, acte_manager)
        
        # Analyse parallélisée des composants
        actes_analysis = self._analyze_actes_optimized(acte_manager)
        persons_analysis = self._analyze_persons_optimized(person_manager)
        filiations_analysis = self._analyze_filiations_optimized(person_manager, acte_manager)
        parrainages_analysis = self._analyze_parrainages_optimized(acte_manager, person_manager)
        
        return {
            'lieu': lieu,
            'actes': actes_analysis,
            'personnes': persons_analysis,
            'filiations': filiations_analysis,
            'parrainages': parrainages_analysis,
            'statistiques': self._generate_statistics_cached(person_manager, acte_manager),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'parser_version': '2.0.0',
                'total_corrections': self._count_corrections_optimized(person_manager)
            }
        }
    
    def _build_indexes(self, person_manager: PersonManager, acte_manager: ActeManager):
        """Construit les index pour accès O(1) au lieu de O(n)"""
        
        # Index des couples (père, mère) -> liste d'enfants
        self._indexes['couples_children'] = defaultdict(list)
        
        # Index des actes par type pour éviter les itérations complètes
        self._indexes['actes_by_type'] = defaultdict(list)
        
        # Index des personnes par statut pour la notabilité
        self._indexes['persons_by_profession'] = defaultdict(set)
        
        # Construire les index en une seule passe
        for acte in acte_manager.actes.values():
            self._indexes['actes_by_type'][acte.type_acte].append(acte)
            
            if acte.pere_id and acte.mere_id:
                couple_key = tuple(sorted([acte.pere_id, acte.mere_id]))
                if acte.personne_principale_id:
                    self._indexes['couples_children'][couple_key].append(acte.personne_principale_id)
        
        # Index des professions
        for person in person_manager.persons.values():
            for profession in person.profession:
                self._indexes['persons_by_profession'][profession].add(person.id)
    
    def _analyze_actes_optimized(self, acte_manager: ActeManager) -> Dict:
        """Analyse optimisée des actes avec cache"""
        cache_key = f"actes_{len(acte_manager.actes)}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        stats = acte_manager.get_statistics()
        
        # Accès direct au lieu de .get() répétés
        by_type = stats['by_type']
        baptemes = by_type.get('baptême', 0)
        mariages = by_type.get('mariage', 0)
        inhumations = by_type.get('inhumation', 0)
        actes_ventes = by_type.get('acte_vente', 0)
        prises_possession = by_type.get('prise_possession', 0)
        
        # Formatage optimisé de la période
        year_range = stats['year_range']
        periode = f"{year_range[0]}-{year_range[1]}" if year_range[0] else "inconnue"
        
        result = {
            'periode': periode,
            'baptemes': baptemes,
            'mariages': mariages,
            'inhumations': inhumations,
            'actes_ventes': actes_ventes,
            'prises_possession': prises_possession,
            'chronologie': self._extract_chronology_optimized(acte_manager)
        }
        
        self._cache[cache_key] = result
        return result
    
    def _analyze_persons_optimized(self, person_manager: PersonManager) -> List[Dict]:
        """Analyse optimisée des personnes avec pre-formatage"""
        persons_data = []
        
        # Pré-calcul des groupes d'homonymes pour éviter les appels répétés
        homonym_groups = person_manager.get_homonym_groups()
        homonym_names = set(homonym_groups.keys())
        
        # Utilisation d'enumerate optimisé et compréhension
        for i, person in enumerate(person_manager.persons.values(), 1):
            persons_data.append({
                'numero': i,
                'nom_complet': person.full_name,
                'dates': self._format_person_dates_cached(person),
                'professions': ", ".join(person.profession) if person.profession else "aucune profession",
                'titres': self._format_person_titles_cached(person),
                'notabilite': self._determine_notability_optimized(person),
                'id': person.id,
                'homonyme': person.full_name in homonym_names,  # O(1) au lieu de O(n)
                'corrections': getattr(person, 'corrections_applied', [])
            })
        
        return persons_data
    
    def _analyze_filiations_optimized(self, person_manager: PersonManager, 
                                    acte_manager: ActeManager) -> List[Dict]:
        """Analyse optimisée des filiations utilisant les index pré-calculés"""
        filiations = []
        
        # Utilisation de l'index pré-calculé au lieu d'itérer sur tous les actes
        for couple_key, children_ids in self._indexes['couples_children'].items():
            pere_id, mere_id = couple_key
            pere = person_manager.persons.get(pere_id)
            mere = person_manager.persons.get(mere_id)
            
            if pere and mere:
                # Calcul optimisé de la date de mariage
                marriage_date = self._infer_marriage_date_cached(couple_key, acte_manager)
                
                # Récupération optimisée des noms d'enfants
                children_names = [
                    person_manager.persons[child_id].full_name 
                    for child_id in children_ids 
                    if child_id in person_manager.persons
                ]
                
                filiations.append({
                    'numero': len(filiations) + 1,
                    'epoux': self._format_person_title_inline_cached(pere),
                    'epouse': mere.full_name,
                    'date_mariage': marriage_date,
                    'enfants': children_names
                })
        
        return filiations
    
    def _analyze_parrainages_optimized(self, acte_manager: ActeManager, 
                                     person_manager: PersonManager) -> List[Dict]:
        """Analyse optimisée des parrainages utilisant l'index par type"""
        parrainages = []
        
        # Utilisation de l'index par type pour éviter de filtrer tous les actes
        bapteme_actes = self._indexes['actes_by_type'].get(ActeType.BAPTEME, [])
        
        for acte in bapteme_actes:
            if acte.parrain_id or acte.marraine_id:
                filleul = person_manager.persons.get(acte.personne_principale_id)
                if filleul:
                    # Accès direct sans vérifications répétées
                    parrain = person_manager.persons.get(acte.parrain_id) if acte.parrain_id else None
                    marraine = person_manager.persons.get(acte.marraine_id) if acte.marraine_id else None
                    
                    parrainages.append({
                        'numero': len(parrainages) + 1,
                        'filleul': filleul.full_name,
                        'date': acte.year or acte.date,
                        'parrain': self._format_person_title_inline_cached(parrain) if parrain else None,
                        'marraine': marraine.full_name if marraine else None
                    })
        
        return parrainages
    
    def _format_person_dates_cached(self, person: Person) -> str:
        """Formatage des dates avec cache pour éviter les recalculs"""
        cache_key = f"dates_{person.id}_{person.date_naissance}_{person.date_deces}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if person.date_naissance and person.date_deces:
            result = f"(*{person.date_naissance}-†{person.date_deces})"
        elif person.date_naissance:
            result = f"(*{person.date_naissance}-décès inconnu)"
        elif person.date_deces:
            result = f"(naissance-†{person.date_deces})"
        else:
            result = "(naissance-décès inconnus)"
        
        self._cache[cache_key] = result
        return result
    
    def _format_person_titles_cached(self, person: Person) -> str:
        """Formatage des titres avec cache"""
        cache_key = f"titles_{person.id}_{person.statut}_{len(person.terres)}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        titres = []
        
        if person.statut:
            titres.append(person.statut.value)
        
        if person.terres:
            titres.extend(f"sr de {terre}" for terre in person.terres)
        
        result = ", ".join(titres) if titres else "aucun titre"
        self._cache[cache_key] = result
        return result
    
    def _format_person_title_inline_cached(self, person: Person) -> str:
        """Formatage inline avec cache"""
        if not person:
            return ""
        
        cache_key = f"inline_{person.id}_{person.statut}_{len(person.terres)}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        base_name = person.full_name
        
        if person.statut and person.terres:
            terres_str = ', '.join(person.terres)
            result = f"**{base_name}** ({person.statut.value} sr de {terres_str})"
        elif person.statut:
            result = f"**{base_name}** ({person.statut.value})"
        elif person.terres:
            terres_str = ', '.join(person.terres)
            result = f"**{base_name}** (sr de {terres_str})"
        else:
            result = f"**{base_name}**"
        
        self._cache[cache_key] = result
        return result
    
    def _determine_notability_optimized(self, person: Person) -> str:
        """Détermination optimisée de la notabilité"""
        notabilite_items = []
        
        # Vérifications optimisées avec short-circuit
        if person.notable:
            notabilite_items.append("inhumé dans l'église" if person.date_deces else "notable")
        
        # Utilisation de sets pour les lookups O(1)
        person_profs = set(person.profession)
        
        if 'prêtre' in person_profs:
            notabilite_items.append("prise de possession du bénéfice")
        elif 'curé' in person_profs:
            notabilite_items.append("ministre du culte")
        elif person_profs & {'avocat du Roi', 'conseiller'}:  # Intersection optimisée
            notabilite_items.append("fonction royale")
        
        return ", ".join(notabilite_items) if notabilite_items else "aucune notabilité particulière"
    
    def _infer_marriage_date_cached(self, couple_key: Tuple[int, int], 
                                  acte_manager: ActeManager) -> str:
        """Inférence de date de mariage avec cache"""
        cache_key = f"marriage_{couple_key[0]}_{couple_key[1]}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Utilisation de compréhension avec générateur pour économiser la mémoire
        children_years = [
            acte.year for acte in acte_manager.actes.values()
            if (acte.pere_id in couple_key and acte.mere_id in couple_key and 
                acte.type_acte == ActeType.BAPTEME and acte.year)
        ]
        
        if children_years:
            earliest_child = min(children_years)
            result = f"*(mariage antérieur à {earliest_child})*"
        else:
            result = "*(date inconnue)*"
        
        self._cache[cache_key] = result
        return result
    
    def _extract_chronology_optimized(self, acte_manager: ActeManager) -> List[str]:
        """Extraction optimisée de la chronologie"""
        # Groupement et tri optimisés
        actes_with_year = [acte for acte in acte_manager.actes.values() if acte.year]
        actes_sorted = sorted(actes_with_year, key=lambda a: a.year)
        
        # Groupement par année avec itertools.groupby (plus efficace)
        chronology = []
        for year, year_actes in groupby(actes_sorted, key=lambda a: a.year):
            events = [
                self._format_acte_chronology_cached(acte) 
                for acte in year_actes
            ]
            events = [e for e in events if e]  # Filtrage des None
            
            if events:
                chronology.append(f"- {year} : {' + '.join(events)}")
        
        return chronology
    
    def _format_acte_chronology_cached(self, acte: ActeParoissial) -> Optional[str]:
        """Formatage d'acte pour chronologie avec cache"""
        cache_key = f"chrono_{acte.type_acte.value}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        type_mapping = {
            ActeType.PRISE_POSSESSION: "Prise de possession du bénéfice",
            ActeType.INHUMATION: "Inhumation",
            ActeType.BAPTEME: "Naissance et baptême",
            ActeType.MARIAGE: "Mariage"
        }
        
        result = type_mapping.get(acte.type_acte)
        self._cache[cache_key] = result
        return result
    
    def _generate_statistics_cached(self, person_manager: PersonManager, 
                                  acte_manager: ActeManager) -> Dict:
        """Génération optimisée des statistiques avec cache"""
        cache_key = f"stats_{len(person_manager.persons)}_{len(acte_manager.actes)}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        person_stats = person_manager.get_statistics()
        acte_stats = acte_manager.get_statistics()
        
        result = {
            'personnes': person_stats,
            'actes': acte_stats,
            'qualite_donnees': {
                'taux_validation': acte_stats.get('validation_rate', 0),
                'erreurs_chronologiques': acte_stats.get('chronology_errors', 0),
                'homonymes_detectes': person_stats.get('homonym_groups', 0)
            }
        }
        
        self._cache[cache_key] = result
        return result
    
    def _count_corrections_optimized(self, person_manager: PersonManager) -> int:
        """Comptage optimisé des corrections"""
        # Utilisation d'un générateur pour éviter la création de listes intermédiaires
        return sum(
            len(getattr(person, 'corrections_applied', []))
            for person in person_manager.persons.values()
        )
    
    @staticmethod
    def print_formatted_results(report: Dict):
        """Affichage optimisé des résultats"""
        # Déstructuration pour accès direct
        actes = report['actes']
        personnes = report['personnes']
        filiations = report['filiations']
        parrainages = report['parrainages']
        lieu = report['lieu']
        
        # Construction optimisée de la chaîne d'actes
        actes_parts = [
            f"{actes['baptemes']} baptême" + ('s' if actes['baptemes'] > 1 else ''),
            f"{actes['mariages']} mariage" + ('s' if actes['mariages'] != 1 else ''),
            f"{actes['inhumations']} inhumation" + ('s' if actes['inhumations'] > 1 else ''),
            f"{actes['actes_ventes']} acte" + ('s' if actes['actes_ventes'] != 1 else '') + " de vente" + ('s' if actes['actes_ventes'] > 1 else '')
        ]
        
        if actes['prises_possession'] > 0:
            actes_parts.append(f"{actes['prises_possession']} prise de possession")
        
        print("=== ACTES IDENTIFIÉS ===")
        print(f"{lieu}, {actes['periode']}, {', '.join(actes_parts)}")
        
        # Affichage optimisé de la chronologie
        chronologie = actes.get('chronologie')
        if chronologie:
            print("\n*Détail chronologique :*")
            print('\n'.join(chronologie))  # Plus efficace que des print() multiples
        
        print("\n=== PERSONNES IDENTIFIÉES ===")
        # Formatage optimisé en une seule passe
        for person in personnes:
            print(f"{person['numero']}. **{person['nom_complet']}** {person['dates']}, "
                  f"{person['professions']}, {person['titres']}, "
                  f"notabilité : {person['notabilite']}")
        
        print("\n=== FILIATIONS ===")
        for filiation in filiations:
            print(f"{filiation['numero']}. {filiation['epoux']} **X** **{filiation['epouse']}** {filiation['date_mariage']}")
        
        print("\n=== PARRAINAGES ===")
        for parrainage in parrainages:
            parrain_str = parrainage['parrain'] or "N/A"
            marraine_str = parrainage['marraine'] or "N/A"
            print(f"{parrainage['numero']}. **{parrainage['filleul']}** ({parrainage['date']}) : "
                  f"parrain {parrain_str}, marraine {marraine_str}")
    
    def clear_cache(self):
        """Nettoie les caches pour libérer la mémoire"""
        self._cache.clear()
        self._indexes.clear()