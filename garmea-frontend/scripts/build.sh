#!/bin/bash

# Script de build pour la production
echo "🚀 Démarrage du build de production..."

# Nettoyage du cache
echo "🧹 Nettoyage du cache..."
rm -rf node_modules/.cache
rm -rf build

# Installation des dépendances
echo "📦 Installation des dépendances..."
npm ci --only=production

# Build de production
echo "🔨 Build de production..."
npm run build

# Vérification du build
if [ -d "build" ]; then
    echo "✅ Build réussi !"
    echo "📁 Dossier build créé avec succès"
    echo "📊 Taille du build:"
    du -sh build/
else
    echo "❌ Erreur lors du build"
    exit 1
fi

echo "🎉 Build terminé avec succès !" 