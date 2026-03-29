import { useAuth } from '../contexts/AuthContext';

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
const Login = () => {
  const { user } = useAuth();

  const handleGoogleLogin = () => {
    const redirectUrl = window.location.origin + '/';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  if (user) {
    window.location.href = '/';
    return null;
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #0f0f0f 0%, #1a2a1a 50%, #0f0f0f 100%)' }}>
      <div className="w-full max-w-md mx-4">
        <div className="text-center mb-10">
          <div className="w-16 h-16 rounded-2xl mx-auto mb-4 flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #5C745A, #3a4d39)' }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
          </div>
          <h1 className="text-4xl font-bold text-white tracking-tight">MoneyInsights</h1>
          <p className="text-white/50 mt-2 text-sm">Track your finances across all accounts</p>
        </div>

        <div className="rounded-2xl p-8 border" style={{ background: '#1e1e1e', borderColor: '#2a2a2a' }}>
          <h2 className="text-xl font-semibold text-white mb-2">Welcome</h2>
          <p className="text-white/50 text-sm mb-6">Sign in to manage your financial data</p>

          <button
            onClick={handleGoogleLogin}
            className="flex items-center justify-center gap-3 w-full py-3 px-4 rounded-xl font-medium transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] cursor-pointer"
            style={{ background: '#fff', color: '#1a1a1a' }}
            data-testid="google-login-btn"
          >
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </button>

          <p className="text-white/30 text-xs text-center mt-6">
            Your data is stored securely and never shared with third parties
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
