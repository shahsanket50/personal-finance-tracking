import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const AuthCallback = () => {
  const navigate = useNavigate();
  const { exchangeSession } = useAuth();
  const [error, setError] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');

    if (sessionId) {
      exchangeSession(sessionId).then(success => {
        if (success) {
          navigate('/', { replace: true });
        } else {
          setError('Authentication failed');
          setTimeout(() => navigate('/login', { replace: true }), 2000);
        }
      });
    } else {
      navigate('/login', { replace: true });
    }
  }, [exchangeSession, navigate]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#1a1a1a' }}>
        <div className="text-center">
          <p className="text-red-400">{error}</p>
          <p className="text-white/50 text-sm mt-2">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: '#1a1a1a' }}>
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-[#5C745A] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-white/70">Completing sign in...</p>
      </div>
    </div>
  );
};

export default AuthCallback;
