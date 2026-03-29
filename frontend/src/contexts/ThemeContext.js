import { createContext, useContext, useState, useEffect } from 'react';

const THEMES = {
  light: {
    name: 'Light',
    preview: '#F9F8F6',
    vars: {
      '--app-bg': '#F9F8F6',
      '--app-sidebar': '#FFFFFF',
      '--app-sidebar-border': '#E5E2DC',
      '--app-text': '#1C1917',
      '--app-text-secondary': '#78716C',
      '--app-text-muted': '#A8A29E',
      '--app-accent': '#5C745A',
      '--app-accent-hover': '#475F45',
      '--app-accent-light': '#E7F3F0',
      '--app-accent-text': '#2D4A39',
      '--app-card-bg': '#FFFFFF',
      '--app-card-border': '#E5E2DC',
      '--app-card-hover': '#F5F4F2',
      '--app-input-bg': '#FFFFFF',
      '--app-input-border': '#E5E2DC',
      '--app-nav-active-bg': 'rgba(92,116,90,0.12)',
      '--app-nav-active-text': '#5C745A',
      '--app-nav-text': '#78716C',
      '--app-nav-hover': '#1C1917',
      '--app-danger': '#C06B52',
      '--app-danger-hover': '#A35943',
      '--app-mobile-header': '#FFFFFF',
      '--app-overlay': 'rgba(0,0,0,0.3)',
      '--app-badge-bg': '#F0F0EE',
    }
  },
  dark: {
    name: 'Dark',
    preview: '#111111',
    vars: {
      '--app-bg': '#111111',
      '--app-sidebar': '#161616',
      '--app-sidebar-border': '#222222',
      '--app-text': '#E8E8E8',
      '--app-text-secondary': '#999999',
      '--app-text-muted': '#666666',
      '--app-accent': '#8eb88a',
      '--app-accent-hover': '#a5cda1',
      '--app-accent-light': 'rgba(92,116,90,0.2)',
      '--app-accent-text': '#8eb88a',
      '--app-card-bg': '#1a1a1a',
      '--app-card-border': '#2a2a2a',
      '--app-card-hover': '#222222',
      '--app-input-bg': '#1a1a1a',
      '--app-input-border': '#333333',
      '--app-nav-active-bg': 'rgba(142,184,138,0.15)',
      '--app-nav-active-text': '#8eb88a',
      '--app-nav-text': 'rgba(255,255,255,0.5)',
      '--app-nav-hover': 'rgba(255,255,255,0.8)',
      '--app-danger': '#E57373',
      '--app-danger-hover': '#EF5350',
      '--app-mobile-header': '#161616',
      '--app-overlay': 'rgba(0,0,0,0.6)',
      '--app-badge-bg': '#222222',
    }
  },
  forest: {
    name: 'Forest',
    preview: '#1a2a1a',
    vars: {
      '--app-bg': '#0f1a0f',
      '--app-sidebar': '#142014',
      '--app-sidebar-border': '#1e3020',
      '--app-text': '#d4e8d0',
      '--app-text-secondary': '#8aab86',
      '--app-text-muted': '#5a7a56',
      '--app-accent': '#6db668',
      '--app-accent-hover': '#85cc80',
      '--app-accent-light': 'rgba(109,182,104,0.15)',
      '--app-accent-text': '#6db668',
      '--app-card-bg': '#162016',
      '--app-card-border': '#243824',
      '--app-card-hover': '#1c2c1c',
      '--app-input-bg': '#162016',
      '--app-input-border': '#2a4030',
      '--app-nav-active-bg': 'rgba(109,182,104,0.15)',
      '--app-nav-active-text': '#6db668',
      '--app-nav-text': 'rgba(212,232,208,0.5)',
      '--app-nav-hover': 'rgba(212,232,208,0.8)',
      '--app-danger': '#cf6b5e',
      '--app-danger-hover': '#e07060',
      '--app-mobile-header': '#142014',
      '--app-overlay': 'rgba(0,0,0,0.5)',
      '--app-badge-bg': '#1e3020',
    }
  },
  ocean: {
    name: 'Ocean',
    preview: '#EEF4F8',
    vars: {
      '--app-bg': '#EEF4F8',
      '--app-sidebar': '#FFFFFF',
      '--app-sidebar-border': '#D0DDE5',
      '--app-text': '#1B2D3A',
      '--app-text-secondary': '#5A7B8F',
      '--app-text-muted': '#8FAAB8',
      '--app-accent': '#2D7D9A',
      '--app-accent-hover': '#1F6580',
      '--app-accent-light': '#DCF0F7',
      '--app-accent-text': '#1B5A72',
      '--app-card-bg': '#FFFFFF',
      '--app-card-border': '#D0DDE5',
      '--app-card-hover': '#E8F0F5',
      '--app-input-bg': '#FFFFFF',
      '--app-input-border': '#C5D5DF',
      '--app-nav-active-bg': 'rgba(45,125,154,0.1)',
      '--app-nav-active-text': '#2D7D9A',
      '--app-nav-text': '#5A7B8F',
      '--app-nav-hover': '#1B2D3A',
      '--app-danger': '#C06060',
      '--app-danger-hover': '#A34545',
      '--app-mobile-header': '#FFFFFF',
      '--app-overlay': 'rgba(0,0,0,0.3)',
      '--app-badge-bg': '#E0ECF2',
    }
  },
  sand: {
    name: 'Sand',
    preview: '#F5F0E8',
    vars: {
      '--app-bg': '#F5F0E8',
      '--app-sidebar': '#FEFCF8',
      '--app-sidebar-border': '#E0D8CC',
      '--app-text': '#3D3428',
      '--app-text-secondary': '#8A7E6E',
      '--app-text-muted': '#B0A594',
      '--app-accent': '#9A7B4F',
      '--app-accent-hover': '#7D6340',
      '--app-accent-light': '#F0E8D8',
      '--app-accent-text': '#6B5535',
      '--app-card-bg': '#FEFCF8',
      '--app-card-border': '#E0D8CC',
      '--app-card-hover': '#F2ECE0',
      '--app-input-bg': '#FEFCF8',
      '--app-input-border': '#D8D0C0',
      '--app-nav-active-bg': 'rgba(154,123,79,0.12)',
      '--app-nav-active-text': '#9A7B4F',
      '--app-nav-text': '#8A7E6E',
      '--app-nav-hover': '#3D3428',
      '--app-danger': '#B85C4A',
      '--app-danger-hover': '#9A4838',
      '--app-mobile-header': '#FEFCF8',
      '--app-overlay': 'rgba(0,0,0,0.25)',
      '--app-badge-bg': '#EBE4D8',
    }
  }
};

const ThemeContext = createContext(null);
export const useTheme = () => useContext(ThemeContext);
export { THEMES };

export const ThemeProvider = ({ children }) => {
  const [themeKey, setThemeKey] = useState(() => {
    return localStorage.getItem('app-theme') || 'light';
  });

  useEffect(() => {
    const theme = THEMES[themeKey] || THEMES.light;
    const root = document.documentElement;
    Object.entries(theme.vars).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });
    localStorage.setItem('app-theme', themeKey);
  }, [themeKey]);

  const setTheme = (key) => {
    if (THEMES[key]) setThemeKey(key);
  };

  return (
    <ThemeContext.Provider value={{ theme: themeKey, setTheme, themes: THEMES }}>
      {children}
    </ThemeContext.Provider>
  );
};
