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

  useEffect(() => {
    fetchAvailableSeasons();
  }, [fetchAvailableSeasons]);

  const latestSeasonYear = availableSeasons.length > 0 ? Math.max(...availableSeasons) : null;

  // 1. All Seasons Overview
  const { data: allSeasonsData, error: seasonsErr } = useQuery({
    queryKey: ['allSeasonsOverview'],
    queryFn: getAllSeasonsOverview,
  });

  // 2. Latest Season Detailed Report (for Standings Table)
  const { data: seasonReport } = useQuery({
    queryKey: ['seasonReport', latestSeasonYear],
    queryFn: () => getSeasonReportData(latestSeasonYear!),
    enabled: latestSeasonYear !== null,
  });

  // 3. Recent Matches (for Match Center)
  const { data: matchesData } = useQuery({
    queryKey: ['matchesBySeason', latestSeasonYear],
    queryFn: () => getMatchesBySeason(latestSeasonYear!),
    enabled: latestSeasonYear !== null,
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
  const standings = rawTable.map(([teamName, stats]: any, idx: number) => ({
    rank: idx + 1,
    name: teamName,
    mp: stats.p || stats.mp || 38,
    w: stats.w || 0,
    d: stats.d || 0,
    l: stats.l || 0,
    gf: stats.gf || 0,
    ga: stats.ga || 0,
    gd: stats.gd || (Number(stats.gf || 0) - Number(stats.ga || 0)),
    pts: stats.pts || 0,
  })).sort((a, b) => b.pts - a.pts || b.gd - a.gd);

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
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 0.5 }}>
            <Typography variant="h4" sx={{ fontWeight: 900, fontFamily: 'Outfit, sans-serif', color: '#ffffff', letterSpacing: '-0.02em', textShadow: '0 2px 10px rgba(0,0,0,0.5)' }}>
              Premier League Command Center
            </Typography>
            <Chip
              label={`Season ${latestSeasonYear}`}
              size="small"
              sx={{ bgcolor: 'rgba(34, 197, 94, 0.2)', color: '#4ade80', fontWeight: 800, borderRadius: 9999, border: '1px solid rgba(74, 222, 128, 0.3)' }}
            />
          </Box>
          <Typography variant="body2" sx={{ fontWeight: 600, color: '#a7f3d0' }}>
            Real-time league standings, match results, top goalscorers, and AI season simulation. ({totalSeasons} seasons simulated • Champion: {championTeam} {championPoints} PTS)
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <IconButton
            sx={{
              bgcolor: 'rgba(8, 32, 14, 0.75)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: 9999,
              p: 1.2,
              color: '#ffffff',
              boxShadow: '4px 4px 10px rgba(0,0,0,0.3)'
            }}
          >
            <TuneIcon fontSize="small" sx={{ color: '#4ade80' }} />
          </IconButton>

          <Button
            variant="contained"
            onClick={() => runSimMutation.mutate()}
            disabled={runSimMutation.isPending}
            startIcon={runSimMutation.isPending ? <CircularProgress size={18} color="inherit" /> : <AddIcon />}
            sx={{
              background: 'linear-gradient(145deg, rgba(34, 197, 94, 0.9), rgba(21, 128, 61, 0.95))',
              color: '#ffffff',
              px: 3,
              py: 1.2,
              borderRadius: 9999,
              fontWeight: 800,
              fontSize: '0.88rem',
              boxShadow: '5px 5px 15px rgba(0, 15, 4, 0.5), -2px -2px 6px rgba(255, 255, 255, 0.3)',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              '&:hover': {
                background: 'linear-gradient(145deg, rgba(74, 222, 128, 0.95), rgba(22, 163, 74, 1))',
              }
            }}
          >
            Run Season Simulation
          </Button>
        </Box>
      </Box>

      {/* 2. TOP FOOTBALL KPI METRIC CARDS (4 ESSENTIAL WIDGETS) */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', lg: 'repeat(4, 1fr)' }, gap: 2.5 }}>

        {/* CARD 1: League Champions */}
        <Card sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider', borderRadius: '20px', boxShadow: theme.palette.mode === 'dark' ? '0 10px 30px rgba(0,0,0,0.3)' : '0 10px 30px -5px rgba(0,0,0,0.04)' }}>
          <CardContent sx={{ p: 3, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'text.secondary' }}>League Champion</Typography>
              <Avatar sx={{ bgcolor: 'rgba(251, 191, 36, 0.15)', color: '#d97706', width: 36, height: 36 }}>
                <EmojiEventsIcon fontSize="small" />
              </Avatar>
            </Box>
            <Box sx={{ my: 1.5, display: 'flex', alignItems: 'center', gap: 2 }}>
              <Avatar sx={{ width: 44, height: 44, background: getClubMeta(championTeam).bg, color: '#fff', fontWeight: 900, fontSize: '0.9rem' }}>
                {getClubMeta(championTeam).code}
              </Avatar>
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 900, color: 'text.primary', fontFamily: 'Outfit, sans-serif' }}>
                  {championTeam}
                </Typography>
                <Chip label={`${championPoints} PTS`} size="small" sx={{ height: 18, fontSize: '0.65rem', fontWeight: 800, bgcolor: 'rgba(16, 185, 129, 0.15)', color: '#10b981', mt: 0.3 }} />
              </Box>
            </Box>
            <Box sx={{ pt: 1, borderTop: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>Title Winner</Typography>
              <Typography variant="caption" sx={{ fontWeight: 800, color: '#4f46e5' }}>Season {latestSeasonYear}</Typography>
            </Box>
          </CardContent>
        </Card>

        {/* CARD 2: Top Scorer / Golden Boot */}
        <Card sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider', borderRadius: '20px', boxShadow: theme.palette.mode === 'dark' ? '0 10px 30px rgba(0,0,0,0.3)' : '0 10px 30px -5px rgba(0,0,0,0.04)' }}>
          <CardContent sx={{ p: 3, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'text.secondary' }}>Golden Boot Leader</Typography>
              <Avatar sx={{ bgcolor: 'rgba(79, 70, 229, 0.1)', color: '#4f46e5', width: 36, height: 36 }}>
                <SportsSoccerIcon fontSize="small" />
              </Avatar>
            </Box>
            <Box sx={{ my: 1.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Avatar sx={{ width: 44, height: 44, bgcolor: '#4f46e5', color: '#fff', fontWeight: 900, fontSize: '0.9rem' }}>
                {topScorer.name ? topScorer.name.substring(0, 2).toUpperCase() : "MA"}
              </Avatar>
              <Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 900, color: 'text.primary', lineHeight: 1.1 }}>
                  {topScorer.name}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                  {topScorer.team} • <strong style={{ color: '#4f46e5' }}>{topScorer.goals} Goals</strong>
                </Typography>
              </Box>
            </Box>
            <Box sx={{ pt: 1, borderTop: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>Top Scorer</Typography>
              <Chip label={`${topScorer.goals} Goals`} size="small" sx={{ height: 18, fontSize: '0.65rem', fontWeight: 800, bgcolor: 'rgba(79, 70, 229, 0.12)', color: '#4f46e5' }} />
            </Box>
          </CardContent>
        </Card>

        {/* CARD 3: Season Total Goals */}
        <Card sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider', borderRadius: '20px', boxShadow: theme.palette.mode === 'dark' ? '0 10px 30px rgba(0,0,0,0.3)' : '0 10px 30px -5px rgba(0,0,0,0.04)' }}>
          <CardContent sx={{ p: 3, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'text.secondary' }}>Season Goals Scored</Typography>
              <Avatar sx={{ bgcolor: 'rgba(16, 185, 129, 0.1)', color: '#10b981', width: 36, height: 36 }}>
                <TrendingUpIcon fontSize="small" />
              </Avatar>
            </Box>
            <Box sx={{ my: 1.5 }}>
              <Typography variant="h4" sx={{ fontWeight: 900, color: 'text.primary', fontFamily: 'Outfit, sans-serif' }}>
                {latestSummary?.total_goals ?? 1048}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                {latestSummary?.avg_goals_per_match ?? 2.76} goals / match average
              </Typography>
            </Box>
            <Box sx={{ height: 30, width: '100%', pt: 0.5 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barWidgetData}>
                  <Bar dataKey="val" fill="#10b981" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </Card>

        {/* CARD 4: Total League Completed Deals */}
        <Card sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider', borderRadius: '20px', boxShadow: theme.palette.mode === 'dark' ? '0 10px 30px rgba(0,0,0,0.3)' : '0 10px 30px -5px rgba(0,0,0,0.04)' }}>
          <CardContent sx={{ p: 3, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'text.secondary' }}>Transfer Market Volume</Typography>
              <Avatar sx={{ bgcolor: 'rgba(6, 182, 212, 0.1)', color: '#0891b2', width: 36, height: 36 }}>
                <SwapHorizIcon fontSize="small" />
              </Avatar>
            </Box>
            <Box sx={{ my: 1.5 }}>
              <Typography variant="h4" sx={{ fontWeight: 900, color: 'text.primary', fontFamily: 'Outfit, sans-serif' }}>
                {latestSummary?.transfers_completed ?? 48} Deals
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                £ 1.86B total squad market value
              </Typography>
            </Box>
            <Box sx={{ pt: 1, borderTop: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>Market Status</Typography>
              <Chip label="Window Active" size="small" sx={{ height: 20, fontSize: '0.68rem', fontWeight: 800, bgcolor: 'rgba(6, 182, 212, 0.12)', color: '#0891b2' }} />
            </Box>
          </CardContent>
        </Card>

      </Box>

      {/* 3. MAIN DASHBOARD GRID: LEAGUE STANDINGS & RECENT MATCH RESULTS */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '7fr 5fr' }, gap: 3.5 }}>

        {/* LEFT COLUMN: Official Premier League Standings Table */}
        <Card sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider', borderRadius: '24px', boxShadow: theme.palette.mode === 'dark' ? '0 10px 30px rgba(0,0,0,0.3)' : '0 10px 30px -5px rgba(0,0,0,0.04)' }}>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2.5, flexWrap: 'wrap', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Avatar sx={{ bgcolor: 'rgba(79, 70, 229, 0.1)', color: '#4f46e5', width: 38, height: 38 }}>
                  <LeaderboardIcon />
                </Avatar>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 800, fontFamily: 'Outfit, sans-serif' }}>
                    Premier League Standings
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                    Official League Table • Season {latestSeasonYear}
                  </Typography>
                </Box>
              </Box>

              <Button
                component={Link}
                to="/league-overview"
                size="small"
                endIcon={<ArrowForwardIcon fontSize="small" />}
                sx={{ fontWeight: 700, color: '#4f46e5' }}
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
                              bgcolor: isTop4 ? '#4f46e5' : theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.08)' : '#e2e8f0',
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
        <Card sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider', borderRadius: '24px', boxShadow: theme.palette.mode === 'dark' ? '0 10px 30px rgba(0,0,0,0.3)' : '0 10px 30px -5px rgba(0,0,0,0.04)', display: 'flex', flexDirection: 'column' }}>
          <CardContent sx={{ p: 3, flex: 1, display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2.5, flexWrap: 'wrap', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Avatar sx={{ bgcolor: 'rgba(79, 70, 229, 0.1)', color: '#4f46e5', width: 38, height: 38 }}>
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
                size="small"
                endIcon={<ArrowForwardIcon fontSize="small" />}
                sx={{ fontWeight: 700, color: '#4f46e5' }}
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
                      bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : '#f8fafc',
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
                        bgcolor: theme.palette.mode === 'dark' ? 'rgba(79, 70, 229, 0.12)' : '#eef2ff',
                        borderColor: 'rgba(79, 70, 229, 0.3)'
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
                    <Box sx={{ px: 2, py: 0.5, borderRadius: 9999, bgcolor: 'background.paper', border: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 900, color: homeWon ? '#4f46e5' : 'text.primary' }}>
                        {hScore}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">:</Typography>
                      <Typography variant="subtitle2" sx={{ fontWeight: 900, color: awayWon ? '#4f46e5' : 'text.primary' }}>
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
        <Card sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider', borderRadius: '24px', boxShadow: theme.palette.mode === 'dark' ? '0 10px 30px rgba(0,0,0,0.3)' : '0 10px 30px -5px rgba(0,0,0,0.04)' }}>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <Avatar sx={{ bgcolor: 'rgba(79, 70, 229, 0.1)', color: '#4f46e5', width: 36, height: 36, mr: 1.5 }}>
                <TrendingUpIcon fontSize="small" />
              </Avatar>
              <Typography variant="h6" sx={{ fontWeight: 800, fontFamily: 'Outfit, sans-serif', color: 'text.primary' }}>
                Multi-Season Goals & Transfers Overview
              </Typography>
            </Box>
            {seasonTrendData.length > 0 ? (
              <Box sx={{ height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={seasonTrendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.06)' : '#f1f5f9'} />
                    <XAxis dataKey="season" tick={{ fill: theme.palette.text.secondary, fontSize: 11 }} />
                    <YAxis tick={{ fill: theme.palette.text.secondary, fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: theme.palette.mode === 'dark' ? '#1e2235' : '#0f172a',
                        border: 'none',
                        borderRadius: 12,
                        color: '#ffffff',
                        boxShadow: '0 10px 25px rgba(0,0,0,0.3)'
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="goals" name="Goals Scored" fill="#4f46e5" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="transfers" name="Transfers Completed" fill="#818cf8" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            ) : (
              <Typography color="text.secondary">No season trend data available.</Typography>
            )}
          </CardContent>
        </Card>

        {/* Top Players Leaderboard */}
        <Card sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider', borderRadius: '24px', boxShadow: theme.palette.mode === 'dark' ? '0 10px 30px rgba(0,0,0,0.3)' : '0 10px 30px -5px rgba(0,0,0,0.04)' }}>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Avatar sx={{ bgcolor: 'rgba(251, 191, 36, 0.12)', color: '#fbbf24', width: 36, height: 36 }}>
                  <StarIcon fontSize="small" />
                </Avatar>
                <Typography variant="h6" sx={{ fontWeight: 800, fontFamily: 'Outfit, sans-serif', color: 'text.primary' }}>
                  Top Performer Leaderboard
                </Typography>
              </Box>
              <Button
                component={Link}
                to="/player-profiles"
                size="small"
                endIcon={<ArrowForwardIcon fontSize="small" />}
                sx={{ fontWeight: 700, color: '#4f46e5' }}
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
                        bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : '#f8fafc',
                        border: 1,
                        borderColor: 'divider',
                        textDecoration: 'none',
                        color: 'inherit',
                        transition: 'all 0.2s',
                        '&:hover': { transform: 'translateX(4px)', bgcolor: 'rgba(79, 70, 229, 0.12)' }
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
                          bgcolor: 'rgba(79, 70, 229, 0.12)',
                          color: '#4f46e5',
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
