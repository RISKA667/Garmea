import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Home, DollarSign, CreditCard, BarChart3, TreePine, UserCheck } from 'lucide-react';

// Import des pages
import LandingPage from './pages/LandingPage';
import PricingPage from './pages/PricingPage';
import CheckoutPage from './pages/CheckoutPage';
import DashboardPro from './pages/DashboardPro';
import FamilyTreeInteractive from './pages/FamilyTreeInteractive';
import OnboardingPage from './pages/OnboardingPage';

// Menu de navigation amélioré
const Navigation = () => (
  <nav className="fixed top-0 left-0 right-0 bg-black/80 backdrop-blur-sm text-white p-4 z-50">
    <div className="container mx-auto flex items-center justify-between">
      <div className="flex items-center space-x-4">
        <TreePine className="w-6 h-6 text-emerald-400" />
        <span className="font-bold text-lg">Garméa Dev</span>
      </div>
      
      <div className="flex items-center space-x-2">
        <Link 
          to="/" 
          className="flex items-center space-x-1 bg-blue-500 hover:bg-blue-600 px-3 py-2 rounded-lg transition-colors text-sm"
        >
          <Home className="w-4 h-4" />
          <span>Landing</span>
        </Link>
        
        <Link 
          to="/pricing" 
          className="flex items-center space-x-1 bg-green-500 hover:bg-green-600 px-3 py-2 rounded-lg transition-colors text-sm"
        >
          <DollarSign className="w-4 h-4" />
          <span>Pricing</span>
        </Link>
        
        <Link 
          to="/checkout" 
          className="flex items-center space-x-1 bg-yellow-500 hover:bg-yellow-600 px-3 py-2 rounded-lg transition-colors text-sm"
        >
          <CreditCard className="w-4 h-4" />
          <span>Checkout</span>
        </Link>
        
        <Link 
          to="/dashboard" 
          className="flex items-center space-x-1 bg-red-500 hover:bg-red-600 px-3 py-2 rounded-lg transition-colors text-sm"
        >
          <BarChart3 className="w-4 h-4" />
          <span>Dashboard</span>
        </Link>
        
        <Link 
          to="/tree" 
          className="flex items-center space-x-1 bg-purple-500 hover:bg-purple-600 px-3 py-2 rounded-lg transition-colors text-sm"
        >
          <TreePine className="w-4 h-4" />
          <span>Tree</span>
        </Link>
        
        <Link 
          to="/onboarding" 
          className="flex items-center space-x-1 bg-pink-500 hover:bg-pink-600 px-3 py-2 rounded-lg transition-colors text-sm"
        >
          <UserCheck className="w-4 h-4" />
          <span>Onboarding</span>
        </Link>
      </div>
    </div>
  </nav>
);

function App() {
  return (
    <Router>
      <Navigation />
      <div className="pt-20">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/dashboard" element={<DashboardPro />} />
          <Route path="/tree" element={<FamilyTreeInteractive />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;