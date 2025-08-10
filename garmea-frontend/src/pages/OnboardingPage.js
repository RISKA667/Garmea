import React, { useState } from 'react';
import { 
  User, 
  FileText, 
  Search, 
  TreePine, 
  CheckCircle, 
  ArrowRight, 
  ArrowLeft,
  Upload,
  MapPin,
  Calendar,
  Users,
  Star
} from 'lucide-react';

const OnboardingPage = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    birthDate: '',
    birthPlace: '',
    familyMembers: [],
    documents: []
  });

  const steps = [
    {
      id: 0,
      title: 'Bienvenue sur Garméa',
      subtitle: 'Découvrez vos ancêtres en quelques étapes simples',
      icon: <Star className="w-12 h-12 text-primary-500" />,
      content: (
        <div className="text-center space-y-6">
          <div className="bg-gradient-to-r from-primary-500 to-secondary-500 p-8 rounded-2xl text-white">
            <h2 className="text-3xl font-bold mb-4">🎯 Commençons votre voyage généalogique</h2>
            <p className="text-lg opacity-90">
              Garméa utilise l'intelligence artificielle pour analyser vos documents 
              et reconstituer votre arbre généalogique automatiquement.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
            <div className="bg-white p-6 rounded-xl shadow-soft border border-gray-100">
              <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
                <Upload className="w-6 h-6 text-primary-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">1. Uploadez vos documents</h3>
              <p className="text-gray-600 text-sm">Actes de naissance, mariage, décès, photos anciennes...</p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-soft border border-gray-100">
              <div className="w-12 h-12 bg-secondary-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
                <Search className="w-6 h-6 text-secondary-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">2. Analyse automatique</h3>
              <p className="text-gray-600 text-sm">Notre IA extrait et analyse toutes les informations</p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-soft border border-gray-100">
              <div className="w-12 h-12 bg-accent-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
                <TreePine className="w-6 h-6 text-accent-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">3. Arbre généalogique</h3>
              <p className="text-gray-600 text-sm">Visualisez votre histoire familiale interactive</p>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 1,
      title: 'Vos informations personnelles',
      subtitle: 'Commençons par vos données de base',
      icon: <User className="w-12 h-12 text-primary-500" />,
      content: (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Prénom *
              </label>
              <input
                type="text"
                value={formData.firstName}
                onChange={(e) => setFormData({...formData, firstName: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                placeholder="Votre prénom"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nom de famille *
              </label>
              <input
                type="text"
                value={formData.lastName}
                onChange={(e) => setFormData({...formData, lastName: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                placeholder="Votre nom de famille"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Date de naissance
              </label>
              <input
                type="date"
                value={formData.birthDate}
                onChange={(e) => setFormData({...formData, birthDate: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Lieu de naissance
              </label>
              <input
                type="text"
                value={formData.birthPlace}
                onChange={(e) => setFormData({...formData, birthPlace: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                placeholder="Ville, Pays"
              />
            </div>
          </div>
          
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <CheckCircle className="w-5 h-5 text-blue-600" />
              </div>
              <div className="ml-3">
                <p className="text-sm text-blue-800">
                  <strong>Confidentialité garantie :</strong> Vos données personnelles sont protégées 
                  et ne seront utilisées que pour votre recherche généalogique.
                </p>
              </div>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 2,
      title: 'Membres de votre famille',
      subtitle: 'Ajoutez les personnes que vous connaissez déjà',
      icon: <Users className="w-12 h-12 text-primary-500" />,
      content: (
        <div className="space-y-6">
          <div className="bg-gray-50 p-6 rounded-lg">
            <h3 className="font-semibold text-gray-900 mb-4">Ajouter un membre de famille</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <input
                type="text"
                placeholder="Prénom"
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              <input
                type="text"
                placeholder="Nom"
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              <select className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent">
                <option>Relation</option>
                <option>Père</option>
                <option>Mère</option>
                <option>Frère</option>
                <option>Sœur</option>
                <option>Grand-père</option>
                <option>Grand-mère</option>
                <option>Oncle</option>
                <option>Tante</option>
              </select>
            </div>
            
            <button className="bg-primary-500 text-white px-4 py-2 rounded-lg hover:bg-primary-600 transition-colors">
              Ajouter
            </button>
          </div>
          
          <div className="space-y-3">
            <h3 className="font-semibold text-gray-900">Membres ajoutés</h3>
            
            <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">Jean Dupont</p>
                    <p className="text-sm text-gray-500">Père</p>
                  </div>
                </div>
                <button className="text-red-500 hover:text-red-700">
                  Supprimer
                </button>
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-secondary-100 rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-secondary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">Marie Dupont</p>
                    <p className="text-sm text-gray-500">Mère</p>
                  </div>
                </div>
                <button className="text-red-500 hover:text-red-700">
                  Supprimer
                </button>
              </div>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 3,
      title: 'Uploadez vos documents',
      subtitle: 'Plus vous ajoutez de documents, plus votre arbre sera complet',
      icon: <FileText className="w-12 h-12 text-primary-500" />,
      content: (
        <div className="space-y-6">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-primary-400 transition-colors">
            <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Glissez-déposez vos documents ici
            </h3>
            <p className="text-gray-500 mb-4">
              ou cliquez pour sélectionner des fichiers
            </p>
            <button className="bg-primary-500 text-white px-6 py-3 rounded-lg hover:bg-primary-600 transition-colors">
              Sélectionner des fichiers
            </button>
            <p className="text-sm text-gray-400 mt-4">
              PDF, JPG, PNG jusqu'à 10MB par fichier
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-blue-50 p-6 rounded-lg">
              <h4 className="font-semibold text-blue-900 mb-3">📋 Documents recommandés</h4>
              <ul className="space-y-2 text-sm text-blue-800">
                <li>• Actes de naissance</li>
                <li>• Actes de mariage</li>
                <li>• Actes de décès</li>
                <li>• Livrets de famille</li>
                <li>• Photos anciennes</li>
                <li>• Certificats de baptême</li>
              </ul>
            </div>
            
            <div className="bg-green-50 p-6 rounded-lg">
              <h4 className="font-semibold text-green-900 mb-3">✅ Documents uploadés</h4>
              <div className="space-y-2">
                <div className="flex items-center justify-between bg-white p-3 rounded">
                  <span className="text-sm text-green-800">acte_naissance.pdf</span>
                  <CheckCircle className="w-4 h-4 text-green-600" />
                </div>
                <div className="flex items-center justify-between bg-white p-3 rounded">
                  <span className="text-sm text-green-800">photo_famille.jpg</span>
                  <CheckCircle className="w-4 h-4 text-green-600" />
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 4,
      title: 'Finalisation',
      subtitle: 'Votre profil est presque prêt !',
      icon: <CheckCircle className="w-12 h-12 text-green-500" />,
      content: (
        <div className="text-center space-y-8">
          <div className="bg-gradient-to-r from-green-500 to-blue-500 p-8 rounded-2xl text-white">
            <CheckCircle className="w-16 h-16 mx-auto mb-4" />
            <h2 className="text-3xl font-bold mb-4">🎉 Félicitations !</h2>
            <p className="text-lg opacity-90">
              Votre profil Garméa est maintenant configuré. 
              Nous allons commencer l'analyse de vos documents.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-xl shadow-soft border border-gray-100">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
                <Search className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">Analyse en cours</h3>
              <p className="text-gray-600 text-sm">Nos algorithmes analysent vos documents</p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-soft border border-gray-100">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
                <TreePine className="w-6 h-6 text-green-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">Arbre généalogique</h3>
              <p className="text-gray-600 text-sm">Construction de votre arbre familial</p>
            </div>
            
            <div className="bg-white p-6 rounded-xl shadow-soft border border-gray-100">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
                <Star className="w-6 h-6 text-purple-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">Découvertes</h3>
              <p className="text-gray-600 text-sm">Révélation de vos ancêtres cachés</p>
            </div>
          </div>
          
          <div className="bg-yellow-50 p-6 rounded-lg">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <Calendar className="w-5 h-5 text-yellow-600" />
              </div>
              <div className="ml-3">
                <p className="text-sm text-yellow-800">
                  <strong>Durée estimée :</strong> L'analyse complète prendra entre 24h et 48h. 
                  Vous recevrez une notification dès que vos résultats seront prêts.
                </p>
              </div>
            </div>
          </div>
        </div>
      )
    }
  ];

  const nextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const currentStepData = steps[currentStep];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Garméa</h1>
          <p className="text-gray-600">Votre assistant généalogique intelligent</p>
        </div>

        {/* Progress Bar */}
        <div className="max-w-4xl mx-auto mb-8">
          <div className="flex items-center justify-between mb-4">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium ${
                  index <= currentStep 
                    ? 'bg-primary-500 text-white' 
                    : 'bg-gray-200 text-gray-500'
                }`}>
                  {index < currentStep ? <CheckCircle className="w-5 h-5" /> : index + 1}
                </div>
                {index < steps.length - 1 && (
                  <div className={`w-16 h-1 mx-2 ${
                    index < currentStep ? 'bg-primary-500' : 'bg-gray-200'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-2xl shadow-large p-8">
            {/* Step Header */}
            <div className="text-center mb-8">
              <div className="flex justify-center mb-4">
                {currentStepData.icon}
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">
                {currentStepData.title}
              </h2>
              <p className="text-lg text-gray-600">
                {currentStepData.subtitle}
              </p>
            </div>

            {/* Step Content */}
            <div className="mb-8">
              {currentStepData.content}
            </div>

            {/* Navigation */}
            <div className="flex justify-between items-center pt-6 border-t border-gray-200">
              <button
                onClick={prevStep}
                disabled={currentStep === 0}
                className={`flex items-center px-6 py-3 rounded-lg font-medium transition-colors ${
                  currentStep === 0
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Précédent
              </button>

              <div className="text-sm text-gray-500">
                Étape {currentStep + 1} sur {steps.length}
              </div>

              <button
                onClick={nextStep}
                className={`flex items-center px-6 py-3 rounded-lg font-medium transition-colors ${
                  currentStep === steps.length - 1
                    ? 'bg-green-500 text-white hover:bg-green-600'
                    : 'bg-primary-500 text-white hover:bg-primary-600'
                }`}
              >
                {currentStep === steps.length - 1 ? (
                  <>
                    Terminer
                    <CheckCircle className="w-4 h-4 ml-2" />
                  </>
                ) : (
                  <>
                    Suivant
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OnboardingPage;
