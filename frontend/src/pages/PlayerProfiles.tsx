import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Typography,
  Box,
  Card,
  CardContent,
  Avatar,
  CircularProgress,
  Alert,
  TextField,
  InputAdornment,
  Chip,
  LinearProgress,
  IconButton,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import GridViewIcon from "@mui/icons-material/GridView";
import ViewListIcon from "@mui/icons-material/ViewList";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";
import { useSimulationStore } from "../store/simulationStore";
import type { Player } from "../services/api";

// Club Palette Map for realistic team avatars
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
  const bg = "linear-gradient(135deg, #028391 0%, #01204E 100%)";
  return { code, bg };
}

const getOverallRating = (attributes: Player["attributes"]): number => {
  if (!attributes) return 0;
  let total = 0;
  let count = 0;
  for (const attrType in attributes) {
    if (attributes[attrType]) {
      for (const subAttr in attributes[attrType]) {
        total += attributes[attrType][subAttr] || 0;
        count += 1;
      }
    }
  }
  return count > 0 ? Math.round(total / count) : 0;
};

const PlayerProfiles: React.FC = () => {
  const { selectedSeason, currentReport, isLoading, error, fetchAvailableSeasons } = useSimulationStore();
  const [allPlayers, setAllPlayers] = useState<Player[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [posFilter, setPosFilter] = useState<string>("ALL");
  const [localLoading, setLocalLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  useEffect(() => {
    if (!selectedSeason) {
      fetchAvailableSeasons();
    }
  }, [selectedSeason, fetchAvailableSeasons]);

  useEffect(() => {
    if (currentReport) {
      setLocalLoading(true);
      const playersFromReport: Player[] = [];
      currentReport.all_teams_details.forEach((team) => {
        playersFromReport.push(...team.players);
      });
      const sortedPlayers = playersFromReport.sort((a, b) => (b.market_value || 0) - (a.market_value || 0));
      setAllPlayers(sortedPlayers);
      setLocalLoading(false);
    } else if (!currentReport && !isLoading && !error && selectedSeason) {
      setLocalLoading(true);
    }
  }, [currentReport, isLoading, error, selectedSeason]);

  const filteredPlayers = useMemo(() => {
    return allPlayers.filter((player) => {
      const lowerSearch = searchTerm.toLowerCase();
      const matchesSearch =
        player.name.toLowerCase().includes(lowerSearch) ||
        player.team.toLowerCase().includes(lowerSearch) ||
        player.position.toLowerCase().includes(lowerSearch);

      if (!matchesSearch) return false;

      const pos = (player.position || "").toUpperCase();
      if (posFilter === "FW") return pos.includes("F") || pos.includes("S") || pos.includes("ST") || pos.includes("RW") || pos.includes("LW");
      if (posFilter === "MF") return pos.includes("M") || pos.includes("CAM") || pos.includes("CDM") || pos.includes("CM");
      if (posFilter === "DF") return pos.includes("CB") || pos.includes("LB") || pos.includes("RB") || pos.includes("D");
      if (posFilter === "GK") return pos.includes("GK");
      return true;
    }).slice(0, 60);
  }, [allPlayers, searchTerm, posFilter]);

  if (isLoading || localLoading) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <CircularProgress size={44} sx={{ color: "#01204E" }} />
        <Typography mt={2} sx={{ fontWeight: 600, color: "#028391" }}>
          Loading player profiles...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ bgcolor: "rgba(244, 63, 94, 0.1)", color: "#f43f5e", border: "1px solid rgba(244, 63, 94, 0.2)" }}>
          {error}
        </Alert>
      </Box>
    );
  }

  if (allPlayers.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography variant="h6" sx={{ fontWeight: 800, color: "#01204E" }}>
          No player data available.
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Please run a simulation first to populate player records.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3.5, pb: 6 }}>
      {/* 1. HERO TITLE HEADER */}
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 2 }}>
        <Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 0.5 }}>
            <Box sx={{ display: "inline-flex", alignItems: "center", gap: 1, px: 1.8, py: 0.6, borderRadius: 9999, bgcolor: "#FAA968", border: "1px solid rgba(1, 32, 78, 0.15)", boxShadow: "0 4px 12px rgba(1, 32, 78, 0.06)" }}>
              <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: "#01204E" }} />
              <Typography variant="caption" sx={{ fontWeight: 800, color: "#01204E", letterSpacing: "0.06em", textTransform: "uppercase", fontSize: "0.72rem" }}>
                SEASON {selectedSeason} SQUAD ROSTER
              </Typography>
            </Box>
          </Box>
          <Typography variant="h3" sx={{ fontWeight: 900, fontFamily: "Outfit, sans-serif", color: "#01204E", letterSpacing: "-0.03em" }}>
            Player Profiles
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600, color: "#028391", mt: 0.5 }}>
            {allPlayers.length} registered players across Premier League teams
          </Typography>
        </Box>

        {/* View Mode Toggle Buttons */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, bgcolor: "#F6DCAC", p: 0.6, borderRadius: 9999, border: "1px solid rgba(1, 32, 78, 0.15)" }}>
          <IconButton
            size="small"
            onClick={() => setViewMode("grid")}
            sx={{
              bgcolor: viewMode === "grid" ? "#01204E" : "transparent",
              color: viewMode === "grid" ? "#ffffff" : "#01204E",
              "&:hover": { bgcolor: viewMode === "grid" ? "#01204E" : "rgba(1, 32, 78, 0.1)" }
            }}
          >
            <GridViewIcon fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            onClick={() => setViewMode("list")}
            sx={{
              bgcolor: viewMode === "list" ? "#01204E" : "transparent",
              color: viewMode === "list" ? "#ffffff" : "#01204E",
              "&:hover": { bgcolor: viewMode === "list" ? "#01204E" : "rgba(1, 32, 78, 0.1)" }
            }}
          >
            <ViewListIcon fontSize="small" />
          </IconButton>
        </Box>
      </Box>

      {/* 2. SEARCH & POSITION FILTER TOOLBAR */}
      <Box
        sx={{
          bgcolor: "#F6DCAC",
          p: 2,
          borderRadius: "24px",
          border: "1.5px solid rgba(250, 169, 104, 0.45)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 2,
          boxShadow: "0 8px 24px rgba(1, 32, 78, 0.06)"
        }}
      >
        {/* Search Field */}
        <Box sx={{ flex: 1, minWidth: 260 }}>
          <TextField
            placeholder="Search by name, team, or position (e.g. Palmer, Arsenal, CB)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            size="small"
            fullWidth
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ color: "#028391" }} />
                </InputAdornment>
              ),
              sx: {
                borderRadius: 9999,
                bgcolor: "#ffffff",
                fontSize: "0.875rem",
                fontWeight: 600,
                color: "#01204E",
                "& fieldset": { borderColor: "rgba(1, 32, 78, 0.15)" },
                "&:hover fieldset": { borderColor: "#028391" }
              }
            }}
          />
        </Box>

        {/* Position Filter Tactile Pills */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          {[
            { id: "ALL", label: "All Players" },
            { id: "FW", label: "Forwards" },
            { id: "MF", label: "Midfielders" },
            { id: "DF", label: "Defenders" },
            { id: "GK", label: "Goalkeepers" },
          ].map((item) => {
            const isSelected = posFilter === item.id;
            return (
              <Chip
                key={item.id}
                label={item.label}
                onClick={() => setPosFilter(item.id)}
                clickable
                sx={{
                  bgcolor: isSelected ? "#FAA968" : "#ffffff",
                  color: "#01204E",
                  fontWeight: isSelected ? 800 : 700,
                  fontSize: "0.78rem",
                  borderRadius: 9999,
                  border: "1px solid rgba(1, 32, 78, 0.15)",
                  boxShadow: isSelected ? "0 4px 12px rgba(1, 32, 78, 0.1)" : "none",
                  transition: "all 0.2s ease-in-out",
                  "&:hover": {
                    bgcolor: isSelected ? "#f79a52" : "rgba(255,255,255,0.85)",
                    transform: "scale(1.04)"
                  }
                }}
              />
            );
          })}
        </Box>
      </Box>

      {/* 3. GRID VIEW */}
      {viewMode === "grid" && (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              sm: "repeat(2, 1fr)",
              md: "repeat(3, 1fr)",
              lg: "repeat(4, 1fr)",
            },
            gap: 2.5,
          }}
        >
          {filteredPlayers.map((player, idx) => {
            const overall = getOverallRating(player.attributes);
            const clubMeta = getClubMeta(player.team);
            const valMillions = ((player.market_value ?? 0) / 1e6).toFixed(0);

            return (
              <Card
                key={`${player.name}-${idx}`}
                className="finnova-card"
                sx={{
                  borderRadius: "20px",
                  border: "1px solid rgba(250, 169, 104, 0.4)",
                  bgcolor: "#fde8c5",
                  transition: "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
                  "&:hover": {
                    transform: "translateY(-4px)",
                    boxShadow: "0 12px 28px rgba(1, 32, 78, 0.12)",
                    borderColor: "#FAA968"
                  }
                }}
              >
                <CardContent sx={{ p: 2.5 }}>
                  {/* Top Row: Avatar, Name/Team, and Rating Badge */}
                  <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", mb: 2, gap: 1.5 }}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, minWidth: 0 }}>
                      <Avatar
                        sx={{
                          width: 46,
                          height: 46,
                          background: clubMeta.bg,
                          color: "#ffffff",
                          fontWeight: 900,
                          fontSize: "0.85rem",
                          boxShadow: "0 4px 12px rgba(1, 32, 78, 0.18)",
                          border: "1.5px solid rgba(255, 255, 255, 0.4)"
                        }}
                      >
                        {clubMeta.code}
                      </Avatar>
                      <Box sx={{ minWidth: 0 }}>
                        <Typography
                          component={Link}
                          to={`/player-profiles/${player.name}`}
                          sx={{
                            fontWeight: 800,
                            fontFamily: "Outfit, sans-serif",
                            fontSize: "1rem",
                            textDecoration: "none",
                            color: "#01204E",
                            display: "block",
                            lineHeight: 1.2,
                            "&:hover": { color: "#028391" },
                          }}
                          noWrap
                        >
                          {player.name}
                        </Typography>
                        <Typography
                          component={Link}
                          to={`/team-details/${player.team}`}
                          variant="caption"
                          sx={{
                            fontWeight: 600,
                            color: "#028391",
                            textDecoration: "none",
                            display: "block",
                            mt: 0.2,
                            "&:hover": { underline: "always" },
                          }}
                          noWrap
                        >
                          {player.team}
                        </Typography>
                      </Box>
                    </Box>

                    {/* Overall Rating Circle Pill */}
                    <Box
                      sx={{
                        width: 32,
                        height: 32,
                        borderRadius: "50%",
                        bgcolor: "#01204E",
                        color: "#F6DCAC",
                        fontWeight: 900,
                        fontSize: "0.8rem",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        boxShadow: "0 3px 8px rgba(1, 32, 78, 0.25)",
                        flexShrink: 0
                      }}
                    >
                      {overall || 70}
                    </Box>
                  </Box>

                  {/* Position & Age Tactile Pills */}
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2.5 }}>
                    <Chip
                      label={player.position}
                      size="small"
                      sx={{
                        bgcolor: "#FAA968",
                        color: "#01204E",
                        fontWeight: 800,
                        fontSize: "0.72rem",
                        borderRadius: 9999,
                        height: 22,
                        border: "1px solid rgba(1, 32, 78, 0.12)"
                      }}
                    />
                    <Chip
                      label={`${player.age}y`}
                      size="small"
                      sx={{
                        bgcolor: "#F6DCAC",
                        color: "#01204E",
                        fontWeight: 700,
                        fontSize: "0.72rem",
                        borderRadius: 9999,
                        height: 22,
                        border: "1px solid rgba(1, 32, 78, 0.12)"
                      }}
                    />
                    {player.is_injured && (
                      <Chip
                        icon={<LocalHospitalIcon sx={{ fontSize: 12, color: "#ffffff !important" }} />}
                        label="Injured"
                        size="small"
                        sx={{
                          height: 22,
                          fontSize: "0.68rem",
                          fontWeight: 800,
                          bgcolor: "#f43f5e",
                          color: "#ffffff",
                          borderRadius: 9999
                        }}
                      />
                    )}
                  </Box>

                  {/* Key Stats Row */}
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2, pt: 1.5, borderTop: "1px solid rgba(1, 32, 78, 0.1)" }}>
                    <Box sx={{ textAlign: "center" }}>
                      <Typography variant="h6" sx={{ fontWeight: 900, color: "#01204E", lineHeight: 1.1 }}>
                        {player.stats?.goals ?? 0}
                      </Typography>
                      <Typography variant="caption" sx={{ fontWeight: 700, color: "#028391", fontSize: "0.7rem" }}>
                        Goals
                      </Typography>
                    </Box>

                    <Box sx={{ textAlign: "center" }}>
                      <Typography variant="h6" sx={{ fontWeight: 900, color: "#01204E", lineHeight: 1.1 }}>
                        {player.stats?.assists ?? 0}
                      </Typography>
                      <Typography variant="caption" sx={{ fontWeight: 700, color: "#028391", fontSize: "0.7rem" }}>
                        Assists
                      </Typography>
                    </Box>

                    <Box sx={{ textAlign: "center" }}>
                      <Typography variant="h6" sx={{ fontWeight: 900, color: "#01204E", lineHeight: 1.1 }}>
                        £{valMillions}M
                      </Typography>
                      <Typography variant="caption" sx={{ fontWeight: 700, color: "#028391", fontSize: "0.7rem" }}>
                        Value
                      </Typography>
                    </Box>
                  </Box>

                  {/* Potential Progress Bar */}
                  <Box>
                    <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                      <Typography variant="caption" sx={{ fontWeight: 700, color: "#028391", fontSize: "0.72rem" }}>
                        Potential
                      </Typography>
                      <Typography variant="caption" sx={{ fontWeight: 800, color: "#01204E", fontSize: "0.72rem" }}>
                        {Math.round(player.potential)}
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={Math.min(100, Math.max(0, player.potential))}
                      sx={{
                        height: 6,
                        borderRadius: 9999,
                        bgcolor: "rgba(1, 32, 78, 0.12)",
                        "& .MuiLinearProgress-bar": {
                          borderRadius: 9999,
                          background: "linear-gradient(90deg, #028391, #FAA968)",
                        },
                      }}
                    />
                  </Box>
                </CardContent>
              </Card>
            );
          })}
        </Box>
      )}

      {/* 4. LIST VIEW */}
      {viewMode === "list" && (
        <Card
          sx={{
            borderRadius: "20px",
            border: "1px solid rgba(250, 169, 104, 0.45)",
            bgcolor: "#fde8c5",
            overflow: "hidden",
            boxShadow: "0 8px 24px rgba(1, 32, 78, 0.06)"
          }}
        >
          <Box sx={{ overflowX: "auto" }}>
            {filteredPlayers.map((player, idx) => {
              const overall = getOverallRating(player.attributes);
              const clubMeta = getClubMeta(player.team);
              const valMillions = ((player.market_value ?? 0) / 1e6).toFixed(1);

              return (
                <Box
                  key={`${player.name}-${idx}`}
                  component={Link}
                  to={`/player-profiles/${player.name}`}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    p: 2,
                    textDecoration: "none",
                    color: "inherit",
                    borderBottom: "1px solid rgba(1, 32, 78, 0.1)",
                    transition: "all 0.2s ease-in-out",
                    "&:hover": { bgcolor: "#F6DCAC" },
                    "&:last-child": { borderBottom: "none" },
                  }}
                >
                  <Avatar
                    sx={{
                      width: 40,
                      height: 40,
                      background: clubMeta.bg,
                      color: "#ffffff",
                      fontWeight: 900,
                      fontSize: "0.8rem",
                      boxShadow: "0 2px 8px rgba(1, 32, 78, 0.15)"
                    }}
                  >
                    {clubMeta.code}
                  </Avatar>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography sx={{ fontWeight: 800, color: "#01204E", fontFamily: "Outfit, sans-serif" }} noWrap>
                      {player.name}
                    </Typography>
                    <Typography variant="caption" sx={{ fontWeight: 600, color: "#028391" }}>
                      {player.team}
                    </Typography>
                  </Box>
                  <Chip
                    label={player.position}
                    size="small"
                    sx={{ bgcolor: "#FAA968", color: "#01204E", fontWeight: 800, borderRadius: 9999, fontSize: "0.72rem" }}
                  />
                  <Chip
                    label={`${player.age}y`}
                    size="small"
                    sx={{ bgcolor: "#F6DCAC", color: "#01204E", fontWeight: 700, borderRadius: 9999, fontSize: "0.72rem" }}
                  />
                  <Box sx={{ display: "flex", gap: 3, alignItems: "center" }}>
                    <Box sx={{ textAlign: "center", minWidth: 45 }}>
                      <Typography variant="body2" sx={{ fontWeight: 800, color: "#01204E" }}>
                        {player.stats?.goals ?? 0}
                      </Typography>
                      <Typography variant="caption" sx={{ fontWeight: 600, color: "#028391", fontSize: "0.65rem" }}>
                        Goals
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: "center", minWidth: 45 }}>
                      <Typography variant="body2" sx={{ fontWeight: 800, color: "#01204E" }}>
                        {player.stats?.assists ?? 0}
                      </Typography>
                      <Typography variant="caption" sx={{ fontWeight: 600, color: "#028391", fontSize: "0.65rem" }}>
                        Assists
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: "center", minWidth: 65 }}>
                      <Typography variant="body2" sx={{ fontWeight: 800, color: "#01204E" }}>
                        £{valMillions}M
                      </Typography>
                      <Typography variant="caption" sx={{ fontWeight: 600, color: "#028391", fontSize: "0.65rem" }}>
                        Value
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        width: 30,
                        height: 30,
                        borderRadius: "50%",
                        bgcolor: "#01204E",
                        color: "#F6DCAC",
                        fontWeight: 900,
                        fontSize: "0.75rem",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      {overall || 70}
                    </Box>
                  </Box>
                </Box>
              );
            })}
          </Box>
        </Card>
      )}

      {/* Results Count Footer */}
      <Typography variant="caption" sx={{ fontWeight: 700, color: "#028391", textAlign: "center", display: "block" }}>
        Showing {filteredPlayers.length} of {allPlayers.length} player profiles
      </Typography>
    </Box>
  );
};

export default PlayerProfiles;
