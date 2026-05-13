import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { initSentry } from './lib/sentry';
import './index.css';

// Fire-and-forget — Sentry init does nothing unless VITE_SENTRY_DSN is set
// AND @sentry/react is installed. Both opt-in.
initSentry();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
