import re
from typing import Dict, Pattern
from functools import lru_cache

class PatternCompiler:
    def __init__(self):
        self.name_pattern = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][a-zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-]{1,25}'
        self.full_name_pattern = rf'{self.name_pattern}(?:\s+{self.name_pattern})*'
        self.tolerant_name_pattern = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß\d][a-zA-Zàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\'\-\.\s]{1,40}'
        
        self.month_names = 'janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre|janv|fév|sept|oct|nov|déc'
        self.republican_months = 'vendémiaire|brumaire|frimaire|nivôse|pluviôse|ventôse|germinal|floréal|prairial|messidor|thermidor|fructidor'
        
        self.particles = 'de|du|des|le|la|les|d\'|von|van'
        self.titles = 'sieur|sr|seigneur|sgr|écuyer|éc|noble|damoiselle|dame'
        
        self.relation_words = {
            'filiation': 'fils|fille|filz',
            'marriage': 'épouse|femme|veuve|mari|époux',
            'godparent': 'parrain|marraine|parr|marr'
        }
        
        self.compiled_patterns = self._compile_all_patterns()
    
    def _compile_all_patterns(self) -> Dict[str, Pattern]:
        patterns = {}
        
        patterns['name_basic'] = re.compile(rf'\b({self.name_pattern})\b')
        patterns['name_full'] = re.compile(rf'\b({self.full_name_pattern})\b')
        patterns['name_tolerant'] = re.compile(rf'({self.tolerant_name_pattern})')
        
        patterns['name_with_title'] = re.compile(
            rf'\b(?:{self.titles})\s+(?:de\s+)?({self.full_name_pattern})\b', re.IGNORECASE
        )
        
        patterns['name_with_particle'] = re.compile(
            rf'\b({self.name_pattern}(?:\s+(?:{self.particles})\s+{self.name_pattern})*)\b', re.IGNORECASE
        )
        
        patterns['compound_name'] = re.compile(
            rf'\b({self.name_pattern}(?:\-{self.name_pattern})*)\b'
        )
        
        patterns['filiation_strict'] = re.compile(
            rf'({self.full_name_pattern}),?\s*(?:{self.relation_words["filiation"]})\s+de\s+({self.full_name_pattern})(?:\s+et\s+(?:de\s+)?({self.full_name_pattern}))?',
            re.IGNORECASE
        )
        
        patterns['filiation_tolerant'] = re.compile(
            rf'({self.tolerant_name_pattern})\s*[,\.;:]?\s*(?:{self.relation_words["filiation"]})\s+de\s+({self.tolerant_name_pattern})(?:\s+et\s+(?:de\s+)?({self.tolerant_name_pattern}))?',
            re.IGNORECASE
        )
        
        patterns['marriage_basic'] = re.compile(
            rf'({self.full_name_pattern}),?\s*(?:{self.relation_words["marriage"]})\s+de\s+({self.full_name_pattern})',
            re.IGNORECASE
        )
        
        patterns['marriage_tolerant'] = re.compile(
            rf'({self.tolerant_name_pattern})\s*[,\.;:]?\s*(?:{self.relation_words["marriage"]})\s+de\s+({self.tolerant_name_pattern})',
            re.IGNORECASE
        )
        
        patterns['godparent_basic'] = re.compile(
            rf'(?:{self.relation_words["godparent"]})\s*:?\s*({self.full_name_pattern})',
            re.IGNORECASE
        )
        
        patterns['godparent_tolerant'] = re.compile(
            rf'(?:{self.relation_words["godparent"]})\s*[\.:]?\s*({self.tolerant_name_pattern})',
            re.IGNORECASE
        )
        
        patterns['date_standard'] = re.compile(
            rf'(\d{{1,2}})\s+({self.month_names})\s+(\d{{4}})', re.IGNORECASE
        )
        
        patterns['date_year_first'] = re.compile(
            rf'(\d{{4}}),?\s+(\d{{1,2}})\s+({self.month_names})', re.IGNORECASE
        )
        
        patterns['date_republican'] = re.compile(
            rf'(\d{{1,2}})\s+({self.republican_months})\s+(?:de\s+)?l\'an\s+([IVX]+)', re.IGNORECASE
        )
        
        patterns['date_year_only'] = re.compile(r'\b(1[5-8]\d{2})\b')
        
        patterns['profession'] = re.compile(
            r'\b(curé|prestre|prêtre|avocat|conseiller|trésorier|notaire|marchand|laboureur|chirurgien|maître|procureur)\b',
            re.IGNORECASE
        )
        
        patterns['title_land'] = re.compile(
            rf'\b(?:{self.titles})\s+de\s+({self.name_pattern}(?:\s+{self.name_pattern})*)\b',
            re.IGNORECASE
        )
        
        patterns['royal_office'] = re.compile(
            r'\b(conseiller|trésorier|avocat)\s+du\s+roi\b', re.IGNORECASE
        )
        
        patterns['cleanup_spaces'] = re.compile(r'\s+')
        patterns['cleanup_punctuation'] = re.compile(r'[,;\.]{2,}')
        patterns['cleanup_dashes'] = re.compile(r'(\w)\s*-\s*(\w)')
        
        return patterns
    
    @lru_cache(maxsize=100)
    def get_pattern(self, pattern_name: str) -> Pattern:
        return self.compiled_patterns.get(pattern_name)
    
    def get_all_patterns(self) -> Dict[str, Pattern]:
        return self.compiled_patterns.copy()
    
    def add_custom_pattern(self, name: str, pattern: str, flags: int = 0):
        self.compiled_patterns[name] = re.compile(pattern, flags)

pattern_compiler = PatternCompiler()