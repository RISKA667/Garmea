import React, { useState, useEffect, useRef } from 'react';
import { 
  Users, Crown, Search, Filter, Download, Share, ZoomIn, ZoomOut, 
  RotateCcw, MapPin, Calendar, User, Camera, FileText, Star, 
  ChevronLeft, ChevronRight, TreePine, Settings, Award, Globe,
  Heart, BookOpen, Clock, TrendingUp, Eye, Maximize, Home
} from 'lucide-react';

const FamilyTreeInteractive = () => {
  const [selectedAncestor, setSelectedAncestor] = useState(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [currentGeneration, setCurrentGeneration] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeFilter, setActiveFilter] = useState('all');
  const [showTimeline, setShowTimeline] = useState(true);
  const [treeView, setTreeView] = useState('traditional'); // 'traditional', 'circular', 'timeline'
  const treeRef = useRef(null);

  // Données des ancêtres organisées par génération
  const ancestorsData = {
    0: [
      {
        id: 'user',
        name: 'Marie Dubois',
        birth: '1985',
        place: 'Lyon, France',
        relation: 'Vous',
        profession: 'Ingénieure',
        nobility: false,
        generation: 0,
        x: 400,
        y: 50,
        photo: true,
        documents: 0
      }
    ],
    1: [
      {
        id: 'father',
        name: 'Jean Dubois',
        birth: '1960',
        death: '2020',
        place: 'Lyon, France',
        relation: 'Père',
        profession: 'Professeur',
        nobility: false,
        generation: 1,
        x: 300,
        y: 150,
        photo: true,
        documents: 5,
        children: ['user']
      },
      {
        id: 'mother',
        name: 'Claire Martin',
        birth: '1962',
        place: 'Marseille, France',
        relation: 'Mère',
        profession: 'Médecin',
        nobility: false,
        generation: 1,
        x: 500,
        y: 150,
        photo: true,
        documents: 3,
        children: ['user']
      }
    ],
    2: [
      {
        id: 'grandpa1',
        name: 'Henri Dubois',
        birth: '1935',
        death: '2010',
        place: 'Lyon, France',
        relation: 'Grand-père paternel',
        profession: 'Charpentier',
        nobility: false,
        generation: 2,
        x: 200,
        y: 250,
        photo: true,
        documents: 8,
        children: ['father']
      },
      {
        id: 'grandma1',
        name: 'Marie Rousseau',
        birth: '1938',
        death: '2015',
        place: 'Lyon, France',
        relation: 'Grand-mère paternelle',
        profession: 'Couturière',
        nobility: false,
        generation: 2,
        x: 400,
        y: 250,
        photo: true,
        documents: 6,
        children: ['father']
      },
      {
        id: 'grandpa2',
        name: 'Pierre Martin',
        birth: '1940',
        place: 'Marseille, France',
        relation: 'Grand-père maternel',
        profession: 'Capitaine de marine',
        nobility: false,
        generation: 2,
        x: 600,
        y: 250,
        photo: false,
        documents: 12,
        children: ['mother']
      },
      {
        id: 'grandma2',
        name: 'Comtesse Élisabeth de Montclair',
        birth: '1942',
        place: 'Nice, France',
        relation: 'Grand-mère maternelle',
        profession: 'Comtesse',
        nobility: true,
        generation: 2,
        x: 800,
        y: 250,
        photo: false,
        documents: 15,
        children: ['mother']
      }
    ],
    3: [
      {
        id: 'ggrandpa1',
        name: 'Jean-Baptiste Dubois',
        birth: '1910',
        death: '1990',
        place: 'Lyon, France',
        relation: 'Arrière-grand-père',
        profession: 'Maître charpentier',
        nobility: false,
        generation: 3,
        x: 100,
        y: 350,
        photo: false,
        documents: 4,
        children: ['grandpa1']
      },
      {
        id: 'ggrandma1',
        name: 'Catherine Moreau',
        birth: '1912',
        death: '1995',
        place: 'Lyon, France',
        relation: 'Arrière-grand-mère',
        profession: 'Institutrice',
        nobility: false,
        generation: 3,
        x: 300,
        y: 350,
        photo: true,
        documents: 7,
        children: ['grandpa1']
      },
      {
        id: 'duke',
        name: 'Duc Alexandre de Montclair',
        birth: '1915',
        death: '1980',
        place: 'Château de Montclair, France',
        relation: 'Arrière-grand-père',
        profession: 'Duc de Montclair',
        nobility: true,
        generation: 3,
        x: 700,
        y: 350,
        photo: false,
        documents: 23,
        children: ['grandma2']
      },
      {
        id: 'duchess',
        name: 'Duchesse Marguerite de Bourbon',
        birth: '1918',
        death: '1985',
        place: 'Versailles, France',
        relation: 'Arrière-grand-mère',
        profession: 'Duchesse de Bourbon',
        nobility: true,
        generation: 3,
        x: 900,
        y: 350,
        photo: false,
        documents: 31,
        children: ['grandma2']
      }
    ]
  };

  const allAncestors = Object.values(ancestorsData).flat();
  const maxGeneration = Math.max(...allAncestors.map(a => a.generation));

  const filteredAncestors = allAncestors.filter(ancestor => {
    const matchesSearch = ancestor.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         ancestor.profession.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesFilter = activeFilter === 'all' || 
                         (activeFilter === 'nobility' && ancestor.nobility) ||
                         (activeFilter === 'photos' && ancestor.photo) ||
                         (activeFilter === 'documents' && ancestor.documents > 0);
    
    return matchesSearch && matchesFilter;
  });

  const handleZoomIn = () => setZoomLevel(prev => Math.min(prev + 0.2, 3));
  const handleZoomOut = () => setZoomLevel(prev => Math.max(prev - 0.2, 0.5));
  const handleReset = () => {
    setZoomLevel(1);
    if (treeRef.current) {
      treeRef.current.scrollTo({ top: 0, left: 0, behavior: 'smooth' });
    }
  };

  const handleExport = () => {
    alert("📄 Export PDF en cours...\n\n✅ Arbre généalogique complet\n📊 Statistiques familiales\n🏰 Blasons et titres de noblesse\n📱 Format A3 haute qualité\n\n⏳ Téléchargement dans quelques secondes...");
  };

  const handleShare = () => {
    alert("📤 Partage de votre arbre...\n\n🔗 Lien privé généré\n👨‍👩‍👧‍👦 Partage familial sécurisé\n⚡ Accès en lecture seule\n🎯 Valable 30 jours\n\n📋 Lien copié dans le presse-papier !");
  };

  const StatCard = ({ icon: Icon, title, value, color = "text-emerald-400" }) => (
    <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
      <div className="flex items-center space-x-3">
        <Icon className={`w-5 h-5 ${color}`} />
        <div>
          <p className="text-white/70 text-sm">{title}</p>
          <p className={`font-bold ${color}`}>{value}</p>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-800">
      {/* Header */}
      <header className="border-b border-white/10 bg-black/20 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <div className="flex items-center space-x-3">
                <button className="text-white/80 hover:text-white transition-colors">
                  <Home className="w-5 h-5" />
                </button>
                <TreePine className="w-8 h-8 text-emerald-400" />
                <div>
                  <span className="text-xl font-bold text-white">Arbre Généalogique</span>
                  <div className="text-sm text-white/60">Marie Dubois - 247 ancêtres découverts</div>
                </div>
              </div>
              
              <div className="bg-gradient-to-r from-yellow-500/20 to-orange-500/20 border border-yellow-400/50 rounded-full px-4 py-2">
                <div className="flex items-center space-x-2">
                  <Crown className="w-4 h-4 text-yellow-400" />
                  <span className="text-yellow-300 font-semibold text-sm">3 Lignées Nobles</span>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <button 
                onClick={handleExport}
                className="bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
              >
                <Download className="w-4 h-4" />
                <span>Export PDF</span>
              </button>
              <button 
                onClick={handleShare}
                className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
              >
                <Share className="w-4 h-4" />
                <span>Partager</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex h-screen">
        {/* Sidebar */}
        <div className="w-80 bg-black/20 backdrop-blur-sm border-r border-white/10 p-6 overflow-y-auto">
          {/* Contrôles de navigation */}
          <div className="mb-6">
            <h3 className="text-white font-bold mb-4 flex items-center">
              <Settings className="w-5 h-5 mr-2" />
              Navigation
            </h3>
            <div className="grid grid-cols-3 gap-2 mb-4">
              <button 
                onClick={handleZoomIn}
                className="bg-white/10 hover:bg-white/20 text-white p-2 rounded-lg transition-colors flex items-center justify-center"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button 
                onClick={handleZoomOut}
                className="bg-white/10 hover:bg-white/20 text-white p-2 rounded-lg transition-colors flex items-center justify-center"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button 
                onClick={handleReset}
                className="bg-white/10 hover:bg-white/20 text-white p-2 rounded-lg transition-colors flex items-center justify-center"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
            <div className="text-center text-white/60 text-sm mb-4">
              Zoom: {Math.round(zoomLevel * 100)}%
            </div>
          </div>

          {/* Recherche et filtres */}
          <div className="mb-6">
            <h3 className="text-white font-bold mb-4 flex items-center">
              <Search className="w-5 h-5 mr-2" />
              Recherche
            </h3>
            <div className="relative mb-4">
              <Search className="absolute left-3 top-3 w-4 h-4 text-white/50" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Rechercher un ancêtre..."
                className="w-full pl-10 pr-4 py-2 rounded-lg bg-white/20 border border-white/30 text-white placeholder-white/50 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
              />
            </div>
            
            <div className="space-y-2">
              {[
                { id: 'all', label: 'Tous les ancêtres', count: allAncestors.length },
                { id: 'nobility', label: 'Noblesse', count: allAncestors.filter(a => a.nobility).length },
                { id: 'photos', label: 'Avec photos', count: allAncestors.filter(a => a.photo).length },
                { id: 'documents', label: 'Avec documents', count: allAncestors.filter(a => a.documents > 0).length }
              ].map(filter => (
                <button
                  key={filter.id}
                  onClick={() => setActiveFilter(filter.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                    activeFilter === filter.id 
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/50' 
                      : 'bg-white/10 text-white/70 hover:bg-white/20'
                  }`}
                >
                  <span>{filter.label}</span>
                  <span className="bg-white/20 px-2 py-1 rounded-full text-xs">{filter.count}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Statistiques */}
          <div className="mb-6">
            <h3 className="text-white font-bold mb-4 flex items-center">
              <TrendingUp className="w-5 h-5 mr-2" />
              Statistiques
            </h3>
            <div className="space-y-3">
              <StatCard icon={Users} title="Total ancêtres" value="247" />
              <StatCard icon={Crown} title="Lignées nobles" value="3" color="text-yellow-400" />
              <StatCard icon={Calendar} title="Générations" value="12" color="text-blue-400" />
              <StatCard icon={FileText} title="Documents" value="159" color="text-purple-400" />
              <StatCard icon={Globe} title="Pays" value="8" color="text-emerald-400" />
            </div>
          </div>

          {/* Navigation par génération */}
          <div className="mb-6">
            <h3 className="text-white font-bold mb-4 flex items-center">
              <Clock className="w-5 h-5 mr-2" />
              Générations
            </h3>
            <div className="space-y-2">
              {Array.from({ length: maxGeneration + 1 }, (_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentGeneration(i)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                    currentGeneration === i 
                      ? 'bg-blue-500/20 text-blue-300 border border-blue-400/50' 
                      : 'bg-white/10 text-white/70 hover:bg-white/20'
                  }`}
                >
                  <span>
                    {i === 0 ? 'Vous' : 
                     i === 1 ? 'Parents' : 
                     i === 2 ? 'Grands-parents' : 
                     `Génération -${i}`}
                  </span>
                  <span className="bg-white/20 px-2 py-1 rounded-full text-xs">
                    {ancestorsData[i]?.length || 0}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Timeline historique */}
          {showTimeline && (
            <div>
              <h3 className="text-white font-bold mb-4 flex items-center">
                <BookOpen className="w-5 h-5 mr-2" />
                Timeline
              </h3>
              <div className="space-y-3">
                {[
                  { period: '1500-1600', count: 8, color: 'bg-red-500' },
                  { period: '1600-1700', count: 23, color: 'bg-orange-500' },
                  { period: '1700-1800', count: 45, color: 'bg-yellow-500' },
                  { period: '1800-1900', count: 89, color: 'bg-green-500' },
                  { period: '1900-2000', count: 82, color: 'bg-blue-500' }
                ].map((era, index) => (
                  <div key={index} className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full ${era.color}`}></div>
                    <div className="flex-1">
                      <div className="text-white text-sm">{era.period}</div>
                      <div className="text-white/60 text-xs">{era.count} ancêtres</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Zone principale de l'arbre */}
        <div className="flex-1 relative overflow-hidden">
          <div 
            ref={treeRef}
            className="w-full h-full overflow-auto"
            style={{ 
              transform: `scale(${zoomLevel})`,
              transformOrigin: 'top left',
              transition: 'transform 0.3s ease'
            }}
          >
            <div className="relative" style={{ width: '1200px', height: '800px' }}>
              {/* Lignes de connexion SVG */}
              <svg className="absolute inset-0 w-full h-full pointer-events-none">
                <defs>
                  <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
                    <path d="M 50 0 L 0 0 0 50" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="1"/>
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#grid)" />
                
                {/* Lines connecting family members */}
                {allAncestors.map(ancestor => {
                  if (ancestor.children) {
                    return ancestor.children.map(childId => {
                      const child = allAncestors.find(a => a.id === childId);
                      if (!child) return null;
                      
                      return (
                        <line
                          key={`${ancestor.id}-${childId}`}
                          x1={ancestor.x + 60}
                          y1={ancestor.y + 80}
                          x2={child.x + 60}
                          y2={child.y + 20}
                          stroke="rgba(255,255,255,0.3)"
                          strokeWidth="2"
                          strokeDasharray={ancestor.nobility ? "5,5" : "none"}
                        />
                      );
                    });
                  }
                  return null;
                })}
              </svg>

              {/* Cartes des ancêtres */}
              {filteredAncestors.map(ancestor => (
                <div
                  key={ancestor.id}
                  className={`absolute cursor-pointer transform transition-all duration-300 hover:scale-110 hover:z-20 ${
                    selectedAncestor?.id === ancestor.id ? 'scale-110 z-20' : ''
                  }`}
                  style={{
                    left: `${ancestor.x}px`,
                    top: `${ancestor.y}px`,
                    width: '120px'
                  }}
                  onClick={() => setSelectedAncestor(ancestor)}
                >
                  <div className={`rounded-2xl p-4 border-2 shadow-lg backdrop-blur-sm ${
                    ancestor.nobility 
                      ? 'bg-gradient-to-br from-yellow-500/20 to-orange-500/20 border-yellow-400/50' 
                      : 'bg-white/10 border-white/20'
                  }`}>
                    {/* Photo/Avatar */}
                    <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-3 ${
                      ancestor.nobility 
                        ? 'bg-gradient-to-br from-yellow-400 to-orange-500' 
                        : 'bg-gradient-to-br from-emerald-400 to-blue-400'
                    }`}>
                      {ancestor.nobility ? (
                        <Crown className="w-8 h-8 text-white" />
                      ) : ancestor.photo ? (
                        <Camera className="w-8 h-8 text-white" />
                      ) : (
                        <User className="w-8 h-8 text-white" />
                      )}
                    </div>

                    {/* Nom */}
                    <h4 className="text-white font-bold text-center text-sm mb-1 leading-tight">
                      {ancestor.name}
                    </h4>

                    {/* Relation */}
                    <p className={`text-center text-xs mb-2 ${
                      ancestor.nobility ? 'text-yellow-300' : 'text-emerald-400'
                    }`}>
                      {ancestor.relation}
                    </p>

                    {/* Dates */}
                    <div className="text-center text-white/70 text-xs mb-2">
                      {ancestor.birth}
                      {ancestor.death && ` - ${ancestor.death}`}
                    </div>

                    {/* Badges */}
                    <div className="flex justify-center space-x-1">
                      {ancestor.nobility && (
                        <div className="w-4 h-4 bg-yellow-500 rounded-full flex items-center justify-center">
                          <Crown className="w-2 h-2 text-white" />
                        </div>
                      )}
                      {ancestor.photo && (
                        <div className="w-4 h-4 bg-blue-500 rounded-full flex items-center justify-center">
                          <Camera className="w-2 h-2 text-white" />
                        </div>
                      )}
                      {ancestor.documents > 0 && (
                        <div className="w-4 h-4 bg-purple-500 rounded-full flex items-center justify-center">
                          <FileText className="w-2 h-2 text-white" />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Légende flottante */}
          <div className="absolute bottom-6 left-6 bg-black/50 backdrop-blur-lg rounded-2xl p-4 border border-white/20">
            <h4 className="text-white font-bold mb-3 text-sm">Légende</h4>
            <div className="space-y-2 text-xs">
              <div className="flex items-center space-x-2">
                <Crown className="w-4 h-4 text-yellow-400" />
                <span className="text-white/80">Noblesse</span>
              </div>
              <div className="flex items-center space-x-2">
                <Camera className="w-4 h-4 text-blue-400" />
                <span className="text-white/80">Photo disponible</span>
              </div>
              <div className="flex items-center space-x-2">
                <FileText className="w-4 h-4 text-purple-400" />
                <span className="text-white/80">Documents</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-4 h-1 bg-white/30" style={{borderTop: '2px dashed rgba(255,255,255,0.5)'}}></div>
                <span className="text-white/80">Lignée noble</span>
              </div>
            </div>
          </div>

          {/* Contrôles de zoom flottants */}
          <div className="absolute top-6 right-6 bg-black/50 backdrop-blur-lg rounded-2xl p-2 border border-white/20">
            <div className="flex flex-col space-y-2">
              <button 
                onClick={handleZoomIn}
                className="bg-white/10 hover:bg-white/20 text-white p-2 rounded-lg transition-colors"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button 
                onClick={handleZoomOut}
                className="bg-white/10 hover:bg-white/20 text-white p-2 rounded-lg transition-colors"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button 
                onClick={handleReset}
                className="bg-white/10 hover:bg-white/20 text-white p-2 rounded-lg transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
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
                  <div className={`w-20 h-20 rounded-2xl flex items-center justify-center ${
                    selectedAncestor.nobility 
                      ? 'bg-gradient-to-br from-yellow-400 to-orange-500' 
                      : 'bg-gradient-to-br from-emerald-400 to-blue-400'
                  }`}>
                    {selectedAncestor.nobility ? (
                      <Crown className="w-10 h-10 text-white" />
                    ) : (
                      <User className="w-10 h-10 text-white" />
                    )}
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white">{selectedAncestor.name}</h2>
                    <p className={`font-medium text-lg ${
                      selectedAncestor.nobility ? 'text-yellow-400' : 'text-emerald-400'
                    }`}>
                      {selectedAncestor.relation}
                    </p>
                    {selectedAncestor.nobility && (
                      <div className="bg-yellow-500/20 border border-yellow-400/50 rounded-full px-3 py-1 mt-2 inline-block">
                        <span className="text-yellow-300 text-sm font-semibold">👑 Lignée Noble</span>
                      </div>
                    )}
                  </div>
                </div>
                <button 
                  onClick={() => setSelectedAncestor(null)}
                  className="text-white/60 hover:text-white text-3xl font-light leading-none"
                >
                  ×
                </button>
              </div>

              <div className="grid md:grid-cols-2 gap-6 mb-6">
                <div className="space-y-4">
                  <div>
                    <h3 className="text-white font-semibold mb-3 flex items-center">
                      <User className="w-4 h-4 mr-2" />
                      Informations personnelles
                    </h3>
                    <div className="space-y-2 text-white/80">
                      <div className="flex items-center space-x-3">
                        <Calendar className="w-4 h-4 text-white/60" />
                        <span>
                          Né en {selectedAncestor.birth}
                          {selectedAncestor.death && ` - Décédé en ${selectedAncestor.death}`}
                        </span>
                      </div>
                      <div className="flex items-center space-x-3">
                        <MapPin className="w-4 h-4 text-white/60" />
                        <span>{selectedAncestor.place}</span>
                      </div>
                      <div className="flex items-center space-x-3">
                        <Award className="w-4 h-4 text-white/60" />
                        <span>{selectedAncestor.profession}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <h3 className="text-white font-semibold mb-3 flex items-center">
                      <FileText className="w-4 h-4 mr-2" />
                      Ressources disponibles
                    </h3>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between bg-white/10 rounded-lg p-3">
                        <div className="flex items-center space-x-2">
                          <FileText className="w-4 h-4 text-blue-400" />
                          <span className="text-white/80 text-sm">Documents historiques</span>
                        </div>
                        <span className="text-blue-400 font-semibold">{selectedAncestor.documents}</span>
                      </div>
                      
                      <div className="flex items-center justify-between bg-white/10 rounded-lg p-3">
                        <div className="flex items-center space-x-2">
                          <Camera className="w-4 h-4 text-emerald-400" />
                          <span className="text-white/80 text-sm">Photographies</span>
                        </div>
                        <span className={`font-semibold ${selectedAncestor.photo ? 'text-emerald-400' : 'text-white/50'}`}>
                          {selectedAncestor.photo ? 'Disponible' : 'Aucune'}
                        </span>
                      </div>

                      {selectedAncestor.nobility && (
                        <div className="flex items-center justify-between bg-yellow-500/10 border border-yellow-400/30 rounded-lg p-3">
                          <div className="flex items-center space-x-2">
                            <Crown className="w-4 h-4 text-yellow-400" />
                            <span className="text-white/80 text-sm">Titres de noblesse</span>
                          </div>
                          <span className="text-yellow-400 font-semibold">Authentifiés</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex space-x-4">
                <button className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-3 rounded-xl transition-colors flex items-center justify-center space-x-2">
                  <Eye className="w-4 h-4" />
                  <span>Voir les documents</span>
                </button>
                <button className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-xl transition-colors flex items-center space-x-2">
                  <Share className="w-4 h-4" />
                  <span>Partager</span>
                </button>
                <button className="bg-purple-500 hover:bg-purple-600 text-white px-6 py-3 rounded-xl transition-colors">
                  <Download className="w-4 h-4" />
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

export default FamilyTreeInteractive;
