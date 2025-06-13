"""
Module d'authentification et autorisation sécurisé pour Garméa
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

# Configuration sécurisée
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable required")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Context de hashage sécurisé
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security
security = HTTPBearer()

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_admin: bool = False

class UserCreate(UserBase):
    password: str
    confirm_password: str
    
    def validate_passwords(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords don't match")
        if len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters")
        return self

class UserInDB(UserBase):
    id: int
    hashed_password: str
    created_at: datetime
    last_login: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    scopes: list[str] = []

class AuthManager:
    """Gestionnaire d'authentification sécurisé"""
    
    def __init__(self):
        self.pwd_context = pwd_context
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Vérifie un mot de passe"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash un mot de passe"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], 
                          expires_delta: Optional[timedelta] = None) -> str:
        """Crée un token d'accès JWT"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        })
        
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    def create_refresh_token(self, user_id: int) -> str:
        """Crée un refresh token"""
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        }
        
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    def verify_token(self, token: str) -> TokenData:
        """Vérifie et décode un token JWT"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Vérifier le type de token
            token_type = payload.get("type")
            if token_type != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            # Extraire les données
            user_id: int = payload.get("user_id")
            email: str = payload.get("email")
            
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            token_data = TokenData(user_id=user_id, email=email)
            return token_data
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

# Instance globale
auth_manager = AuthManager()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Dependency pour récupérer l'utilisateur actuel"""
    token = credentials.credentials
    return auth_manager.verify_token(token)

async def get_current_admin_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Dependency pour vérifier les droits admin"""
    # Ici vous devriez vérifier en base si l'utilisateur est admin
    # Pour l'exemple, on simule
    if not current_user.email or "admin" not in current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user

class RateLimiter:
    """Rate limiter simple en mémoire (à remplacer par Redis en production)"""
    
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, key: str, max_requests: int = 100, window_minutes: int = 60) -> bool:
        """Vérifie si la requête est autorisée"""
        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Nettoyer les anciennes requêtes
        self.requests[key] = [req_time for req_time in self.requests[key] if req_time > window_start]
        
        # Vérifier la limite
        if len(self.requests[key]) >= max_requests:
            return False
        
        # Ajouter la requête actuelle
        self.requests[key].append(now)
        return True

rate_limiter = RateLimiter()