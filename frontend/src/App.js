import { useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import Dashboard from './pages/Dashboard';
import Accounts from './pages/Accounts';
import Transactions from './pages/Transactions';
import Upload from './pages/Upload';
import Categories from './pages/Categories';
import Settings from './pages/Settings';
import { House, CreditCard, ArrowsLeftRight, UploadSimple, Tag, SignOut, List, Gear } from '@phosphor-icons/react';
import './App.css';

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: House },
  { path: '/accounts', label: 'Accounts', icon: CreditCard },
  { path: '/transactions', label: 'Transactions', icon: ArrowsLeftRight },
  { path: '/upload', label: 'Upload', icon: UploadSimple },
  { path: '/categories', label: 'Categories', icon: Tag },
  { path: '/settings', label: 'Settings', icon: Gear },
];

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--app-bg)' }}>
        <div className="w-10 h-10 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--app-accent)', borderTopColor: 'transparent' }} />
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
    <div className="flex h-screen" style={{ background: 'var(--app-bg)' }}>
      {/* Sidebar - Desktop */}
      <aside className="hidden lg:flex flex-col w-64 border-r" style={{ background: 'var(--app-sidebar)', borderColor: 'var(--app-sidebar-border)' }}>
        <div className="p-5 border-b" style={{ borderColor: 'var(--app-sidebar-border)' }}>
          <h1 className="text-lg font-bold tracking-tight" style={{ color: 'var(--app-text)' }}>MoneyInsights</h1>
        </div>
        <nav className="flex-1 py-3 px-3 space-y-1">
          {NAV_ITEMS.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors`
              }
              style={({ isActive }) => ({
                background: isActive ? 'var(--app-nav-active-bg)' : 'transparent',
                color: isActive ? 'var(--app-nav-active-text)' : 'var(--app-nav-text)',
              })}
              data-testid={`nav-${item.label.toLowerCase()}`}
            >
              <item.icon size={20} />
              {item.label}
            </NavLink>
          ))}
        </nav>
        {user && (
          <div className="p-3 border-t" style={{ borderColor: 'var(--app-sidebar-border)' }}>
            <div className="flex items-center gap-3 px-3 py-2">
              {user.picture ? (
                <img src={user.picture} alt="" className="w-8 h-8 rounded-full" />
              ) : (
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                  style={{ background: 'var(--app-accent-light)', color: 'var(--app-accent-text)' }}>
                  {user.name?.[0] || user.email?.[0] || '?'}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm truncate" style={{ color: 'var(--app-text)' }}>{user.name || user.email}</p>
              </div>
              <button
                onClick={logout}
                className="p-1.5 rounded-lg transition-colors"
                style={{ color: 'var(--app-text-muted)' }}
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
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 h-14 border-b"
        style={{ background: 'var(--app-mobile-header)', borderColor: 'var(--app-sidebar-border)' }}>
        <h1 className="text-lg font-bold" style={{ color: 'var(--app-text)' }}>MoneyInsights</h1>
        <div className="flex items-center gap-2">
          <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="p-2" style={{ color: 'var(--app-text-secondary)' }} data-testid="mobile-menu-btn">
            <List size={24} />
          </button>
        </div>
      </div>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-40" onClick={() => setMobileMenuOpen(false)}>
          <div className="absolute inset-0" style={{ background: 'var(--app-overlay)' }} />
          <div className="absolute top-14 right-0 w-64 h-full border-l"
            style={{ background: 'var(--app-sidebar)', borderColor: 'var(--app-sidebar-border)' }}
            onClick={e => e.stopPropagation()}>
            <nav className="py-3 px-3 space-y-1">
              {NAV_ITEMS.map(item => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
                  style={({ isActive }) => ({
                    background: isActive ? 'var(--app-nav-active-bg)' : 'transparent',
                    color: isActive ? 'var(--app-nav-active-text)' : 'var(--app-nav-text)',
                  })}
                >
                  <item.icon size={20} />
                  {item.label}
                </NavLink>
              ))}
            </nav>
            {user && (
              <div className="px-3 pt-3 border-t" style={{ borderColor: 'var(--app-sidebar-border)' }}>
                <button onClick={logout} className="flex items-center gap-2 px-3 py-2.5 text-sm rounded-lg w-full" style={{ color: 'var(--app-danger)' }}>
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
            <Route path="/categories" element={<Categories />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

function AppRouter() {
  const location = useLocation();
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
      <ThemeProvider>
        <AuthProvider>
          <AppRouter />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
