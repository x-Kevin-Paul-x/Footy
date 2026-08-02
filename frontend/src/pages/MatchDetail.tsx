import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Typography,
  Box,
  CircularProgress,
  Alert,
  Grid,
  Card,
  CardContent,
  alpha,
  Avatar,
  Chip,
  useTheme,
  Divider,
} from "@mui/material";
import SportsSoccerIcon from "@mui/icons-material/SportsSoccer";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import ArticleIcon from "@mui/icons-material/Article";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import EventNoteIcon from "@mui/icons-material/EventNote";
import {
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
} from "@mui/lab";
import { getMatchDetails } from "../services/api";
import FormationViewer from "../components/FormationViewer";
import MatchStats from "../components/MatchStats";

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

const getEventIconAndColor = (details: string, type: string) => {
  const detailLower = (details || "").toLowerCase();
  const typeLower = (type || "").toLowerCase();

  if (typeLower === "goal" || detailLower.includes("goal") || detailLower.includes("scores")) {
    return {
      icon: <SportsSoccerIcon sx={{ fontSize: 16, color: "#10b981" }} />,
      color: "success" as const,
      bgcolor: "#10b981",
    };
  }
  if (detailLower.includes("yellow card")) {
    return {
      icon: <span style={{ width: 10, height: 14, backgroundColor: "#fbbf24", borderRadius: 1.5, display: "inline-block" }} />,
      color: "warning" as const,
      bgcolor: "#fbbf24",
    };
  }
  if (detailLower.includes("red card")) {
    return {
      icon: <span style={{ width: 10, height: 14, backgroundColor: "#ef4444", borderRadius: 1.5, display: "inline-block" }} />,
      color: "error" as const,
      bgcolor: "#ef4444",
    };
  }
  if (detailLower.includes("injured") || detailLower.includes("injury") || detailLower.includes("stretchered")) {
    return {
      icon: <LocalHospitalIcon sx={{ fontSize: 16, color: "#f43f5e" }} />,
      color: "error" as const,
      bgcolor: "#f43f5e",
    };
  }
  if (detailLower.includes("substitut") || detailLower.includes("subbed") || detailLower.includes("comes on")) {
    return {
      icon: <SwapHorizIcon sx={{ fontSize: 16, color: "#3b82f6" }} />,
      color: "info" as const,
      bgcolor: "#3b82f6",
    };
  }

  return {
    icon: <ArticleIcon sx={{ fontSize: 16, color: "#9ca3af" }} />,
    color: "grey" as const,
    bgcolor: "#4b5563",
  };
};

// Helper to determine if an event was performed by Home or Away team
const checkIsHomeEvent = (event: any, homeTeam: string, awayTeam: string, idx: number): boolean => {
  const details = (event.details || "").toLowerCase();
  const hName = (homeTeam || "").toLowerCase().trim();
  const aName = (awayTeam || "").toLowerCase().trim();

  if (event.team_name) {
    if (event.team_name.toLowerCase().includes(hName)) return true;
    if (event.team_name.toLowerCase().includes(aName)) return false;
  }

  if (details.includes(hName)) return true;
  if (details.includes(aName)) return false;

  return idx % 2 === 0;
};

