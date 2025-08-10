# Garméa Frontend

Frontend moderne pour l'application Garméa - Assistant généalogique intelligent.

## 🚀 Fonctionnalités

- **Interface moderne** : Design responsive avec Tailwind CSS
- **Navigation fluide** : Routing avec React Router
- **Composants réutilisables** : Architecture modulaire
- **Gestion d'état** : Hooks personnalisés pour une meilleure organisation
- **API intégrée** : Service complet pour communiquer avec le backend
- **Onboarding guidé** : Processus d'inscription en 5 étapes
- **Pages complètes** : Landing, Pricing, Checkout, Dashboard, Arbre généalogique

## 🛠️ Technologies

- **React 19** : Framework principal
- **Tailwind CSS 4** : Framework CSS utilitaire
- **Lucide React** : Icônes modernes
- **React Router** : Navigation et routing
- **PostCSS** : Traitement CSS avancé

## 📦 Installation

```bash
# Cloner le projet
git clone <repository-url>
cd garmea-frontend

# Installer les dépendances
npm install

# Démarrer en mode développement
npm start
```

## 🔧 Configuration

### Variables d'environnement

Copiez le fichier `env.example` vers `.env.local` et configurez :

```bash
# Configuration API
REACT_APP_API_URL=http://localhost:8000

# Environnement
REACT_APP_ENV=development

# Version de l'application
REACT_APP_VERSION=0.1.0
```

### Scripts disponibles

```bash
# Développement
npm start          # Démarrer le serveur de développement
npm run build      # Build de production
npm test           # Lancer les tests
npm run eject      # Éjecter la configuration (irréversible)

# Qualité de code
npm run lint       # Vérifier le code avec ESLint
npm run format     # Formater le code avec Prettier
```

## 📁 Structure du projet

```
src/
├── components/          # Composants réutilisables
│   ├── Button.js       # Bouton avec variantes
│   ├── Input.js        # Champ de saisie
│   ├── Card.js         # Conteneur
│   └── index.js        # Exports
├── hooks/              # Hooks personnalisés
│   ├── useLocalStorage.js
│   ├── useApi.js
│   └── index.js
├── services/           # Services API
│   ├── api.js          # Service principal
│   └── index.js
├── pages/              # Pages de l'application
│   ├── LandingPage.js
│   ├── PricingPage.js
│   ├── CheckoutPage.js
│   ├── DashboardPro.js
│   ├── FamilyTreeInteractive.js
│   └── OnboardingPage.js
├── App.js              # Composant principal
├── index.js            # Point d'entrée
└── index.css           # Styles globaux
```

## 🎨 Design System

### Couleurs

- **Primary** : Bleu (#3B82F6) - Actions principales
- **Secondary** : Vert (#22C55E) - Actions secondaires
- **Accent** : Orange (#F59E0B) - Accents et alertes
- **Emerald** : Vert émeraude (#10B981) - Succès
- **Indigo** : Indigo (#6366F1) - Navigation
- **Purple** : Violet (#A855F7) - Fonctionnalités premium
- **Pink** : Rose (#EC4899) - Actions spéciales

### Composants

Tous les composants suivent une API cohérente avec :
- Support des variantes
- États (disabled, loading, error, success)
- Accessibilité intégrée
- Design responsive

## 🔌 API

Le service API (`src/services/api.js`) fournit des méthodes pour :

- **Authentification** : login, register, logout
- **Utilisateurs** : CRUD complet
- **Documents** : Upload, gestion, suppression
- **Analyse** : Déclenchement et suivi
- **Arbre généalogique** : Récupération et visualisation
- **Rapports** : Génération et téléchargement
- **Abonnements** : Gestion des plans

## 🧪 Tests

```bash
# Lancer tous les tests
npm test

# Tests en mode watch
npm test -- --watch

# Tests avec couverture
npm test -- --coverage
```

## 📦 Build et déploiement

### Build de production

```bash
npm run build
```

### Script de build automatisé

```bash
chmod +x scripts/build.sh
./scripts/build.sh
```

### Configuration de déploiement

Le fichier `deploy.config.js` contient la configuration pour différents environnements.

## 🐛 Débogage

### Mode développement

```bash
npm start
```

L'application sera disponible sur `http://localhost:3000`

### Outils de développement

- **React Developer Tools** : Extension navigateur
- **Redux DevTools** : Si Redux est ajouté
- **Console** : Logs détaillés en mode développement

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🆘 Support

Pour toute question ou problème :

1. Consultez la documentation
2. Vérifiez les issues existantes
3. Créez une nouvelle issue avec les détails

---

**Garméa** - Découvrez vos ancêtres avec l'intelligence artificielle 🧬