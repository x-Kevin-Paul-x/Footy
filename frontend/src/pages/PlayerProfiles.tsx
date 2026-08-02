import React, { useEffect, useState } from "react";
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
  alpha,
  ToggleButton,
  ToggleButtonGroup,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import GridViewIcon from "@mui/icons-material/GridView";
import ViewListIcon from "@mui/icons-material/ViewList";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";
import { useSimulationStore } from "../store/simulationStore";
import type { Player } from "../services/api";

// Position color definitions
const getPositionColor = (position: string): string => {
  if (position.startsWith("GK")) return "#a78bfa"; // violet/purple
  if (position.startsWith("D")) return "#06b6d4"; // cyan
  if (position.startsWith("M")) return "#10b981"; // emerald
  if (position.startsWith("F") || position.startsWith("S")) return "#f43f5e"; // rose/crimson
  return "#8b5cf6";
};

// Dynamic FINNOVA Card Style with Top Border Indicator and Position Color Accent
const getPlayerCardSx = (position: string) => {
  const color = getPositionColor(position);
  return {
    position: "relative" as const,
    borderRadius: "20px",
    transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
    overflow: "hidden",
    "&::before": {
      content: '""',
      position: "absolute",
      top: 0,
      left: 0,
      right: 0,
      height: 4,
      background: `linear-gradient(90deg, ${color}, ${alpha(color, 0.4)})`,
    },
    "&:hover": {
      transform: "translateY(-4px)",
      borderColor: color,
      boxShadow: `0 12px 32px 0 ${alpha(color, 0.15)}`,
    },
  };
};

const generalGlassCardSx = {
  borderRadius: "20px !important",
  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important",
  "&:hover": {
    borderColor: "#6366f1 !important",
    boxShadow: "0 12px 32px 0 rgba(99, 102, 241, 0.15) !important",
  }
};


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
  return count > 0 ? total / count : 0;
};

