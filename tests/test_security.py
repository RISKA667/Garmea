"""
Tests de sécurité pour Garméa
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import tempfile
import os

from api.secure_main import app
from security.auth import auth_manager, AuthManager
from security.file_validator import SecureFileValidator

client = TestClient(app)

class TestAuthentication:
    """Tests d'authentification"""
    
    def test_jwt_token_creation(self):
        """Test de création de token JWT"""
        auth = AuthManager()
        
        token = auth.create_access_token(data={"user_id": 123, "email": "test@example.com"})
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT est assez long
    
    def test_jwt_token_verification(self):
        """Test de vérification de token JWT"""
        auth = AuthManager()
        
        # Créer un token
        original_data = {"user_id": 123, "email": "test@example.com"}
        token = auth.create_access_token(data=original_data)
        
        # Vérifier le token
        token_data = auth.verify_token(token)
        
        assert token_data.user_id == 123
        assert token_data.email == "test@example.com"
    
    def test_invalid_token_rejection(self):
        """Test de rejet des tokens invalides"""
        auth = AuthManager()
        
        with pytest.raises(Exception):
            auth.verify_token("invalid_token")
    
    def test_password_hashing(self):
        """Test de hashage des mots de passe"""
        auth = AuthManager()
        
        password = "test_password_123"
        hashed = auth.get_password_hash(password)
        
        assert hashed != password
        assert auth.verify_password(password, hashed)
        assert not auth.verify_password("wrong_password", hashed)

class TestFileValidation:
    """Tests de validation de fichiers"""
    
    @pytest.fixture
    def validator(self):
        return SecureFileValidator()
    
    def test_valid_pdf_file(self, validator):
        """Test de validation d'un PDF valide"""
        # Créer un fichier PDF minimal
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF'
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(pdf_content)
            tmp.flush()
            
            # Simuler un UploadFile
            mock_file = Mock()
            mock_file.filename = "test.pdf"
            mock_file.read = Mock(return_value=pdf_content)
            mock_file.file.seek = Mock()
            
            # Test de validation
            is_valid, error = asyncio.run(validator.validate_file(mock_file))
            
        os.unlink(tmp.name)
        assert is_valid
        assert error is None
    
    def test_malicious_filename_rejection(self, validator):
        """Test de rejet des noms de fichiers malveillants"""
        malicious_names = [
            "../../../etc/passwd",
            "test<script>.pdf",
            "file|rm -rf /.pdf",
            "test\x00.pdf",
            "con.pdf",  # Windows reserved name
        ]
        
        for filename in malicious_names:
            assert not validator._validate_filename(filename)
    
    def test_file_size_limits(self, validator):
        """Test des limites de taille de fichier"""
        # Fichier trop gros
        large_content = b'A' * (100 * 1024 * 1024 + 1)  # 100MB + 1 byte
        
        assert not validator._validate_file_size(large_content, "test.pdf")
        
        # Fichier de taille acceptable
        normal_content = b'A' * (1024 * 1024)  # 1MB
        assert validator._validate_file_size(normal_content, "test.pdf")
    
    def test_mime_type_validation(self, validator):
        """Test de validation des types MIME"""
        # Types autorisés
        allowed_types = [
            'application/pdf',
            'image/jpeg',
            'image/png',
            'text/plain'
        ]
        
        for mime_type in allowed_types:
            assert validator._validate_mime_type(mime_type)
        
        # Types interdits
        forbidden_types = [
            'application/x-executable',
            'text/html',
            'application/javascript',
            'image/svg+xml'
        ]
        
        for mime_type in forbidden_types:
            assert not validator._validate_mime_type(mime_type)

class TestAPIEndpoints:
    """Tests de sécurité des endpoints API"""
    
    def test_unauthenticated_access_denied(self):
        """Test de refus d'accès sans authentification"""
        # Tentative d'upload sans token
        response = client.post("/documents/upload", files={"file": ("test.pdf", b"test", "application/pdf")})
        
        assert response.status_code == 403  # Forbidden
    
    def test_malformed_token_rejection(self):
        """Test de rejet des tokens malformés"""
        headers = {"Authorization": "Bearer invalid_token"}
        
        response = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("test.pdf", b"test", "application/pdf")}
        )
        
        assert response.status_code == 401  # Unauthorized
    
    def test_rate_limiting(self):
        """Test du rate limiting"""
        # Simuler de nombreuses requêtes rapides
        responses = []
        
        for i in range(150):  # Dépasser la limite
            response = client.get("/health")
            responses.append(response.status_code)
        
        # Au moins une requête devrait être limitée
        assert 429 in responses  # Too Many Requests
    
    def test_cors_headers(self):
        """Test des headers CORS"""
        response = client.options("/")
        
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers

