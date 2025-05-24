import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class ParserConfig:
    """Configuration centralisée du parser"""
    # Seuils de similarité
    similarity_threshold: float = 0.85
    homonym_threshold: float = 0.95
    
    # Validation
    chronology_validation: bool = True
    gender_validation: bool = True
    ml_patterns_enabled: bool = True
    
    # Performance
    max_persons: int = 10000
    cache_size: int = 1000
    batch_size: int = 100
    
    # Abréviations
    abbreviations: Dict[str, str] = None
    
    # Lieux connus
    known_places: list = None
    
    def __post_init__(self):
        if self.abbreviations is None:
            self.abbreviations = {
                'Bapt.': 'baptême', 'mar.': 'mariage', 'inh.': 'inhumation',
                'sr': 'sieur', 'sgr': 'seigneur', 'éc.': 'écuyer',
                'fév.': 'février', 'sept.': 'septembre', 'oct.': 'octobre'
            }
        
        if self.known_places is None:
            self.known_places = [
                'Notre-Dame d\'Esméville', 'Saint-Sylvain', 'Bréville'
            ]
    
    @classmethod
    def from_file(cls, config_path: str) -> 'ParserConfig':
        """Charge la configuration depuis un fichier JSON"""
        if Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return cls(**data)
        return cls()
    
    def save_to_file(self, config_path: str):
        """Sauvegarde la configuration dans un fichier JSON"""
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)