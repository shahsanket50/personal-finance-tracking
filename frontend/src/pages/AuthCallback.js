import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const AuthCallback = () => {
  const navigate = useNavigate();
  const { exchangeSession } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Use ref to prevent double-processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    // Extract session_id from URL hash fragment
    const hash = window.location.hash;
    const params = new URLSearchParams(hash.replace('#', ''));
    const sessionId = params.get('session_id');

    if (sessionId) {
      exchangeSession(sessionId).then(success => {
        // Clear the hash
        window.history.replaceState({}, '', window.location.pathname);
        if (success) {
          navigate('/', { replace: true });
        } else {
          navigate('/login', { replace: true });
        }
      });
    } else {
      navigate('/login', { replace: true });
    }
  }, [exchangeSession, navigate]);

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
