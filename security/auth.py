"""
Module d'authentification et autorisation sécurisé pour Garméa
"""
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import bcrypt
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel

class UserIn(BaseModel):
    username: str
    email: str
    password: str

class UserOut(BaseModel):
    user_id: str
    username: str
    email: str
    is_admin: bool = False

class UserLogin(BaseModel):
    username: str
    password: str

class AuthManager:
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        
        # Stockage temporaire des utilisateurs (en production, utiliser une base de données)
        self.users: Dict[str, Dict[str, Any]] = {}
        
        # Créer un utilisateur admin par défaut
        self._create_default_admin()
    
    def _create_default_admin(self):
        """Créer un utilisateur administrateur par défaut"""
        admin_user = {
            "user_id": "admin-001",
            "username": "admin",
            "email": "admin@garmea.fr",
            "password_hash": bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()),
            "is_admin": True,
            "created_at": datetime.now()
        }
        self.users[admin_user["user_id"]] = admin_user
    
    async def register_user(self, user: UserIn) -> UserOut:
        """Enregistrer un nouvel utilisateur"""
        # Vérifier si l'utilisateur existe déjà
        for existing_user in self.users.values():
            if existing_user["username"] == user.username or existing_user["email"] == user.email:
                raise ValueError("Utilisateur ou email déjà existant")
        
        # Créer le nouvel utilisateur
        user_id = str(uuid.uuid4())
        password_hash = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
        
        new_user = {
            "user_id": user_id,
            "username": user.username,
            "email": user.email,
            "password_hash": password_hash,
            "is_admin": False,
            "created_at": datetime.now()
        }
        
        self.users[user_id] = new_user
        
        return UserOut(
            user_id=user_id,
            username=user.username,
            email=user.email,
            is_admin=False
        )
    
    async def authenticate_user(self, user: UserLogin) -> Dict[str, Any]:
        """Authentifier un utilisateur et retourner un token"""
        # Rechercher l'utilisateur
        target_user = None
        for existing_user in self.users.values():
            if existing_user["username"] == user.username:
                target_user = existing_user
                break
        
        if not target_user:
            raise PermissionError("Nom d'utilisateur ou mot de passe incorrect")
        
        # Vérifier le mot de passe
        if not bcrypt.checkpw(user.password.encode('utf-8'), target_user["password_hash"]):
            raise PermissionError("Nom d'utilisateur ou mot de passe incorrect")
        
        # Créer le token d'accès
        access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
        access_token = self._create_access_token(
            data={"sub": target_user["user_id"]}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserOut(
                user_id=target_user["user_id"],
                username=target_user["username"],
                email=target_user["email"],
                is_admin=target_user["is_admin"]
            )
        }
    
    def _create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Créer un token d'accès JWT"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Vérifier un token JWT et retourner les données utilisateur"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            return self.users.get(user_id)
        except jwt.PyJWTError:
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer un utilisateur par son ID"""
        return self.users.get(user_id)
    
    async def count_users(self) -> int:
        """Compter le nombre total d'utilisateurs"""
        return len(self.users)

# Fonctions utilitaires pour FastAPI
async def get_current_user(token: str = Depends(HTTPBearer())) -> Dict[str, Any]:
    """Dépendance FastAPI pour récupérer l'utilisateur actuel"""
    auth_manager = AuthManager()
    user = await auth_manager.verify_token(token.credentials)
    if user is None:
        raise HTTPException(status_code=401, detail="Token invalide")
    return user

async def get_current_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dépendance FastAPI pour récupérer un utilisateur administrateur"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Accès administrateur requis")
    return current_user

def is_admin_user(user: Dict[str, Any]) -> bool:
    """Vérifier si un utilisateur est administrateur"""
    return user.get("is_admin", False)