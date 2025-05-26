import React, { useState, useEffect } from 'react';
import { Search, Users, MapPin, Calendar, TreePine, Star, Clock, Globe, Award } from 'lucide-react';

const AncestorFinder = () => {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    birthPlace: ''
  });
  const [currentView, setCurrentView] = useState('form'); // 'form', 'loading', 'results'
  const [searchResults, setSearchResults] = useState(null);
  const [loadingStep, setLoadingStep] = useState(0);
  const [loadingText, setLoadingText] = useState('');
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [liveCounter, setLiveCounter] = useState(12847);

  // Animation pour les étoiles en arrière-plan
  const [stars, setStars] = useState([]);

  useEffect(() => {
    const generateStars = () => {
      const newStars = [];
      for (let i = 0; i < 50; i++) {
        newStars.push({
          id: i,
          x: Math.random() * 100,
          y: Math.random() * 100,
          size: Math.random() * 2 + 1,
          opacity: Math.random() * 0.5 + 0.3
        });
      }
      setStars(newStars);
    };
    generateStars();

    // Compteur social proof en temps réel
    const interval = setInterval(() => {
      setLiveCounter(prev => prev + Math.floor(Math.random() * 3) + 1);
    }, 8000);

    return () => clearInterval(interval);
  }, []);

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSearch = async () => {
    if (!formData.firstName || !formData.lastName || !formData.birthPlace) return;

    setCurrentView('loading');
    setLoadingStep(0);

    const loadingSteps = [
      'Connexion aux archives nationales...',
      'Recherche dans les registres d\'état civil...',
      'Analyse des actes de naissance et de mariage...',
      'Recoupement des données familiales...',
      'Construction de l\'arbre généalogique...',
      'Finalisation des résultats...'
    ];

    // Simulation du processus de chargement
    for (let i = 0; i < loadingSteps.length; i++) {
      setLoadingStep(i);
      setLoadingText(loadingSteps[i]);
      await new Promise(resolve => setTimeout(resolve, 1500));
    }

    // Génération des résultats
    const mockResults = {
      totalAncestors: Math.floor(Math.random() * 150) + 120, // Entre 120-270 pour être plus impressionnant
      generations: Math.floor(Math.random() * 4) + 8, // Entre 8-12 générations
      countries: ['France', 'Allemagne', 'Espagne', 'Italie', 'Belgique'].slice(0, Math.floor(Math.random() * 3) + 2),
      ancestors: [
        {
          name: 'Marie Dubois',
          birth: '1852',
          place: 'Lyon, France',
          relation: 'Arrière-grand-mère',
          profession: 'Couturière'
        },
        {
          name: 'Jean Baptiste Martin',
          birth: '1847',
          place: 'Marseille, France',
          relation: 'Arrière-grand-père',
          profession: 'Charpentier'
        },
        {
          name: 'Comte Henri de Rousseau',
          birth: '1823',
          place: 'Bordeaux, France',
          relation: 'Arrière-arrière-grand-père',
          profession: 'Comte - Noblesse'
        },
        {
          name: 'Pierre Lefebvre',
          birth: '1819',
          place: 'Rouen, France',
          relation: 'Arrière-arrière-grand-père',
          profession: 'Boulanger'
        },
        {
          name: 'Duchesse Émilie de Moreau',
          birth: '1834',
          place: 'Nancy, France',
          relation: 'Arrière-grand-mère',
          profession: 'Duchesse - Noblesse'
        },
        {
          name: 'François Petit',
          birth: '1829',
          place: 'Strasbourg, France',
          relation: 'Arrière-grand-père',
          profession: 'Forgeron'
        }
      ]
    };

    setSearchResults(mockResults);
    setCurrentView('results');
  };

  const handleUpgrade = () => {
    // Simulation d'un redirect vers la page de paiement plus réaliste
    setShowUpgradeModal(false);
    
    // Simulation d'un checkout
    setTimeout(() => {
      alert("🎉 Redirection vers Stripe Checkout...\n\n✅ Paiement sécurisé\n💳 9,99€/mois (au lieu de 19,99€)\n🔒 Satisfait ou remboursé 30 jours\n⚡ Accès immédiat à tous vos ancêtres");
    }, 500);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-800 relative overflow-hidden">
      {/* Étoiles animées en arrière-plan */}
      <div className="absolute inset-0">
        {stars.map(star => (
          <div
            key={star.id}
            className="absolute bg-white rounded-full animate-pulse"
            style={{
              left: `${star.x}%`,
              top: `${star.y}%`,
              width: `${star.size}px`,
              height: `${star.size}px`,
              opacity: star.opacity,
              animationDelay: `${Math.random() * 3}s`
            }}
          />
        ))}
      </div>

      {/* Overlay gradient */}
      <div className="absolute inset-0 bg-black/20" />

      <div className="relative z-10">
        {/* Header */}
        <header className="container mx-auto px-6 py-8">
          <nav className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <TreePine className="w-8 h-8 text-emerald-400" />
              <span className="text-2xl font-bold text-white">Garméa France</span>
            </div>
            <div className="hidden md:flex space-x-8 text-white/80 items-center">
              <a href="#" className="hover:text-white transition-colors">Fonctionnalités</a>
              <a href="#" className="hover:text-white transition-colors">Tarifs</a>
              <a href="#" className="hover:text-white transition-colors">À propos</a>
              
              {/* Badge de promotion */}
              <div className="bg-gradient-to-r from-red-500/20 to-orange-500/20 border border-red-400/50 rounded-full px-3 py-1">
                <span className="text-red-200 text-sm font-semibold animate-pulse">
                  🔥 -50% 47h
                </span>
              </div>
              
              <button className="bg-emerald-500 hover:bg-emerald-600 px-4 py-2 rounded-lg transition-colors">
                Connexion
              </button>
            </div>
          </nav>
        </header>

        {/* Hero Section */}
        <main className="container mx-auto px-6 py-16">
          {/* Alerte d'urgence */}
          <div className="max-w-4xl mx-auto mb-8">
            <div className="bg-gradient-to-r from-red-500/20 to-orange-500/20 border border-red-400/50 rounded-2xl p-4 text-center backdrop-blur-sm">
              <div className="flex items-center justify-center space-x-2 text-red-200">
                <Clock className="w-5 h-5 animate-pulse" />
                <span className="font-semibold">⚡ OFFRE DÉCOUVERTE - Plus que 47h pour profiter de l'accès gratuit étendu !</span>
              </div>
            </div>
          </div>

          <div className="text-center mb-16">
            <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
              Découvrez votre
              <span className="bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent block">
                histoire familiale
              </span>
            </h1>
            <p className="text-xl text-white/80 max-w-2xl mx-auto mb-8">
              Notre IA révolutionnaire croise <strong>500 ans de données historiques</strong> (depuis 1500) 
              pour reconstituer automatiquement votre arbre généalogique complet.
            </p>
            
            {/* Social Proof */}
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-4 max-w-md mx-auto mb-8 border border-white/20">
              <div className="flex items-center justify-center space-x-3">
                <div className="flex -space-x-2">
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full border-2 border-white"></div>
                  <div className="w-8 h-8 bg-gradient-to-br from-emerald-400 to-blue-500 rounded-full border-2 border-white"></div>
                  <div className="w-8 h-8 bg-gradient-to-br from-pink-400 to-red-500 rounded-full border-2 border-white"></div>
                </div>
                <div className="text-white">
                  <div className="font-bold text-lg text-emerald-300">{liveCounter.toLocaleString()}</div>
                  <div className="text-sm text-white/70">arbres créés cette semaine</div>
                </div>
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              </div>
            </div>

            <p className="text-lg text-emerald-300 max-w-xl mx-auto mb-12 font-medium">
              📋 Indiquez les informations de l'un de vos grands-parents
            </p>
          </div>

          {/* Formulaire de recherche */}
          {currentView === 'form' && (
            <div className="max-w-4xl mx-auto">
              <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-8 border border-white/20 shadow-2xl">
                <div className="space-y-6">
                  <div className="grid md:grid-cols-3 gap-6">
                    <div className="space-y-2">
                      <label className="text-white/90 font-medium">Prénom</label>
                      <input
                        type="text"
                        name="firstName"
                        value={formData.firstName}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white placeholder-white/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent transition-all"
                        placeholder="Entrez le prénom"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-white/90 font-medium">Nom de famille</label>
                      <input
                        type="text"
                        name="lastName"
                        value={formData.lastName}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white placeholder-white/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent transition-all"
                        placeholder="Entrez le nom"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-white/90 font-medium">Lieu de naissance</label>
                      <input
                        type="text"
                        name="birthPlace"
                        value={formData.birthPlace}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white placeholder-white/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent transition-all"
                        placeholder="Ville, Pays"
                        required
                      />
                    </div>
                  </div>
                  <div className="text-center">
                    <button
                      onClick={handleSearch}
                      className="bg-gradient-to-r from-emerald-500 to-blue-500 hover:from-emerald-600 hover:to-blue-600 text-white px-12 py-4 rounded-xl font-semibold text-lg shadow-lg transform hover:scale-105 transition-all duration-200 flex items-center space-x-3 mx-auto"
                    >
                      <Search className="w-5 h-5" />
                      <span>Découvrir mes ancêtres</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Page de chargement */}
          {currentView === 'loading' && (
            <div className="max-w-4xl mx-auto">
              <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-12 border border-white/20 shadow-2xl text-center">
                <div className="mb-8">
                  <div className="animate-spin rounded-full h-20 w-20 border-4 border-emerald-400 border-t-transparent mx-auto mb-6"></div>
                  <h2 className="text-3xl font-bold text-white mb-4">Recherche en cours...</h2>
                  <p className="text-xl text-emerald-300 mb-8">{loadingText}</p>
                </div>
                
                {/* Barre de progression */}
                <div className="w-full bg-white/20 rounded-full h-3 mb-8">
                  <div 
                    className="bg-gradient-to-r from-emerald-400 to-blue-400 h-3 rounded-full transition-all duration-500"
                    style={{ width: `${((loadingStep + 1) / 6) * 100}%` }}
                  ></div>
                </div>

                {/* Étapes de chargement */}
                <div className="grid md:grid-cols-2 gap-4 text-left">
                  {[
                    'Connexion aux archives nationales',
                    'Recherche dans les registres d\'état civil',
                    'Analyse des actes de naissance et de mariage',
                    'Recoupement des données familiales',
                    'Construction de l\'arbre généalogique',
                    'Finalisation des résultats'
                  ].map((step, index) => (
                    <div key={index} className={`flex items-center space-x-3 p-3 rounded-lg ${
                      index <= loadingStep ? 'bg-emerald-500/20 text-emerald-200' : 'bg-white/10 text-white/50'
                    } transition-all duration-300`}>
                      <div className={`w-2 h-2 rounded-full ${
                        index <= loadingStep ? 'bg-emerald-400' : 'bg-white/30'
                      }`}></div>
                      <span className="text-sm">{step}</span>
                      {index <= loadingStep && (
                        <div className="ml-auto">
                          <div className="text-emerald-400">✓</div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Résultats de recherche */}
          {currentView === 'results' && searchResults && (
            <div className="max-w-6xl mx-auto mt-16 animate-fadeIn">
              <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-8 border border-white/20 shadow-2xl">
                <h2 className="text-3xl font-bold text-white mb-8 text-center">
                  🎉 Nous avons trouvé votre histoire !
                </h2>
                
                {/* Statistiques */}
                <div className="grid md:grid-cols-4 gap-6 mb-12">
                  <div className="text-center">
                    <div className="text-4xl font-bold text-emerald-400 mb-2">
                      {searchResults.totalAncestors}
                    </div>
                    <div className="text-white/80">Ancêtres trouvés</div>
                  </div>
                  <div className="text-center">
                    <div className="text-4xl font-bold text-blue-400 mb-2">
                      {searchResults.generations}
                    </div>
                    <div className="text-white/80">Générations</div>
                  </div>
                  <div className="text-center">
                    <div className="text-4xl font-bold text-purple-400 mb-2">
                      {searchResults.countries.length}
                    </div>
                    <div className="text-white/80">Pays d'origine</div>
                  </div>
                  <div className="text-center">
                    <div className="text-4xl font-bold text-pink-400 mb-2">
                      18th
                    </div>
                    <div className="text-white/80">Siècle le plus ancien</div>
                  </div>
                </div>

                {/* Liste des ancêtres */}
                <div className="space-y-4">
                  <h3 className="text-2xl font-bold text-white mb-6">Vos ancêtres découverts</h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    {searchResults.ancestors.map((ancestor, index) => (
                      <div key={index} className="bg-white/10 rounded-xl p-6 border border-white/20 hover:bg-white/20 transition-all transform hover:scale-105">
                        <div className="flex items-start space-x-4">
                          <div className="w-12 h-12 bg-gradient-to-br from-emerald-400 to-blue-400 rounded-full flex items-center justify-center">
                            <Users className="w-6 h-6 text-white" />
                          </div>
                          <div className="flex-1">
                            <h4 className="text-lg font-semibold text-white">{ancestor.name}</h4>
                            <p className="text-emerald-400 font-medium">{ancestor.relation}</p>
                            <div className="flex items-center space-x-4 mt-2 text-white/70 text-sm">
                              <div className="flex items-center space-x-1">
                                <Calendar className="w-4 h-4" />
                                <span>{ancestor.birth}</span>
                              </div>
                              <div className="flex items-center space-x-1">
                                <MapPin className="w-4 h-4" />
                                <span>{ancestor.place}</span>
                              </div>
                            </div>
                            <p className="text-white/60 text-sm mt-1">{ancestor.profession}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="text-center mt-12">
                  <button className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white px-8 py-3 rounded-xl font-semibold transform hover:scale-105 transition-all">
                    Voir l'arbre généalogique complet
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Features Section */}
          <div className="mt-32">
            <h2 className="text-4xl font-bold text-white text-center mb-16">
              Pourquoi choisir AncestorFinder ?
            </h2>
            <div className="grid md:grid-cols-3 gap-8">
              <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20 hover:bg-white/20 transition-all transform hover:scale-105">
                <div className="w-16 h-16 bg-gradient-to-br from-emerald-400 to-blue-400 rounded-2xl flex items-center justify-center mb-6">
                  <Globe className="w-8 h-8 text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-4">Base de données mondiale</h3>
                <p className="text-white/80">Accès à plus de 2 milliards d'enregistrements historiques dans 40+ pays.</p>
              </div>
              <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20 hover:bg-white/20 transition-all transform hover:scale-105">
                <div className="w-16 h-16 bg-gradient-to-br from-purple-400 to-pink-400 rounded-2xl flex items-center justify-center mb-6">
                  <Star className="w-8 h-8 text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-4">IA avancée</h3>
                <p className="text-white/80">Notre intelligence artificielle connecte automatiquement vos liens familiaux.</p>
              </div>
              <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20 hover:bg-white/20 transition-all transform hover:scale-105">
                <div className="w-16 h-16 bg-gradient-to-br from-blue-400 to-indigo-400 rounded-2xl flex items-center justify-center mb-6">
                  <Clock className="w-8 h-8 text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-4">Résultats instantanés</h3>
                <p className="text-white/80">Découvrez votre histoire familiale en quelques minutes seulement.</p>
              </div>
            </div>
          </div>
        </main>

        {/* Modal d'upgrade */}
        {showUpgradeModal && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-8 border border-white/20 shadow-2xl max-w-lg w-full mx-4 animate-fadeIn">
              <div className="text-center">
                {/* Badge d'urgence */}
                <div className="bg-gradient-to-r from-red-500/20 to-orange-500/20 border border-red-400/50 rounded-full px-4 py-2 mb-4 inline-block">
                  <span className="text-red-200 text-sm font-semibold animate-pulse">
                    ⏰ OFFRE LIMITÉE - 47h restantes !
                  </span>
                </div>

                <div className="w-20 h-20 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Award className="w-10 h-10 text-white" />
                </div>
                
                <h3 className="text-2xl font-bold text-white mb-4">
                  🔓 Débloquez TOUT votre héritage !
                </h3>
                
                <p className="text-white/80 mb-6 text-lg">
                  <strong>{searchResults?.totalAncestors - 2} ancêtres supplémentaires</strong> vous attendent ! 
                  Dont <span className="text-yellow-300 font-semibold">2 nobles et 3 actes royaux</span> détectés par notre IA.
                </p>

                {/* Prix avec psychologie */}
                <div className="bg-gradient-to-r from-emerald-500/20 to-blue-500/20 rounded-2xl p-6 mb-6 border border-emerald-400/30">
                  <div className="flex items-center justify-center space-x-4 mb-4">
                    <div className="text-center">
                      <div className="text-white/60 line-through text-lg">19,99€</div>
                      <div className="text-xs text-white/50">Prix normal</div>
                    </div>
                    <div className="text-4xl">→</div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-emerald-300">9,99€</div>
                      <div className="text-xs text-emerald-400">-50% Offre découverte</div>
                    </div>
                  </div>
                  
                  <h4 className="text-emerald-300 font-semibold mb-3">✨ Accès PRO Complet :</h4>
                  <ul className="text-white/80 space-y-2 text-left">
                    <li className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
                      <span><strong>Arbre interactif illimité</strong> - Jusqu'à 20 générations</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
                      <span><strong>Documents historiques originaux</strong> - Actes, photos</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
                      <span><strong>Recherches illimitées</strong> - Toute votre famille</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
                      <span><strong>Export PDF premium</strong> - Partagez votre histoire</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
                      <span className="text-yellow-300"><strong>🏰 Détection de noblesse</strong> - IA exclusive</span>
                    </li>
                  </ul>
                </div>

                {/* Social proof dans la modal */}
                <div className="bg-white/10 rounded-xl p-3 mb-6">
                  <div className="text-sm text-white/70 mb-1">Rejoignez nos membres satisfaits :</div>
                  <div className="flex items-center justify-center space-x-2">
                    <div className="flex -space-x-1">
                      {[...Array(5)].map((_, i) => (
                        <div key={i} className="w-6 h-6 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-full border border-white text-xs flex items-center justify-center text-white">⭐</div>
                      ))}
                    </div>
                    <span className="text-white font-semibold">4.9/5</span>
                    <span className="text-white/60">(2,847 avis)</span>
                  </div>
                </div>

                <div className="flex space-x-4">
                  <button
                    onClick={() => setShowUpgradeModal(false)}
                    className="flex-1 bg-white/20 hover:bg-white/30 text-white px-6 py-3 rounded-xl font-semibold transition-all"
                  >
                    Plus tard
                  </button>
                  <button
                    onClick={handleUpgrade}
                    className="flex-1 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-white px-6 py-3 rounded-xl font-semibold transform hover:scale-105 transition-all shadow-lg relative"
                  >
                    <span className="mr-2">🚀</span>
                    Débloquer PRO
                    <div className="absolute -top-1 -right-1 bg-red-500 text-white text-xs px-2 py-1 rounded-full animate-bounce">
                      -50%
                    </div>
                  </button>
                </div>

                <p className="text-white/60 text-sm mt-4">
                  🔒 <strong>Satisfait ou remboursé 30 jours</strong> - Annulable à tout moment
                </p>
                
                <div className="mt-3 text-xs text-white/50">
                  ⏰ Cette offre expire dans 47h - Prix normal 19,99€/mois ensuite
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn {
          animation: fadeIn 0.8s ease-out;
        }
      `}</style>
    </div>
  );
};

export default AncestorFinder;
