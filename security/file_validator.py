"""
Validation robuste et sécurisée des fichiers uploadés
"""
import hashlib
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List
import magic
from PIL import Image
from fastapi import HTTPException, UploadFile

class FileValidationError(Exception):
    """Exception pour les erreurs de validation de fichier"""
    pass

class SecureFileValidator:
    """Validateur de fichiers sécurisé"""
    
    # Types MIME autorisés
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/tiff',
        'text/plain'
    }
    
    # Extensions autorisées
    ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.txt'}
    
    # Taille max par type (en bytes)
    MAX_FILE_SIZES = {
        'application/pdf': 50 * 1024 * 1024,  # 50MB
        'image/jpeg': 10 * 1024 * 1024,       # 10MB
        'image/png': 10 * 1024 * 1024,        # 10MB
        'image/tiff': 20 * 1024 * 1024,       # 20MB
        'text/plain': 1 * 1024 * 1024,        # 1MB
    }
    
    # Signatures de fichiers (magic numbers)
    FILE_SIGNATURES = {
        'PDF': [b'%PDF-'],
        'JPEG': [b'\xff\xd8\xff'],
        'PNG': [b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'],
        'TIFF': [b'II*\x00', b'MM\x00*']
    }
    
    def __init__(self):
        self.magic_mime = magic.Magic(mime=True)
    
    async def validate_file(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """
        Validation complète d'un fichier uploadé
        
        Returns:
            (is_valid, error_message)
        """
        try:
            # 1. Validation du nom de fichier
            if not self._validate_filename(file.filename):
                return False, "Nom de fichier invalide ou dangereux"
            
            # 2. Lecture sécurisée du contenu
            content = await file.read()
            file.file.seek(0)  # Reset pour utilisation ultérieure
            
            # 3. Validation de la taille
            if not self._validate_file_size(content, file.filename):
                return False, "Fichier trop volumineux"
            
            # 4. Validation du type MIME réel
            real_mime_type = self.magic_mime.from_buffer(content)
            if not self._validate_mime_type(real_mime_type):
                return False, f"Type de fichier non autorisé: {real_mime_type}"
            
            # 5. Validation de la signature
            if not self._validate_file_signature(content):
                return False, "Signature de fichier invalide ou corrompue"
            
            # 6. Validation spécifique par type
            if not await self._validate_content_specific(content, real_mime_type):
                return False, "Contenu du fichier invalide ou corrompu"
            
            # 7. Scan antivirus (simulé)
            if not self._scan_for_malware(content):
                return False, "Fichier potentiellement malveillant détecté"
            
            return True, None
            
        except Exception as e:
            return False, f"Erreur lors de la validation: {str(e)}"
    
    def _validate_filename(self, filename: str) -> bool:
        """Valide le nom de fichier"""
        if not filename:
            return False
        
        # Caractères dangereux
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        if any(char in filename for char in dangerous_chars):
            return False
        
        # Extension autorisée
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            return False
        
        # Longueur raisonnable
        if len(filename) > 255:
            return False
        
        return True
    
    def _validate_file_size(self, content: bytes, filename: str) -> bool:
        """Valide la taille du fichier"""
        size = len(content)
        
        # Fichier vide
        if size == 0:
            return False
        
        # Taille maximum globale
        if size > 100 * 1024 * 1024:  # 100MB max absolu
            return False
        
        # Taille par type MIME
        ext = Path(filename).suffix.lower()
        mime_type = mimetypes.guess_type(filename)[0]
        
        if mime_type in self.MAX_FILE_SIZES:
            return size <= self.MAX_FILE_SIZES[mime_type]
        
        return size <= 10 * 1024 * 1024  # 10MB par défaut
    
    def _validate_mime_type(self, mime_type: str) -> bool:
        """Valide le type MIME"""
        return mime_type in self.ALLOWED_MIME_TYPES
    
    def _validate_file_signature(self, content: bytes) -> bool:
        """Valide la signature du fichier (magic numbers)"""
        if len(content) < 8:
            return False
        
        header = content[:8]
        
        for file_type, signatures in self.FILE_SIGNATURES.items():
            for signature in signatures:
                if header.startswith(signature):
                    return True
        
        # Pour les fichiers texte (pas de signature fixe)
        try:
            content[:1024].decode('utf-8')
            return True
        except UnicodeDecodeError:
            pass
        
        return False
    
    async def _validate_content_specific(self, content: bytes, mime_type: str) -> bool:
        """Validation spécifique au type de contenu"""
        try:
            if mime_type.startswith('image/'):
                return await self._validate_image_content(content)
            elif mime_type == 'application/pdf':
                return await self._validate_pdf_content(content)
            elif mime_type == 'text/plain':
                return await self._validate_text_content(content)
            
            return True
            
        except Exception:
            return False
    
    async def _validate_image_content(self, content: bytes) -> bool:
        """Valide le contenu d'une image"""
        try:
            with tempfile.NamedTemporaryFile() as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                
                # Ouvrir avec PIL pour validation
                with Image.open(tmp_file.name) as img:
                    # Vérifier les dimensions raisonnables
                    width, height = img.size
                    if width > 10000 or height > 10000:
                        return False
                    
                    # Vérifier que l'image peut être traitée
                    img.verify()
                    
                return True
                
        except Exception:
            return False
    
    async def _validate_pdf_content(self, content: bytes) -> bool:
        """Valide le contenu d'un PDF"""
        try:
            # Vérifications basiques PDF
            content_str = content.decode('latin-1', errors='ignore')
            
            # Doit contenir les marqueurs PDF de base
            if '%PDF-' not in content_str:
                return False
            
            # Pas de JavaScript ou contenu suspicieux
            suspicious_keywords = [
                '/JavaScript', '/JS', '/OpenAction', 
                '/Launch', '/SubmitForm', '/ImportData'
            ]
            
            for keyword in suspicious_keywords:
                if keyword in content_str:
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def _validate_text_content(self, content: bytes) -> bool:
        """Valide le contenu texte"""
        try:
            # Vérifier que c'est du texte UTF-8 valide
            text = content.decode('utf-8')
            
            # Pas de caractères de contrôle dangereux
            dangerous_chars = ['\x00', '\x01', '\x02', '\x03', '\x04']
            if any(char in text for char in dangerous_chars):
                return False
            
            return True
            
        except UnicodeDecodeError:
            return False
    
    def _scan_for_malware(self, content: bytes) -> bool:
        """
        Scan antivirus simulé
        En production, intégrer avec ClamAV ou service cloud
        """
        # Patterns suspects simples
        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'eval(',
            b'exec(',
            b'system(',
            b'shell_exec'
        ]
        
        content_lower = content.lower()
        for pattern in suspicious_patterns:
            if pattern in content_lower:
                return False
        
        return True
    
    def calculate_file_hash(self, content: bytes) -> str:
        """Calcule le hash SHA-256 du fichier"""
        return hashlib.sha256(content).hexdigest()
    
    def get_file_info(self, content: bytes, filename: str) -> dict:
        """Retourne les informations du fichier"""
        return {
            'filename': filename,
            'size': len(content),
            'mime_type': self.magic_mime.from_buffer(content),
            'hash_sha256': self.calculate_file_hash(content),
            'extension': Path(filename).suffix.lower()
        }

# Instance globale
file_validator = SecureFileValidator()

import os
import magic
from typing import Tuple
from fastapi import UploadFile

class FileValidator:
    def __init__(self):
        self.allowed_extensions = {'.pdf', '.txt', '.doc', '.docx'}
        self.allowed_mime_types = {
            'application/pdf',
            'text/plain',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        self.max_file_size = 50 * 1024 * 1024  # 50MB
    
    async def validate_file(self, file: UploadFile) -> Tuple[bool, str]:
        """
        Valider un fichier uploadé
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Vérifier l'extension
            if not self._validate_extension(file.filename):
                return False, "Type de fichier non autorisé"
            
            # Vérifier la taille
            if not await self._validate_size(file):
                return False, "Fichier trop volumineux"
            
            # Vérifier le type MIME
            if not await self._validate_mime_type(file):
                return False, "Type de contenu non autorisé"
            
            return True, ""
            
        except Exception as e:
            return False, f"Erreur de validation: {str(e)}"
    
    def _validate_extension(self, filename: str) -> bool:
        """Vérifier l'extension du fichier"""
        if not filename:
            return False
        
        file_extension = os.path.splitext(filename.lower())[1]
        return file_extension in self.allowed_extensions
    
    async def _validate_size(self, file: UploadFile) -> bool:
        """Vérifier la taille du fichier"""
        try:
            # Lire le début du fichier pour obtenir la taille
            content = await file.read()
            await file.seek(0)  # Remettre le curseur au début
            
            return len(content) <= self.max_file_size
        except Exception:
            return False
    
    async def _validate_mime_type(self, file: UploadFile) -> bool:
        """Vérifier le type MIME du fichier"""
        try:
            content = await file.read(2048)  # Lire les premiers 2KB
            await file.seek(0)  # Remettre le curseur au début
            
            mime_type = magic.from_buffer(content, mime=True)
            return mime_type in self.allowed_mime_types
        except Exception:
            # Si magic ne fonctionne pas, on se base sur l'extension
            return self._validate_extension(file.filename)
    
    def get_file_info(self, file: UploadFile) -> dict:
        """Obtenir les informations sur le fichier"""
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": getattr(file, 'size', 0)
        }