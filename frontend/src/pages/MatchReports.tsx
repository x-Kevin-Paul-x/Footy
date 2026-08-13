import React, { useEffect, useState, useMemo } from "react";
import {
  Typography,
  Box,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  TextField,
  InputAdornment,
  Chip,
  Avatar,
  IconButton,
  useTheme,
  Grid,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import SportsSoccerIcon from "@mui/icons-material/SportsSoccer";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import ArrowForwardIosIcon from "@mui/icons-material/ArrowForwardIos";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import { useSimulationStore } from "../store/simulationStore";
import { getMatchesBySeason } from "../services/api";
import { useNavigate } from "react-router-dom";

// Club Gradient Map for realistic badges
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
  
  // Generic fallback code & gradient
  const code = teamName ? teamName.substring(0, 3).toUpperCase() : "FC";
  const bg = "linear-gradient(135deg, #6366f1 0%, #3730a3 100%)";
  return { code, bg };
}

const MatchReports: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const { selectedSeason, fetchAvailableSeasons, availableSeasons, selectSeason } = useSimulationStore();
  
  const [matches, setMatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Search & Filter state
  const [searchTerm, setSearchTerm] = useState("");
  const [outcomeFilter, setOutcomeFilter] = useState<"all" | "high" | "draw">("all");

  useEffect(() => {
    if (availableSeasons.length === 0) {
      fetchAvailableSeasons();
    }
  }, [availableSeasons, fetchAvailableSeasons]);

  useEffect(() => {
    const fetchMatches = async () => {
      if (selectedSeason) {
        setLoading(true);
        setError(null);
        try {
          const data = await getMatchesBySeason(selectedSeason);
          const sorted = [...data].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
          setMatches(sorted);
        } catch {
          setError("Failed to fetch match fixtures and results.");
        } finally {
          setLoading(false);
        }
      }
    };
    fetchMatches();
  }, [selectedSeason]);

  // Computed stats
  const matchStats = useMemo(() => {
    if (!matches.length) return { total: 0, goals: 0, avgGoals: "0.0", highestScoring: null };
    let totalGoals = 0;
    let highestMatch: any = null;
    let maxGoalsInMatch = -1;

    matches.forEach((m) => {
      const hG = m.home_goals ?? m.home_score ?? 0;
      const aG = m.away_goals ?? m.away_score ?? 0;
      const matchTotal = hG + aG;
      totalGoals += matchTotal;
      if (matchTotal > maxGoalsInMatch) {
        maxGoalsInMatch = matchTotal;
        highestMatch = m;
      }
    });

    return {
      total: matches.length,
      goals: totalGoals,
      avgGoals: (totalGoals / (matches.length || 1)).toFixed(2),
      highestScoring: highestMatch,
    };
  }, [matches]);

  // Filtered matches
  const filteredMatches = useMemo(() => {
    return matches.filter((m) => {
      const homeName = m.home_team_name || "";
      const awayName = m.away_team_name || "";
      const matchesSearch =
        homeName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        awayName.toLowerCase().includes(searchTerm.toLowerCase());

      if (!matchesSearch) return false;

      const hG = m.home_goals ?? m.home_score ?? 0;
      const aG = m.away_goals ?? m.away_score ?? 0;

      if (outcomeFilter === "high") return hG + aG >= 5;
      if (outcomeFilter === "draw") return hG === aG;
      return true;
    });
  }, [matches, searchTerm, outcomeFilter]);

  // Group by date
  const groupedMatches = useMemo(() => {
    const grouped: { [date: string]: any[] } = {};
    filteredMatches.forEach((match) => {
      let dateStr = "Unknown Date";
      if (match.date) {
        const parsed = new Date(match.date);
        dateStr = isNaN(parsed.getTime())
          ? "Unknown Date"
          : parsed.toLocaleDateString(undefined, { weekday: "long", year: "numeric", month: "long", day: "numeric" });
      }
      if (!grouped[dateStr]) grouped[dateStr] = [];
      grouped[dateStr].push(match);
    });
    return grouped;
  }, [filteredMatches]);

  const sortedDates = Object.keys(groupedMatches).sort((a, b) => new Date(b).getTime() - new Date(a).getTime());

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3.5, pb: 6 }}>
      {/* 1. HEADER BANNER & HIGHLIGHT METRICS */}
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 2 }}>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 800, fontFamily: "Outfit, sans-serif", letterSpacing: "-0.02em" }}>
              Match Results & Fixtures Center
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500, mt: 0.5 }}>
              Browse complete match logs, scores, and timeline details for Season {selectedSeason}
            </Typography>
          </Box>

          {/* Season Selector Pills */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.2, overflowX: "auto", py: 0.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 800, color: "#01204E", textTransform: "uppercase", letterSpacing: 0.8 }}>
              Season:
            </Typography>
            {availableSeasons.slice(0, 8).map((seasonYr) => {
              const isSelected = selectedSeason === seasonYr;
              return (
                <Chip
                  key={seasonYr}
                  label={`Season ${seasonYr}`}
                  onClick={() => selectSeason(seasonYr)}
                  clickable
                  sx={{
                    bgcolor: isSelected ? "#FAA968" : "#F6DCAC",
                    color: "#01204E",
                    fontWeight: isSelected ? 800 : 700,
                    fontSize: "0.8rem",
                    borderRadius: 9999,
                    border: "1px solid rgba(1, 32, 78, 0.18)",
                    boxShadow: isSelected ? "0 4px 12px rgba(1, 32, 78, 0.1)" : "0 2px 6px rgba(1, 32, 78, 0.04)",
                    transition: "all 0.2s ease-in-out",
                    "&:hover": {
                      bgcolor: isSelected ? "#f79a52" : "#f5d399",
                      transform: "scale(1.04)"
                    }
                  }}
                />
              );
            })}
          </Box>
        </Box>

        {/* Highlight Metric Cards */}
        <Grid container spacing={2}>
          <Grid item xs={12} sm={4}>
            <Card
              sx={{
                bgcolor: "background.paper",
                border: 1,
                borderColor: "divider",
                borderRadius: "20px",
                p: 2.5,
                boxShadow: theme.palette.mode === "dark" ? "0 10px 30px rgba(0,0,0,0.3)" : "0 10px 30px -5px rgba(0,0,0,0.04)"
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: "uppercase" }}>
                    Total Fixtures
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5 }}>
                    {matchStats.total}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: "rgba(79, 70, 229, 0.1)", color: "#4f46e5", width: 48, height: 48 }}>
                  <CalendarMonthIcon />
                </Avatar>
              </Box>
            </Card>
          </Grid>

          <Grid item xs={12} sm={4}>
            <Card
              sx={{
                bgcolor: "background.paper",
                border: 1,
                borderColor: "divider",
                borderRadius: "20px",
                p: 2.5,
                boxShadow: theme.palette.mode === "dark" ? "0 10px 30px rgba(0,0,0,0.3)" : "0 10px 30px -5px rgba(0,0,0,0.04)"
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: "uppercase" }}>
                    Total Goals Scored
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5, color: "#10b981" }}>
                    {matchStats.goals}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                    Avg {matchStats.avgGoals} goals / match
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: "rgba(16, 185, 129, 0.1)", color: "#10b981", width: 48, height: 48 }}>
                  <SportsSoccerIcon />
                </Avatar>
              </Box>
            </Card>
          </Grid>

          <Grid item xs={12} sm={4}>
            <Card
              sx={{
                bgcolor: "background.paper",
                border: 1,
                borderColor: "divider",
                borderRadius: "20px",
                p: 2.5,
                boxShadow: theme.palette.mode === "dark" ? "0 10px 30px rgba(0,0,0,0.3)" : "0 10px 30px -5px rgba(0,0,0,0.04)"
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: "uppercase" }}>
                    Highest Scoring Match
                  </Typography>
                  <Typography variant="subtitle1" sx={{ fontWeight: 800, mt: 0.5 }} noWrap>
                    {matchStats.highestScoring
                      ? `${matchStats.highestScoring.home_team_name} ${matchStats.highestScoring.home_goals ?? matchStats.highestScoring.home_score} - ${matchStats.highestScoring.away_goals ?? matchStats.highestScoring.away_score} ${matchStats.highestScoring.away_team_name}`
                      : "N/A"}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: "rgba(245, 158, 11, 0.1)", color: "#f59e0b", width: 48, height: 48 }}>
                  <EmojiEventsIcon />
                </Avatar>
              </Box>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* 2. SEARCH & FILTER TOOLBAR */}
      <Box
        sx={{
          bgcolor: "background.paper",
          p: 2,
          borderRadius: "20px",
          border: 1,
          borderColor: "divider",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 2,
          boxShadow: theme.palette.mode === "dark" ? "0 8px 24px rgba(0,0,0,0.2)" : "0 4px 20px rgba(0,0,0,0.02)"
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flex: 1, minWidth: 260 }}>
          <TextField
            placeholder="Search by team name (e.g. Arsenal, Chelsea)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            size="small"
            fullWidth
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ color: "text.secondary" }} />
                </InputAdornment>
              ),
              sx: { borderRadius: 9999, fontSize: "0.875rem" }
            }}
          />
        </Box>

        {/* Outcome Filter Pills */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.2 }}>
          {[
            { id: "all", label: "All Results" },
            { id: "high", label: "High Scoring (5+)" },
            { id: "draw", label: "Draws" },
          ].map((item) => {
            const isSelected = outcomeFilter === item.id;
            return (
              <Chip
                key={item.id}
                label={item.label}
                onClick={() => setOutcomeFilter(item.id as any)}
                clickable
                sx={{
                  bgcolor: isSelected ? "#FAA968" : "#F6DCAC",
                  color: "#01204E",
                  fontWeight: isSelected ? 800 : 700,
                  fontSize: "0.8rem",
                  borderRadius: 9999,
                  border: "1px solid rgba(1, 32, 78, 0.18)",
                  boxShadow: isSelected ? "0 4px 12px rgba(1, 32, 78, 0.1)" : "0 2px 6px rgba(1, 32, 78, 0.04)",
                  transition: "all 0.2s ease-in-out",
                  "&:hover": {
                    bgcolor: isSelected ? "#f79a52" : "#f5d399",
                    transform: "scale(1.04)"
                  }
                }}
              />
            );
          })}
          {(searchTerm || outcomeFilter !== "all") && (
            <IconButton
              size="small"
              onClick={() => {
                setSearchTerm("");
                setOutcomeFilter("all");
              }}
              title="Reset Filters"
            >
              <RestartAltIcon fontSize="small" />
            </IconButton>
          )}
        </Box>
      </Box>

      {/* 3. MATCH RESULTS LIST */}
      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ borderRadius: "16px" }}>
          {error}
        </Alert>
      )}

      {!loading && !error && filteredMatches.length === 0 && (
        <Card sx={{ borderRadius: "20px", border: 1, borderColor: "divider" }}>
          <CardContent sx={{ p: 5, textAlign: "center" }}>
            <CalendarMonthIcon sx={{ fontSize: 56, color: "text.secondary", mb: 2 }} />
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              No matches found
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Try adjusting your search query or season filter.
            </Typography>
          </CardContent>
        </Card>
      )}

      {!loading && !error && sortedDates.map((date) => (
        <Box key={date} sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          {/* Date Group Header */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, px: 1, pt: 1 }}>
            <CalendarMonthIcon sx={{ fontSize: 18, color: "primary.main" }} />
            <Typography variant="subtitle1" sx={{ fontWeight: 800, color: "text.secondary", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: 0.5 }}>
              {date}
            </Typography>
            <Chip
              label={`${groupedMatches[date].length} ${groupedMatches[date].length === 1 ? 'Match' : 'Matches'}`}
              size="small"
              sx={{ height: 20, fontSize: "0.7rem", fontWeight: 700, bgcolor: theme.palette.mode === "dark" ? "rgba(255,255,255,0.08)" : "#e2e8f0" }}
            />
          </Box>

          {/* Match Items Grid */}
          <Grid container spacing={2}>
            {groupedMatches[date].map((match) => {
              const homeMeta = getClubMeta(match.home_team_name);
              const awayMeta = getClubMeta(match.away_team_name);
              const hGoals = match.home_goals ?? match.home_score ?? 0;
              const aGoals = match.away_goals ?? match.away_score ?? 0;
              const homeWon = hGoals > aGoals;
              const awayWon = aGoals > hGoals;

              return (
                <Grid item xs={12} key={match.match_id}>
                  <Card
                    onClick={() => navigate(`/match/${match.match_id}`)}
                    sx={{
                      bgcolor: "background.paper",
                      border: 1,
                      borderColor: "divider",
                      borderRadius: "20px",
                      transition: "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
                      cursor: "pointer",
                      overflow: "hidden",
                      position: "relative",
                      boxShadow: theme.palette.mode === "dark" ? "0 4px 20px rgba(0,0,0,0.2)" : "0 4px 16px rgba(0,0,0,0.03)",
                      "&:hover": {
                        transform: "translateY(-3px)",
                        borderColor: "#6366f1",
                        boxShadow: "0 12px 30px rgba(99, 102, 241, 0.18)",
                        "& .match-arrow-btn": {
                          opacity: 1,
                          transform: "translateX(0)"
                        }
                      }
                    }}
                  >
                    <Box
                      sx={{
                        p: { xs: 2, sm: 2.5 },
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: 2
                      }}
                    >
                      {/* Home Team */}
                      <Box
                        sx={{
                          flex: 1,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "flex-end",
                          gap: 2,
                          textAlign: "right"
                        }}
                      >
                        <Box sx={{ display: { xs: "none", sm: "block" } }}>
                          <Typography
                            variant="subtitle1"
                            sx={{
                              fontWeight: homeWon ? 800 : 600,
                              color: homeWon ? "text.primary" : "text.secondary",
                              lineHeight: 1.2
                            }}
                          >
                            {match.home_team_name}
                          </Typography>
                          {homeWon && (
                            <Chip
                              label="WINNER"
                              size="small"
                              sx={{
                                height: 16,
                                fontSize: "0.6rem",
                                fontWeight: 800,
                                bgcolor: "rgba(16, 185, 129, 0.15)",
                                color: "#10b981",
                                mt: 0.3
                              }}
                            />
                          )}
                        </Box>
                        <Avatar
                          sx={{
                            width: 44,
                            height: 44,
                            background: homeMeta.bg,
                            color: "#ffffff",
                            fontWeight: 800,
                            fontSize: "0.85rem",
                            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                            border: homeWon ? "2px solid #10b981" : "2px solid rgba(255,255,255,0.2)"
                          }}
                        >
                          {homeMeta.code}
                        </Avatar>
                      </Box>

                      {/* Score Badge Center Pill */}
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          px: 2.8,
                          py: 0.8,
                          borderRadius: 9999,
                          bgcolor: "#01204E",
                          border: "1px solid rgba(255, 255, 255, 0.15)",
                          boxShadow: "0 4px 14px rgba(1, 32, 78, 0.3)",
                          minWidth: 95
                        }}
                      >
                        <Typography
                          variant="h6"
                          sx={{
                            fontWeight: 900,
                            fontFamily: "Outfit, sans-serif",
                            color: "#ffffff",
                            letterSpacing: "0.1em"
                          }}
                        >
                          {hGoals} : {aGoals}
                        </Typography>
                      </Box>

                      {/* Away Team */}
                      <Box
                        sx={{
                          flex: 1,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "flex-start",
                          gap: 2,
                          textAlign: "left"
                        }}
                      >
                        <Avatar
                          sx={{
                            width: 44,
                            height: 44,
                            background: awayMeta.bg,
                            color: "#ffffff",
                            fontWeight: 800,
                            fontSize: "0.85rem",
                            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                            border: awayWon ? "2px solid #10b981" : "2px solid rgba(255,255,255,0.2)"
                          }}
                        >
                          {awayMeta.code}
                        </Avatar>
                        <Box sx={{ display: { xs: "none", sm: "block" } }}>
                          <Typography
                            variant="subtitle1"
                            sx={{
                              fontWeight: awayWon ? 800 : 600,
                              color: awayWon ? "text.primary" : "text.secondary",
                              lineHeight: 1.2
                            }}
                          >
                            {match.away_team_name}
                          </Typography>
                          {awayWon && (
                            <Chip
                              label="WINNER"
                              size="small"
                              sx={{
                                height: 16,
                                fontSize: "0.6rem",
                                fontWeight: 800,
                                bgcolor: "rgba(16, 185, 129, 0.15)",
                                color: "#10b981",
                                mt: 0.3
                              }}
                            />
                          )}
                        </Box>
                      </Box>

                      {/* Hover Details Arrow */}
                      <Box
                        className="match-arrow-btn"
                        sx={{
                          opacity: 0.4,
                          transform: "translateX(-4px)",
                          transition: "all 0.2s ease",
                          display: { xs: "none", md: "block" }
                        }}
                      >
                        <ArrowForwardIosIcon sx={{ fontSize: 16, color: "#4f46e5" }} />
                      </Box>
                    </Box>
                  </Card>
                </Grid>
              );
            })}
          </Grid>
        </Box>
      ))}
    </Box>
  );
};

export default MatchReports;
