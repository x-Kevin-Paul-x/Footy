import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import React, { useState, useCallback } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
import Toast from './components/Toast';
import Dashboard from './components/Dashboard.tsx';
import LeagueOverview from './components/LeagueOverview.tsx';
import PlayerProfiles from './components/PlayerProfiles.tsx'; // Keep for general list if needed, or remove if only individual pages
import PlayerDetail from './components/PlayerDetail.tsx'; // New import
import ManagerProfiles from './components/ManagerProfiles.tsx';
import ManagerDetail from './components/ManagerDetail.tsx'; // New import
import TeamDetails from './components/TeamDetails.tsx';
import TransferMarket from './components/TransferMarket.tsx';
import MatchReports from './components/MatchReports.tsx';
import MatchDetail from './components/MatchDetail.tsx';
import YouthAcademy from './components/YouthAcademy.tsx';
import SeasonReports from './components/SeasonReports.tsx';
import StatisticsAnalytics from './components/StatisticsAnalytics.tsx';
import './App.css';

// Material UI imports
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Button from '@mui/material/Button';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import DashboardIcon from '@mui/icons-material/Dashboard';
import TableChartIcon from '@mui/icons-material/TableChart';
import GroupsIcon from '@mui/icons-material/Groups';
import PersonIcon from '@mui/icons-material/Person';
import TransferWithinAStationIcon from '@mui/icons-material/TransferWithinAStation';
import Breadcrumbs from '@mui/material/Breadcrumbs';
import Box from '@mui/material/Box';

const drawerWidth = 220;

const sections = [
  { label: 'Dashboard', path: '/', icon: <DashboardIcon /> },
  { label: 'League Overview', path: '/league-overview', icon: <TableChartIcon /> },
  { label: 'Player Profiles', path: '/player-profiles', icon: <PersonIcon /> }, // This will be a generic link, actual player details will be dynamic
  { label: 'Manager Profiles', path: '/manager-profiles', icon: <PersonIcon /> }, // Generic link
  { label: 'Transfer Market', path: '/transfer-market', icon: <TransferWithinAStationIcon /> },
  { label: 'Match Reports', path: '/match-reports', icon: <TableChartIcon /> },
  { label: 'Youth Academy', path: '/youth-academy', icon: <GroupsIcon /> },
  { label: 'Season Reports', path: '/season-reports', icon: <TableChartIcon /> },
  { label: 'Statistics & Analytics', path: '/statistics-analytics', icon: <TableChartIcon /> },
];

function Placeholder({ title }: { title: string }) {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4">{title}</Typography>
      <Typography variant="body2" color="text.secondary">
        Placeholder page for {title}
      </Typography>
    </Box>
  );
}

function AppBreadcrumbs() {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter((x) => x);

  return (
    <Breadcrumbs aria-label="breadcrumb" sx={{ mb: 2 }}>
      <Link to="/">Dashboard</Link>
      {pathnames.map((value, idx) => {
        const to = `/${pathnames.slice(0, idx + 1).join('/')}`;
        const label = sections.find((s) => s.path === to)?.label || value;
        return (
          <Link key={to} to={to}>
            {label}
          </Link>
        );
      })}
    </Breadcrumbs>
  );
}

function App() {
  const [toast, setToast] = useState<{ message: string; type?: "success" | "error" | "info" } | null>(null);
  const [mode, setMode] = useState<'light' | 'dark'>('light');

  // showToast was removed as it was unused. If toast functionality is needed, it should be re-implemented.

  const theme = React.useMemo(
    () =>
      createTheme({
        palette: {
          mode,
          primary: { main: "#1976d2" },
          secondary: { main: "#ff9800" },
          background: { default: mode === "light" ? "#f4f6f8" : "#121212" },
        },
        typography: {
          fontFamily: "'Roboto', 'Arial', sans-serif",
          h4: { fontWeight: 700, letterSpacing: "0.02em" },
          h6: { fontWeight: 600 },
        },
        spacing: 8,
        components: {
          MuiButton: {
            styleOverrides: {
              root: { borderRadius: 8, textTransform: "none" },
            },
          },
        },
      }),
    [mode]
  );

  return (
    <ErrorBoundary>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <Box sx={{ display: 'flex' }}>
            <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
              <Toolbar>
                <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
                  Footy App
                </Typography>
                <Button
                  color="inherit"
                  onClick={() => setMode(mode === 'light' ? 'dark' : 'light')}
                  sx={{ ml: 2 }}
                >
                  Toggle {mode === 'light' ? 'Dark' : 'Light'} Mode
                </Button>
              </Toolbar>
            </AppBar>
            <Drawer
              variant="permanent"
              sx={{
                width: drawerWidth,
                flexShrink: 0,
                [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
              }}
            >
              <Toolbar />
              <List>
                {sections.map((section) => (
                  <ListItem key={section.path} disablePadding>
                    <ListItemButton component={Link} to={section.path}>
                      <ListItemIcon>{section.icon}</ListItemIcon>
                      <ListItemText primary={section.label} />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            </Drawer>
            <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
              <Toolbar />
              <AppBreadcrumbs />
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/league-overview" element={<LeagueOverview />} />
                <Route path="/player-profiles" element={<PlayerProfiles />} /> {/* Generic Player Profiles, will show list */}
                <Route path="/player-profiles/:playerName" element={<PlayerDetail />} /> {/* Dynamic Player Details */}
                <Route path="/manager-profiles" element={<ManagerProfiles />} /> {/* Generic Manager Profiles, will show list */}
                <Route path="/manager-profiles/:managerName" element={<ManagerDetail />} /> {/* Dynamic Manager Details */}
                <Route path="/team-details/:teamName" element={<TeamDetails />} /> {/* Dynamic Team Details */}
                <Route path="/transfer-market" element={<TransferMarket />} />
                <Route path="/match-reports" element={<MatchReports />} />
                <Route path="/match/:matchId" element={<MatchDetail />} />
                <Route path="/youth-academy" element={<YouthAcademy />} />
                <Route path="/season-reports" element={<SeasonReports />} />
                <Route path="/statistics-analytics" element={<StatisticsAnalytics />} />
                <Route path="*" element={<Placeholder title="Not Found" />} />
              </Routes>
              {toast && (
                <Toast
                  message={toast.message}
                  type={toast.type}
                  onClose={() => setToast(null)}
                />
              )}
            </Box>
          </Box>
        </Router>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
