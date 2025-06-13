# utils/smart_cache.py
import sqlite3
import json
import hashlib
import time
from typing import Any, Optional, Dict
from pathlib import Path
import logging

class SmartCache:
    """Cache intelligent persistant pour Garmea"""
    
    def __init__(self, cache_dir: str = "cache", ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600
        self.logger = logging.getLogger(__name__)
        
        # Base de données SQLite pour le cache
        self.db_path = self.cache_dir / "garmea_cache.db"
        self._init_db()
    
    def _init_db(self):
        """Initialise la base de données de cache"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    ttl_seconds INTEGER NOT NULL,
                    cache_type TEXT NOT NULL
                )
            """)
            
            # Index pour performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_created_at 
                ON cache_entries(created_at)
            """)
    
    def _create_key(self, category: str, identifier: str) -> str:
        """Crée une clé de cache sécurisée"""
        combined = f"{category}:{identifier}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def set(self, category: str, identifier: str, value: Any, 
            ttl_hours: Optional[int] = None) -> bool:
        """Stocke une valeur dans le cache"""
        try:
            key = self._create_key(category, identifier)
            ttl = (ttl_hours or (self.ttl_seconds // 3600)) * 3600
            
            # Sérialisation
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                serialized_value = str(value)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache_entries 
                    (key, value, created_at, ttl_seconds, cache_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (key, serialized_value, time.time(), ttl, category))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur cache set: {e}")
            return False
    
    def get(self, category: str, identifier: str, default: Any = None) -> Any:
        """Récupère une valeur du cache"""
        try:
            key = self._create_key(category, identifier)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT value, created_at, ttl_seconds, cache_type
                    FROM cache_entries 
                    WHERE key = ?
                """, (key,))
                
                row = cursor.fetchone()
                if not row:
                    return default
                
                value, created_at, ttl_seconds, cache_type = row
                
                # Vérifier expiration
                if time.time() - created_at > ttl_seconds:
                    self.delete(category, identifier)
                    return default
                
                # Désérialisation
                if category in ['relationships', 'persons', 'actes']:
                    return json.loads(value)
                else:
                    return value
                    
        except Exception as e:
            self.logger.error(f"Erreur cache get: {e}")
            return default
    
    def delete(self, category: str, identifier: str) -> bool:
        """Supprime une entrée du cache"""
        try:
            key = self._create_key(category, identifier)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur cache delete: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """Nettoie les entrées expirées"""
        try:
            current_time = time.time()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM cache_entries 
                    WHERE (created_at + ttl_seconds) < ?
                """, (current_time,))
                
                return cursor.rowcount
                
        except Exception as e:
            self.logger.error(f"Erreur cleanup cache: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Nombre total d'entrées
                total_count = conn.execute("SELECT COUNT(*) FROM cache_entries").fetchone()[0]
                
                # Par catégorie
                categories = conn.execute("""
                    SELECT cache_type, COUNT(*) 
                    FROM cache_entries 
                    GROUP BY cache_type
                """).fetchall()
                
                # Entrées expirées
                current_time = time.time()
                expired_count = conn.execute("""
                    SELECT COUNT(*) FROM cache_entries 
                    WHERE (created_at + ttl_seconds) < ?
                """, (current_time,)).fetchone()[0]
                
                return {
                    'total_entries': total_count,
                    'expired_entries': expired_count,
                    'categories': dict(categories),
                    'hit_rate': getattr(self, '_hit_rate', 0),
                    'db_size_mb': self.db_path.stat().st_size / (1024 * 1024)
                }
                
        except Exception as e:
            self.logger.error(f"Erreur stats cache: {e}")
            return {'error': str(e)}

# Décorateur pour automatiser le cache
def cached(cache: SmartCache, category: str, ttl_hours: int = 24):
    """Décorateur pour automatiser la mise en cache"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Créer un identifiant unique basé sur les arguments
            cache_id = hashlib.md5(str((args, kwargs)).encode()).hexdigest()
            
            # Essayer le cache d'abord
            cached_result = cache.get(category, cache_id)
            if cached_result is not None:
                return cached_result
            
            # Calculer le résultat
            result = func(*args, **kwargs)
            
            # Mettre en cache
            cache.set(category, cache_id, result, ttl_hours)
            
            return result
        return wrapper
    return decorator

# Usage dans votre code existant
cache = SmartCache()

# Remplacer vos caches manuels par ceci :
class RelationshipParserCached:
    def __init__(self, config):
        self.cache = SmartCache()
        # ... reste de votre code
    
    @cached(cache, 'relationships', 2)  # Cache 2 heures
    def extract_relationships(self, text: str):
        # Votre logique existante
        pass
    
    @cached(cache, 'names', 24)  # Cache 24 heures  
    def clean_person_name(self, name: str):
        # Votre logique existante
        pass