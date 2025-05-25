import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class ParserConfig:
    similarity_threshold: float = 0.85
    homonym_threshold: float = 0.95
    chronology_validation: bool = True
    gender_validation: bool = True
    ml_patterns_enabled: bool = True
    max_persons: int = 10000
    cache_size: int = 1000
    batch_size: int = 100
    abbreviations: Dict[str, str] = None
    known_places: list = None
    
    def __post_init__(self):
        if self.abbreviations is None:
            self.abbreviations = {
                'Bapt.': 'baptême', 'mar.': 'mariage', 'inh.': 'inhumation',
                'sr': 'sieur', 'sgr': 'seigneur', 'éc.': 'écuyer',
                'fév.': 'février', 'sept.': 'septembre', 'oct.': 'octobre'}
        
        if self.known_places is None:
            self.known_places = [
                'Notre-Dame d\'Esméville', 'Saint-Sylvain', 'Bréville']
    
    @classmethod
    def from_file(cls, config_path: str) -> 'ParserConfig':
        if Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return cls(**data)
        return cls()
    
    def save_to_file(self, config_path: str):
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)