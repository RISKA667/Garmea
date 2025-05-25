import logging
from collections import defaultdict
from datetime import datetime
from core.models import ActeParoissial, ActeType, ValidationResult
from config.settings import ParserConfig
from parsers.date_parser import DateParser

class ActeManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.actes = {}
        self.acte_id_counter = 1
        self._year_index = defaultdict(list)
        self._type_index = defaultdict(list)
        self._person_index = defaultdict(list)
        self.date_parser = DateParser(config)
        self.stats = {'actes_created': 0, 'actes_validated': 0, 'chronology_errors': 0}
    
    def create_acte(self, acte_data):
        acte_type = ActeType.BAPTEME
        if acte_data.get('type_acte'):
            try:
                acte_type = ActeType(acte_data['type_acte'])
            except ValueError:
                self.logger.warning(f"Type d'acte inconnu: {acte_data['type_acte']}")
        date_str = acte_data.get('date', '')
        parsed_dates = self.date_parser.extract_all_dates(date_str) if date_str else []
        parsed_date = parsed_dates[0].parsed_date if parsed_dates else None
        acte = ActeParoissial(id=self.acte_id_counter, type_acte=acte_type, date=date_str, date_parsed=parsed_date, lieu=acte_data.get('lieu', ''), personne_principale_id=acte_data.get('personne_principale_id'), pere_id=acte_data.get('pere_id'), mere_id=acte_data.get('mere_id'), conjoint_id=acte_data.get('conjoint_id'), parrain_id=acte_data.get('parrain_id'), marraine_id=acte_data.get('marraine_id'), temoin_ids=acte_data.get('temoin_ids', []), texte_original=acte_data.get('texte_original', ''), notable=acte_data.get('notable', False))
        self.actes[self.acte_id_counter] = acte
        self._add_to_indexes(acte)
        self.acte_id_counter += 1
        self.stats['actes_created'] += 1
        return acte
    
    def _add_to_indexes(self, acte):
        if acte.year:
            self._year_index[acte.year].append(acte.id)
        self._type_index[acte.type_acte].append(acte.id)
        person_ids = [acte.personne_principale_id, acte.pere_id, acte.mere_id, acte.conjoint_id, acte.parrain_id, acte.marraine_id]
        person_ids.extend(acte.temoin_ids)
        for person_id in person_ids:
            if person_id:
                self._person_index[person_id].append(acte.id)
    
    def validate_acte(self, acte, person_manager):
        errors = []
        warnings = []
        confidence = 1.0
        if not acte.date:
            warnings.append("Acte sans date")
            confidence -= 0.1
        elif not acte.year:
            warnings.append("Date sans année identifiable")
            confidence -= 0.2
        if acte.year:
            person_ids = [acte.personne_principale_id, acte.pere_id, acte.mere_id]
            for person_id in person_ids:
                if person_id:
                    person = person_manager.persons.get(person_id)
                    if person and person.date_deces:
                        death_year = self.date_parser.get_year_from_text(person.date_deces)
                        if death_year and acte.year > death_year:
                            errors.append(f"Personne {person.full_name} présente dans acte {acte.year} après décès {death_year}")
                            confidence -= 0.4
        if acte.type_acte == ActeType.BAPTEME:
            if not acte.pere_id and not acte.mere_id:
                warnings.append("Baptême sans parents identifiés")
                confidence -= 0.1
        elif acte.type_acte == ActeType.MARIAGE:
            if not acte.personne_principale_id or not acte.conjoint_id:
                errors.append("Mariage sans époux identifiés")
                confidence -= 0.3
        elif acte.type_acte == ActeType.INHUMATION:
            if not acte.personne_principale_id:
                errors.append("Inhumation sans défunt identifié")
                confidence -= 0.3
        result = ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings, confidence_score=max(0.0, confidence))
        acte.validation_result = result
        self.stats['actes_validated'] += 1
        if errors:
            self.stats['chronology_errors'] += 1
        return result
    
    def get_actes_by_year(self, year):
        acte_ids = self._year_index.get(year, [])
        return [self.actes[aid] for aid in acte_ids]
    
    def get_actes_by_type(self, acte_type):
        acte_ids = self._type_index.get(acte_type, [])
        return [self.actes[aid] for aid in acte_ids]
    
    def get_actes_by_person(self, person_id):
        acte_ids = self._person_index.get(person_id, [])
        return [self.actes[aid] for aid in acte_ids]
    
    def get_family_actes(self, person_id, person_manager):
        person = person_manager.persons.get(person_id)
        if not person:
            return {}
        family_actes = {'own_actes': self.get_actes_by_person(person_id), 'children_actes': [], 'spouse_actes': []}
        for acte in self.actes.values():
            if acte.pere_id == person_id or acte.mere_id == person_id:
                family_actes['children_actes'].append(acte)
        if person.conjoint_id:
            family_actes['spouse_actes'] = self.get_actes_by_person(person.conjoint_id)
        return family_actes
    
    def get_statistics(self):
        type_counts = {}
        for acte_type in ActeType:
            type_counts[acte_type.value] = len(self._type_index[acte_type])
        years = list(self._year_index.keys())
        year_range = (min(years), max(years)) if years else (None, None)
        return {'total_actes': len(self.actes), 'actes_created': self.stats['actes_created'], 'actes_validated': self.stats['actes_validated'], 'chronology_errors': self.stats['chronology_errors'], 'by_type': type_counts, 'year_range': year_range, 'years_covered': len(years), 'validation_rate': (self.stats['actes_validated'] / max(1, self.stats['actes_created'])) * 100}