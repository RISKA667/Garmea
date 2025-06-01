import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';

// Import tes 6 pages (copie-les dans src/pages/)
import LandingPage from './pages/LandingPage';
import PricingPage from './pages/PricingPage';
import CheckoutPage from './pages/CheckoutPage';
import DashboardPro from './pages/DashboardPro';
import FamilyTreeInteractive from './pages/FamilyTreeInteractive';
import OnboardingPage from './pages/OnboardingPage';

// Menu de navigation pour tester
const Navigation = () => (
  <nav style={{ 
    position: 'fixed', top: 0, left: 0, background: 'rgba(0,0,0,0.8)', 
    color: 'white', padding: '10px', zIndex: 1000, display: 'flex', gap: '10px'
  }}>
    <Link to="/" style={{ background: '#3B82F6', padding: '5px 10px', borderRadius: '4px', color: 'white', textDecoration: 'none' }}>🏠 Landing</Link>
    <Link to="/pricing" style={{ background: '#10B981', padding: '5px 10px', borderRadius: '4px', color: 'white', textDecoration: 'none' }}>💰 Pricing</Link>
    <Link to="/checkout" style={{ background: '#F59E0B', padding: '5px 10px', borderRadius: '4px', color: 'white', textDecoration: 'none' }}>💳 Checkout</Link>
    <Link to="/dashboard" style={{ background: '#EF4444', padding: '5px 10px', borderRadius: '4px', color: 'white', textDecoration: 'none' }}>📊 Dashboard</Link>
    <Link to="/tree" style={{ background: '#8B5CF6', padding: '5px 10px', borderRadius: '4px', color: 'white', textDecoration: 'none' }}>🌳 Tree</Link>
    <Link to="/onboarding" style={{ background: '#EC4899', padding: '5px 10px', borderRadius: '4px', color: 'white', textDecoration: 'none' }}>🎯 Onboarding</Link>
  </nav>
);

function App() {
  return (
    <Router>
      <Navigation />
      <div style={{ paddingTop: '60px' }}>
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