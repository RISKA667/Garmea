import React, { useState, useEffect } from 'react';
import { Shield, CreditCard, Lock, CheckCircle, Star, Clock, Award, ArrowLeft, Users } from 'lucide-react';

const CheckoutPage = () => {
  const [formData, setFormData] = useState({
    email: '',
    cardNumber: '',
    expiryDate: '',
    cvv: '',
    cardName: '',
    country: 'France',
    postalCode: ''
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [timeLeft, setTimeLeft] = useState(47 * 3600); // 47 heures en secondes
  const [currentTestimonial, setCurrentTestimonial] = useState(0);

  const testimonials = [
    {
      name: "Marie D.",
      location: "Lyon",
      text: "J'ai découvert que mon arrière-grand-père était comte ! Incroyable ce que Garméa a trouvé en quelques minutes.",
      rating: 5,
      avatar: "bg-gradient-to-br from-pink-400 to-red-500"
    },
    {
      name: "Jean-Pierre L.",
      location: "Marseille", 
      text: "15 générations remontées automatiquement. J'ai économisé des mois de recherche !",
      rating: 5,
      avatar: "bg-gradient-to-br from-blue-400 to-purple-500"
    },
    {
      name: "Sophie R.",
      location: "Bordeaux",
      text: "Les documents historiques sont authentiques. J'ai même trouvé des actes de mariage du 16ème siècle !",
      rating: 5,
      avatar: "bg-gradient-to-br from-emerald-400 to-blue-500"
    }
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft(prev => Math.max(0, prev - 1));
    }, 1000);

    const testimonialTimer = setInterval(() => {
      setCurrentTestimonial(prev => (prev + 1) % testimonials.length);
    }, 4000);

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

  const handleInputChange = (e) => {
    let value = e.target.value;
    
    // Formatage automatique des champs
    if (e.target.name === 'cardNumber') {
      value = value.replace(/\s/g, '').replace(/(.{4})/g, '$1 ').trim();
      if (value.length > 19) value = value.substring(0, 19);
    }
    
    if (e.target.name === 'expiryDate') {
      value = value.replace(/\D/g, '').replace(/(\d{2})(\d)/, '$1/$2');
      if (value.length > 5) value = value.substring(0, 5);
    }
    
    if (e.target.name === 'cvv') {
      value = value.replace(/\D/g, '');
      if (value.length > 3) value = value.substring(0, 3);
    }

    setFormData({ ...formData, [e.target.name]: value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsProcessing(true);
    
    // Simulation du processus de paiement
    setTimeout(() => {
      alert("🎉 Paiement réussi !\n\n✅ Votre abonnement PRO est activé\n🚀 Accès immédiat à tous vos ancêtres\n📧 Email de confirmation envoyé\n\nRedirection vers votre dashboard...");
      setIsProcessing(false);
    }, 3000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-800">
      {/* Header */}
      <header className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <button className="text-white/80 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div className="w-8 h-8 bg-gradient-to-br from-emerald-400 to-blue-400 rounded-lg flex items-center justify-center">
                <Users className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-white">Garméa France</span>
            </div>
            
            {/* Countdown d'urgence */}
            <div className="bg-gradient-to-r from-red-500/20 to-orange-500/20 border border-red-400/50 rounded-full px-4 py-2">
              <div className="flex items-center space-x-2">
                <Clock className="w-4 h-4 text-red-300 animate-pulse" />
                <span className="text-red-200 font-semibold text-sm">
                  Offre expire dans {formatTime(timeLeft)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-12">
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-3 gap-12">
            
            {/* Colonne principale - Formulaire */}
            <div className="lg:col-span-2">
              <div className="bg-white/10 backdrop-blur-lg rounded-3xl border border-white/20 p-8">
                <div className="mb-8">
                  <h1 className="text-3xl font-bold text-white mb-2">
                    Finaliser votre abonnement PRO
                  </h1>
                  <p className="text-white/70">
                    Débloquez instantanément l'accès complet à votre histoire familiale
                  </p>
                </div>

                <div className="space-y-8">
                  {/* Informations de contact */}
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                      <div className="w-6 h-6 bg-emerald-500 rounded-full flex items-center justify-center mr-3 text-sm font-bold">1</div>
                      Informations de contact
                    </h3>
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      placeholder="votre@email.com"
                      className="w-full px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white placeholder-white/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent transition-all"
                      required
                    />
                  </div>

                  {/* Informations de paiement */}
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                      <div className="w-6 h-6 bg-emerald-500 rounded-full flex items-center justify-center mr-3 text-sm font-bold">2</div>
                      Informations de paiement
                      <div className="flex items-center ml-auto space-x-2">
                        <Lock className="w-4 h-4 text-green-400" />
                        <span className="text-green-400 text-sm">Sécurisé SSL</span>
                      </div>
                    </h3>
                    
                    <div className="space-y-4">
                      <div>
                        <label className="text-white/80 text-sm mb-2 block">Numéro de carte</label>
                        <div className="relative">
                          <input
                            type="text"
                            name="cardNumber"
                            value={formData.cardNumber}
                            onChange={handleInputChange}
                            placeholder="1234 5678 9012 3456"
                            className="w-full px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white placeholder-white/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent transition-all"
                            required
                          />
                          <CreditCard className="absolute right-3 top-3 w-5 h-5 text-white/50" />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-white/80 text-sm mb-2 block">Date d'expiration</label>
                          <input
                            type="text"
                            name="expiryDate"
                            value={formData.expiryDate}
                            onChange={handleInputChange}
                            placeholder="MM/AA"
                            className="w-full px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white placeholder-white/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent transition-all"
                            required
                          />
                        </div>
                        <div>
                          <label className="text-white/80 text-sm mb-2 block">CVV</label>
                          <input
                            type="text"
                            name="cvv"
                            value={formData.cvv}
                            onChange={handleInputChange}
                            placeholder="123"
                            className="w-full px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white placeholder-white/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent transition-all"
                            required
                          />
                        </div>
                      </div>

                      <div>
                        <label className="text-white/80 text-sm mb-2 block">Nom sur la carte</label>
                        <input
                          type="text"
                          name="cardName"
                          value={formData.cardName}
                          onChange={handleInputChange}
                          placeholder="Jean Dupont"
                          className="w-full px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white placeholder-white/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent transition-all"
                          required
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-white/80 text-sm mb-2 block">Pays</label>
                          <select
                            name="country"
                            value={formData.country}
                            onChange={handleInputChange}
                            className="w-full px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent transition-all"
                          >
                            <option value="France">France</option>
                            <option value="Belgique">Belgique</option>
                            <option value="Suisse">Suisse</option>
                            <option value="Canada">Canada</option>
                          </select>
                        </div>
                        <div>
                          <label className="text-white/80 text-sm mb-2 block">Code postal</label>
                          <input
                            type="text"
                            name="postalCode"
                            value={formData.postalCode}
                            onChange={handleInputChange}
                            placeholder="75001"
                            className="w-full px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white placeholder-white/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent transition-all"
                            required
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Bouton de paiement */}
                  <button
                    onClick={handleSubmit}
                    disabled={isProcessing}
                    className="w-full bg-gradient-to-r from-emerald-500 to-blue-500 hover:from-emerald-600 hover:to-blue-600 text-white px-8 py-4 rounded-xl font-semibold text-lg shadow-lg transform hover:scale-105 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-3"
                  >
                    {isProcessing ? (
                      <>
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                        <span>Traitement en cours...</span>
                      </>
                    ) : (
                      <>
                        <Lock className="w-5 h-5" />
                        <span>Confirmer le paiement - 9,99€</span>
                      </>
                    )}
                  </button>

                  {/* Garanties de sécurité */}
                  <div className="flex items-center justify-center space-x-6 text-white/60 text-sm">
                    <div className="flex items-center space-x-2">
                      <Shield className="w-4 h-4 text-green-400" />
                      <span>Paiement sécurisé</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-green-400" />
                      <span>Satisfait ou remboursé</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Award className="w-4 h-4 text-green-400" />
                      <span>Annulable à tout moment</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Sidebar - Récapitulatif et témoignages */}
            <div className="space-y-8">
              {/* Récapitulatif de commande */}
              <div className="bg-white/10 backdrop-blur-lg rounded-3xl border border-white/20 p-6">
                <h3 className="text-xl font-bold text-white mb-6">Récapitulatif</h3>
                
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-white/80">Plan PRO - Mensuel</span>
                    <span className="text-white/60 line-through">19,99€</span>
                  </div>
                  
                  <div className="flex justify-between items-center text-emerald-300 font-semibold">
                    <span>Réduction -50%</span>
                    <span>-10,00€</span>
                  </div>
                  
                  <hr className="border-white/20" />
                  
                  <div className="flex justify-between items-center text-xl font-bold text-white">
                    <span>Total aujourd'hui</span>
                    <span>9,99€</span>
                  </div>
                  
                  <div className="text-white/60 text-sm">
                    <p>• Puis 19,99€/mois (résiliable à tout moment)</p>
                    <p>• Garantie satisfait ou remboursé 30 jours</p>
                    <p>• Accès immédiat à tous vos ancêtres</p>
                  </div>
                </div>

                {/* Ce que vous obtenez */}
                <div className="mt-6 pt-6 border-t border-white/20">
                  <h4 className="font-semibold text-white mb-4">✨ Vous débloquez :</h4>
                  <ul className="space-y-2 text-white/80 text-sm">
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      <span>Arbre généalogique interactif complet</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      <span>120+ ancêtres supplémentaires</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      <span>Documents historiques originaux</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      <span>Détection de noblesse IA</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      <span>Export PDF premium</span>
                    </li>
                  </ul>
                </div>
              </div>

              {/* Témoignages rotatifs */}
              <div className="bg-white/10 backdrop-blur-lg rounded-3xl border border-white/20 p-6">
                <h3 className="text-lg font-bold text-white mb-4">💬 Ils nous font confiance</h3>
                
                <div className="transition-all duration-500">
                  <div className="mb-4">
                    <div className="flex items-center space-x-3 mb-3">
                      <div className={`w-10 h-10 ${testimonials[currentTestimonial].avatar} rounded-full flex items-center justify-center text-white font-bold`}>
                        {testimonials[currentTestimonial].name.charAt(0)}
                      </div>
                      <div>
                        <div className="font-semibold text-white">{testimonials[currentTestimonial].name}</div>
                        <div className="text-white/60 text-sm">{testimonials[currentTestimonial].location}</div>
                      </div>
                    </div>
                    
                    <div className="flex mb-2">
                      {[...Array(testimonials[currentTestimonial].rating)].map((_, i) => (
                        <Star key={i} className="w-4 h-4 text-yellow-400 fill-current" />
                      ))}
                    </div>
                    
                    <p className="text-white/80 text-sm italic">
                      "{testimonials[currentTestimonial].text}"
                    </p>
                  </div>
                  
                  <div className="flex justify-center space-x-2">
                    {testimonials.map((_, index) => (
                      <div
                        key={index}
                        className={`w-2 h-2 rounded-full transition-all ${
                          index === currentTestimonial ? 'bg-emerald-400' : 'bg-white/30'
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </div>

              {/* Badge de confiance */}
              <div className="bg-gradient-to-r from-emerald-500/20 to-blue-500/20 border border-emerald-400/50 rounded-2xl p-4 text-center">
                <div className="flex items-center justify-center space-x-2 mb-2">
                  <Shield className="w-5 h-5 text-emerald-400" />
                  <span className="text-emerald-300 font-semibold">Paiement 100% sécurisé</span>
                </div>
                <p className="text-white/70 text-sm">
                  Vos données sont protégées par un cryptage SSL de niveau bancaire
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CheckoutPage;