const MatchDetail: React.FC = () => {
  const theme = useTheme();
  const { matchId } = useParams<{ matchId: string }>();
  const [match, setMatch] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMatch = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getMatchDetails(Number(matchId));
        setMatch(data);
      } catch (err) {
        setError("Failed to fetch match details.");
      } finally {
        setLoading(false);
      }
    };
    fetchMatch();
  }, [matchId]);

  // Sample tactical positions for Home and Away
  const homePlayers = [
    { name: "GK Position", position: "GK", x: 0.08, y: 0.5, number: 1 },
    { name: "Defender 1", position: "LB", x: 0.25, y: 0.2, number: 3 },
    { name: "Defender 2", position: "CB", x: 0.22, y: 0.4, number: 4 },
    { name: "Defender 3", position: "CB", x: 0.22, y: 0.6, number: 5 },
    { name: "Defender 4", position: "RB", x: 0.25, y: 0.8, number: 2 },
    { name: "Midfielder 1", position: "LM", x: 0.48, y: 0.2, number: 11 },
    { name: "Midfielder 2", position: "CM", x: 0.45, y: 0.4, number: 6 },
    { name: "Midfielder 3", position: "CM", x: 0.45, y: 0.6, number: 8 },
    { name: "Midfielder 4", position: "RM", x: 0.48, y: 0.8, number: 7 },
    { name: "Striker 1", position: "ST", x: 0.75, y: 0.38, number: 9 },
    { name: "Striker 2", position: "ST", x: 0.75, y: 0.62, number: 10 },
  ];

  const awayPlayers = [
    { name: "GK Position", position: "GK", x: 0.08, y: 0.5, number: 1 },
    { name: "Defender 1", position: "LB", x: 0.25, y: 0.2, number: 3 },
    { name: "Defender 2", position: "CB", x: 0.22, y: 0.4, number: 4 },
    { name: "Defender 3", position: "CB", x: 0.22, y: 0.6, number: 5 },
    { name: "Defender 4", position: "RB", x: 0.25, y: 0.8, number: 2 },
    { name: "Midfielder 1", position: "DM", x: 0.42, y: 0.5, number: 6 },
    { name: "Midfielder 2", position: "CM", x: 0.55, y: 0.35, number: 8 },
    { name: "Midfielder 3", position: "CM", x: 0.55, y: 0.65, number: 10 },
    { name: "Winger 1", position: "LW", x: 0.75, y: 0.2, number: 11 },
    { name: "Striker 1", position: "ST", x: 0.78, y: 0.5, number: 9 },
    { name: "Winger 2", position: "RW", x: 0.75, y: 0.8, number: 7 },
  ];

  if (loading) return <Box sx={{ p: 4, display: "flex", justifyContent: "center" }}><CircularProgress /></Box>;
  if (error) return <Box sx={{ p: 4 }}><Alert severity="error">{error}</Alert></Box>;
  if (!match) return null;

  const homeMeta = getClubMeta(match.home_team_name);
  const awayMeta = getClubMeta(match.away_team_name);
  const hGoals = match.home_goals ?? match.home_score ?? 0;
  const aGoals = match.away_goals ?? match.away_score ?? 0;
  const homeWon = hGoals > aGoals;
  const awayWon = aGoals > hGoals;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3.5, pb: 6 }}>
      {/* 1. SCOREBOARD BANNER CARD */}
      <Card
        sx={{
          bgcolor: "background.paper",
          border: 1,
          borderColor: "divider",
          borderRadius: "24px",
          overflow: "hidden",
          boxShadow: theme.palette.mode === "dark" ? "0 10px 30px rgba(0,0,0,0.3)" : "0 10px 30px -5px rgba(0,0,0,0.04)"
        }}
      >
        <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 2.5 }}>
            {/* Home Team Header */}
            <Box sx={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 2, textAlign: "right" }}>
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 800, fontFamily: "Outfit, sans-serif", color: "text.primary" }}>
                  {match.home_team_name}
                </Typography>
                {homeWon && (
                  <Chip
                    label="WINNER"
                    size="small"
                    sx={{ height: 18, fontSize: "0.65rem", fontWeight: 800, bgcolor: "rgba(16, 185, 129, 0.15)", color: "#10b981", mt: 0.3 }}
                  />
                )}
              </Box>
              <Avatar
                sx={{
                  width: 48,
                  height: 48,
                  background: homeMeta.bg,
                  color: "#ffffff",
                  fontWeight: 900,
                  fontSize: "1rem",
                  boxShadow: "0 4px 14px rgba(0,0,0,0.15)",
                  border: homeWon ? "3px solid #10b981" : "2px solid rgba(255,255,255,0.2)"
                }}
              >
                {homeMeta.code}
              </Avatar>
            </Box>

            {/* Score Pill Center */}
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 0.5,
                px: 3,
                py: 1.2,
                borderRadius: "16px",
                background: theme.palette.mode === "dark" ? "rgba(255,255,255,0.04)" : "#f8fafc",
                border: 1,
                borderColor: "divider",
                minWidth: 120
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <Typography variant="h4" sx={{ fontWeight: 900, fontFamily: "Outfit, sans-serif", color: homeWon ? "#4f46e5" : "text.primary", fontSize: "1.8rem" }}>
                  {hGoals}
                </Typography>
                <Typography variant="h5" sx={{ color: "text.secondary", fontWeight: 300 }}>
                  :
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 900, fontFamily: "Outfit, sans-serif", color: awayWon ? "#4f46e5" : "text.primary", fontSize: "1.8rem" }}>
                  {aGoals}
                </Typography>
              </Box>
              <Chip
                label="FULL TIME"
                size="small"
                sx={{
                  height: 18,
                  fontSize: "0.65rem",
                  fontWeight: 800,
                  bgcolor: theme.palette.mode === "dark" ? "rgba(255,255,255,0.1)" : "#e2e8f0",
                  color: "text.secondary"
                }}
              />
            </Box>

            {/* Away Team Header */}
            <Box sx={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "flex-start", gap: 2, textAlign: "left" }}>
              <Avatar
                sx={{
                  width: 48,
                  height: 48,
                  background: awayMeta.bg,
                  color: "#ffffff",
                  fontWeight: 900,
                  fontSize: "1rem",
                  boxShadow: "0 4px 14px rgba(0,0,0,0.15)",
                  border: awayWon ? "3px solid #10b981" : "2px solid rgba(255,255,255,0.2)"
                }}
              >
                {awayMeta.code}
              </Avatar>
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 800, fontFamily: "Outfit, sans-serif", color: "text.primary" }}>
                  {match.away_team_name}
                </Typography>
                {awayWon && (
                  <Chip
                    label="WINNER"
                    size="small"
                    sx={{ height: 18, fontSize: "0.65rem", fontWeight: 800, bgcolor: "rgba(16, 185, 129, 0.15)", color: "#10b981", mt: 0.3 }}
                  />
                )}
              </Box>
            </Box>
          </Box>

          <Box sx={{ textAlign: "center", mt: 3, pt: 2, borderTop: 1, borderColor: "divider", display: "flex", alignItems: "center", justifyContent: "center", gap: 1 }}>
            <CalendarMonthIcon sx={{ fontSize: 16, color: "text.secondary" }} />
            <Typography variant="subtitle2" color="text.secondary" sx={{ fontWeight: 600 }}>
              {new Date(match.date).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
            </Typography>
          </Box>
        </CardContent>
      </Card>

      {/* 2. BALANCED TWO-COLUMN DASHBOARD GRID */}
      <Grid container spacing={3.5} alignItems="flex-start">
        {/* LEFT COLUMN: Tactical Formations & Match Stats (lg={7}) */}
        <Grid item xs={12} lg={7} sx={{ display: "flex", flexDirection: "column", gap: 3.5 }}>
          {/* Tactical Formations Header & Viewers */}
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <FormationViewer
              teamName={match.home_team_name}
              formation="4-4-2"
              players={homePlayers}
              teamColor={homeMeta.bg.includes("#2563eb") ? "#2563eb" : "#4f46e5"}
            />
            <FormationViewer
              teamName={match.away_team_name}
              formation="4-3-3"
              players={awayPlayers}
              teamColor={awayMeta.bg.includes("#334155") ? "#334155" : "#f43f5e"}
            />
          </Box>

          {/* Match Statistics */}
          <MatchStats
            stats={{
              home: {
                total: match.shots?.home?.total ?? 0,
                on_target: match.shots?.home?.on_target ?? 0,
                passes_attempted: match.home_passes_attempted ?? 0,
                passes_completed: match.home_passes_completed ?? 0,
                fouls: match.home_fouls ?? 0,
                corners: match.home_corners ?? 0,
                offsides: match.home_offsides ?? 0,
              },
              away: {
                total: match.shots?.away?.total ?? 0,
                on_target: match.shots?.away?.on_target ?? 0,
                passes_attempted: match.away_passes_attempted ?? 0,
                passes_completed: match.away_passes_completed ?? 0,
                fouls: match.away_fouls ?? 0,
                corners: match.away_corners ?? 0,
                offsides: match.away_offsides ?? 0,
              },
            }}
            possession={{
              home: match.home_possession ?? 50,
              away: match.away_possession ?? 50,
            }}
          />
        </Grid>

        {/* RIGHT COLUMN: Compact Dual-Sided Match Event Timeline (lg={5}) */}
        <Grid item xs={12} lg={5} sx={{ position: "sticky", top: 80 }}>
          <Card
            sx={{
              bgcolor: "background.paper",
              border: 1,
              borderColor: "divider",
              borderRadius: "24px",
              boxShadow: theme.palette.mode === "dark" ? "0 10px 30px rgba(0,0,0,0.3)" : "0 10px 30px -5px rgba(0,0,0,0.04)",
              display: "flex",
              flexDirection: "column",
              maxHeight: { lg: "calc(100vh - 120px)" }
            }}
          >
            <CardContent sx={{ p: { xs: 2.5, md: 3 }, display: "flex", flexDirection: "column", height: "100%" }}>
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2, flexWrap: "wrap", gap: 1.5 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                  <Avatar sx={{ bgcolor: "rgba(79, 70, 229, 0.1)", color: "#4f46e5", width: 36, height: 36 }}>
                    <EventNoteIcon />
                  </Avatar>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 800, fontFamily: "Outfit, sans-serif", fontSize: "1.05rem" }}>
                      Match Event Timeline
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                      Home (Left) • Away (Right)
                    </Typography>
                  </Box>
                </Box>

                {/* Team Legend Bar */}
                <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.8 }}>
                    <Avatar sx={{ width: 20, height: 20, background: homeMeta.bg, fontSize: "0.55rem", fontWeight: 800 }}>
                      {homeMeta.code}
                    </Avatar>
                    <Typography variant="caption" sx={{ fontWeight: 700, fontSize: "0.75rem" }}>
                      {match.home_team_name}
                    </Typography>
                  </Box>
                  <Divider orientation="vertical" flexItem />
                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.8 }}>
                    <Avatar sx={{ width: 20, height: 20, background: awayMeta.bg, fontSize: "0.55rem", fontWeight: 800 }}>
                      {awayMeta.code}
                    </Avatar>
                    <Typography variant="caption" sx={{ fontWeight: 700, fontSize: "0.75rem" }}>
                      {match.away_team_name}
                    </Typography>
                  </Box>
                </Box>
              </Box>

              <Divider sx={{ mb: 2 }} />

              {/* Scrollable Timeline Box */}
              <Box
                sx={{
                  flex: 1,
                  overflowY: "auto",
                  pr: 1,
                  "&::-webkit-scrollbar": { width: 5 },
                  "&::-webkit-scrollbar-thumb": { bgcolor: "divider", borderRadius: 9999 }
                }}
              >
                <Timeline position="alternate" sx={{ p: 0 }}>
                  {(match.events || []).map((event: any, idx: number) => {
                    const { icon, bgcolor } = getEventIconAndColor(event.details, event.type);
                    const isHome = checkIsHomeEvent(event, match.home_team_name, match.away_team_name, idx);
                    const sidePos = isHome ? "left" : "right";

                    return (
                      <TimelineItem key={idx} position={sidePos}>
                        <TimelineSeparator>
                          <TimelineDot
                            sx={{
                              bgcolor: alpha(bgcolor, 0.15),
                              border: `2px solid ${bgcolor}`,
                              p: 0.8,
                              boxShadow: `0 0 10px ${alpha(bgcolor, 0.3)}`
                            }}
                          >
                            {icon}
                          </TimelineDot>
                          {idx < (match.events.length - 1) && <TimelineConnector sx={{ bgcolor: "divider" }} />}
                        </TimelineSeparator>

                        <TimelineContent sx={{ py: 1, px: 1.5 }}>
                          <Box
                            sx={{
                              display: "inline-block",
                              p: 1.2,
                              px: 1.5,
                              borderRadius: "14px",
                              bgcolor: isHome
                                ? theme.palette.mode === "dark" ? "rgba(79, 70, 229, 0.1)" : "#eef2ff"
                                : theme.palette.mode === "dark" ? "rgba(244, 63, 94, 0.1)" : "#fff1f2",
                              border: 1,
                              borderColor: isHome ? "rgba(79, 70, 229, 0.2)" : "rgba(244, 63, 94, 0.2)",
                              textAlign: isHome ? "right" : "left",
                              maxWidth: 240,
                              boxShadow: "0 2px 6px rgba(0,0,0,0.02)"
                            }}
                          >
                            <Box sx={{ display: "flex", alignItems: "center", gap: 0.8, justifyContent: isHome ? "flex-end" : "flex-start", mb: 0.3 }}>
                              <Chip
                                label={`${event.minute}'`}
                                size="small"
                                sx={{
                                  height: 16,
                                  fontSize: "0.65rem",
                                  fontWeight: 800,
                                  bgcolor: isHome ? "#4f46e5" : "#f43f5e",
                                  color: "#ffffff"
                                }}
                              />
                              <Typography variant="caption" sx={{ fontWeight: 800, fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: 0.3, color: isHome ? "#4f46e5" : "#e11d48" }}>
                                {isHome ? match.home_team_name : match.away_team_name}
                              </Typography>
                            </Box>
                            <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.8rem", color: "text.primary", lineHeight: 1.3 }}>
                              {event.details}
                            </Typography>
                          </Box>
                        </TimelineContent>
                      </TimelineItem>
                    );
                  })}

                  {(!match.events || match.events.length === 0) && (
                    <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
                      No timeline events recorded for this match.
                    </Typography>
                  )}
                </Timeline>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default MatchDetail;
