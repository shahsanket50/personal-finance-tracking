import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation, useNavigate } from 'react-router-dom';
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
import AccountingDashboard from './pages/AccountingDashboard';
import ChartOfAccounts from './pages/ChartOfAccounts';
import Vouchers from './pages/Vouchers';
import Daybook from './pages/Daybook';
import TrialBalance from './pages/TrialBalance';
import Reports from './pages/Reports';
import {
  House, CreditCard, ArrowsLeftRight, UploadSimple, Tag, SignOut, List, Gear,
  Buildings, TreeStructure, Receipt, BookOpen, Scales, ChartLine, ArrowsClockwise, X, UserCircle
} from '@phosphor-icons/react';
import './App.css';

const TRACKER_NAV = [
  { path: '/', label: 'Dashboard', icon: House },
  { path: '/accounts', label: 'Accounts', icon: CreditCard },
  { path: '/transactions', label: 'Transactions', icon: ArrowsLeftRight },
  { path: '/upload', label: 'Upload', icon: UploadSimple },
  { path: '/categories', label: 'Categories', icon: Tag },
];

const ACCOUNTING_NAV = [
  { path: '/accounting', label: 'Dashboard', icon: Buildings },
  { path: '/accounting/chart', label: 'Chart of Accounts', icon: TreeStructure },
  { path: '/accounting/vouchers', label: 'Vouchers', icon: Receipt },
  { path: '/accounting/daybook', label: 'Daybook', icon: BookOpen },
  { path: '/accounting/trial-balance', label: 'Trial Balance', icon: Scales },
  { path: '/accounting/reports', label: 'Reports', icon: ChartLine },
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
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const [viewMode, setViewMode] = useState(() => sessionStorage.getItem('viewMode') || 'tracker');

  useEffect(() => {
    if (location.pathname.startsWith('/accounting')) {
      setViewMode('accounting');
      sessionStorage.setItem('viewMode', 'accounting');
    } else if (location.pathname !== '/settings') {
      setViewMode('tracker');
      sessionStorage.setItem('viewMode', 'tracker');
    }
  }, [location.pathname]);

  const isAccounting = viewMode === 'accounting';
  const navItems = isAccounting ? ACCOUNTING_NAV : TRACKER_NAV;

  const toggleView = () => {
    const newMode = isAccounting ? 'tracker' : 'accounting';
    setViewMode(newMode);
    sessionStorage.setItem('viewMode', newMode);
    navigate(newMode === 'accounting' ? '/accounting' : '/');
  };

  return (
    <div className="flex flex-col h-screen" style={{ background: 'var(--app-bg)' }}>
      {/* Top Navigation Bar */}
      <header className="shrink-0 border-b" style={{ background: 'var(--app-sidebar)', borderColor: 'var(--app-sidebar-border)' }}>
        <div className="max-w-screen-2xl mx-auto flex items-center h-14 px-4 gap-2">
          {/* Logo */}
          <div className="shrink-0 mr-3">
            <h1 className="text-base font-bold tracking-tight" style={{ color: 'var(--app-text)' }}>MoneyInsights</h1>
          </div>

          {/* View Toggle */}
          <button
            onClick={toggleView}
            data-testid="view-toggle"
            className="shrink-0 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider px-3 py-1.5 rounded-full border transition-colors mr-2"
            style={{
              borderColor: isAccounting ? '#7CA1A6' : '#5C745A',
              color: isAccounting ? '#7CA1A6' : '#5C745A',
              background: isAccounting ? '#7CA1A610' : '#5C745A10',
            }}
          >
            <ArrowsClockwise size={13} />
            {isAccounting ? 'Accounting' : 'Tracker'}
          </button>

          {/* Desktop Nav Tabs */}
          <nav className="hidden md:flex items-center gap-0.5 flex-1 overflow-x-auto" data-testid="top-nav">
            {navItems.map(item => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/' || item.path === '/accounting'}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors whitespace-nowrap"
                style={({ isActive }) => ({
                  background: isActive ? 'var(--app-nav-active-bg)' : 'transparent',
                  color: isActive ? 'var(--app-nav-active-text)' : 'var(--app-nav-text)',
                })}
                data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
              >
                <item.icon size={16} />
                {item.label}
              </NavLink>
            ))}
          </nav>

          {/* Right side: Settings, User, Menu */}
          <div className="flex items-center gap-1 ml-auto shrink-0">
            <NavLink
              to="/settings"
              className="hidden md:flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-[13px] font-medium transition-colors"
              style={({ isActive }) => ({
                background: isActive ? 'var(--app-nav-active-bg)' : 'transparent',
                color: isActive ? 'var(--app-nav-active-text)' : 'var(--app-nav-text)',
              })}
              data-testid="nav-settings"
            >
              <Gear size={16} />
            </NavLink>

            {user && (
              <div className="hidden md:flex items-center gap-2 ml-1 pl-2 border-l" style={{ borderColor: 'var(--app-sidebar-border)' }}>
                {user.picture ? (
                  <img src={user.picture} alt="" className="w-7 h-7 rounded-full" />
                ) : (
                  <div className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold"
                    style={{ background: 'var(--app-accent-light)', color: 'var(--app-accent-text)' }}>
                    {user.name?.[0] || user.email?.[0] || '?'}
                  </div>
                )}
                <button onClick={logout} className="p-1.5 rounded-lg transition-colors" style={{ color: 'var(--app-text-muted)' }}
                  data-testid="logout-btn" title="Sign out">
                  <SignOut size={16} />
                </button>
              </div>
            )}

            {/* Mobile burger */}
            <button onClick={() => setMenuOpen(!menuOpen)} className="md:hidden p-2" style={{ color: 'var(--app-text-secondary)' }}
              data-testid="mobile-menu-btn">
              <List size={22} />
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Menu Overlay */}
      {menuOpen && (
        <div className="md:hidden fixed inset-0 z-50" onClick={() => setMenuOpen(false)}>
          <div className="absolute inset-0" style={{ background: 'rgba(0,0,0,0.4)' }} />
          <div className="absolute top-0 right-0 w-72 h-full border-l shadow-xl"
            style={{ background: 'var(--app-sidebar)', borderColor: 'var(--app-sidebar-border)' }}
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: 'var(--app-sidebar-border)' }}>
              <span className="font-semibold" style={{ color: 'var(--app-text)' }}>Menu</span>
              <button onClick={() => setMenuOpen(false)} className="p-1" style={{ color: 'var(--app-text-muted)' }}><X size={20} /></button>
            </div>
            <nav className="py-3 px-3 space-y-1">
              {navItems.map(item => (
                <NavLink key={item.path} to={item.path}
                  end={item.path === '/' || item.path === '/accounting'}
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
                  style={({ isActive }) => ({
                    background: isActive ? 'var(--app-nav-active-bg)' : 'transparent',
                    color: isActive ? 'var(--app-nav-active-text)' : 'var(--app-nav-text)',
                  })}>
                  <item.icon size={18} /> {item.label}
                </NavLink>
              ))}
              <div className="pt-2 mt-2 border-t" style={{ borderColor: 'var(--app-sidebar-border)' }}>
                <NavLink to="/settings" onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium"
                  style={({ isActive }) => ({ color: isActive ? 'var(--app-nav-active-text)' : 'var(--app-nav-text)' })}>
                  <Gear size={18} /> Settings
                </NavLink>
              </div>
            </nav>
            {user && (
              <div className="absolute bottom-0 left-0 right-0 p-4 border-t" style={{ borderColor: 'var(--app-sidebar-border)' }}>
                <div className="flex items-center gap-3 mb-3">
                  {user.picture ? (
                    <img src={user.picture} alt="" className="w-8 h-8 rounded-full" />
                  ) : (
                    <UserCircle size={32} style={{ color: 'var(--app-text-muted)' }} />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate" style={{ color: 'var(--app-text)' }}>{user.name || user.email}</p>
                    <p className="text-xs truncate" style={{ color: 'var(--app-text-muted)' }}>{user.email}</p>
                  </div>
                </div>
                <button onClick={() => { logout(); setMenuOpen(false); }}
                  className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg w-full" style={{ color: 'var(--app-danger)' }}>
                  <SignOut size={16} /> Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-7xl mx-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/analytics" element={<Navigate to="/" replace />} />
            <Route path="/categories" element={<Categories />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/accounting" element={<AccountingDashboard />} />
            <Route path="/accounting/chart" element={<ChartOfAccounts />} />
            <Route path="/accounting/vouchers" element={<Vouchers />} />
            <Route path="/accounting/daybook" element={<Daybook />} />
            <Route path="/accounting/trial-balance" element={<TrialBalance />} />
            <Route path="/accounting/reports" element={<Reports />} />
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
