import { useState, useEffect } from 'react';
import '@/App.css';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import axios from 'axios';
import Dashboard from './pages/Dashboard';
import Accounts from './pages/Accounts';
import Transactions from './pages/Transactions';
import Categories from './pages/Categories';
import Upload from './pages/Upload';
import Analytics from './pages/Analytics';
import { Toaster } from './components/ui/sonner';
import { 
  ChartLine, 
  Wallet, 
  ArrowsLeftRight, 
  Tag, 
  UploadSimple, 
  ChartBar 
} from '@phosphor-icons/react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Layout = ({ children }) => {
  const location = useLocation();
  
  const navItems = [
    { path: '/', icon: ChartLine, label: 'Dashboard' },
    { path: '/accounts', icon: Wallet, label: 'Accounts' },
    { path: '/transactions', icon: ArrowsLeftRight, label: 'Transactions' },
    { path: '/categories', icon: Tag, label: 'Categories' },
    { path: '/upload', icon: UploadSimple, label: 'Upload' },
    { path: '/analytics', icon: ChartBar, label: 'Analytics' },
  ];
  
  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-[#F9F8F6]/70 border-b border-[#E5E2DC] shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="font-heading text-2xl tracking-tight" style={{ fontFamily: 'Manrope, sans-serif', color: '#1C1917' }}>
                MoneyInsights
              </h1>
              <p className="text-xs" style={{ color: '#78716C' }}>Track, Analyze, Optimize</p>
            </div>
          </div>
        </div>
      </header>
      
      {/* Navigation */}
      <nav className="border-b border-[#E5E2DC] bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-1 overflow-x-auto">
            {navItems.map(({ path, icon: Icon, label }) => {
              const isActive = location.pathname === path;
              return (
                <Link
                  key={path}
                  to={path}
                  data-testid={`nav-${label.toLowerCase()}`}
                  className={`flex items-center gap-2 px-4 py-3 text-sm transition-all duration-200 border-b-2 ${
                    isActive 
                      ? 'border-[#5C745A] text-[#5C745A]' 
                      : 'border-transparent text-[#78716C] hover:text-[#1C1917] hover:bg-[#F9F8F6]'
                  }`}
                  style={{ fontFamily: 'IBM Plex Sans, sans-serif' }}
                >
                  <Icon size={18} weight={isActive ? 'fill' : 'regular'} />
                  {label}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>
      
      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {children}
      </main>
    </div>
  );
};

function App() {
  useEffect(() => {
    // Initialize default categories on app load
    axios.post(`${API}/init`).catch(err => console.error('Init error:', err));
  }, []);
  
  return (
    <div className="App" style={{ backgroundColor: '#F9F8F6', minHeight: '100vh', fontFamily: 'IBM Plex Sans, sans-serif' }}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/categories" element={<Categories />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </Layout>
      </BrowserRouter>
      <Toaster />
    </div>
  );
}

export default App;
