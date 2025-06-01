import React, { useState, useEffect } from 'react';
import { 
  Check, X, Crown, Users, FileText, Download, Share, Award, 
  Clock, Star, Shield, ChevronDown, ChevronUp, TreePine,
  Zap, Globe, Camera, BookOpen, TrendingUp, Heart, Sparkles
} from 'lucide-react';

const PricingPage = () => {
  const [timeLeft, setTimeLeft] = useState(47 * 3600); // 47 heures
  const [showFaq, setShowFaq] = useState({});
  const [selectedPlan, setSelectedPlan] = useState('pro');
  const [currentTestimonial, setCurrentTestimonial] = useState(0);

  const testimonials = [
    {
      name: "Sophie R.",
      location: "Lyon, France",
      text: "J'ai découvert que mon arrière-grand-père était baron ! Le plan PRO vaut chaque centime.",
      rating: 5,
      avatar: "bg-gradient-to-br from-pink-400 to-red-500",
      badge: "👑 Noblesse découverte"
    },
    {
      name: "Michel D.",
      location: "Marseille, France", 
      text: "247 ancêtres trouvés automatiquement. J'ai économisé des années de recherche !",
      rating: 5,
      avatar: "bg-gradient-to-br from-blue-400 to-purple-500",
      badge: "🏆 12 générations"
    },
    {
      name: "Isabelle L.",
      location: "Bordeaux, France",
      text: "Les documents historiques sont authentiques. J'ai même des actes du 16ème siècle !",
      rating: 5,
      avatar: "bg-gradient-to-br from-emerald-400 to-blue-500",
      badge: "📜 89 documents"
    }
  ];

  const faqs = [
    {
      question: "Comment l'IA trouve-t-elle autant d'ancêtres ?",
      answer: "Notre algorithme propriétaire croise automatiquement plus de 2 milliards de documents historiques depuis 1500. Il analyse les actes d'état civil, registres paroissiaux, recensements et archives nobiliaires pour reconstituer votre lignée complète."
    },
    {
      question: "Puis-je vraiment découvrir des ancêtres nobles ?",
      answer: "Oui ! Notre IA détecte automatiquement les titres de noblesse, armoiries et liens aristocratiques. 23% de nos utilisateurs PRO découvrent au moins un ancêtre noble dans leur lignée."
    },
    {
      question: "Les documents sont-ils authentiques ?",
      answer: "Absolument. Nous travaillons directement avec les Archives Nationales, bibliothèques et centres d'archives européens. Chaque document est vérifié et source."
    },
    {
      question: "Puis-je annuler à tout moment ?",
      answer: "Oui, vous pouvez annuler votre abonnement à tout moment depuis votre tableau de bord. Aucun engagement, aucune pénalité. Garantie satisfait ou remboursé 30 jours."
    },
    {
      question: "Combien de temps faut-il pour avoir des résultats ?",
      answer: "Les premiers résultats apparaissent en 2-3 minutes ! Notre IA continue ensuite d'enrichir votre arbre pendant plusieurs jours pour découvrir un maximum d'ancêtres."
    },
    {
      question: "Que se passe-t-il si je repasse en gratuit ?",
      answer: "Vous gardez accès à vos 3 premiers ancêtres découverts. Pour retrouver l'accès complet à tous vos ancêtres et documents, il suffit de réactiver PRO à tout moment."
    }
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft(prev => Math.max(0, prev - 1));
    }, 1000);

    const testimonialTimer = setInterval(() => {
      setCurrentTestimonial(prev => (prev + 1) % testimonials.length);
    }, 5000);

    return () => {
      clearInterval(timer);
      clearInterval(testimonialTimer);
    };
  }, []);

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const toggleFaq = (index) => {
    setShowFaq(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const handleUpgrade = (plan) => {
    if (plan === 'pro') {
      alert("🚀 Redirection vers le checkout PRO...\n\n✅ Accès à tous vos ancêtres\n👑 Détection de noblesse\n📜 Documents historiques\n💳 9,99€/mois au lieu de 19,99€");
    } else {
      alert("🎯 Démarrage de votre recherche gratuite...\n\n✅ 3 ancêtres découverts\n⚡ Résultats en 2-3 minutes\n🔄 Possibilité d'upgrade vers PRO");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-800">
      {/* Header avec urgence */}
      <header className="border-b border-white/10 bg-black/20 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <TreePine className="w-8 h-8 text-emerald-400" />
                <span className="text-2xl font-bold text-white">Garméa France</span>
              </div>
              <nav className="hidden md:flex space-x-6 text-white/80">
                <a href="#" className="hover:text-white transition-colors">Accueil</a>
                <a href="#" className="hover:text-white transition-colors">Fonctionnalités</a>
                <a href="#" className="text-emerald-400 font-semibold">Tarifs</a>
                <a href="#" className="hover:text-white transition-colors">Contact</a>
              </nav>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="bg-gradient-to-r from-red-500/20 to-orange-500/20 border border-red-400/50 rounded-full px-4 py-2">
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-red-300 animate-pulse" />
                  <span className="text-red-200 font-semibold text-sm">
                    Offre -50% expire dans {formatTime(timeLeft)}
                  </span>
                </div>
              </div>
              <button className="bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-lg transition-colors">
                Connexion
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-16">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <div className="bg-gradient-to-r from-red-500/20 to-orange-500/20 border border-red-400/50 rounded-2xl p-4 max-w-2xl mx-auto mb-8">
            <div className="flex items-center justify-center space-x-3">
              <Sparkles className="w-6 h-6 text-orange-300 animate-pulse" />
              <span className="text-orange-200 font-bold text-lg">
                🔥 OFFRE LIMITÉE - Plus que {formatTime(timeLeft)} !
              </span>
              <Sparkles className="w-6 h-6 text-orange-300 animate-pulse" />
            </div>
          </div>

          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6 leading-tight">
            Découvrez <span className="bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">tous</span> vos ancêtres
          </h1>
          <p className="text-xl text-white/80 max-w-3xl mx-auto mb-8">
            Notre IA révolutionnaire croise <strong>500 ans de données historiques</strong> pour reconstituer 
            automatiquement votre arbre généalogique complet. Déjà <strong>12,847 familles</strong> ont découvert leur héritage !
          </p>

          {/* Social proof */}
          <div className="flex items-center justify-center space-x-8 mb-12">
            <div className="flex items-center space-x-2">
              <div className="flex -space-x-1">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="w-8 h-8 bg-gradient-to-br from-emerald-400 to-blue-400 rounded-full border-2 border-white"></div>
                ))}
              </div>
              <div className="text-white">
                <div className="font-bold">12,847+</div>
                <div className="text-sm text-white/70">familles satisfaites</div>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <div className="flex">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-5 h-5 text-yellow-400 fill-current" />
                ))}
              </div>
              <div className="text-white">
                <div className="font-bold">4.9/5</div>
                <div className="text-sm text-white/70">note moyenne</div>
              </div>
            </div>
          </div>
        </div>

        {/* Plans de tarification */}
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-8 mb-16">
            
            {/* Plan Gratuit */}
            <div className="bg-white/10 backdrop-blur-lg rounded-3xl border border-white/20 p-8 relative">
              <div className="text-center mb-8">
                <h3 className="text-2xl font-bold text-white mb-2">Découverte Gratuite</h3>
                <p className="text-white/70 mb-6">Parfait pour commencer votre recherche</p>
                <div className="text-4xl font-bold text-white mb-2">0€</div>
                <p className="text-white/60">Toujours gratuit</p>
              </div>

              <div className="space-y-4 mb-8">
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-white">3 ancêtres découverts</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-white">2 générations explorées</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-white">Aperçu des documents</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
                    <X className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-white/60">Arbre généalogique complet</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
                    <X className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-white/60">Détection de noblesse</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
                    <X className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-white/60">Documents historiques</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
                    <X className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-white/60">Export PDF</span>
                </div>
              </div>

              <button 
                onClick={() => handleUpgrade('free')}
                className="w-full bg-white/20 hover:bg-white/30 text-white px-8 py-4 rounded-xl font-semibold text-lg transition-all border border-white/30"
              >
                Commencer gratuitement
              </button>
            </div>

            {/* Plan PRO */}
            <div className="bg-gradient-to-br from-emerald-500/20 to-blue-500/20 backdrop-blur-lg rounded-3xl border-2 border-emerald-400/50 p-8 relative transform scale-105 shadow-2xl">
              {/* Badge populaire */}
              <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                <div className="bg-gradient-to-r from-yellow-500 to-orange-500 text-white px-6 py-2 rounded-full font-bold text-sm shadow-lg">
                  🔥 PLUS POPULAIRE
                </div>
              </div>

              <div className="text-center mb-8">
                <div className="flex items-center justify-center space-x-2 mb-4">
                  <Crown className="w-8 h-8 text-yellow-400" />
                  <h3 className="text-2xl font-bold text-white">PRO - Accès Complet</h3>
                </div>
                <p className="text-white/70 mb-6">Débloquez toute votre histoire familiale</p>
                
                <div className="flex items-center justify-center space-x-4 mb-4">
                  <div className="text-white/60 line-through text-2xl">19,99€</div>
                  <div className="text-5xl font-bold text-white">9,99€</div>
                </div>
                <div className="bg-gradient-to-r from-red-500/20 to-orange-500/20 border border-red-400/50 rounded-full px-4 py-2 inline-block">
                  <span className="text-red-200 font-bold text-sm">🎯 -50% OFFRE LIMITÉE</span>
                </div>
                <p className="text-white/60 mt-2">par mois • puis 19,99€/mois</p>
              </div>

              <div className="space-y-4 mb-8">
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-white font-medium">Jusqu'à 500+ ancêtres découverts</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-white font-medium">12+ générations explorées</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-yellow-500 rounded-full flex items-center justify-center">
                    <Crown className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-yellow-300 font-medium">🏰 Détection de noblesse IA</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-white font-medium">Arbre généalogique interactif</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-white font-medium">Documents historiques complets</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-white font-medium">Export PDF premium</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-white font-medium">Recherches illimitées</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-white font-medium">Support prioritaire</span>
                </div>
              </div>

              <button 
                onClick={() => handleUpgrade('pro')}
                className="w-full bg-gradient-to-r from-emerald-500 to-blue-500 hover:from-emerald-600 hover:to-blue-600 text-white px-8 py-4 rounded-xl font-bold text-lg shadow-lg transform hover:scale-105 transition-all duration-200 relative"
              >
                <span className="mr-2">🚀</span>
                Débloquer PRO maintenant
                <div className="absolute -top-2 -right-2 bg-red-500 text-white text-xs px-2 py-1 rounded-full animate-bounce">
                  -50%
                </div>
              </button>

              <div className="text-center mt-4">
                <p className="text-white/60 text-sm">
                  ✅ <strong>Essai 7 jours gratuits</strong> • 🔒 Satisfait ou remboursé 30 jours
                </p>
              </div>
            </div>
          </div>

          {/* Garanties */}
          <div className="grid md:grid-cols-3 gap-6 mb-16">
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6 text-center">
              <Shield className="w-12 h-12 text-emerald-400 mx-auto mb-4" />
              <h3 className="text-white font-bold mb-2">Satisfait ou remboursé</h3>
              <p className="text-white/70 text-sm">30 jours pour tester sans risque</p>
            </div>
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6 text-center">
              <Heart className="w-12 h-12 text-red-400 mx-auto mb-4" />
              <h3 className="text-white font-bold mb-2">Annulation facile</h3>
              <p className="text-white/70 text-sm">Résiliez en 1 clic depuis votre compte</p>
            </div>
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6 text-center">
              <Award className="w-12 h-12 text-blue-400 mx-auto mb-4" />
              <h3 className="text-white font-bold mb-2">Support premium</h3>
              <p className="text-white/70 text-sm">Équipe d'experts à votre écoute</p>
            </div>
          </div>

          {/* Témoignage rotatif */}
          <div className="bg-gradient-to-r from-white/10 to-white/5 backdrop-blur-lg rounded-3xl border border-white/20 p-8 mb-16">
            <h3 className="text-2xl font-bold text-white text-center mb-8">💬 Ce que disent nos membres PRO</h3>
            
            <div className="max-w-4xl mx-auto transition-all duration-500">
              <div className="text-center">
                <div className={`w-20 h-20 ${testimonials[currentTestimonial].avatar} rounded-full flex items-center justify-center mx-auto mb-6 text-white font-bold text-2xl`}>
                  {testimonials[currentTestimonial].name.charAt(0)}
                </div>
                
                <div className="bg-gradient-to-r from-emerald-500/20 to-blue-500/20 border border-emerald-400/50 rounded-full px-4 py-2 inline-block mb-4">
                  <span className="text-emerald-300 font-semibold text-sm">
                    {testimonials[currentTestimonial].badge}
                  </span>
                </div>
                
                <div className="flex justify-center mb-4">
                  {[...Array(testimonials[currentTestimonial].rating)].map((_, i) => (
                    <Star key={i} className="w-6 h-6 text-yellow-400 fill-current" />
                  ))}
                </div>
                
                <blockquote className="text-white/90 text-xl italic mb-6 max-w-2xl mx-auto">
                  "{testimonials[currentTestimonial].text}"
                </blockquote>
                
                <cite className="text-white/70 font-semibold">
                  — {testimonials[currentTestimonial].name}, {testimonials[currentTestimonial].location}
                </cite>
              </div>
              
              <div className="flex justify-center space-x-2 mt-8">
                {testimonials.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentTestimonial(index)}
                    className={`w-3 h-3 rounded-full transition-all ${
                      index === currentTestimonial ? 'bg-emerald-400' : 'bg-white/30'
                    }`}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* FAQ */}
          <div className="max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold text-white text-center mb-8">❓ Questions fréquentes</h2>
            
            <div className="space-y-4">
              {faqs.map((faq, index) => (
                <div key={index} className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 overflow-hidden">
                  <button
                    onClick={() => toggleFaq(index)}
                    className="w-full flex items-center justify-between p-6 text-left hover:bg-white/5 transition-colors"
                  >
                    <span className="text-white font-semibold text-lg pr-4">{faq.question}</span>
                    {showFaq[index] ? (
                      <ChevronUp className="w-5 h-5 text-white/70 flex-shrink-0" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-white/70 flex-shrink-0" />
                    )}
                  </button>
                  
                  {showFaq[index] && (
                    <div className="px-6 pb-6">
                      <p className="text-white/80 leading-relaxed">{faq.answer}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Footer CTA */}
      <div className="bg-gradient-to-r from-emerald-600 to-blue-600 py-16">
        <div className="container mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            🚀 Prêt à découvrir votre héritage familial ?
          </h2>
          <p className="text-white/90 text-lg mb-8 max-w-2xl mx-auto">
            Rejoignez les 12,847+ familles qui ont déjà découvert leurs racines avec Garméa France. 
            Offre -50% encore disponible pendant <strong>{formatTime(timeLeft)}</strong> !
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center max-w-md mx-auto">
            <button 
              onClick={() => handleUpgrade('free')}
              className="bg-white/20 hover:bg-white/30 text-white px-8 py-4 rounded-xl font-semibold transition-all border border-white/30"
            >
              Essayer gratuitement
            </button>
            <button 
              onClick={() => handleUpgrade('pro')}
              className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-white px-8 py-4 rounded-xl font-bold shadow-lg transform hover:scale-105 transition-all relative"
            >
              <span className="mr-2">👑</span>
              Passer PRO (-50%)
              <div className="absolute -top-2 -right-2 bg-red-500 text-white text-xs px-2 py-1 rounded-full animate-pulse">
                PROMO
              </div>
            </button>
          </div>
          
          <p className="text-white/70 text-sm mt-6">
            🔒 Paiement sécurisé • ✅ Satisfait ou remboursé 30 jours • ❌ Aucun engagement
          </p>
        </div>
      </div>
    </div>
  );
};

export default PricingPage;
