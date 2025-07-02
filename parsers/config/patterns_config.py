from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class PatternsConfig:
    name_patterns: Dict[str, str]
    date_patterns: Dict[str, str]
    relationship_patterns: Dict[str, str]
    profession_patterns: Dict[str, str]
    cleanup_patterns: Dict[str, str]
    
    @classmethod
    def get_default_config(cls) -> 'PatternsConfig':
        return cls(
            name_patterns={
                'basic_name': r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-]{1,25}',
                'full_name': r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-]{1,25}(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-]{1,25})*',
                'compound_name': r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-]+(?:\-[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-]+)*',
                'particles': r'de|du|des|le|la|les|d\'|von|van',
                'titles': r'sieur|sr|seigneur|sgr|écuyer|éc|noble|damoiselle|dame'
            },
            
            date_patterns={
                'months_french': r'janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre|janv|fév|sept|oct|nov|déc',
                'months_republican': r'vendémiaire|brumaire|frimaire|nivôse|pluviôse|ventôse|germinal|floréal|prairial|messidor|thermidor|fructidor',
                'standard_date': r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre|janv|fév|sept|oct|nov|déc)\s+(\d{4})',
                'republican_date': r'(\d{1,2})\s+(vendémiaire|brumaire|frimaire|nivôse|pluviôse|ventôse|germinal|floréal|prairial|messidor|thermidor|fructidor)\s+(?:de\s+)?l\'an\s+([IVX]+)',
                'year_only': r'\b(1[5-8]\d{2})\b'
            },
            
            relationship_patterns={
                'filiation_words': r'fils|fille|filz',
                'marriage_words': r'épouse|femme|veuve|mari|époux',
                'godparent_words': r'parrain|marraine|parr|marr',
                'filiation_basic': r'({full_name}),?\s*(?:fils|fille|filz)\s+de\s+({full_name})(?:\s+et\s+(?:de\s+)?({full_name}))?',
                'marriage_basic': r'({full_name}),?\s*(?:épouse|femme|veuve|mari|époux)\s+(?:de\s+)?({full_name})',
                'godparent_basic': r'(?:parrain|marraine|parr|marr)\s*:?\s*({full_name})'
            },
            
            profession_patterns={
                'clerical': r'curé|prestre|prêtre|vicaire|chapelain',
                'legal': r'avocat|notaire|procureur|greffier|huissier',
                'royal_office': r'conseiller|trésorier|avocat|procureur|greffier',
                'craftsman': r'maître|maistre|charpentier|maçon|tailleur|cordonnier|boulanger',
                'merchant': r'marchand|marchant|négociant',
                'agricultural': r'laboureur|fermier|métayer'
            },
            
            cleanup_patterns={
                'multiple_spaces': r'\s+',
                'multiple_punctuation': r'[,;\.]{2,}',
                'dash_spacing': r'(\w)\s*-\s*(\w)',
                'period_spacing': r'(\w)\s*\.\s*(\w)',
                'normalize_quotes': r'[""„"‚'']',
                'normalize_dashes': r'[–—―]'
            }
        )
    
    @classmethod
    def get_strict_config(cls) -> 'PatternsConfig':
        default = cls.get_default_config()
        
        default.name_patterns['strict_name'] = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]{2,}'
        default.name_patterns['strict_person'] = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]{2,}(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]{2,})*'
        
        default.relationship_patterns['filiation_ultra_strict'] = r'({strict_person}),?\s+(?:fils|fille)\s+de\s+({strict_name}(?:\s+et\s+(?:de\s+)?{strict_name})?)'
        
        return default
    
    @classmethod
    def get_tolerant_config(cls) -> 'PatternsConfig':
        default = cls.get_default_config()
        
        default.name_patterns['tolerant_name'] = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß\d][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-\.\s]{1,40}'
        
        default.relationship_patterns['filiation_tolerant'] = r'({tolerant_name})\s*[,\.;:]?\s*(?:fils|fille|filz)\s+de\s+({tolerant_name})(?:\s+et\s+(?:de\s+)?({tolerant_name}))?'
        default.relationship_patterns['marriage_tolerant'] = r'({tolerant_name})\s*[,\.;:]?\s*(?:épouse|femme|veuve|mari|époux)\s+(?:de\s+)?({tolerant_name})'
        default.relationship_patterns['godparent_tolerant'] = r'(?:parrain|marraine|parr|marr)\s*[\.:]?\s*({tolerant_name})'
        
        return default
    
    def get_compiled_patterns(self) -> Dict[str, Any]:
        import re
        compiled = {}
        
        for category, patterns in [
            ('name', self.name_patterns),
            ('date', self.date_patterns),
            ('relationship', self.relationship_patterns),
            ('profession', self.profession_patterns),
            ('cleanup', self.cleanup_patterns)
        ]:
            compiled[category] = {}
            for name, pattern in patterns.items():
                try:
                    compiled[category][name] = re.compile(pattern, re.IGNORECASE)
                except re.error as e:
                    print(f"Erreur compilation pattern {category}.{name}: {e}")
        
        return compiled
    
    def expand_pattern_variables(self) -> 'PatternsConfig':
        """Expand pattern variables like {full_name} in other patterns"""
        expanded = PatternsConfig(
            name_patterns=self.name_patterns.copy(),
            date_patterns=self.date_patterns.copy(),
            relationship_patterns={},
            profession_patterns=self.profession_patterns.copy(),
            cleanup_patterns=self.cleanup_patterns.copy()
        )
        
        all_patterns = {**self.name_patterns, **self.date_patterns}
        
        for name, pattern in self.relationship_patterns.items():
            expanded_pattern = pattern
            for var_name, var_pattern in all_patterns.items():
                expanded_pattern = expanded_pattern.replace(f'{{{var_name}}}', var_pattern)
            expanded.relationship_patterns[name] = expanded_pattern
        
        return expanded

patterns_config = PatternsConfig.get_default_config()
strict_patterns_config = PatternsConfig.get_strict_config()
tolerant_patterns_config = PatternsConfig.get_tolerant_config()