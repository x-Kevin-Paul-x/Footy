import React, { useState, Suspense, lazy } from "react";
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
  CircularProgress,
  useTheme,
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

// Lazy-loaded page components for optimal bundle splitting & performance
const Dashboard = lazy(() => import("./pages/Dashboard"));
const LeagueOverview = lazy(() => import("./pages/LeagueOverview"));
const PlayerProfiles = lazy(() => import("./pages/PlayerProfiles"));
const PlayerDetail = lazy(() => import("./pages/PlayerDetail"));
const ManagerProfiles = lazy(() => import("./pages/ManagerProfiles"));
const ManagerDetail = lazy(() => import("./pages/ManagerDetail"));
const TeamDetails = lazy(() => import("./pages/TeamDetails"));
const TransferMarket = lazy(() => import("./pages/TransferMarket"));
const MatchReports = lazy(() => import("./pages/MatchReports"));
const MatchDetail = lazy(() => import("./pages/MatchDetail"));
const YouthAcademy = lazy(() => import("./pages/YouthAcademy"));
const SeasonReports = lazy(() => import("./pages/SeasonReports"));
const StatisticsAnalytics = lazy(() => import("./pages/StatisticsAnalytics"));
const MlBenchmarks = lazy(() => import("./pages/MlBenchmarks"));

