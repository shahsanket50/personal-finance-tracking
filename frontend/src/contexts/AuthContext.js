import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';
const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/auth/me`, { withCredentials: true });
      setUser(res.data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const exchangeSession = async (sessionId) => {
    try {
      const res = await axios.post(`${API}/auth/session`, { session_id: sessionId }, { withCredentials: true });
      setUser(res.data);
      // Init defaults for new user
      await axios.post(`${API}/init`, {}, { withCredentials: true });
      return true;
    } catch (err) {
      console.error('Session exchange failed:', err);
      return false;
    }
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
    } catch {}
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, exchangeSession, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
};
