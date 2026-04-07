import React from "react";
import ReactDOM from "react-dom/client";
import axios from "axios";
import "@/index.css";
import App from "@/App";
import { App as CapApp } from '@capacitor/app';

// Set axios defaults for all requests
axios.defaults.withCredentials = true;

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

// Register service worker for PWA
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch(() => {});
  });
}

// Handle Android back button via Capacitor
CapApp.addListener('backButton', ({ canGoBack }) => {
  if (canGoBack) {
    window.history.back();
  } else {
    CapApp.exitApp();
  }
});
