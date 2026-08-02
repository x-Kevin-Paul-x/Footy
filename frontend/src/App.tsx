import React, { useState } from "react";
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from "react-router-dom";
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  Box,
  Typography,
  Breadcrumbs,
  Chip,
  Avatar,
  IconButton,
  Badge,
} from "@mui/material";
import NavigateNextIcon from "@mui/icons-material/NavigateNext";
import HomeIcon from "@mui/icons-material/Home";
import SportsSoccerIcon from "@mui/icons-material/SportsSoccer";
import NotificationsIcon from "@mui/icons-material/Notifications";
import SettingsIcon from "@mui/icons-material/Settings";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import LightModeIcon from "@mui/icons-material/LightMode";
import BookmarkIcon from "@mui/icons-material/Bookmark";
import ViewModuleIcon from "@mui/icons-material/ViewModule";

// Lazy / direct page imports from src/pages
import Dashboard from "./pages/Dashboard";
import LeagueOverview from "./pages/LeagueOverview";
import PlayerProfiles from "./pages/PlayerProfiles";
import PlayerDetail from "./pages/PlayerDetail";
import ManagerProfiles from "./pages/ManagerProfiles";
import ManagerDetail from "./pages/ManagerDetail";
import TeamDetails from "./pages/TeamDetails";
import TransferMarket from "./pages/TransferMarket";
import MatchReports from "./pages/MatchReports";
import MatchDetail from "./pages/MatchDetail";
import YouthAcademy from "./pages/YouthAcademy";
import SeasonReports from "./pages/SeasonReports";
import StatisticsAnalytics from "./pages/StatisticsAnalytics";
import MlBenchmarks from "./pages/MlBenchmarks";
import Toast from "./components/Toast";

const sections = [
  { label: "Overview", path: "/" },
  { label: "League", path: "/league-overview" },
  { label: "Players", path: "/player-profiles" },
  { label: "Managers", path: "/manager-profiles" },
  { label: "Transfers", path: "/transfer-market" },
  { label: "Matches", path: "/match-reports" },
  { label: "Academy", path: "/youth-academy" },
  { label: "Season", path: "/season-reports" },
  { label: "Analytics", path: "/statistics-analytics" },
  { label: "AI Benchmarks", path: "/ai-benchmarks" },
];

function AppBreadcrumbs() {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter((x) => x);

  if (pathnames.length === 0) return null;

  const validStaticRoutes = sections.map((s) => s.path);
  const dynamicRoutePatterns = ['/team-details', '/player-profiles', '/manager-profiles', '/match'];

  return (
    <Box
      sx={{
        py: 0.8,
        px: 2,
        mb: 2.5,
        borderRadius: 9999,
        display: 'inline-flex',
        alignItems: 'center',
        background: 'background.paper',
        boxShadow: '0 2px 10px rgba(0,0,0,0.03)',
        border: 1,
        borderColor: 'divider',
      }}
    >
      <Breadcrumbs
        separator={<NavigateNextIcon fontSize="small" sx={{ color: 'text.disabled', fontSize: 14 }} />}
        aria-label="breadcrumb"
      >
        <Chip
          component={Link}
          to="/"
          icon={<HomeIcon sx={{ fontSize: 14 }} />}
          label="Home"
          size="small"
          clickable
          sx={{ bgcolor: 'transparent', height: 24, fontSize: '0.75rem', '&:hover': { bgcolor: 'action.hover' } }}
        />
        {pathnames.map((value, idx) => {
          const to = `/${pathnames.slice(0, idx + 1).join('/')}`;
          const section = sections.find((s) => s.path === to);
          
          // Friendly label formatting (e.g. replace raw match IDs like '3031' with 'Match Detail')
          let label = section?.label || decodeURIComponent(value).replace(/-/g, ' ');
          if (pathnames[idx - 1] === 'match') {
            label = 'Match Detail';
          } else if (!isNaN(Number(value))) {
            label = `ID: ${value}`;
          }

          const isLast = idx === pathnames.length - 1;
          const isValidRoute = validStaticRoutes.includes(to) ||
            (dynamicRoutePatterns.some(pattern => to.startsWith(pattern)) && to !== dynamicRoutePatterns.find(p => to.startsWith(p)));

          if (!isLast && dynamicRoutePatterns.includes(to)) return null;

          return (
            <Chip
              key={to}
              component={isLast || !isValidRoute ? 'span' : Link}
              to={isLast || !isValidRoute ? undefined : to}
              label={label}
              size="small"
              clickable={!isLast && isValidRoute}
              sx={{
                bgcolor: isLast ? 'rgba(79, 70, 229, 0.12)' : 'transparent',
                color: isLast ? '#4f46e5' : 'text.primary',
                fontWeight: isLast ? 700 : 500,
                height: 24,
                fontSize: '0.75rem',
                textTransform: 'capitalize',
                border: isLast ? '1px solid rgba(79, 70, 229, 0.25)' : 'none',
              }}
            />
          );
        }).filter(Boolean)}
      </Breadcrumbs>
    </Box>
  );
}

