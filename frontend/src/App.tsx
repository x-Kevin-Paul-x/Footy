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
} from "@mui/material";
import NavigateNextIcon from "@mui/icons-material/NavigateNext";
import HomeIcon from "@mui/icons-material/Home";
import SportsSoccerIcon from "@mui/icons-material/SportsSoccer";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import LightModeIcon from "@mui/icons-material/LightMode";

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
                bgcolor: isLast ? 'rgba(22, 163, 74, 0.15)' : 'transparent',
                color: isLast ? '#15803d' : 'text.primary',
                fontWeight: isLast ? 700 : 500,
                height: 24,
                fontSize: '0.75rem',
                textTransform: 'capitalize',
                border: isLast ? '1px solid rgba(34, 197, 94, 0.3)' : 'none',
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
    <Box sx={{ minHeight: '100vh', color: mode === 'dark' ? '#f1f5f9' : '#1e293b' }}>
      {/* Top Floating Header Bar - Clean Floating Anchorpoint Capsule */}
      <Box
        sx={{
          maxWidth: 1600,
          mx: 'auto',
          px: { xs: 2, md: 4 },
          pt: 2,
          pb: 1,
          position: 'sticky',
          top: 0,
          zIndex: 1100,
        }}
      >
        <Box
          className="finnova-nav-capsule"
          sx={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: { xs: 2, md: 3 },
            py: 1,
          }}
        >
          {/* Left: Brand Logo & Title */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, whiteSpace: 'nowrap', flexShrink: 0 }}>
            <Avatar
              sx={{
                bgcolor: 'rgba(34, 197, 94, 0.25)',
                color: '#ffffff',
                width: 38,
                height: 38,
                border: '1px solid rgba(74, 222, 128, 0.4)',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
              }}
            >
              <SportsSoccerIcon sx={{ color: '#4ade80', fontSize: 22 }} />
            </Avatar>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.1, fontFamily: 'Outfit, sans-serif', letterSpacing: '0.05em', color: '#ffffff', fontSize: '1.05rem' }}>
                FOOTY
              </Typography>
              <Typography variant="caption" sx={{ fontWeight: 700, fontSize: '0.65rem', display: 'block', color: '#4ade80', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Tactical Infrastructure
              </Typography>
            </Box>
          </Box>

          {/* Center: Segmented Navigation */}
          <Box
            sx={{
              display: { xs: 'none', md: 'flex' },
              alignItems: 'center',
              gap: 0.5,
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

          {/* Right: + INITIATE Button & User Avatar */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, flexShrink: 0 }}>
            <button className="turf-pill-btn">
              + INITIATE
            </button>
            <IconButton
              size="small"
              onClick={() => setMode(mode === 'light' ? 'dark' : 'light')}
              sx={{ color: '#ffffff', background: 'rgba(255,255,255,0.12)', border: '1px solid rgba(255,255,255,0.2)' }}
            >
              {mode === 'light' ? <DarkModeIcon fontSize="small" /> : <LightModeIcon fontSize="small" />}
            </IconButton>
            <Avatar
              sx={{
                width: 36,
                height: 36,
                bgcolor: 'rgba(4, 28, 12, 0.85)',
                color: '#ffffff',
                fontWeight: 800,
                fontSize: '0.85rem',
                border: '1px solid rgba(255, 255, 255, 0.4)',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
                cursor: 'pointer'
              }}
            >
              FM
            </Avatar>
          </Box>
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
            main: '#16a34a',
            light: '#22c55e',
            dark: '#15803d',
            contrastText: '#ffffff',
          },
          secondary: {
            main: '#4ade80',
            contrastText: '#06170d',
          },
          background: {
            default: 'transparent',
            paper: '#154a22',
          },
          text: {
            primary: '#ffffff',
            secondary: '#a7f3d0',
          },
          divider: 'rgba(255, 255, 255, 0.14)',
        },
        typography: {
          fontFamily: "'Nunito', 'Inter', sans-serif",
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
                backgroundColor: '#154a22 !important',
                borderRadius: '28px',
                border: '1px solid rgba(255, 255, 255, 0.14)',
                boxShadow: '9px 9px 20px rgba(3, 14, 6, 0.88), -9px -9px 20px rgba(36, 128, 58, 0.38)',
                color: '#ffffff',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                '&:hover': {
                  transform: 'translateY(-3px)',
                  boxShadow: '14px 14px 28px rgba(3, 14, 6, 0.95), -12px -12px 24px rgba(36, 128, 58, 0.48)',
                  borderColor: 'rgba(74, 222, 128, 0.35)',
                },
              },
            },
          },
          MuiPaper: {
            styleOverrides: {
              root: {
                backgroundImage: 'none',
                backgroundColor: '#154a22 !important',
                borderRadius: '28px',
                border: '1px solid rgba(255, 255, 255, 0.14)',
                boxShadow: '9px 9px 20px rgba(3, 14, 6, 0.88), -9px -9px 20px rgba(36, 128, 58, 0.38)',
                color: '#ffffff',
              },
            },
          },
          MuiButton: {
            styleOverrides: {
              root: {
                borderRadius: '9999px',
                textTransform: 'uppercase',
                fontWeight: 800,
                letterSpacing: '0.05em',
                boxShadow: '6px 6px 14px rgba(3, 14, 6, 0.88), -5px -5px 12px rgba(36, 128, 58, 0.38)',
              },
              contained: {
                backgroundColor: '#154a22 !important',
                color: '#ffffff !important',
                border: '1px solid rgba(255, 255, 255, 0.25)',
                '&:hover': {
                  backgroundColor: '#1c5e2d !important',
                  color: '#4ade80 !important',
                  boxShadow: '9px 9px 18px rgba(3, 14, 6, 0.95), -7px -7px 15px rgba(36, 128, 58, 0.45)',
                },
                '&:active': {
                  boxShadow: 'inset 5px 5px 10px rgba(2, 10, 4, 0.85), inset -5px -5px 10px rgba(28, 98, 45, 0.3) !important',
                },
              },
            },
          },
          MuiChip: {
            styleOverrides: {
              root: {
                fontWeight: 800,
                borderRadius: '9999px',
              },
            },
          },
          MuiTableCell: {
            styleOverrides: {
              root: {
                borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                color: '#ffffff',
              },
              head: {
                color: '#4ade80',
                fontWeight: 800,
                backgroundColor: '#0a2711',
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
