import React, { useState, useEffect } from 'react';
import { 
  Users, Download, Search, Filter, MapPin, Calendar, Crown, FileText, 
  Settings, Bell, LogOut, TreePine, Star, Award, Eye, Share, 
  ChevronDown, ChevronRight, User, Home, BarChart3, Camera, 
  Globe, Clock, Heart, BookOpen, TrendingUp
} from 'lucide-react';

const DashboardPro = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedAncestor, setSelectedAncestor] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterPeriod, setFilterPeriod] = useState('all');
  const [expandedNodes, setExpandedNodes] = useState(new Set(['root']));

  // Données simulées
  const userData = {
    name: "Marie Dubois",
    email: "marie.dubois@email.com",
    memberSince: "2024-11-15",
    totalAncestors: 247,
    generations: 12,
    documents: 89,
    countries: 8,
    nobility: 3,
    completionRate: 87
  };

  const ancestors = [
    {
      id: 1,
      name: "Jean-Baptiste Dubois",
      birth: "1847",
      death: "1923",
      place: "Lyon, France",
      relation: "Arrière-grand-père",
      profession: "Maître charpentier",
      nobility: false,
      documents: 5,
      photo: true,
      generation: 3
    },
    {
      id: 2,
      name: "Comte Henri de Rousseau",
      birth: "1823",
      death: "1889",
      place: "Château de Malmaison, France",
      relation: "Arrière-arrière-grand-père",
      profession: "Comte, Propriétaire terrien",
      nobility: true,
      documents: 12,
      photo: false,
      generation: 4
    },
    {
      id: 3,
      name: "Catherine Moreau",
      birth: "1834",
      death: "1901",
      place: "Nancy, France",
      relation: "Arrière-grand-mère",
      profession: "Institutrice",
      nobility: false,
      documents: 8,
      photo: true,
      generation: 3
    },
    {
      id: 4,
      name: "Duchesse Émilie de Montclair",
      birth: "1802",
      death: "1876",
      place: "Versailles, France",
      relation: "5x arrière-grand-mère",
      profession: "Duchesse de Montclair",
      nobility: true,
      documents: 18,
      photo: false,
      generation: 6
    },
    {
      id: 5,
      name: "Pierre Lefebvre",
      birth: "1819",
      death: "1885",
      place: "Rouen, France",
      relation: "Arrière-arrière-grand-père",
      profession: "Boulanger",
      nobility: false,
      documents: 3,
      photo: false,
      generation: 4
    }
  ];

  const documents = [
    {
      id: 1,
      name: "Acte de naissance - Jean-Baptiste Dubois",
      type: "Acte de naissance",
      date: "1847",
      location: "Lyon",
      ancestorId: 1
    },
    {
      id: 2,
      name: "Titre de noblesse - Comte de Rousseau",
      type: "Titre de noblesse",
      date: "1850",
      location: "Paris",
      ancestorId: 2
    },
    {
      id: 3,
      name: "Acte de mariage - Catherine & Pierre",
      type: "Acte de mariage",
      date: "1853",
      location: "Nancy",
      ancestorId: 3
    }
  ];

  const filteredAncestors = ancestors.filter(ancestor => {
    const matchesSearch = ancestor.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         ancestor.profession.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesPeriod = filterPeriod === 'all' || 
                         (filterPeriod === '1800s' && ancestor.birth >= '1800' && ancestor.birth < '1900') ||
                         (filterPeriod === '1700s' && ancestor.birth >= '1700' && ancestor.birth < '1800') ||
                         (filterPeriod === 'nobility' && ancestor.nobility);
    
    return matchesSearch && matchesPeriod;
  });

  const toggleNode = (nodeId) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId);
    } else {
      newExpanded.add(nodeId);
    }
    setExpandedNodes(newExpanded);
  };

  const StatCard = ({ icon: Icon, title, value, subtitle, color }) => (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 border border-white/20 hover:bg-white/15 transition-all">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-white/70 text-sm font-medium">{title}</p>
          <p className={`text-3xl font-bold ${color}`}>{value}</p>
          {subtitle && <p className="text-white/60 text-sm mt-1">{subtitle}</p>}
        </div>
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center bg-gradient-to-br ${color === 'text-emerald-400' ? 'from-emerald-400/20 to-emerald-600/20' : color === 'text-blue-400' ? 'from-blue-400/20 to-blue-600/20' : color === 'text-purple-400' ? 'from-purple-400/20 to-purple-600/20' : 'from-yellow-400/20 to-yellow-600/20'}`}>
          <Icon className={`w-6 h-6 ${color}`} />
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-800">
      {/* Header */}
      <header className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <div className="flex items-center space-x-3">
                <TreePine className="w-8 h-8 text-emerald-400" />
                <span className="text-2xl font-bold text-white">Garméa France</span>
              </div>
              
              <div className="bg-gradient-to-r from-yellow-500/20 to-orange-500/20 border border-yellow-400/50 rounded-full px-4 py-2">
                <div className="flex items-center space-x-2">
                  <Crown className="w-4 h-4 text-yellow-400" />
                  <span className="text-yellow-300 font-semibold text-sm">PRO</span>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <button className="relative p-2 rounded-xl bg-white/10 hover:bg-white/20 transition-colors">
                <Bell className="w-5 h-5 text-white" />
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full"></div>
              </button>
              
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-emerald-400 to-blue-400 rounded-full flex items-center justify-center">
                  <span className="text-white font-bold">{userData.name.charAt(0)}</span>
                </div>
                <div className="hidden md:block">
                  <p className="text-white font-medium">{userData.name}</p>
                  <p className="text-white/60 text-sm">Membre PRO</p>
                </div>
              </div>
              
              <button className="p-2 rounded-xl bg-white/10 hover:bg-white/20 transition-colors">
                <LogOut className="w-5 h-5 text-white" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        <div className="flex gap-8">
          {/* Sidebar Navigation */}
          <div className="w-64 flex-shrink-0">
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6">
              <nav className="space-y-2">
                {[
                  { id: 'overview', label: 'Vue d\'ensemble', icon: Home },
                  { id: 'tree', label: 'Arbre généalogique', icon: TreePine },
                  { id: 'ancestors', label: 'Mes ancêtres', icon: Users },
                  { id: 'documents', label: 'Documents', icon: FileText },
                  { id: 'analytics', label: 'Statistiques', icon: BarChart3 },
                  { id: 'settings', label: 'Paramètres', icon: Settings }
                ].map(item => (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all ${
                      activeTab === item.id 
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/50' 
                        : 'text-white/70 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    <item.icon className="w-5 h-5" />
                    <span className="font-medium">{item.label}</span>
                  </button>
                ))}
              </nav>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1">
            {/* Vue d'ensemble */}
            {activeTab === 'overview' && (
              <div className="space-y-8">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2">
                    Bonjour {userData.name.split(' ')[0]} ! 👋
                  </h1>
                  <p className="text-white/70">
                    Voici un aperçu de votre histoire familiale découverte avec Garméa PRO
                  </p>
                </div>

                {/* Statistiques principales */}
                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <StatCard
                    icon={Users}
                    title="Ancêtres découverts"
                    value={userData.totalAncestors}
                    subtitle="Sur 12 générations"
                    color="text-emerald-400"
                  />
                  <StatCard
                    icon={Crown}
                    title="Lignées nobles"
                    value={userData.nobility}
                    subtitle="Titres de noblesse"
                    color="text-yellow-400"
                  />
                  <StatCard
                    icon={FileText}
                    title="Documents trouvés"
                    value={userData.documents}
                    subtitle="Actes et photos"
                    color="text-blue-400"
                  />
                  <StatCard
                    icon={Globe}
                    title="Pays d'origine"
                    value={userData.countries}
                    subtitle="Répartition mondiale"
                    color="text-purple-400"
                  />
                </div>

                {/* Progrès de découverte */}
                <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xl font-bold text-white">Progression de votre arbre</h3>
                    <span className="text-emerald-400 font-semibold">{userData.completionRate}%</span>
                  </div>
                  <div className="w-full bg-white/20 rounded-full h-3 mb-4">
                    <div 
                      className="bg-gradient-to-r from-emerald-400 to-blue-400 h-3 rounded-full transition-all duration-500"
                      style={{ width: `${userData.completionRate}%` }}
                    ></div>
                  </div>
                  <p className="text-white/70 text-sm">
                    Excellent progrès ! Notre IA continue d'analyser les archives pour découvrir plus d'ancêtres.
                  </p>
                </div>

                {/* Dernières découvertes */}
                <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6">
                  <h3 className="text-xl font-bold text-white mb-6">🎉 Dernières découvertes</h3>
                  <div className="space-y-4">
                    {ancestors.slice(0, 3).map(ancestor => (
                      <div key={ancestor.id} className="flex items-center space-x-4 p-4 bg-white/10 rounded-xl">
                        <div className="w-12 h-12 bg-gradient-to-br from-emerald-400 to-blue-400 rounded-full flex items-center justify-center">
                          {ancestor.nobility ? <Crown className="w-6 h-6 text-white" /> : <User className="w-6 h-6 text-white" />}
                        </div>
                        <div className="flex-1">
                          <h4 className="text-white font-semibold">{ancestor.name}</h4>
                          <p className="text-white/70 text-sm">{ancestor.relation} • {ancestor.birth}</p>
                          <p className="text-white/60 text-sm">{ancestor.profession}</p>
                        </div>
                        {ancestor.nobility && (
                          <div className="bg-yellow-500/20 border border-yellow-400/50 rounded-full px-3 py-1">
                            <span className="text-yellow-300 text-xs font-semibold">Noble</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Arbre généalogique */}
            {activeTab === 'tree' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Arbre généalogique interactif</h1>
                    <p className="text-white/70">Explorez votre lignée familiale sur 12 générations</p>
                  </div>
                  <div className="flex space-x-3">
                    <button className="bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors">
                      <Download className="w-4 h-4" />
                      <span>Exporter PDF</span>
                    </button>
                    <button className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors">
                      <Share className="w-4 h-4" />
                      <span>Partager</span>
                    </button>
                  </div>
                </div>

                {/* Arbre simplifié */}
                <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-8">
                  <div className="text-center space-y-8">
                    {/* Vous */}
                    <div className="flex justify-center">
                      <div className="bg-gradient-to-br from-emerald-400 to-blue-400 rounded-2xl p-6 text-white max-w-xs">
                        <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
                          <User className="w-8 h-8" />
                        </div>
                        <h3 className="font-bold text-lg">{userData.name}</h3>
                        <p className="text-sm opacity-80">Vous</p>
                      </div>
                    </div>

                    {/* Parents */}
                    <div className="flex justify-center space-x-12">
                      {['Père', 'Mère'].map((parent, index) => (
                        <div key={index} className="bg-white/10 rounded-xl p-4 text-white max-w-xs">
                          <div className="w-12 h-12 bg-purple-500/30 rounded-full flex items-center justify-center mx-auto mb-3">
                            <User className="w-6 h-6" />
                          </div>
                          <h4 className="font-semibold">{parent}</h4>
                          <p className="text-xs opacity-70">Génération -1</p>
                        </div>
                      ))}
                    </div>

                    {/* Grands-parents */}
                    <div className="flex justify-center space-x-6">
                      {ancestors.filter(a => a.generation === 3).map((ancestor, index) => (
                        <button
                          key={ancestor.id}
                          onClick={() => setSelectedAncestor(ancestor)}
                          className="bg-white/10 hover:bg-white/20 rounded-xl p-4 text-white max-w-xs transition-all transform hover:scale-105"
                        >
                          <div className={`w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3 ${ancestor.nobility ? 'bg-yellow-500/30' : 'bg-emerald-500/30'}`}>
                            {ancestor.nobility ? <Crown className="w-6 h-6" /> : <User className="w-6 h-6" />}
                          </div>
                          <h4 className="font-semibold text-sm">{ancestor.name}</h4>
                          <p className="text-xs opacity-70">{ancestor.birth}</p>
                          {ancestor.nobility && (
                            <div className="mt-2 bg-yellow-500/20 rounded-full px-2 py-1">
                              <span className="text-yellow-300 text-xs">Noble</span>
                            </div>
                          )}
                        </button>
                      ))}
                    </div>

                    <div className="text-center">
                      <p className="text-white/60 text-sm">
                        + {userData.totalAncestors - 6} autres ancêtres sur {userData.generations} générations
                      </p>
                      <button className="mt-4 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white px-6 py-3 rounded-xl font-semibold transition-all">
                        Voir l'arbre complet interactif
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Liste des ancêtres */}
            {activeTab === 'ancestors' && (
              <div className="space-y-6">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2">Mes ancêtres ({filteredAncestors.length})</h1>
                  <p className="text-white/70">Explorez en détail chaque membre de votre famille</p>
                </div>

                {/* Filtres et recherche */}
                <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6">
                  <div className="flex flex-wrap gap-4">
                    <div className="flex-1 min-w-64">
                      <div className="relative">
                        <Search className="absolute left-3 top-3 w-5 h-5 text-white/50" />
                        <input
                          type="text"
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                          placeholder="Rechercher un ancêtre ou profession..."
                          className="w-full pl-10 pr-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                        />
                      </div>
                    </div>
                    
                    <select 
                      value={filterPeriod}
                      onChange={(e) => setFilterPeriod(e.target.value)}
                      className="px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white focus:outline-none focus:ring-2 focus:ring-emerald-400"
                    >
                      <option value="all">Toutes les époques</option>
                      <option value="1800s">XIXe siècle</option>
                      <option value="1700s">XVIIIe siècle</option>
                      <option value="nobility">Noblesse uniquement</option>
                    </select>
                  </div>
                </div>

                {/* Liste des ancêtres */}
                <div className="grid md:grid-cols-2 gap-6">
                  {filteredAncestors.map(ancestor => (
                    <div key={ancestor.id} className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6 hover:bg-white/15 transition-all">
                      <div className="flex items-start space-x-4">
                        <div className={`w-16 h-16 rounded-2xl flex items-center justify-center ${ancestor.nobility ? 'bg-gradient-to-br from-yellow-400 to-orange-500' : 'bg-gradient-to-br from-emerald-400 to-blue-400'}`}>
                          {ancestor.nobility ? <Crown className="w-8 h-8 text-white" /> : <User className="w-8 h-8 text-white" />}
                        </div>
                        
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-2">
                            <h3 className="text-lg font-bold text-white">{ancestor.name}</h3>
                            {ancestor.nobility && (
                              <div className="bg-yellow-500/20 border border-yellow-400/50 rounded-full px-2 py-1">
                                <span className="text-yellow-300 text-xs font-semibold">Noble</span>
                              </div>
                            )}
                          </div>
                          
                          <p className="text-emerald-400 font-medium mb-2">{ancestor.relation}</p>
                          
                          <div className="space-y-1 text-white/70 text-sm">
                            <div className="flex items-center space-x-2">
                              <Calendar className="w-4 h-4" />
                              <span>{ancestor.birth} - {ancestor.death}</span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <MapPin className="w-4 h-4" />
                              <span>{ancestor.place}</span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <User className="w-4 h-4" />
                              <span>{ancestor.profession}</span>
                            </div>
                          </div>
                          
                          <div className="flex items-center justify-between mt-4">
                            <div className="flex items-center space-x-4 text-white/60 text-sm">
                              <div className="flex items-center space-x-1">
                                <FileText className="w-4 h-4" />
                                <span>{ancestor.documents} docs</span>
                              </div>
                              {ancestor.photo && (
                                <div className="flex items-center space-x-1">
                                  <Camera className="w-4 h-4" />
                                  <span>Photo</span>
                                </div>
                              )}
                            </div>
                            
                            <button 
                              onClick={() => setSelectedAncestor(ancestor)}
                              className="bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm transition-colors"
                            >
                              Voir détails
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Documents */}
            {activeTab === 'documents' && (
              <div className="space-y-6">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2">Documents historiques ({documents.length})</h1>
                  <p className="text-white/70">Actes, photos et documents authentiques de vos ancêtres</p>
                </div>

                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {documents.map(doc => (
                    <div key={doc.id} className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6 hover:bg-white/15 transition-all">
                      <div className="flex items-center space-x-3 mb-4">
                        <div className="w-12 h-12 bg-gradient-to-br from-emerald-400 to-blue-400 rounded-xl flex items-center justify-center">
                          <FileText className="w-6 h-6 text-white" />
                        </div>
                        <div className="flex-1">
                          <h3 className="font-semibold text-white">{doc.name}</h3>
                          <p className="text-white/60 text-sm">{doc.type}</p>
                        </div>
                      </div>
                      
                      <div className="space-y-2 text-white/70 text-sm mb-4">
                        <div className="flex items-center space-x-2">
                          <Calendar className="w-4 h-4" />
                          <span>{doc.date}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <MapPin className="w-4 h-4" />
                          <span>{doc.location}</span>
                        </div>
                      </div>
                      
                      <div className="flex space-x-2">
                        <button className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white py-2 px-4 rounded-lg text-sm transition-colors flex items-center justify-center space-x-2">
                          <Eye className="w-4 h-4" />
                          <span>Voir</span>
                        </button>
                        <button className="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded-lg text-sm transition-colors">
                          <Download className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Statistiques */}
            {activeTab === 'analytics' && (
              <div className="space-y-6">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2">Statistiques familiales</h1>
                  <p className="text-white/70">Analyse détaillée de votre héritage généalogique</p>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  {/* Répartition par siècles */}
                  <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6">
                    <h3 className="text-xl font-bold text-white mb-6">Répartition par siècles</h3>
                    <div className="space-y-4">
                      {[
                        { period: 'XVIe siècle (1500-1599)', count: 8, percentage: 15 },
                        { period: 'XVIIe siècle (1600-1699)', count: 23, percentage: 35 },
                        { period: 'XVIIIe siècle (1700-1799)', count: 45, percentage: 65 },
                        { period: 'XIXe siècle (1800-1899)', count: 89, percentage: 90 }
                      ].map((item, index) => (
                        <div key={index}>
                          <div className="flex justify-between text-white mb-1">
                            <span className="text-sm">{item.period}</span>
                            <span className="font-semibold">{item.count}</span>
                          </div>
                          <div className="w-full bg-white/20 rounded-full h-2">
                            <div 
                              className="bg-gradient-to-r from-emerald-400 to-blue-400 h-2 rounded-full transition-all duration-500"
                              style={{ width: `${item.percentage}%` }}
                            ></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Répartition géographique */}
                  <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6">
                    <h3 className="text-xl font-bold text-white mb-6">Origines géographiques</h3>
                    <div className="space-y-3">
                      {[
                        { country: 'France', count: 189, flag: '🇫🇷' },
                        { country: 'Allemagne', count: 23, flag: '🇩🇪' },
                        { country: 'Espagne', count: 15, flag: '🇪🇸' },
                        { country: 'Italie', count: 12, flag: '🇮🇹' },
                        { country: 'Belgique', count: 8, flag: '🇧🇪' }
                      ].map((item, index) => (
                        <div key={index} className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            <span className="text-2xl">{item.flag}</span>
                            <span className="text-white">{item.country}</span>
                          </div>
                          <div className="text-white font-semibold">{item.count}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Professions les plus courantes */}
                <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6">
                  <h3 className="text-xl font-bold text-white mb-6">Professions ancestrales</h3>
                  <div className="grid md:grid-cols-3 gap-4">
                    {[
                      { profession: 'Agriculteurs', count: 67, icon: '🌾' },
                      { profession: 'Artisans', count: 45, icon: '🔨' },
                      { profession: 'Commerçants', count: 32, icon: '🏪' },
                      { profession: 'Nobles', count: 18, icon: '👑' },
                      { profession: 'Religieux', count: 15, icon: '⛪' },
                      { profession: 'Militaires', count: 12, icon: '⚔️' }
                    ].map((item, index) => (
                      <div key={index} className="bg-white/10 rounded-xl p-4 text-center">
                        <div className="text-3xl mb-2">{item.icon}</div>
                        <div className="text-white font-semibold">{item.profession}</div>
                        <div className="text-emerald-400 font-bold text-xl">{item.count}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Paramètres */}
            {activeTab === 'settings' && (
              <div className="space-y-6">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2">Paramètres du compte</h1>
                  <p className="text-white/70">Gérez votre abonnement et vos préférences</p>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6">
                    <h3 className="text-xl font-bold text-white mb-4">Informations du compte</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="text-white/80 text-sm">Nom</label>
                        <input 
                          type="text" 
                          value={userData.name}
                          className="w-full mt-1 px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white"
                        />
                      </div>
                      <div>
                        <label className="text-white/80 text-sm">Email</label>
                        <input 
                          type="email" 
                          value={userData.email}
                          className="w-full mt-1 px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-white"
                        />
                      </div>
                      <button className="bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-3 rounded-xl transition-colors">
                        Sauvegarder
                      </button>
                    </div>
                  </div>

                  <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6">
                    <h3 className="text-xl font-bold text-white mb-4">Abonnement PRO</h3>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-white">Status</span>
                        <div className="bg-emerald-500/20 border border-emerald-400/50 rounded-full px-3 py-1">
                          <span className="text-emerald-300 text-sm font-semibold">Actif</span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-white">Prix</span>
                        <span className="text-white font-semibold">9,99€/mois</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-white">Prochain paiement</span>
                        <span className="text-white/70">15 décembre 2024</span>
                      </div>
                      <div className="pt-4 border-t border-white/20">
                        <button className="w-full bg-red-500/20 hover:bg-red-500/30 border border-red-400/50 text-red-300 px-6 py-3 rounded-xl transition-colors">
                          Annuler l'abonnement
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modal de détail d'ancêtre */}
      {selectedAncestor && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white/10 backdrop-blur-lg rounded-3xl border border-white/20 shadow-2xl max-w-2xl w-full mx-4 animate-fadeIn">
            <div className="p-8">
              <div className="flex items-start justify-between mb-6">
                <div className="flex items-center space-x-4">
                  <div className={`w-16 h-16 rounded-2xl flex items-center justify-center ${selectedAncestor.nobility ? 'bg-gradient-to-br from-yellow-400 to-orange-500' : 'bg-gradient-to-br from-emerald-400 to-blue-400'}`}>
                    {selectedAncestor.nobility ? <Crown className="w-8 h-8 text-white" /> : <User className="w-8 h-8 text-white" />}
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white">{selectedAncestor.name}</h2>
                    <p className="text-emerald-400 font-medium">{selectedAncestor.relation}</p>
                  </div>
                </div>
                <button 
                  onClick={() => setSelectedAncestor(null)}
                  className="text-white/60 hover:text-white text-2xl"
                >
                  ×
                </button>
              </div>

              <div className="grid md:grid-cols-2 gap-6 mb-6">
                <div className="space-y-4">
                  <div>
                    <h3 className="text-white font-semibold mb-2">Informations générales</h3>
                    <div className="space-y-2 text-white/70">
                      <div className="flex items-center space-x-2">
                        <Calendar className="w-4 h-4" />
                        <span>Né en {selectedAncestor.birth}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <MapPin className="w-4 h-4" />
                        <span>{selectedAncestor.place}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <User className="w-4 h-4" />
                        <span>{selectedAncestor.profession}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <h3 className="text-white font-semibold mb-2">Documents disponibles</h3>
                    <div className="flex items-center space-x-4 text-white/70">
                      <div className="flex items-center space-x-1">
                        <FileText className="w-4 h-4" />
                        <span>{selectedAncestor.documents} documents</span>
                      </div>
                      {selectedAncestor.photo && (
                        <div className="flex items-center space-x-1">
                          <Camera className="w-4 h-4" />
                          <span>Photo disponible</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex space-x-4">
                <button className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-3 rounded-xl transition-colors">
                  Voir les documents
                </button>
                <button className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-xl transition-colors">
                  Partager
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

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

export default DashboardPro;