function MainLayout({ mode, setMode, toast, setToast }: {
  mode: 'light' | 'dark';
  setMode: (mode: 'light' | 'dark') => void;
  toast: { message: string; type?: "success" | "error" | "info" } | null;
  setToast: (t: { message: string; type?: "success" | "error" | "info" } | null) => void;
}) {
  const location = useLocation();

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: mode === 'dark' ? '#0b0d14' : '#f3f4f8', color: mode === 'dark' ? '#f1f5f9' : '#1e293b' }}>
      {/* Top FINNOVA Header Bar - Single Row Alignment */}
      <Box
        sx={{
          px: { xs: 2, md: 3, lg: 4 },
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'nowrap',
          borderBottom: mode === 'dark' ? '1px solid rgba(255, 255, 255, 0.08)' : '1px solid rgba(0, 0, 0, 0.06)',
          background: mode === 'dark' ? '#0f111a' : '#ffffff',
          position: 'sticky',
          top: 0,
          zIndex: 1100,
          boxShadow: mode === 'dark' ? '0 4px 20px rgba(0,0,0,0.4)' : '0 4px 20px rgba(0,0,0,0.03)',
          overflowX: 'auto',
          '&::-webkit-scrollbar': { display: 'none' }
        }}
      >
        {/* Left: Brand Logo & Title */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, whiteSpace: 'nowrap', flexShrink: 0 }}>
          <Avatar
            sx={{
              bgcolor: '#4f46e5',
              width: 36,
              height: 36,
              boxShadow: '0 4px 14px rgba(79, 70, 229, 0.4)',
            }}
          >
            <SportsSoccerIcon sx={{ color: '#ffffff', fontSize: 20 }} />
          </Avatar>
          <Box sx={{ display: { xs: 'none', sm: 'block' } }}>
            <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.1, fontFamily: 'Outfit, sans-serif', letterSpacing: '-0.02em', color: mode === 'dark' ? '#ffffff' : '#0f172a', fontSize: '1rem' }}>
              FOOTY
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, fontSize: '0.65rem', display: 'block' }}>
              Smart Analytics, Better Football
            </Typography>
          </Box>
          <Chip
            label="80"
            size="small"
            sx={{
              bgcolor: mode === 'dark' ? 'rgba(255,255,255,0.1)' : '#f1f5f9',
              color: mode === 'dark' ? '#cbd5e1' : '#64748b',
              fontWeight: 800,
              height: 20,
              fontSize: '0.7rem',
              borderRadius: 9999,
            }}
          />
        </Box>

        {/* Center: Capsule Pill Navigation */}
        <Box
          className="finnova-nav-capsule"
          sx={{
            display: { xs: 'none', md: 'flex' },
            alignItems: 'center',
            gap: 0.3,
            mx: 2,
            flexShrink: 1,
            overflowX: 'auto',
            '&::-webkit-scrollbar': { display: 'none' }
          }}
        >
          {sections.map((sec) => {
            const isActive = location.pathname === sec.path || (sec.path !== '/' && location.pathname.startsWith(sec.path));
            return (
              <Link
                key={sec.path}
                to={sec.path}
                className={`finnova-nav-item ${isActive ? 'active' : ''}`}
              >
                {sec.label}
              </Link>
            );
          })}
        </Box>

        {/* Right: Actions & User Avatar */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8, flexShrink: 0, justifyContent: 'flex-end' }}>
          <IconButton size="small" sx={{ color: mode === 'dark' ? '#94a3b8' : '#64748b' }}>
            <BookmarkIcon fontSize="small" />
          </IconButton>
          <IconButton size="small" sx={{ color: mode === 'dark' ? '#94a3b8' : '#64748b' }}>
            <ViewModuleIcon fontSize="small" />
          </IconButton>
          <IconButton size="small" sx={{ color: mode === 'dark' ? '#94a3b8' : '#64748b' }}>
            <Badge variant="dot" color="error">
              <NotificationsIcon fontSize="small" />
            </Badge>
          </IconButton>
          <IconButton size="small" sx={{ color: mode === 'dark' ? '#94a3b8' : '#64748b' }}>
            <SettingsIcon fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            onClick={() => setMode(mode === 'light' ? 'dark' : 'light')}
            sx={{ color: mode === 'dark' ? '#fbbf24' : '#64748b' }}
          >
            {mode === 'light' ? <DarkModeIcon fontSize="small" /> : <LightModeIcon fontSize="small" />}
          </IconButton>
          <Avatar
            sx={{
              width: 36,
              height: 36,
              ml: 1,
              bgcolor: '#4f46e5',
              color: '#ffffff',
              fontWeight: 800,
              fontSize: '0.85rem',
              border: '2px solid #818cf8',
              boxShadow: '0 4px 12px rgba(79, 70, 229, 0.4)',
              cursor: 'pointer'
            }}
          >
            FM
          </Avatar>
        </Box>
      </Box>

      {/* Main Page Area */}
      <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: 1600, mx: 'auto' }}>
        <AppBreadcrumbs />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/league-overview" element={<LeagueOverview />} />
          <Route path="/player-profiles" element={<PlayerProfiles />} />
          <Route path="/player-profiles/:playerName" element={<PlayerDetail />} />
          <Route path="/manager-profiles" element={<ManagerProfiles />} />
          <Route path="/manager-profiles/:managerName" element={<ManagerDetail />} />
          <Route path="/team-details/:teamName" element={<TeamDetails />} />
          <Route path="/transfer-market" element={<TransferMarket />} />
          <Route path="/match-reports" element={<MatchReports />} />
          <Route path="/match/:matchId" element={<MatchDetail />} />
          <Route path="/youth-academy" element={<YouthAcademy />} />
          <Route path="/season-reports" element={<SeasonReports />} />
          <Route path="/statistics-analytics" element={<StatisticsAnalytics />} />
          <Route path="/ai-benchmarks" element={<MlBenchmarks />} />
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
  );
}

