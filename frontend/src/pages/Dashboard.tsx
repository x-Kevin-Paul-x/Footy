import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Typography,
  Box,
  CircularProgress,
  Alert,
  Chip,
  Avatar,
  IconButton,
  Button,
  useTheme,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  FormControl,
  Select,
  MenuItem,
} from "@mui/material";
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSimulationSocket } from "../hooks/useSimulationSocket";
import { useSimulationStore } from "../store/simulationStore";
import {
  getAllSeasonsOverview,
  getSeasonReportData,
  getMatchesBySeason,
  runSimulation
} from "../services/api";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend,
} from "recharts";

// Icons
import SportsSoccerIcon from "@mui/icons-material/SportsSoccer";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import AddIcon from "@mui/icons-material/Add";
import TuneIcon from "@mui/icons-material/Tune";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import StarIcon from "@mui/icons-material/Star";
import LeaderboardIcon from "@mui/icons-material/Leaderboard";
import EventNoteIcon from "@mui/icons-material/EventNote";

// Club Palette map
const CLUB_PALETTES: { [key: string]: { code: string; bg: string } } = {
  "arsenal": { code: "ARS", bg: "linear-gradient(135deg, #ef4444 0%, #991b1b 100%)" },
  "chelsea": { code: "CHE", bg: "linear-gradient(135deg, #2563eb 0%, #1e40af 100%)" },
  "manchester city": { code: "MCI", bg: "linear-gradient(135deg, #38bdf8 0%, #0284c7 100%)" },
  "man city": { code: "MCI", bg: "linear-gradient(135deg, #38bdf8 0%, #0284c7 100%)" },
  "manchester united": { code: "MUN", bg: "linear-gradient(135deg, #dc2626 0%, #7f1d1d 100%)" },
  "man united": { code: "MUN", bg: "linear-gradient(135deg, #dc2626 0%, #7f1d1d 100%)" },
  "liverpool": { code: "LIV", bg: "linear-gradient(135deg, #e11d48 0%, #9f1239 100%)" },
  "tottenham": { code: "TOT", bg: "linear-gradient(135deg, #475569 0%, #0f172a 100%)" },
  "spurs": { code: "TOT", bg: "linear-gradient(135deg, #475569 0%, #0f172a 100%)" },
  "brighton": { code: "BHA", bg: "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)" },
  "aston villa": { code: "AVL", bg: "linear-gradient(135deg, #7c3aed 0%, #4c1d95 100%)" },
  "newcastle": { code: "NEW", bg: "linear-gradient(135deg, #334155 0%, #0f172a 100%)" },
  "wolves": { code: "WOL", bg: "linear-gradient(135deg, #f59e0b 0%, #b45309 100%)" },
  "west ham": { code: "WHU", bg: "linear-gradient(135deg, #9333ea 0%, #581c87 100%)" },
  "everton": { code: "EVE", bg: "linear-gradient(135deg, #1d4ed8 0%, #1e3a8a 100%)" },
  "fulham": { code: "FUL", bg: "linear-gradient(135deg, #64748b 0%, #1e293b 100%)" },
  "brentford": { code: "BRE", bg: "linear-gradient(135deg, #ea580c 0%, #9a3412 100%)" },
  "crystal palace": { code: "CRY", bg: "linear-gradient(135deg, #2563eb 0%, #dc2626 100%)" },
  "nottingham forest": { code: "NFO", bg: "linear-gradient(135deg, #f43f5e 0%, #881337 100%)" },
  "burnley": { code: "BUR", bg: "linear-gradient(135deg, #881337 0%, #4c0519 100%)" },
  "sheffield united": { code: "SHU", bg: "linear-gradient(135deg, #ef4444 0%, #450a0a 100%)" },
  "luton": { code: "LUT", bg: "linear-gradient(135deg, #f97316 0%, #7c2d12 100%)" },
};

function getClubMeta(teamName: string) {
  const clean = (teamName || "").toLowerCase().trim();
  if (CLUB_PALETTES[clean]) return CLUB_PALETTES[clean];
  const code = teamName ? teamName.substring(0, 3).toUpperCase() : "FC";
  const bg = "linear-gradient(135deg, #6366f1 0%, #3730a3 100%)";
  return { code, bg };
}

