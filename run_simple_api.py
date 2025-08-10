#!/usr/bin/env python3
"""
Script de démarrage pour l'API Garméa (version simplifiée)
"""

import os
import sys
import uvicorn
from pathlib import Path

# Ajouter le répertoire racine au path Python
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Démarrage de l'API simplifiée"""
    
    # Configuration par défaut
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    print(f"🚀 Démarrage de l'API Garméa (version simplifiée) sur {host}:{port}")
    print(f"📖 Documentation: http://{host}:{port}/docs")
    print(f"🔄 Mode reload: {'activé' if reload else 'désactivé'}")
    print(f"🔑 Compte admin: admin / admin123")
    
    # Démarrage du serveur
    uvicorn.run(
        "api.simple_main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    main() 