function App() {
  const [toast, setToast] = useState<{ message: string; type?: "success" | "error" | "info" } | null>(null);
  const [mode, setMode] = useState<'light' | 'dark'>('light');

  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', mode);
    if (mode === 'dark') {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  }, [mode]);

  const theme = React.useMemo(
    () =>
      createTheme({
        palette: {
          mode,
          primary: {
            main: '#4f46e5',
            light: '#6366f1',
            dark: '#3730a3',
            contrastText: '#ffffff',
          },
          secondary: {
            main: '#fbbf24',
            contrastText: '#0f172a',
          },
          background: {
            default: mode === 'dark' ? '#0b0d14' : '#f3f4f8',
            paper: mode === 'dark' ? '#161826' : '#ffffff',
          },
          text: {
            primary: mode === 'dark' ? '#f1f5f9' : '#0f172a',
            secondary: mode === 'dark' ? '#94a3b8' : '#64748b',
          },
          divider: mode === 'dark' ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
        },
        typography: {
          fontFamily: "'Inter', sans-serif",
          h1: { fontFamily: "'Outfit', sans-serif", fontWeight: 800 },
          h2: { fontFamily: "'Outfit', sans-serif", fontWeight: 800 },
          h3: { fontFamily: "'Outfit', sans-serif", fontWeight: 800 },
          h4: { fontFamily: "'Outfit', sans-serif", fontWeight: 800 },
          h5: { fontFamily: "'Outfit', sans-serif", fontWeight: 700 },
          h6: { fontFamily: "'Outfit', sans-serif", fontWeight: 700 },
        },
        components: {
          MuiCard: {
            styleOverrides: {
              root: {
                backgroundImage: 'none',
                borderRadius: '16px',
              },
            },
          },
          MuiButton: {
            styleOverrides: {
              root: {
                borderRadius: '10px',
                textTransform: 'none',
                fontWeight: 600,
              },
            },
          },
        },
      }),
    [mode]
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <MainLayout mode={mode} setMode={setMode} toast={toast} setToast={setToast} />
      </Router>
    </ThemeProvider>
  );
}

const Placeholder: React.FC<{ title: string }> = ({ title }) => (
  <Box sx={{ p: 4, textAlign: 'center' }}>
    <Typography variant="h4" sx={{ fontWeight: 800, mb: 1, fontFamily: 'Outfit, sans-serif' }}>{title}</Typography>
    <Typography color="text.secondary">This page module is coming soon.</Typography>
  </Box>
);

export default App;