const PlayerProfiles: React.FC = () => {
  const { selectedSeason, currentReport, isLoading, error, fetchAvailableSeasons } = useSimulationStore();
  const [allPlayers, setAllPlayers] = useState<Player[]>([]);
  const [filteredPlayers, setFilteredPlayers] = useState<Player[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
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
      const sortedPlayers = playersFromReport.sort((a, b) => b.market_value - a.market_value);
      setAllPlayers(sortedPlayers);
      setFilteredPlayers(sortedPlayers.slice(0, 50));
      setLocalLoading(false);
    } else if (!currentReport && !isLoading && !error && selectedSeason) {
      setLocalLoading(true);
    }
  }, [currentReport, isLoading, error, selectedSeason]);

  useEffect(() => {
    const lowercasedSearchTerm = searchTerm.toLowerCase();
    const filtered = allPlayers.filter(
      (player) =>
        player.name.toLowerCase().includes(lowercasedSearchTerm) ||
        player.team.toLowerCase().includes(lowercasedSearchTerm) ||
        player.position.toLowerCase().includes(lowercasedSearchTerm)
    );
    setFilteredPlayers(filtered.slice(0, 50));
  }, [searchTerm, allPlayers]);

  if (isLoading || localLoading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress size={48} />
        <Typography mt={2} color="text.secondary">Loading player profiles...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (allPlayers.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <Typography variant="h6">No player data available.</Typography>
        <Typography variant="body2" color="text.secondary">
          Please run a simulation first.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: { xs: 1, md: 0 } }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Player Profiles
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {allPlayers.length} players • Season {selectedSeason}
        </Typography>
      </Box>

      {/* Search & Controls */}
      <Box
        sx={{
          display: "flex",
          gap: 2,
          mb: 4,
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <TextField
          placeholder="Search by name, team, or position..."
          variant="outlined"
          size="small"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          sx={{
            flex: 1,
            minWidth: 250,
            "& .MuiOutlinedInput-root": {
              bgcolor: (theme) => alpha(theme.palette.background.paper, 0.6),
              backdropFilter: "blur(10px)",
            },
          }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon color="action" />
              </InputAdornment>
            ),
          }}
        />
        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={(_, v) => v && setViewMode(v)}
          size="small"
        >
          <ToggleButton value="grid">
            <GridViewIcon />
          </ToggleButton>
          <ToggleButton value="list">
            <ViewListIcon />
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* Grid View */}
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
            gap: 3,
          }}
        >
          {filteredPlayers.map((player, idx) => {
            const overall = getOverallRating(player.attributes);
            const posColor = getPositionColor(player.position);

            return (
              <Card key={idx} sx={getPlayerCardSx(player.position)}>
                <CardContent sx={{ p: 2.5 }}>
                  {/* Header with Avatar */}
                  <Box sx={{ display: "flex", alignItems: "flex-start", mb: 2 }}>
                    <Avatar
                      sx={{
                        width: 56,
                        height: 56,
                        bgcolor: alpha(posColor, 0.2),
                        color: posColor,
                        fontWeight: 700,
                        fontSize: 20,
                        mr: 2,
                      }}
                    >
                      {player.name[0]}
                    </Avatar>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography
                        component={Link}
                        to={`/player-profiles/${player.name}`}
                        sx={{
                          fontWeight: 600,
                          fontSize: "1rem",
                          textDecoration: "none",
                          color: "text.primary",
                          display: "block",
                          "&:hover": { color: "primary.main" },
                        }}
                        noWrap
                      >
                        {player.name}
                      </Typography>
                      <Typography
                        component={Link}
                        to={`/team-details/${player.team}`}
                        variant="body2"
                        sx={{
                          color: "text.secondary",
                          textDecoration: "none",
                          "&:hover": { color: "primary.main" },
                        }}
                        noWrap
                      >
                        {player.team}
                      </Typography>
                    </Box>
                    <Chip
                      label={(overall ?? 0).toFixed(0)}
                      size="small"
                      sx={{
                        fontWeight: 700,
                        bgcolor: overall >= 75 ? "success.main" : overall >= 60 ? "warning.main" : "action.selected",
                        color: overall >= 60 ? "white" : "text.primary",
                      }}
                    />
                  </Box>

                  {/* Position & Age */}
                  <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
                    <Chip
                      label={player.position}
                      size="small"
                      sx={{ bgcolor: alpha(posColor, 0.15), color: posColor, fontWeight: 600 }}
                    />
                    <Chip label={`${player.age}y`} size="small" variant="outlined" />
                    {player.is_injured && (
                      <Chip
                        icon={<LocalHospitalIcon sx={{ fontSize: 14 }} />}
                        label="Injured"
                        size="small"
                        color="error"
                      />
                    )}
                  </Box>

                  {/* Stats */}
                  <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1.5 }}>
                    <Box sx={{ textAlign: "center" }}>
                      <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main" }}>
                        {player.stats?.goals || 0}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Goals
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: "center" }}>
                      <Typography variant="h6" sx={{ fontWeight: 700, color: "info.main" }}>
                        {player.stats?.assists || 0}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Assists
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: "center" }}>
                      <Typography variant="h6" sx={{ fontWeight: 700, color: "success.main" }}>
                        £{((player?.market_value ?? 0) / 1e6).toFixed(0)}M
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Value
                      </Typography>
                    </Box>
                  </Box>

                  {/* Potential Bar */}
                  <Box>
                    <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">
                        Potential
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {Math.round(player.potential)}
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={player.potential}
                      sx={{
                        height: 6,
                        borderRadius: 3,
                        bgcolor: (theme) => alpha(theme.palette.primary.main, 0.1),
                        "& .MuiLinearProgress-bar": {
                          borderRadius: 3,
                          background: `linear-gradient(90deg, #3b82f6, #8b5cf6)`,
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

      {/* List View */}
      {viewMode === "list" && (
        <Card sx={generalGlassCardSx}>
          <Box sx={{ overflow: "auto" }}>
            {filteredPlayers.map((player, idx) => {
              const overall = getOverallRating(player.attributes);
              const posColor = getPositionColor(player.position);

              return (
                <Box
                  key={idx}
                  component={Link}
                  to={`/player-profiles/${player.name}`}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    p: 2,
                    textDecoration: "none",
                    color: "inherit",
                    borderBottom: "1px solid",
                    borderColor: "divider",
                    "&:hover": { bgcolor: "action.hover" },
                    "&:last-child": { borderBottom: "none" },
                  }}
                >
                  <Avatar
                    sx={{
                      width: 40,
                      height: 40,
                      bgcolor: alpha(posColor, 0.2),
                      color: posColor,
                      fontWeight: 600,
                    }}
                  >
                    {player.name[0]}
                  </Avatar>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography sx={{ fontWeight: 600 }} noWrap>
                      {player.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {player.team}
                    </Typography>
                  </Box>
                  <Chip label={player.position} size="small" sx={{ bgcolor: alpha(posColor, 0.15), color: posColor }} />
                  <Box sx={{ display: "flex", gap: 3, alignItems: "center" }}>
                    <Box sx={{ textAlign: "center", minWidth: 50 }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {player.stats?.goals || 0}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        G
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: "center", minWidth: 50 }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {player.stats?.assists || 0}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        A
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: "center", minWidth: 70 }}>
                      <Typography variant="body2" sx={{ fontWeight: 600, color: "success.main" }}>
                        £{((player?.market_value ?? 0) / 1e6).toFixed(1)}M
                      </Typography>
                    </Box>
                    <Chip
                      label={(overall ?? 0).toFixed(0)}
                      size="small"
                      sx={{
                        fontWeight: 700,
                        bgcolor: overall >= 75 ? "success.main" : overall >= 60 ? "warning.main" : "action.selected",
                        color: overall >= 60 ? "white" : "text.primary",
                        minWidth: 40,
                      }}
                    />
                  </Box>
                </Box>
              );
            })}
          </Box>
        </Card>
      )}

      {/* Results count */}
      <Typography variant="body2" color="text.secondary" sx={{ mt: 3, textAlign: "center" }}>
        Showing {filteredPlayers.length} of {allPlayers.length} players
      </Typography>
    </Box>
  );
};

export default PlayerProfiles;