import Toast from "./components/Toast";
import { HeaderBookmarksMenu } from "./components/HeaderBookmarksMenu";
import { HeaderAppLauncher } from "./components/HeaderAppLauncher";
import { HeaderNotificationsDrawer } from "./components/HeaderNotificationsDrawer";
import { HeaderSettingsModal } from "./components/HeaderSettingsModal";
import { HeaderProfileMenu } from "./components/HeaderProfileMenu";

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
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const pathnames = location.pathname.split('/').filter((x) => x);

  if (pathnames.length === 0) return null;

  return (
    <Box sx={{ mb: 3 }}>
      <Breadcrumbs
        separator={<NavigateNextIcon fontSize="small" sx={{ color: isDark ? '#8FE3EC' : '#01204E', opacity: 0.7 }} />}
        aria-label="breadcrumb"
      >
        <Link to="/" style={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }}>
          <Chip
            icon={<HomeIcon sx={{ fontSize: '14px !important', color: `${isDark ? '#8FE3EC' : '#01204E'} !important` }} />}
            label="Home"
            size="small"
            clickable
            sx={{
              bgcolor: isDark ? 'rgba(143, 227, 236, 0.12)' : 'rgba(1, 32, 78, 0.08)',
              color: isDark ? '#F8EBD5' : '#01204E',
              fontWeight: 700,
              height: 24,
              fontSize: '0.75rem',
              '&:hover': { bgcolor: isDark ? 'rgba(143, 227, 236, 0.22)' : 'rgba(1, 32, 78, 0.15)' }
            }}
          />
        </Link>
        {pathnames.map((value, index) => {
          const to = `/${pathnames.slice(0, index + 1).join('/')}`;
          const isLast = index === pathnames.length - 1;
          const formatted = value.replace(/-/g, ' ');

          return isLast ? (
            <Chip
              key={to}
              label={formatted}
              size="small"
              sx={{
                bgcolor: isDark ? 'rgba(248, 85, 37, 0.2)' : 'rgba(1, 32, 78, 0.15)',
                color: isDark ? '#F8EBD5' : '#01204E',
                fontWeight: 800,
                height: 24,
                fontSize: '0.75rem',
                textTransform: 'capitalize',
                border: isDark ? '1px solid rgba(248, 85, 37, 0.4)' : '1px solid rgba(1, 32, 78, 0.3)',
              }}
            />
          ) : (
            <Link key={to} to={to} style={{ textDecoration: 'none' }}>
              <Chip
                label={formatted}
                size="small"
                clickable
                sx={{
                  bgcolor: isDark ? 'rgba(143, 227, 236, 0.12)' : 'rgba(1, 32, 78, 0.08)',
                  color: isDark ? '#8FE3EC' : '#01204E',
                  fontWeight: 600,
                  height: 24,
                  fontSize: '0.75rem',
                  textTransform: 'capitalize',
                  '&:hover': { bgcolor: isDark ? 'rgba(143, 227, 236, 0.22)' : 'rgba(1, 32, 78, 0.15)' }
                }}
              />
            </Link>
          );
        })}
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
  const isDark = mode === 'dark';

  // Header popover & modal states
  const [bookmarksAnchor, setBookmarksAnchor] = useState<HTMLElement | null>(null);
  const [appsAnchor, setAppsAnchor] = useState<HTMLElement | null>(null);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [profileAnchor, setProfileAnchor] = useState<HTMLElement | null>(null);
  const [unreadCount, setUnreadCount] = useState(3);

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ message, type });
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default', color: 'text.secondary', p: { xs: 1.5, md: 2.5 }, transition: 'background-color 0.3s ease, color 0.3s ease' }}>
      {/* Top Header Bar - Floating Soft Tactile Capsule (Screenshot Style) */}
      <Box
        className="finnova-header-bar"
        sx={{
          px: { xs: 2, md: 3, lg: 4 },
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'nowrap',
          mb: 3,
          position: 'sticky',
          top: 16,
          zIndex: 1100,
          overflowX: 'auto',
          '&::-webkit-scrollbar': { display: 'none' }
        }}
      >
        {/* Left: Brand Logo & Title */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, whiteSpace: 'nowrap', flexShrink: 0 }}>
          <Avatar
            sx={{
              bgcolor: isDark ? '#132B4F' : '#01204E',
              width: 36,
              height: 36,
              border: isDark ? '1.5px solid rgba(248, 85, 37, 0.5)' : 'none',
              boxShadow: isDark ? '0 4px 14px rgba(0, 0, 0, 0.5)' : '0 4px 14px rgba(1, 32, 78, 0.4)',
            }}
          >
            <SportsSoccerIcon sx={{ color: isDark ? '#F85525' : '#028391', fontSize: 20 }} />
          </Avatar>
          <Box sx={{ display: { xs: 'none', sm: 'block' } }}>
            <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.1, fontFamily: 'Outfit, sans-serif', letterSpacing: '-0.02em', color: isDark ? '#F8EBD5' : '#01204E', fontSize: '1rem' }}>
              FOOTY
            </Typography>
            <Typography variant="caption" sx={{ fontWeight: 700, fontSize: '0.65rem', display: 'block', color: isDark ? '#8FE3EC' : '#01204E', opacity: 0.9 }}>
              Smart Analytics, Better Football
            </Typography>
          </Box>
          <Chip
            label="80"
            size="small"
            sx={{
              bgcolor: isDark ? '#132B4F' : '#F6DCAC',
              color: isDark ? '#8FE3EC' : '#01204E',
              border: isDark ? '1px solid rgba(2, 131, 145, 0.3)' : 'none',
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
          <IconButton
            size="small"
            title="Saved Favorites & Bookmarks"
            onClick={(e) => setBookmarksAnchor(e.currentTarget)}
            sx={{ color: isDark ? '#F8EBD5' : '#01204E', transition: 'all 0.2s', '&:hover': { transform: 'scale(1.1)' } }}
          >
            <BookmarkIcon fontSize="small" />
          </IconButton>

          <IconButton
            size="small"
            title="Module & View Launcher"
            onClick={(e) => setAppsAnchor(e.currentTarget)}
            sx={{ color: isDark ? '#F8EBD5' : '#01204E', transition: 'all 0.2s', '&:hover': { transform: 'scale(1.1)' } }}
          >
            <ViewModuleIcon fontSize="small" />
          </IconButton>

          <IconButton
            size="small"
            title="Live Activity Notifications"
            onClick={() => setNotificationsOpen(true)}
            sx={{ color: isDark ? '#F8EBD5' : '#01204E', transition: 'all 0.2s', '&:hover': { transform: 'scale(1.1)' } }}
          >
            <Badge
              badgeContent={unreadCount}
              sx={{
                '& .MuiBadge-badge': {
                  bgcolor: '#f43f5e',
                  color: '#fff',
                  fontWeight: 800,
                  fontSize: '0.65rem',
                  height: 16,
                  minWidth: 16,
                },
              }}
            >
              <NotificationsIcon fontSize="small" />
            </Badge>
          </IconButton>

          <IconButton
            size="small"
            title="Simulation & RL Settings"
            onClick={() => setSettingsOpen(true)}
            sx={{ color: isDark ? '#F8EBD5' : '#01204E', transition: 'all 0.2s', '&:hover': { transform: 'scale(1.1)' } }}
          >
            <SettingsIcon fontSize="small" />
          </IconButton>

          <IconButton
            size="small"
            title={`Switch to ${mode === 'light' ? 'Dark' : 'Light'} Mode`}
            onClick={() => setMode(mode === 'light' ? 'dark' : 'light')}
            sx={{ color: isDark ? '#F8EBD5' : '#01204E', transition: 'all 0.2s', '&:hover': { transform: 'scale(1.1)' } }}
          >
            {mode === 'light' ? <DarkModeIcon fontSize="small" /> : <LightModeIcon fontSize="small" />}
          </IconButton>

          <Avatar
            title="Manager Profile & Quick Save"
            onClick={(e) => setProfileAnchor(e.currentTarget)}
            sx={{
              width: 36,
              height: 36,
              ml: 1,
              bgcolor: isDark ? '#F85525' : '#01204E',
              color: '#ffffff',
              fontWeight: 800,
              fontSize: '0.85rem',
              border: isDark ? '2px solid #8FE3EC' : '2px solid #028391',
              boxShadow: isDark ? '0 4px 12px rgba(0, 0, 0, 0.6)' : '0 4px 12px rgba(1, 32, 78, 0.4)',
              cursor: 'pointer',
              transition: 'all 0.2s',
              '&:hover': { transform: 'scale(1.08)', boxShadow: isDark ? '0 6px 16px rgba(248, 85, 37, 0.5)' : '0 6px 16px rgba(1, 32, 78, 0.6)' },
            }}
          >
            FM
          </Avatar>
        </Box>
      </Box>

      {/* Header Dropdowns & Dialogs */}
      <HeaderBookmarksMenu
        anchorEl={bookmarksAnchor}
        open={Boolean(bookmarksAnchor)}
        onClose={() => setBookmarksAnchor(null)}
      />

      <HeaderAppLauncher
        anchorEl={appsAnchor}
        open={Boolean(appsAnchor)}
        onClose={() => setAppsAnchor(null)}
      />

      <HeaderNotificationsDrawer
        open={notificationsOpen}
        onClose={() => setNotificationsOpen(false)}
        unreadCount={unreadCount}
        setUnreadCount={setUnreadCount}
      />

      <HeaderSettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onShowToast={showToast}
      />

      <HeaderProfileMenu
        anchorEl={profileAnchor}
        open={Boolean(profileAnchor)}
        onClose={() => setProfileAnchor(null)}
        onShowToast={showToast}
      />

      {/* Main Page Area - Framed Inset Container (Screenshot Style) */}
      <Box className="finnova-main-frame" sx={{ p: { xs: 2.5, md: 4 }, maxWidth: 1600, mx: 'auto' }}>
        <AppBreadcrumbs />
        <Suspense fallback={<PageLoadingFallback />}>
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
        </Suspense>
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
  const [mode, setMode] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('footy_theme_mode') as 'light' | 'dark') || 'dark';
  });

  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', mode);
    localStorage.setItem('footy_theme_mode', mode);
    if (mode === 'dark') {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  }, [mode]);

  const theme = React.useMemo(() => {
    const isDark = mode === 'dark';
    return createTheme({
      palette: {
        mode,
        primary: {
          main: isDark ? '#F85525' : '#01204E',
          light: isDark ? '#ff7347' : '#028391',
          dark: isDark ? '#d43e12' : '#001330',
          contrastText: '#ffffff',
        },
        secondary: {
          main: isDark ? '#028391' : '#01204E',
          light: isDark ? '#8FE3EC' : '#028391',
          dark: isDark ? '#01204E' : '#001330',
          contrastText: '#ffffff',
        },
        background: {
          default: isDark ? '#06101E' : '#FAA968',
          paper: isDark ? '#0C1D36' : '#F6DCAC',
        },
        text: {
          primary: isDark ? '#F8EBD5' : '#01204E',
          secondary: isDark ? '#8FE3EC' : '#028391',
        },
        divider: isDark ? 'rgba(2, 131, 145, 0.22)' : 'rgba(1, 32, 78, 0.12)',
      },
      typography: {
        fontFamily: "'Inter', sans-serif",
        h1: { fontFamily: "'Outfit', sans-serif", fontWeight: 900, color: isDark ? '#F8EBD5' : '#01204E' },
        h2: { fontFamily: "'Outfit', sans-serif", fontWeight: 900, color: isDark ? '#F8EBD5' : '#01204E' },
        h3: { fontFamily: "'Outfit', sans-serif", fontWeight: 900, color: isDark ? '#F8EBD5' : '#01204E' },
        h4: { fontFamily: "'Outfit', sans-serif", fontWeight: 900, color: isDark ? '#F8EBD5' : '#01204E' },
        h5: { fontFamily: "'Outfit', sans-serif", fontWeight: 800, color: isDark ? '#F8EBD5' : '#01204E' },
        h6: { fontFamily: "'Outfit', sans-serif", fontWeight: 800, color: isDark ? '#F8EBD5' : '#01204E' },
        subtitle1: { color: isDark ? '#8FE3EC' : '#028391', fontWeight: 700 },
        subtitle2: { color: isDark ? '#8FE3EC' : '#028391', fontWeight: 700 },
        body1: { color: isDark ? '#8FE3EC' : '#028391' },
        body2: { color: isDark ? '#8FE3EC' : '#028391' },
        caption: { color: isDark ? '#6497A4' : '#028391' },
      },
      components: {
        MuiCard: {
          styleOverrides: {
            root: {
              backgroundImage: 'none',
              borderRadius: '24px',
              backgroundColor: isDark ? '#0C1D36' : '#F6DCAC',
              border: isDark ? '1.5px solid rgba(2, 131, 145, 0.22)' : '1.5px solid rgba(250, 169, 104, 0.45)',
              boxShadow: isDark
                ? '0 12px 36px rgba(0, 0, 0, 0.5), 0 2px 10px rgba(2, 131, 145, 0.12)'
                : '0 12px 32px rgba(1, 32, 78, 0.08), 0 2px 8px rgba(250, 169, 104, 0.3)',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              '&:hover': {
                transform: 'translateY(-3px)',
                boxShadow: isDark
                  ? '0 16px 42px rgba(0, 0, 0, 0.65), 0 4px 14px rgba(248, 85, 37, 0.3)'
                  : '0 16px 40px rgba(1, 32, 78, 0.12), 0 4px 14px rgba(250, 169, 104, 0.4)',
                borderColor: isDark ? 'rgba(248, 85, 37, 0.45)' : 'rgba(1, 32, 78, 0.25)',
              },
            },
          },
        },
        MuiPaper: {
          styleOverrides: {
            root: {
              backgroundColor: isDark ? '#0C1D36' : '#F6DCAC',
              color: isDark ? '#8FE3EC' : '#028391',
              borderRadius: '20px',
              backgroundImage: 'none',
            },
          },
        },
        MuiButton: {
          styleOverrides: {
            root: {
              borderRadius: '9999px',
              textTransform: 'none',
              fontWeight: 800,
              fontSize: '0.85rem',
              letterSpacing: '0.03em',
              backgroundColor: isDark ? '#F85525' : '#01204E',
              color: '#ffffff',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              boxShadow: isDark
                ? '0 8px 20px rgba(248, 85, 37, 0.35), inset 0 1px 1px rgba(255, 255, 255, 0.3)'
                : '0 8px 20px rgba(1, 32, 78, 0.35), inset 0 1px 1px rgba(255, 255, 255, 0.3)',
              transition: 'all 0.25s ease',
              '&:hover': {
                backgroundColor: isDark ? '#ff6f43' : '#028391',
                boxShadow: isDark
                  ? '0 12px 28px rgba(248, 85, 37, 0.5)'
                  : '0 12px 28px rgba(2, 131, 145, 0.45)',
                transform: 'translateY(-2px)',
              },
            },
            containedPrimary: {
              backgroundColor: isDark ? '#F85525' : '#01204E',
              color: '#ffffff',
              '&:hover': {
                backgroundColor: isDark ? '#ff6f43' : '#028391',
              },
            },
            containedSecondary: {
              backgroundColor: isDark ? '#028391' : '#01204E',
              color: '#ffffff',
              '&:hover': {
                backgroundColor: isDark ? '#02a0b1' : '#028391',
              },
            },
            outlinedPrimary: {
              borderColor: isDark ? '#F85525' : '#01204E',
              color: isDark ? '#F85525' : '#01204E',
              backgroundColor: 'transparent',
              '&:hover': {
                backgroundColor: isDark ? 'rgba(248, 85, 37, 0.12)' : 'rgba(1, 32, 78, 0.08)',
                borderColor: isDark ? '#ff7347' : '#028391',
              },
            },
          },
        },
        MuiTableCell: {
          styleOverrides: {
            head: {
              color: isDark ? '#F8EBD5' : '#01204E',
              fontWeight: 800,
              borderBottom: isDark ? '1px solid rgba(2, 131, 145, 0.2)' : '1px solid rgba(1, 32, 78, 0.15)',
            },
            body: {
              color: isDark ? '#8FE3EC' : '#028391',
              borderBottom: isDark ? '1px solid rgba(2, 131, 145, 0.1)' : '1px solid rgba(1, 32, 78, 0.08)',
            },
          },
        },
        MuiChip: {
          styleOverrides: {
            root: {
              fontWeight: 800,
              borderRadius: '9999px',
            },
            filled: {
              backgroundColor: isDark ? '#132B4F' : '#01204E',
              color: isDark ? '#F8EBD5' : '#ffffff',
            },
          },
        },
      },
    });
  }, [mode]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <MainLayout mode={mode} setMode={setMode} toast={toast} setToast={setToast} />
      </Router>
    </ThemeProvider>
  );
}

const PageLoadingFallback: React.FC = () => (
  <Box
    sx={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '50vh',
      gap: 2,
      py: 8,
    }}
  >
    <CircularProgress size={44} sx={{ color: '#F85525' }} thickness={4} />
    <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.secondary', letterSpacing: '0.04em' }}>
      Loading Module...
    </Typography>
  </Box>
);

const Placeholder: React.FC<{ title: string }> = ({ title }) => (
  <Box sx={{ p: 4, textAlign: 'center' }}>
    <Typography variant="h4" sx={{ fontWeight: 800, mb: 1, fontFamily: 'Outfit, sans-serif' }}>{title}</Typography>
    <Typography color="text.secondary">This page module is coming soon.</Typography>
  </Box>
);

export default App;
