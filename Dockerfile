# Dockerfile sécurisé pour Garméa
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="garméa-team"
LABEL version="2.0.0"
LABEL description="Garméa - Secure Genealogy Analysis API"

# Créer un utilisateur non-root
RUN groupadd -r garmea && useradd -r -g garmea garmea

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    # Pour PyMuPDF et traitement PDF
    libmupdf-dev \
    libmagic1 \
    # Pour Pillow/images
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    # Outils de base
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Définir le répertoire de travail
WORKDIR /app

# Copier les requirements d'abord (cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Créer les répertoires nécessaires
RUN mkdir -p /app/logs /app/uploads /app/temp && \
    chown -R garmea:garmea /app

# Passer à l'utilisateur non-root
USER garmea

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Exposer le port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Commande par défaut
CMD ["uvicorn", "api.secure_main:app", "--host", "0.0.0.0", "--port", "8000"]