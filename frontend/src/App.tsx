import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import LeagueTablePage from './pages/LeagueTablePage';
import TransfersPage from './pages/TransfersPage';
import ClubPage from './pages/ClubPage';
import PlayerPage from './pages/PlayerPage'; // Import PlayerPage
import NotFoundPage from './pages/NotFoundPage';
import './App.css'; // Keep if it contains any global styles you want, or remove if Tailwind handles all

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="league-table" element={<LeagueTablePage />} />
          <Route path="transfers" element={<TransfersPage />} />
          <Route path="club/:clubName/:season" element={<ClubPage />} />
          <Route path="player/:playerName/:season" element={<PlayerPage />} /> {/* Add PlayerPage route */}
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
