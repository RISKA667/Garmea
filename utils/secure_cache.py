"""
Cache sécurisé avec Redis et chiffrement
"""
import json
import pickle
import hashlib
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import redis.asyncio as redis
from cryptography.fernet import Fernet
import structlog

logger = structlog.get_logger()

class SecureRedisCache:
    """Cache Redis sécurisé avec chiffrement optionnel"""
    
    def __init__(self, redis_url: str, ttl_hours: int = 24, encrypt: bool = True):
        self.redis_url = redis_url
        self.ttl_hours = ttl_hours
        self.encrypt = encrypt
        self.redis_client = None
        
        # Clé de chiffrement (en production, utiliser une variable d'environnement)
        if encrypt:
            encryption_key = os.getenv("CACHE_ENCRYPTION_KEY")
            if not encryption_key:
                # Générer une clé temporaire (NON RECOMMANDÉ EN PRODUCTION)
                encryption_key = Fernet.generate_key()
                logger.warning("Using temporary encryption key for cache")
            
            self.cipher = Fernet(encryption_key if isinstance(encryption_key, bytes) else encryption_key.encode())
    
    async def connect(self):
        """Connexion au Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.error("Redis connection failed", error=str(e))
            raise
    
    async def disconnect(self):
        """Déconnexion du Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis cache disconnected")
    
    def _make_key(self, category: str, key: str) -> str:
        """Génère une clé sécurisée"""
        # Hash pour éviter les collisions et masquer les données sensibles
        key_hash = hashlib.sha256(f"{category}:{key}".encode()).hexdigest()[:16]
        return f"garmea:v2:{category}:{key_hash}"
    
    def _serialize_data(self, data: Any) -> bytes:
        """Sérialise et optionnellement chiffre les données"""
        try:
            # Sérialisation
            if isinstance(data, (dict, list)):
                serialized = json.dumps(data, default=str).encode()
            else:
                serialized = pickle.dumps(data)
            
            # Chiffrement optionnel
            if self.encrypt and self.cipher:
                serialized = self.cipher.encrypt(serialized)
            
            return serialized
            
        except Exception as e:
            logger.error("Data serialization failed", error=str(e))
            raise
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Déchiffre et désérialise les données"""
        try:
            # Déchiffrement optionnel
            if self.encrypt and self.cipher:
                data = self.cipher.decrypt(data)
            
            # Tentative de désérialisation JSON d'abord
            try:
                return json.loads(data.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                return pickle.loads(data)
                
        except Exception as e:
            logger.error("Data deserialization failed", error=str(e))
            return None
    
    async def set(self, category: str, key: str, value: Any, ttl_hours: Optional[int] = None) -> bool:
        """Stocke une valeur dans le cache"""
        if not self.redis_client:
            logger.warning("Redis not connected")
            return False
        
        try:
            cache_key = self._make_key(category, key)
            serialized_data = self._serialize_data(value)
            
            # TTL
            ttl_seconds = (ttl_hours or self.ttl_hours) * 3600
            
            # Métadonnées
            metadata = {
                'created_at': datetime.utcnow().isoformat(),
                'category': category,
                'ttl_hours': ttl_hours or self.ttl_hours
            }
            
            # Stockage avec métadonnées
            await self.redis_client.hset(
                cache_key,
                mapping={
                    'data': serialized_data,
                    'metadata': json.dumps(metadata)
                }
            )
            
            # Définir l'expiration
            await self.redis_client.expire(cache_key, ttl_seconds)
            
            logger.debug("Cache set", category=category, key=key[:20])
            return True
            
        except Exception as e:
            logger.error("Cache set failed", category=category, key=key[:20], error=str(e))
            return False
    
    async def get(self, category: str, key: str) -> Optional[Any]:
        """Récupère une valeur du cache"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._make_key(category, key)
            
            # Récupérer les données
            cached_data = await self.redis_client.hgetall(cache_key)
            
            if not cached_data or b'data' not in cached_data:
                return None
            
            # Désérialiser les données
            data = self._deserialize_data(cached_data[b'data'])
            
            logger.debug("Cache hit", category=category, key=key[:20])
            return data
            
        except Exception as e:
            logger.error("Cache get failed", category=category, key=key[:20], error=str(e))
            return None
    
    async def delete(self, category: str, key: str) -> bool:
        """Supprime une valeur du cache"""
        if not self.redis_client:
            return False
        
        try:
            cache_key = self._make_key(category, key)
            result = await self.redis_client.delete(cache_key)
            
            logger.debug("Cache delete", category=category, key=key[:20], existed=bool(result))
            return bool(result)
            
        except Exception as e:
            logger.error("Cache delete failed", category=category, key=key[:20], error=str(e))
            return False
    
    async def clear_category(self, category: str) -> int:
        """Supprime toutes les clés d'une catégorie"""
        if not self.redis_client:
            return 0
        
        try:
            pattern = f"garmea:v2:{category}:*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                result = await self.redis_client.delete(*keys)
                logger.info("Cache category cleared", category=category, keys_deleted=result)
                return result
            
            return 0
            
        except Exception as e:
            logger.error("Cache clear category failed", category=category, error=str(e))
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques du cache"""
        if not self.redis_client:
            return {"status": "disconnected"}
        
        try:
            info = await self.redis_client.info()
            
            # Compter les clés par catégorie
            pattern = "garmea:v2:*"
            keys = await self.redis_client.keys(pattern)
            
            categories = {}
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                parts = key_str.split(':')
                if len(parts) >= 3:
                    category = parts[2]
                    categories[category] = categories.get(category, 0) + 1
            
            return {
                "status": "connected",
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_keys": len(keys),
                "categories": categories,
                "encryption_enabled": self.encrypt
            }
            
        except Exception as e:
            logger.error("Cache stats failed", error=str(e))
            return {"status": "error", "error": str(e)}
    
    async def health_check(self) -> bool:
        """Vérifie la santé du cache"""
        try:
            if not self.redis_client:
                return False
            
            # Test ping
            pong = await self.redis_client.ping()
            return pong == True
            
        except Exception:
            return False