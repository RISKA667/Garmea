module.exports = {
  // Configuration pour différents environnements
  environments: {
    development: {
      apiUrl: 'http://localhost:8000',
      env: 'development',
      debug: true,
    },
    staging: {
      apiUrl: 'https://staging-api.garmea.fr',
      env: 'staging',
      debug: false,
    },
    production: {
      apiUrl: 'https://api.garmea.fr',
      env: 'production',
      debug: false,
    },
  },

  // Configuration des builds
  build: {
    outputDir: 'build',
    publicPath: '/',
    sourceMap: false, // Désactivé en production
    minify: true,
    optimize: true,
  },

  // Configuration des assets
  assets: {
    images: {
      formats: ['webp', 'jpg', 'png'],
      quality: 85,
    },
    fonts: {
      preload: true,
      display: 'swap',
    },
  },

  // Configuration PWA
  pwa: {
    enabled: true,
    name: 'Garméa',
    shortName: 'Garméa',
    description: 'Votre assistant généalogique intelligent',
    themeColor: '#3B82F6',
    backgroundColor: '#ffffff',
    icon: 'public/icon-192x192.png',
  },
}; 