import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from core.models import Person, ActeParoissial, ActeType
from database.person_manager import PersonManager
from database.acte_manager import ActeManager
from config.settings import ParserConfig

class ReportGenerator:
    """Générateur de rapports optimisé"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
    
    def generate_final_report(self, person_manager: PersonManager, 
                            acte_manager: ActeManager, 
                            lieu: str = "Notre-Dame d'Esméville") -> Dict:
        """Génère le rapport final selon les spécifications exactes"""
        
        # Analyse des actes
        actes_analysis = self._analyze_actes(acte_manager)
        
        # Analyse des personnes
        persons_analysis = self._analyze_persons(person_manager)
        
        # Analyse des filiations
        filiations_analysis = self._analyze_filiations(person_manager, acte_manager)
        
        # Analyse des parrainages
        parrainages_analysis = self._analyze_parrainages(acte_manager, person_manager)
        
        return {
            'lieu': lieu,
            'actes': actes_analysis,
            'personnes': persons_analysis,
            'filiations': filiations_analysis,
            'parrainages': parrainages_analysis,
            'statistiques': self._generate_statistics(person_manager, acte_manager),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'parser_version': '2.0.0',
                'total_corrections': self._count_corrections(person_manager)
            }
        }
    
    def _analyze_actes(self, acte_manager: ActeManager) -> Dict:
        """Analyse des actes par type et chronologie"""
        stats = acte_manager.get_statistics()
        
        # Compter par type selon spécifications
        baptemes = stats['by_type'].get('baptême', 0)
        mariages = stats['by_type'].get('mariage', 0)
        inhumations = stats['by_type'].get('inhumation', 0)
        actes_ventes = stats['by_type'].get('acte_vente', 0)
        prises_possession = stats['by_type'].get('prise_possession', 0)
        
        # Période couverte
        year_range = stats['year_range']
        periode = f"{year_range[0]}-{year_range[1]}" if year_range[0] else "inconnue"
        
        return {
            'periode': periode,
            'baptemes': baptemes,
            'mariages': mariages,
            'inhumations': inhumations,
            'actes_ventes': actes_ventes,
            'prises_possession': prises_possession,
            'chronologie': self._extract_chronology(acte_manager)
        }
    
    def _analyze_persons(self, person_manager: PersonManager) -> List[Dict]:
        """Analyse détaillée de chaque personne"""
        persons_data = []
        
        for i, person in enumerate(person_manager.persons.values(), 1):
            # Formatage des dates selon spécifications
            dates = self._format_person_dates(person)
            
            # Professions
            professions = ", ".join(person.profession) if person.profession else "aucune profession"
            
            # Titres (statut + terres)
            titres = self._format_person_titles(person)
            
            # Notabilité contextuelle
            notabilite = self._determine_notability(person)
            
            persons_data.append({
                'numero': i,
                'nom_complet': person.full_name,
                'dates': dates,
                'professions': professions,
                'titres': titres,
                'notabilite': notabilite,
                'id': person.id,
                'homonyme': self._is_homonym(person, person_manager),
                'corrections': getattr(person, 'corrections_applied', [])
            })
        
        return persons_data
    
    def _analyze_filiations(self, person_manager: PersonManager, 
                          acte_manager: ActeManager) -> List[Dict]:
        """Analyse des relations de filiation et mariage"""
        filiations = []
        couples_found = set()
        
        # Parcourir les actes pour identifier les couples
        for acte in acte_manager.actes.values():
            if acte.pere_id and acte.mere_id:
                couple_key = tuple(sorted([acte.pere_id, acte.mere_id]))
                
                if couple_key not in couples_found:
                    couples_found.add(couple_key)
                    
                    pere = person_manager.persons.get(acte.pere_id)
                    mere = person_manager.persons.get(acte.mere_id)
                    
                    if pere and mere:
                        # Déduction de la date de mariage
                        marriage_date = self._infer_marriage_date(couple_key, acte_manager)
                        
                        filiations.append({
                            'numero': len(filiations) + 1,
                            'epoux': self._format_person_title_inline(pere),
                            'epouse': mere.full_name,
                            'date_mariage': marriage_date,
                            'enfants': self._get_children_names(couple_key, acte_manager, person_manager)
                        })
        
        # Ajouter les mariages explicites sans enfants connus
        self._add_explicit_marriages(filiations, person_manager, couples_found)
        
        return filiations
    
    def _analyze_parrainages(self, acte_manager: ActeManager, 
                           person_manager: PersonManager) -> List[Dict]:
        """Analyse des relations de parrainage"""
        parrainages = []
        
        for acte in acte_manager.actes.values():
            if acte.type_acte == ActeType.BAPTEME and (acte.parrain_id or acte.marraine_id):
                filleul = person_manager.persons.get(acte.personne_principale_id)
                parrain = person_manager.persons.get(acte.parrain_id) if acte.parrain_id else None
                marraine = person_manager.persons.get(acte.marraine_id) if acte.marraine_id else None
                
                if filleul:
                    parrainage_info = {
                        'numero': len(parrainages) + 1,
                        'filleul': filleul.full_name,
                        'date': acte.year or acte.date,
                        'parrain': self._format_person_title_inline(parrain) if parrain else None,
                        'marraine': marraine.full_name if marraine else None
                    }
                    parrainages.append(parrainage_info)
        
        return parrainages
    
    def _format_person_dates(self, person: Person) -> str:
        """Formate les dates selon les spécifications"""
        if person.date_naissance and person.date_deces:
            return f"(*{person.date_naissance}-†{person.date_deces})"
        elif person.date_naissance:
            return f"(*{person.date_naissance}-décès inconnu)"
        elif person.date_deces:
            return f"(naissance-†{person.date_deces})"
        else:
            return "(naissance-décès inconnus)"
    
    def _format_person_titles(self, person: Person) -> str:
        """Formate les titres (statut + terres)"""
        titres = []
        
        if person.statut:
            titres.append(person.statut.value)
        
        if person.terres:
            titres.extend([f"sr de {terre}" for terre in person.terres])
        
        return ", ".join(titres) if titres else "aucun titre"
    
    def _format_person_title_inline(self, person: Person) -> str:
        """Formate le nom avec titre pour les filiations"""
        if not person:
            return ""
        
        base_name = person.full_name
        
        if person.statut and person.terres:
            return f"**{base_name}** ({person.statut.value} sr de {', '.join(person.terres)})"
        elif person.statut:
            return f"**{base_name}** ({person.statut.value})"
        elif person.terres:
            return f"**{base_name}** (sr de {', '.join(person.terres)})"
        else:
            return f"**{base_name}**"
    
    def _determine_notability(self, person: Person) -> str:
        """Détermine la notabilité contextuelle d'une personne"""
        notabilite_items = []
        
        # Notabilité directe
        if person.notable:
            if person.date_deces:
                notabilite_items.append("inhumé dans l'église")
            else:
                notabilite_items.append("notable")
        
        # Notabilité professionnelle
        if 'prêtre' in person.profession:
            notabilite_items.append("prise de possession du bénéfice")
        elif 'curé' in person.profession:
            notabilite_items.append("ministre du culte")
        elif any(prof in ['avocat du Roi', 'conseiller'] for prof in person.profession):
            notabilite_items.append("fonction royale")
        
        # Notabilité familiale (à déterminer via les actes)
        # Cette logique nécessiterait l'accès aux actes...
        
        return ", ".join(notabilite_items) if notabilite_items else "aucune notabilité particulière"
    
    def _is_homonym(self, person: Person, person_manager: PersonManager) -> bool:
        """Vérifie si la personne est un homonyme"""
        homonym_groups = person_manager.get_homonym_groups()
        return person.full_name in homonym_groups
    
    def _infer_marriage_date(self, couple_key: Tuple[int, int], 
                           acte_manager: ActeManager) -> str:
        """Infère la date de mariage basée sur le premier enfant"""
        children_dates = []
        
        for acte in acte_manager.actes.values():
            if (acte.pere_id in couple_key and acte.mere_id in couple_key and 
                acte.type_acte == ActeType.BAPTEME and acte.year):
                children_dates.append(acte.year)
        
        if children_dates:
            earliest_child = min(children_dates)
            return f"*(mariage antérieur à {earliest_child})*"
        
        return "*(date inconnue)*"
    
    def _get_children_names(self, couple_key: Tuple[int, int], 
                          acte_manager: ActeManager, 
                          person_manager: PersonManager) -> List[str]:
        """Récupère les noms des enfants d'un couple"""
        children = []
        
        for acte in acte_manager.actes.values():
            if (acte.pere_id in couple_key and acte.mere_id in couple_key and 
                acte.personne_principale_id):
                child = person_manager.persons.get(acte.personne_principale_id)
                if child:
                    children.append(child.full_name)
        
        return children
    
    def _add_explicit_marriages(self, filiations: List[Dict], 
                              person_manager: PersonManager, 
                              couples_found: set):
        """Ajoute les mariages explicites sans enfants"""
        # Cette logique nécessiterait une analyse des actes de mariage
        # ou des relations "épouse de" dans les textes
        pass
    
    def _extract_chronology(self, acte_manager: ActeManager) -> List[str]:
        """Extrait la chronologie des événements"""
        chronology = []
        
        # Grouper par année
        year_events = defaultdict(list)
        
        for acte in acte_manager.actes.values():
            if acte.year:
                event_desc = self._format_acte_chronology(acte)
                if event_desc:
                    year_events[acte.year].append(event_desc)
        
        # Formater la chronologie
        for year in sorted(year_events.keys()):
            events = year_events[year]
            chronology.append(f"- {year} : {' + '.join(events)}")
        
        return chronology
    
    def _format_acte_chronology(self, acte: ActeParoissial) -> Optional[str]:
        """Formate un acte pour la chronologie"""
        if acte.type_acte == ActeType.PRISE_POSSESSION:
            return "Prise de possession du bénéfice"
        elif acte.type_acte == ActeType.INHUMATION:
            return f"Inhumation"
        elif acte.type_acte == ActeType.BAPTEME:
            return "Naissance et baptême"
        elif acte.type_acte == ActeType.MARIAGE:
            return "Mariage"
        
        return None
    
    def _generate_statistics(self, person_manager: PersonManager, 
                           acte_manager: ActeManager) -> Dict:
        """Génère les statistiques globales"""
        person_stats = person_manager.get_statistics()
        acte_stats = acte_manager.get_statistics()
        
        return {
            'personnes': person_stats,
            'actes': acte_stats,
            'qualite_donnees': {
                'taux_validation': acte_stats.get('validation_rate', 0),
                'erreurs_chronologiques': acte_stats.get('chronology_errors', 0),
                'homonymes_detectes': person_stats.get('homonym_groups', 0)
            }
        }
    
    def _count_corrections(self, person_manager: PersonManager) -> int:
        """Compte le nombre total de corrections appliquées"""
        total_corrections = 0
        
        for person in person_manager.persons.values():
            corrections = getattr(person, 'corrections_applied', [])
            total_corrections += len(corrections)
        
        return total_corrections
    
    @staticmethod
    def print_formatted_results(report: Dict):
        """Affiche les résultats selon le format spécifié"""
        # Format exact selon les spécifications utilisateur
        actes = report['actes']
        personnes = report['personnes']
        filiations = report['filiations']
        parrainages = report['parrainages']
        
        print("=== ACTES IDENTIFIÉS ===")
        print(f"{report['lieu']}, {actes['periode']}, "
              f"{actes['baptemes']} baptême{'s' if actes['baptemes'] > 1 else ''}, "
              f"{actes['mariages']} mariage{'s' if actes['mariages'] != 1 else ''}, "
              f"{actes['inhumations']} inhumation{'s' if actes['inhumations'] > 1 else ''}, "
              f"{actes['actes_ventes']} acte{'s' if actes['actes_ventes'] != 1 else ''} de vente{'s' if actes['actes_ventes'] > 1 else ''}"
              + (f", {actes['prises_possession']} prise de possession" if actes['prises_possession'] > 0 else ""))
        
        if actes.get('chronologie'):
            print("\n*Détail chronologique :*")
            for event in actes['chronologie']:
                print(event)
        
        print("\n=== PERSONNES IDENTIFIÉES ===")
        for person in personnes:
            print(f"{person['numero']}. **{person['nom_complet']}** {person['dates']}, "
                  f"{person['professions']}, {person['titres']}, "
                  f"notabilité : {person['notabilite']}")
        
        print("\n=== FILIATIONS ===")
        for filiation in filiations:
            print(f"{filiation['numero']}. {filiation['epoux']} **X** **{filiation['epouse']}** {filiation['date_mariage']}")
        
        print("\n=== PARRAINAGES ===")
        for parrainage in parrainages:
            parrain_str = parrainage['parrain'] if parrainage['parrain'] else "N/A"
            marraine_str = parrainage['marraine'] if parrainage['marraine'] else "N/A"
            print(f"{parrainage['numero']}. **{parrainage['filleul']}** ({parrainage['date']}) : "
                  f"parrain {parrain_str}, marraine {marraine_str}")