class TestSecurityHeaders:
    """Tests des headers de sécurité"""
    
    def test_security_headers_present(self):
        """Test de présence des headers de sécurité"""
        response = client.get("/")
        
        # Headers de sécurité attendus
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection"
        ]
        
        for header in expected_headers:
            assert header in response.headers

class TestInputValidation:
    """Tests de validation des entrées"""
    
    def test_sql_injection_prevention(self):
        """Test de prévention d'injection SQL"""
        # Tentatives d'injection SQL dans les paramètres de recherche
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'/*",
            "1; DELETE FROM users"
        ]
        
        for malicious_input in malicious_inputs:
            response = client.post(
                "/search",
                json={"nom": malicious_input},
                headers=self._get_auth_headers()
            )
            
            # Devrait retourner une erreur ou un résultat sûr, pas un crash
            assert response.status_code in [400, 401, 422, 200]
    
    def test_xss_prevention(self):
        """Test de prévention XSS"""
        malicious_scripts = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "eval('alert(1)')"
        ]
        
        for script in malicious_scripts:
            response = client.post(
                "/search",
                json={"nom": script},
                headers=self._get_auth_headers()
            )
            
            # Le contenu de la réponse ne devrait pas contenir le script
            assert script not in response.text
    
    def _get_auth_headers(self):
        """Helper pour obtenir des headers d'authentification valides"""
        # En production, utilisez un vrai token de test
        return {"Authorization": "Bearer test_token"}

class TestFileUploadSecurity:
    """Tests de sécurité pour l'upload de fichiers"""
    
    def test_executable_file_rejection(self):
        """Test de rejet des fichiers exécutables"""
        # Contenu d'un fichier exécutable Windows
        exe_content = b'MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff'
        
        response = client.post(
            "/documents/upload",
            headers=self._get_auth_headers(),
            files={"file": ("malware.exe", exe_content, "application/octet-stream")}
        )
        
        assert response.status_code == 400
    
    def test_script_file_rejection(self):
        """Test de rejet des fichiers de script"""
        script_content = b'#!/bin/bash\nrm -rf /'
        
        response = client.post(
            "/documents/upload",
            headers=self._get_auth_headers(),
            files={"file": ("script.sh", script_content, "text/plain")}
        )
        
        assert response.status_code == 400
    
    def test_zip_bomb_prevention(self):
        """Test de prévention des zip bombs"""
        # Simuler un fichier qui se décompresse énormément
        # (en pratique, créer un vrai zip bomb pour ce test)
        large_content = b'PK' + b'A' * (50 * 1024 * 1024)  # Simulé
        
        response = client.post(
            "/documents/upload",
            headers=self._get_auth_headers(),
            files={"file": ("bomb.zip", large_content, "application/zip")}
        )
        
        assert response.status_code == 400
    
    def _get_auth_headers(self):
        """Helper pour les headers d'auth"""
        return {"Authorization": "Bearer valid_test_token"}

# Tests d'intégration de sécurité
class TestSecurityIntegration:
    """Tests d'intégration de sécurité"""
    
    @pytest.mark.asyncio
    async def test_complete_secure_workflow(self):
        """Test du workflow complet sécurisé"""
        # 1. Inscription
        user_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!"
        }
        
        register_response = client.post("/auth/register", json=user_data)
        assert register_response.status_code == 200
        
        # 2. Connexion
        login_response = client.post(
            "/auth/login",
            data={"email": "test@example.com", "password": "SecurePassword123!"}
        )
        assert login_response.status_code == 200
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Upload sécurisé
        pdf_content = b'%PDF-1.4\n%%EOF'
        upload_response = client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("test.pdf", pdf_content, "application/pdf")}
        )
        assert upload_response.status_code == 200
        
        # 4. Recherche sécurisée
        search_response = client.post(
            "/search",
            headers=headers,
            json={"nom": "Dupont"}
        )
        assert search_response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v"])