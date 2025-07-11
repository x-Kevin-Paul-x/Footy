import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import React, { useState, useCallback } from 'react';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import LeagueTablePage from './pages/LeagueTablePage';
import TransfersPage from './pages/TransfersPage';
import ClubPage from './pages/ClubPage';
import PlayerPage from './pages/PlayerPage'; // Import PlayerPage
import NotFoundPage from './pages/NotFoundPage';
import ErrorBoundary from './components/ErrorBoundary';
import Toast from './components/Toast';
import './App.css'; // Keep if it contains any global styles you want, or remove if Tailwind handles all

function App() {
  const [toast, setToast] = useState<{ message: string; type?: "success" | "error" | "info" } | null>(null);

  const showToast = useCallback((message: string, type?: "success" | "error" | "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  return (
    <ErrorBoundary>
      <Router>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<HomePage showToast={showToast} />} />
            <Route path="league-table" element={<LeagueTablePage />} />
            <Route path="transfers" element={<TransfersPage />} />
            <Route path="club/:clubName/:season" element={<ClubPage />} />
            <Route path="player/:playerName/:season" element={<PlayerPage />} /> {/* Add PlayerPage route */}
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
        {toast && (
          <Toast
            message={toast.message}
            type={toast.type}
            onClose={() => setToast(null)}
          />
        )}
      </Router>
    </ErrorBoundary>
  );
}

export default App;
