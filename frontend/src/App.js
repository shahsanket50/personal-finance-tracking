import { useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import Dashboard from './pages/Dashboard';
import Accounts from './pages/Accounts';
import Transactions from './pages/Transactions';
import Upload from './pages/Upload';
import Analytics from './pages/Analytics';
import Categories from './pages/Categories';
import { House, CreditCard, ArrowsLeftRight, UploadSimple, ChartLine, Tag, SignOut, List } from '@phosphor-icons/react';
import './App.css';

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: House },
  { path: '/accounts', label: 'Accounts', icon: CreditCard },
  { path: '/transactions', label: 'Transactions', icon: ArrowsLeftRight },
  { path: '/upload', label: 'Upload', icon: UploadSimple },
  { path: '/analytics', label: 'Analytics', icon: ChartLine },
  { path: '/categories', label: 'Categories', icon: Tag },
];

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#1a1a1a' }}>
        <div className="w-10 h-10 border-4 border-[#5C745A] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

function AppLayout() {
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="flex h-screen" style={{ background: '#111111' }}>
      {/* Sidebar - Desktop */}
      <aside className="hidden lg:flex flex-col w-64 border-r" style={{ background: '#161616', borderColor: '#222' }}>
        <div className="p-5 border-b" style={{ borderColor: '#222' }}>
          <h1 className="text-lg font-bold text-white tracking-tight">MoneyInsights</h1>
        </div>
        <nav className="flex-1 py-3 px-3 space-y-1">
          {NAV_ITEMS.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? 'bg-[#5C745A]/20 text-[#8eb88a]' : 'text-white/50 hover:text-white/80 hover:bg-white/5'
                }`
              }
              data-testid={`nav-${item.label.toLowerCase()}`}
            >
              <item.icon size={20} />
              {item.label}
            </NavLink>
          ))}
        </nav>
        {user && (
          <div className="p-3 border-t" style={{ borderColor: '#222' }}>
            <div className="flex items-center gap-3 px-3 py-2">
              {user.picture ? (
                <img src={user.picture} alt="" className="w-8 h-8 rounded-full" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-[#5C745A]/30 flex items-center justify-center text-white text-xs font-bold">
                  {user.name?.[0] || user.email?.[0] || '?'}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white truncate">{user.name || user.email}</p>
              </div>
              <button
                onClick={logout}
                className="p-1.5 rounded-lg text-white/40 hover:text-white/80 hover:bg-white/5 transition-colors"
                data-testid="logout-btn"
                title="Sign out"
              >
                <SignOut size={18} />
              </button>
            </div>
          </div>
        )}
      </aside>

      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 h-14 border-b" style={{ background: '#161616', borderColor: '#222' }}>
        <h1 className="text-lg font-bold text-white">MoneyInsights</h1>
        <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="text-white/60 p-2" data-testid="mobile-menu-btn">
          <List size={24} />
        </button>
      </div>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-40" onClick={() => setMobileMenuOpen(false)}>
          <div className="absolute inset-0 bg-black/50" />
          <div className="absolute top-14 right-0 w-64 h-full border-l" style={{ background: '#161616', borderColor: '#222' }} onClick={e => e.stopPropagation()}>
            <nav className="py-3 px-3 space-y-1">
              {NAV_ITEMS.map(item => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      isActive ? 'bg-[#5C745A]/20 text-[#8eb88a]' : 'text-white/50 hover:text-white/80 hover:bg-white/5'
                    }`
                  }
                >
                  <item.icon size={20} />
                  {item.label}
                </NavLink>
              ))}
            </nav>
            {user && (
              <div className="px-3 pt-3 border-t" style={{ borderColor: '#222' }}>
                <button onClick={logout} className="flex items-center gap-2 px-3 py-2.5 text-sm text-red-400 hover:bg-red-500/10 rounded-lg w-full">
                  <SignOut size={18} /> Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto lg:pt-0 pt-14">
        <div className="p-6 max-w-7xl mx-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/categories" element={<Categories />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

function AppRouter() {
  const location = useLocation();
  // CRITICAL: Check URL fragment for session_id synchronously during render
  // This must happen BEFORE ProtectedRoute runs to prevent race conditions
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={
        <ProtectedRoute>
          <AppLayout />
        </ProtectedRoute>
      } />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