const barWidgetData = [
  { val: 65 }, { val: 80 }, { val: 75 }, { val: 95 }, { val: 85 }, { val: 110 }
];

const Dashboard: React.FC = () => {
  const theme = useTheme();
  const { availableSeasons, fetchAvailableSeasons } = useSimulationStore();
  const queryClient = useQueryClient();
  useSimulationSocket();

  const [selectedDashboardSeason, setSelectedDashboardSeason] = React.useState<number | null>(null);

  useEffect(() => {
    fetchAvailableSeasons();
  }, [fetchAvailableSeasons]);

  const sortedSeasons = React.useMemo(() => [...availableSeasons].sort((a, b) => b - a), [availableSeasons]);
  const activeSeasonYear = selectedDashboardSeason ?? (sortedSeasons.length > 0 ? sortedSeasons[0] : 2026);

  // 1. All Seasons Overview
  const { data: allSeasonsData, error: seasonsErr } = useQuery({
    queryKey: ['allSeasonsOverview'],
    queryFn: getAllSeasonsOverview,
  });

  // 2. Selected Season Detailed Report (for Standings Table)
  const { data: seasonReport } = useQuery({
    queryKey: ['seasonReport', activeSeasonYear],
    queryFn: () => getSeasonReportData(activeSeasonYear),
    enabled: !!activeSeasonYear,
  });

  // 3. Recent Matches (for Match Center)
  const { data: matchesData } = useQuery({
    queryKey: ['matchesBySeason', activeSeasonYear],
    queryFn: () => getMatchesBySeason(activeSeasonYear),
    enabled: !!activeSeasonYear,
  });

  const runSimMutation = useMutation({
    mutationFn: runSimulation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['financialSummary'] });
      queryClient.invalidateQueries({ queryKey: ['transferActivity'] });
      queryClient.invalidateQueries({ queryKey: ['allSeasonsOverview'] });
      queryClient.invalidateQueries({ queryKey: ['seasonReport'] });
      queryClient.invalidateQueries({ queryKey: ['matchesBySeason'] });
      fetchAvailableSeasons();
    }
  });

  if (seasonsErr) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ bgcolor: 'rgba(244, 63, 94, 0.1)', color: '#f43f5e', border: '1px solid rgba(244, 63, 94, 0.2)' }}>
          Failed to load football simulation data. Please try again.
        </Alert>
      </Box>
    );
  }

  const totalSeasons = allSeasonsData?.total_seasons ?? 0;
  const latestSummary = allSeasonsData?.seasons?.[0];
  const championTeam = latestSummary?.champions || "Wolves";
  const championPoints = latestSummary?.champion_points || 89;
  const topScorer = latestSummary?.top_scorer || { name: "Megan Amerson", team: "Spurs", goals: 28 };

  // Parse League Standings Table
  const rawTable = seasonReport?.table || [];
  const standings = rawTable.map(([teamName, stats]: any, idx: number) => {
    const w = Number(stats.won ?? stats.w ?? 0);
    const d = Number(stats.drawn ?? stats.d ?? 0);
    const l = Number(stats.lost ?? stats.l ?? 0);
    const gf = Number(stats.gf ?? 0);
    const ga = Number(stats.ga ?? 0);
    const gd = Number(stats.gd ?? (gf - ga));
    const pts = Number(stats.points ?? stats.pts ?? 0);
    const mp = Number(stats.played ?? stats.p ?? stats.mp ?? (w + d + l));

    return {
      rank: idx + 1,
      name: String(teamName),
      mp,
      w,
      d,
      l,
      gf,
      ga,
      gd,
      pts,
    };
  }).sort((a, b) => b.pts - a.pts || b.gd - a.gd || b.gf - a.gf);

  // Multi-Season Chart Data
  const seasonTrendData = [...(allSeasonsData?.seasons || [])]
    .sort((a, b) => (a?.season_year ?? 0) - (b?.season_year ?? 0))
    .map(s => ({
      season: `Season ${s?.season_year ?? 0}`,
      goals: s?.total_goals ?? 0,
      transfers: s?.transfers_completed ?? 0,
    }));

  const recentMatches = (matchesData || []).slice(0, 5);
  const bestPlayersList = (seasonReport?.best_players || []).slice(0, 5);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3.5, pb: 6 }}>

      {/* 1. HERO TITLE & SIMULATION COMMAND HUB */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2, p: { xs: 2.5, md: 3 }, borderRadius: '24px', bgcolor: '#F6DCAC', border: '1.5px solid rgba(250, 169, 104, 0.45)', boxShadow: '0 12px 32px rgba(1, 32, 78, 0.08), 0 2px 8px rgba(250, 169, 104, 0.3), inset 0 1px 2px rgba(255, 245, 225, 0.6)' }}>
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
            <FormControl size="small">
              <Select
                value={activeSeasonYear}
                onChange={(e) => setSelectedDashboardSeason(Number(e.target.value))}
                displayEmpty
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: '#01204E' }} />
                    <Typography variant="caption" sx={{ fontWeight: 800, color: '#01204E', letterSpacing: '0.06em', textTransform: 'uppercase', fontSize: '0.72rem' }}>
                      SEASON {selected} COMMAND CENTER
                    </Typography>
                  </Box>
                )}
                sx={{
                  borderRadius: 9999,
                  bgcolor: '#FAA968',
                  border: '1px solid rgba(1, 32, 78, 0.15)',
                  boxShadow: '0 4px 12px rgba(1, 32, 78, 0.06)',
                  height: 32,
                  '& .MuiSelect-select': {
                    display: 'flex',
                    alignItems: 'center',
                    py: '4px !important',
                    pl: '14px !important',
                    pr: '28px !important'
                  },
                  '& .MuiOutlinedInput-notchedOutline': { border: 'none' },
                  '&:hover': { bgcolor: '#f79a52' },
                  '& .MuiSvgIcon-root': { color: '#01204E' }
                }}
              >
                {sortedSeasons.map((s) => (
                  <MenuItem key={s} value={s} sx={{ fontWeight: 700, fontSize: '0.82rem' }}>
                    Season {s} Command Center
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          <Typography variant="h3" sx={{ fontWeight: 900, fontFamily: 'Outfit, sans-serif', color: '#01204E', letterSpacing: '-0.03em', fontSize: { xs: '1.8rem', md: '2.4rem' } }}>
            Premier League Command Center
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600, color: '#028391', mt: 0.5 }}>
            Real-time league standings, match results, top goalscorers, and AI season simulation.
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Button
            variant="contained"
            onClick={() => runSimMutation.mutate()}
            disabled={runSimMutation.isPending}
            startIcon={runSimMutation.isPending ? <CircularProgress size={18} color="inherit" /> : <AddIcon />}
            className="finnova-tactile-btn"
          >
            Run Season Simulation
          </Button>
        </Box>
      </Box>

      {/* 2. STATS OVERVIEW SUMMARY CARDS */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr 1fr' }, gap: 2.5 }}>

        {/* CARD 1: Reigning Champions */}
        <Card className="finnova-card">
          <CardContent sx={{ p: 2.5, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', gap: 1.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="caption" sx={{ fontWeight: 800, color: '#028391', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Reigning Champions
              </Typography>
              <Avatar sx={{ bgcolor: 'rgba(250, 169, 104, 0.25)', color: '#01204E', width: 32, height: 32 }}>
                <EmojiEventsIcon fontSize="small" />
              </Avatar>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Avatar sx={{ width: 44, height: 44, bgcolor: '#FAA968', color: '#01204E', fontWeight: 900, fontSize: '0.9rem', border: '1px solid rgba(1, 32, 78, 0.2)' }}>
                {championTeam.substring(0, 3).toUpperCase()}
              </Avatar>
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 900, color: '#01204E', fontFamily: 'Outfit, sans-serif' }}>
                  {championTeam}
                </Typography>
                <Typography variant="caption" sx={{ fontWeight: 700, color: '#028391' }}>
                  {championPoints} Points Accumulated
                </Typography>
              </Box>
            </Box>
            <Box sx={{ pt: 1, borderTop: '1px solid rgba(1, 32, 78, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="caption" sx={{ fontWeight: 700, color: '#028391' }}>Title Winner</Typography>
              <Typography variant="caption" sx={{ fontWeight: 800, color: '#01204E' }}>Season {activeSeasonYear}</Typography>
            </Box>
          </CardContent>
        </Card>

        {/* CARD 2: Top Scorer / Golden Boot */}
        <Card className="finnova-card">
          <CardContent sx={{ p: 2.5, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', gap: 1.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="caption" sx={{ fontWeight: 800, color: '#028391', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Golden Boot Leader
              </Typography>
              <Avatar sx={{ bgcolor: 'rgba(2, 131, 145, 0.15)', color: '#028391', width: 32, height: 32 }}>
                <SportsSoccerIcon fontSize="small" />
              </Avatar>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Avatar sx={{ width: 44, height: 44, bgcolor: '#028391', color: '#ffffff', fontWeight: 800, fontSize: '0.9rem' }}>
                {topScorer.name ? topScorer.name.substring(0, 2).toUpperCase() : "MA"}
              </Avatar>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 800, color: '#01204E', fontFamily: 'Outfit, sans-serif', lineHeight: 1.2 }}>
                  {topScorer.name}
                </Typography>
                <Typography variant="caption" sx={{ fontWeight: 600, color: '#028391' }}>
                  {topScorer.team} • <strong style={{ color: '#01204E' }}>{topScorer.goals} Goals</strong>
                </Typography>
              </Box>
            </Box>
            <Box sx={{ pt: 1, borderTop: '1px solid rgba(1, 32, 78, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="caption" sx={{ fontWeight: 700, color: '#028391' }}>Golden Boot</Typography>
              <Chip label={`${topScorer.goals} Goals`} size="small" sx={{ height: 18, fontSize: '0.65rem', fontWeight: 800, bgcolor: '#01204E', color: '#ffffff' }} />
            </Box>
          </CardContent>
        </Card>

        {/* CARD 3: Simulated Seasons Metric */}
        <Card className="finnova-card">
          <CardContent sx={{ p: 2.5, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', gap: 1.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="caption" sx={{ fontWeight: 800, color: '#028391', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Simulated History
              </Typography>
              <Avatar sx={{ bgcolor: 'rgba(1, 32, 78, 0.1)', color: '#01204E', width: 32, height: 32 }}>
                <TrendingUpIcon fontSize="small" />
              </Avatar>
            </Box>
            <Box>
              <Typography variant="h3" sx={{ fontWeight: 900, color: '#01204E', fontFamily: 'Outfit, sans-serif' }}>
                {totalSeasons}
              </Typography>
              <Typography variant="caption" sx={{ fontWeight: 700, color: '#028391' }}>
                Complete Seasons Simulated
              </Typography>
            </Box>
            <Box sx={{ pt: 1, borderTop: '1px solid rgba(1, 32, 78, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="caption" sx={{ fontWeight: 700, color: '#028391' }}>Active Model</Typography>
              <Typography variant="caption" sx={{ fontWeight: 800, color: '#01204E' }}>DQN & Heuristics</Typography>
            </Box>
          </CardContent>
        </Card>

        {/* CARD 4: Quick Action Hub */}
        <Card className="finnova-card" sx={{ bgcolor: '#01204E !important', color: '#ffffff !important' }}>
          <CardContent sx={{ p: 2.5, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', gap: 1.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="caption" sx={{ fontWeight: 800, color: '#FAA968', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Quick Navigation
              </Typography>
              <Avatar sx={{ bgcolor: 'rgba(250, 169, 104, 0.2)', color: '#FAA968', width: 32, height: 32 }}>
                <ArrowForwardIcon fontSize="small" />
              </Avatar>
            </Box>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Button
                component={Link}
                to="/transfer-market"
                variant="outlined"
                size="small"
                sx={{ color: '#F6DCAC', borderColor: 'rgba(246, 220, 172, 0.4)', borderRadius: '10px', textTransform: 'none', fontWeight: 700, '&:hover': { bgcolor: 'rgba(250, 169, 104, 0.15)', borderColor: '#FAA968' } }}
              >
                Explore Transfer Market
              </Button>
              <Button
                component={Link}
                to="/match-reports"
                variant="outlined"
                size="small"
                sx={{ color: '#F6DCAC', borderColor: 'rgba(246, 220, 172, 0.4)', borderRadius: '10px', textTransform: 'none', fontWeight: 700, '&:hover': { bgcolor: 'rgba(250, 169, 104, 0.15)', borderColor: '#FAA968' } }}
              >
                View Match Reports
              </Button>
            </Box>
            <Box sx={{ pt: 1, borderTop: '1px solid rgba(255, 255, 255, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.7)', fontWeight: 600 }}>System Status</Typography>
              <Typography variant="caption" sx={{ color: '#4ade80', fontWeight: 800 }}>Online</Typography>
            </Box>
          </CardContent>
        </Card>

      </Box>

      {/* 3. MAIN DASHBOARD GRID: LEAGUE STANDINGS & RECENT MATCH RESULTS */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '7fr 5fr' }, gap: 3.5 }}>

        {/* LEFT COLUMN: Official Premier League Standings Table */}
        <Card className="finnova-card">
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2.5, flexWrap: 'wrap', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Avatar sx={{ bgcolor: 'rgba(1, 32, 78, 0.1)', color: '#01204E', width: 38, height: 38 }}>
                  <LeaderboardIcon />
                </Avatar>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 800, fontFamily: 'Outfit, sans-serif' }}>
                    League Standings
                  </Typography>
                </Box>
              </Box>

              <Button
                component={Link}
                to="/league-overview"
                className="finnova-indented-btn"
                endIcon={<ArrowForwardIcon fontSize="small" />}
              >
                Full Standings
              </Button>
            </Box>

            {/* Standings Table */}
            <TableContainer component={Paper} elevation={0} sx={{ bgcolor: 'transparent' }}>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ '& th': { borderBottom: 1, borderColor: 'divider', fontWeight: 800, color: 'text.secondary', fontSize: '0.75rem', py: 1.2 } }}>
                    <TableCell align="center" width={40}>#</TableCell>
                    <TableCell>Club</TableCell>
                    <TableCell align="center">MP</TableCell>
                    <TableCell align="center">W</TableCell>
                    <TableCell align="center">D</TableCell>
                    <TableCell align="center">L</TableCell>
                    <TableCell align="center">GD</TableCell>
                    <TableCell align="center" sx={{ fontWeight: 900 }}>PTS</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {standings.slice(0, 10).map((team) => {
                    const clubMeta = getClubMeta(team.name);
                    const isTop4 = team.rank <= 4;
                    const isRelegation = team.rank >= 18;

                    return (
                      <TableRow
                        key={team.name}
                        component={Link}
                        to={`/team-details/${team.name}`}
                        sx={{
                          textDecoration: 'none',
                          cursor: 'pointer',
                          transition: 'all 0.2s',
                          '&:hover': { bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.04)' : '#f8fafc' },
                          '& td': { borderBottom: 1, borderColor: 'divider', py: 1.2 }
                        }}
                      >
                        {/* Rank */}
                        <TableCell align="center">
                          <Box
                            sx={{
                              width: 22,
                              height: 22,
                              borderRadius: '50%',
                              bgcolor: isTop4 ? 'rgba(16, 185, 129, 0.15)' : isRelegation ? 'rgba(244, 63, 94, 0.15)' : 'transparent',
                              color: isTop4 ? '#10b981' : isRelegation ? '#f43f5e' : 'text.secondary',
                              fontWeight: 800,
                              fontSize: '0.75rem',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              mx: 'auto'
                            }}
                          >
                            {team.rank}
                          </Box>
                        </TableCell>

                        {/* Club */}
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                            <Avatar sx={{ width: 28, height: 28, background: clubMeta.bg, color: '#fff', fontSize: '0.65rem', fontWeight: 900 }}>
                              {clubMeta.code}
                            </Avatar>
                            <Typography variant="subtitle2" sx={{ fontWeight: 800, color: 'text.primary', fontSize: '0.85rem' }}>
                              {team.name}
                            </Typography>
                          </Box>
                        </TableCell>

                        <TableCell align="center" sx={{ fontWeight: 600, color: 'text.secondary' }}>{team.mp}</TableCell>
                        <TableCell align="center" sx={{ fontWeight: 600 }}>{team.w}</TableCell>
                        <TableCell align="center" sx={{ fontWeight: 600, color: 'text.secondary' }}>{team.d}</TableCell>
                        <TableCell align="center" sx={{ fontWeight: 600, color: 'text.secondary' }}>{team.l}</TableCell>
                        <TableCell align="center" sx={{ fontWeight: 700, color: team.gd > 0 ? '#10b981' : team.gd < 0 ? '#f43f5e' : 'text.secondary' }}>
                          {team.gd > 0 ? `+${team.gd}` : team.gd}
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={team.pts}
                            size="small"
                            sx={{
                              fontWeight: 900,
                              fontSize: '0.8rem',
                              bgcolor: isTop4 ? '#E63946' : theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.08)' : '#e2e8f0',
                              color: isTop4 ? '#ffffff' : 'text.primary',
                              height: 22,
                              minWidth: 32
                            }}
                          />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>

        {/* RIGHT COLUMN: Live Match Fixtures & Recent Match Results */}
        <Card className="finnova-card" sx={{ display: 'flex', flexDirection: 'column' }}>
          <CardContent sx={{ p: 3, flex: 1, display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2.5, flexWrap: 'wrap', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Avatar sx={{ bgcolor: 'rgba(1, 32, 78, 0.1)', color: '#01204E', width: 38, height: 38 }}>
                  <EventNoteIcon />
                </Avatar>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 800, fontFamily: 'Outfit, sans-serif' }}>
                    Match Center Fixtures
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                    Recent Match Results & Scores
                  </Typography>
                </Box>
              </Box>

              <Button
                component={Link}
                to="/match-reports"
                className="finnova-indented-btn"
                endIcon={<ArrowForwardIcon fontSize="small" />}
              >
                All Matches
              </Button>
            </Box>

            {/* List of Recent Matches */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }}>
              {recentMatches.map((m: any, idx: number) => {
                const homeMeta = getClubMeta(m.home_team_name);
                const awayMeta = getClubMeta(m.away_team_name);
                const hScore = m.home_goals ?? m.home_score ?? 0;
                const aScore = m.away_goals ?? m.away_score ?? 0;
                const homeWon = hScore > aScore;
                const awayWon = aScore > hScore;

                return (
                  <Box
                    key={m.id || idx}
                    component={Link}
                    to={`/match/${m.id || 3031}`}
                    sx={{
                      p: 2,
                      borderRadius: '16px',
                      bgcolor: '#F6DCAC',
                      border: 1,
                      borderColor: 'divider',
                      textDecoration: 'none',
                      color: 'inherit',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      transition: 'all 0.2s',
                      '&:hover': {
                        transform: 'translateY(-2px)',
                        bgcolor: 'rgba(1, 32, 78, 0.08)',
                        borderColor: '#01204E'
                      }
                    }}
                  >
                    {/* Home Team */}
                    <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <Avatar sx={{ width: 32, height: 32, background: homeMeta.bg, color: '#fff', fontSize: '0.7rem', fontWeight: 900 }}>
                        {homeMeta.code}
                      </Avatar>
                      <Typography variant="subtitle2" sx={{ fontWeight: homeWon ? 800 : 600, color: 'text.primary', fontSize: '0.85rem' }}>
                        {m.home_team_name}
                      </Typography>
                    </Box>

                    {/* Score Center Pill */}
                    <Box sx={{ px: 2, py: 0.5, borderRadius: 9999, bgcolor: '#01204E', color: '#ffffff', display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#ffffff' }}>
                        {hScore}
                      </Typography>
                      <Typography variant="caption" color="inherit">:</Typography>
                      <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#ffffff' }}>
                        {aScore}
                      </Typography>
                    </Box>

                    {/* Away Team */}
                    <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 1.5 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: awayWon ? 800 : 600, color: 'text.primary', fontSize: '0.85rem' }}>
                        {m.away_team_name}
                      </Typography>
                      <Avatar sx={{ width: 32, height: 32, background: awayMeta.bg, color: '#fff', fontSize: '0.7rem', fontWeight: 900 }}>
                        {awayMeta.code}
                      </Avatar>
                    </Box>
                  </Box>
                );
              })}

              {recentMatches.length === 0 && (
                <Typography color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
                  No recent match fixtures available.
                </Typography>
              )}
            </Box>
          </CardContent>
        </Card>

      </Box>

      {/* 4. BOTTOM ANALYTICS: MULTI-SEASON TRENDS & TOP PLAYERS */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '7fr 5fr' }, gap: 3.5, mt: 1 }}>
        
        {/* Multi-Season Trend Chart */}
        <Card className="finnova-card">
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <Avatar sx={{ bgcolor: 'rgba(1, 32, 78, 0.1)', color: '#01204E', width: 36, height: 36, mr: 1.5 }}>
                <TrendingUpIcon fontSize="small" />
              </Avatar>
              <Typography variant="h6" sx={{ fontWeight: 800, fontFamily: 'Outfit, sans-serif', color: '#01204E' }}>
                Multi-Season Goals & Transfers Overview
              </Typography>
            </Box>
            {seasonTrendData.length > 0 ? (
              <Box sx={{ height: 260, width: '100%', minWidth: 0 }}>
                <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                  <BarChart data={seasonTrendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(1, 32, 78, 0.1)" />
                    <XAxis dataKey="season" tick={{ fill: theme.palette.text.secondary, fontSize: 11 }} />
                    <YAxis tick={{ fill: theme.palette.text.secondary, fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#01204E',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 12,
                        color: '#FFF8ED',
                        boxShadow: '0 10px 25px rgba(0,0,0,0.3)'
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="goals" name="Goals Scored" fill="#01204E" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="transfers" name="Transfers Completed" fill="#028391" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            ) : (
              <Typography color="text.secondary">No season trend data available.</Typography>
            )}
          </CardContent>
        </Card>

        {/* Top Players Leaderboard */}
        <Card className="finnova-card">
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Avatar sx={{ bgcolor: 'rgba(1, 32, 78, 0.12)', color: '#01204E', width: 36, height: 36 }}>
                  <StarIcon fontSize="small" />
                </Avatar>
                <Typography variant="h6" sx={{ fontWeight: 800, fontFamily: 'Outfit, sans-serif', color: 'text.primary' }}>
                  Top Performer Leaderboard
                </Typography>
              </Box>
              <Button
                component={Link}
                to="/player-profiles"
                className="finnova-indented-btn"
                endIcon={<ArrowForwardIcon fontSize="small" />}
              >
                All Players
              </Button>
            </Box>

            {bestPlayersList.length > 0 ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                {bestPlayersList.map((player: any, idx: number) => {
                  const clubMeta = getClubMeta(player.team);
                  return (
                    <Box
                      key={player.name || idx}
                      component={Link}
                      to={`/player-profiles/${player.name}`}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        p: 1.5,
                        px: 2,
                        borderRadius: '16px',
                        bgcolor: '#F6DCAC',
                        border: 1,
                        borderColor: 'divider',
                        textDecoration: 'none',
                        color: 'inherit',
                        transition: 'all 0.2s',
                        '&:hover': { transform: 'translateX(4px)', bgcolor: 'rgba(1, 32, 78, 0.08)' }
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                        <Avatar sx={{ width: 32, height: 32, background: clubMeta.bg, color: '#fff', fontSize: '0.7rem', fontWeight: 900 }}>
                          {clubMeta.code}
                        </Avatar>
                        <Box>
                          <Typography variant="subtitle2" sx={{ fontWeight: 800, color: 'text.primary', lineHeight: 1.1 }}>
                            {player.name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                            {player.team} • {player.position}
                          </Typography>
                        </Box>
                      </Box>

                      <Chip
                        label={`${player.stats?.goals ?? 12} Goals`}
                        size="small"
                        sx={{
                          bgcolor: '#01204E',
                          color: '#ffffff',
                          fontWeight: 800,
                          fontSize: '0.72rem'
                        }}
                      />
                    </Box>
                  );
                })}
              </Box>
            ) : (
              <Typography color="text.secondary">No player leaderboard data available.</Typography>
            )}
          </CardContent>
        </Card>
      </Box>

    </Box>
  );
};

export default Dashboard;
