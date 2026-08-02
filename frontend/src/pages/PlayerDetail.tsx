import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Typography,
  Box,
  Card,
  CardContent,
  Avatar,
  CircularProgress,
  Alert,
  Chip,
  LinearProgress,
  alpha,
  Tabs,
  Tab,
} from "@mui/material";
import { useSimulationStore } from "../store/simulationStore";
import type { Player } from "../services/api";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

// Icons
import SportsSoccerIcon from "@mui/icons-material/SportsSoccer";
import AssistIcon from "@mui/icons-material/Moving";
import PersonIcon from "@mui/icons-material/Person";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";
import FitnessCenterIcon from "@mui/icons-material/FitnessCenter";

const generalGlassCardSx = {
  borderRadius: "16px",
  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important",
  "&:hover": {
    borderColor: "rgba(99, 102, 241, 0.25) !important",
    boxShadow: "0 12px 40px 0 rgba(99, 102, 241, 0.12) !important",
  }
};

const getPositionColor = (position: string): string => {
  if (position.startsWith("GK")) return "#a78bfa"; // violet/purple
  if (position.startsWith("D")) return "#06b6d4"; // cyan
  if (position.startsWith("M")) return "#10b981"; // emerald
  if (position.startsWith("F") || position.startsWith("S")) return "#f43f5e"; // rose/crimson
  return "#8b5cf6";
};

const PlayerDetail: React.FC = () => {
  const { playerName } = useParams<{ playerName: string }>();
  const { selectedSeason, currentReport, isLoading, error, fetchAvailableSeasons } = useSimulationStore();

  const [player, setPlayer] = useState<Player | null>(null);
  const [localLoading, setLocalLoading] = useState(true);
  const [localError, setLocalError] = useState<string | null>(null);
  const [tab, setTab] = useState(0);

  useEffect(() => {
    if (!selectedSeason) {
      fetchAvailableSeasons();
    }
  }, [selectedSeason, fetchAvailableSeasons]);

  useEffect(() => {
    if (currentReport && playerName) {
      setLocalLoading(true);
      setLocalError(null);
      let foundPlayer: Player | null = null;
      for (const teamDetail of currentReport.all_teams_details) {
        foundPlayer = teamDetail.players.find((p) => p.name === playerName) || null;
        if (foundPlayer) break;
      }

      if (foundPlayer) {
        setPlayer(foundPlayer);
      } else {
        setLocalError(`Player "${playerName}" not found for season ${selectedSeason}.`);
      }
      setLocalLoading(false);
    } else if (!currentReport && !isLoading && !error && selectedSeason) {
      setLocalLoading(true);
    }
  }, [currentReport, playerName, selectedSeason, isLoading, error]);

  if (isLoading || localLoading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress size={48} />
        <Typography sx={{ mt: 2 }} color="text.secondary">
          Loading player details...
        </Typography>
      </Box>
    );
  }

  if (error || localError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error || localError}</Alert>
      </Box>
    );
  }

  if (!player) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <Typography variant="h6">No player data available.</Typography>
      </Box>
    );
  }

  const getOverallRating = (attributes: Player["attributes"]) => {
    if (!attributes) return 0;
    const totalAttributeSum = Object.values(attributes).reduce(
      (sum, category: Record<string, number>) =>
        sum + Object.values(category || {}).reduce((catSum, val) => catSum + val, 0),
      0
    );
    const totalAttributeCount = Object.values(attributes).reduce(
      (count, category: Record<string, number>) => count + Object.keys(category || {}).length,
      0
    );
    return totalAttributeCount > 0 ? totalAttributeSum / totalAttributeCount : 0;
  };

  const overall = getOverallRating(player.attributes);
  const posColor = getPositionColor(player.position);

  // Prepare radar chart data (average per category)
  const radarData = Object.entries(player.attributes).map(([category, attrs]) => {
    const values = Object.values(attrs as Record<string, number>);
    const avg = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0;
    return {
      category: category.charAt(0).toUpperCase() + category.slice(1),
      value: Math.round(avg),
      fullMark: 100,
    };
  });

  const statCards = [
    { label: "Goals", value: player.stats?.goals || 0, icon: <SportsSoccerIcon />, color: "#3b82f6" },
    { label: "Assists", value: player.stats?.assists || 0, icon: <AssistIcon />, color: "#10b981" },
    { label: "Appearances", value: player.stats?.appearances || 0, icon: <PersonIcon />, color: "#8b5cf6" },
    { label: "Fitness", value: `${player.stats?.fitness || 0}%`, icon: <FitnessCenterIcon />, color: "#f59e0b" },
  ];

  return (
    <Box sx={{ p: { xs: 1, md: 0 } }}>
      {/* Hero Section */}
      <Card
        sx={{
          mb: 3,
          position: "relative",
          background: `linear-gradient(135deg, ${alpha(posColor, 0.15)} 0%, rgba(15, 23, 42, 0.65) 100%)`,
          backdropFilter: "blur(24px) saturate(120%)",
          WebkitBackdropFilter: "blur(24px) saturate(120%)",
          border: "1px solid rgba(255, 255, 255, 0.05)",
          borderRadius: "16px",
          boxShadow: `0 8px 32px 0 rgba(0, 0, 0, 0.3), inset 0 0 0 1px ${alpha(posColor, 0.15)}`,
          overflow: "hidden",
          "&::before": {
            content: '""',
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 4,
            background: `linear-gradient(90deg, ${posColor}, ${alpha(posColor, 0.3)})`,
          }
        }}
      >
        <CardContent sx={{ p: 4 }}>
          <Box sx={{ display: "flex", alignItems: "flex-start", gap: 3, flexWrap: "wrap" }}>
            {/* Large Avatar */}
            <Avatar
              sx={{
                width: 120,
                height: 120,
                bgcolor: alpha(posColor, 0.2),
                color: posColor,
                fontSize: 48,
                fontWeight: 700,
                border: `4px solid ${posColor}`,
              }}
            >
              {player.name[0]}
            </Avatar>

            {/* Player Info */}
            <Box sx={{ flex: 1, minWidth: 200 }}>
              <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
                {player.name}
              </Typography>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
                <Chip
                  label={player.position}
                  sx={{ bgcolor: alpha(posColor, 0.2), color: posColor, fontWeight: 700 }}
                />
                <Chip
                  component={Link}
                  to={`/team-details/${player.team}`}
                  label={player.team}
                  clickable
                  variant="outlined"
                />
                <Chip label={`${player.age} years`} variant="outlined" />
                <Chip label={player.squad_role} variant="outlined" />
                {player.is_injured && (
                  <Chip
                    icon={<LocalHospitalIcon />}
                    label={`Injured (${player.recovery_time}d)`}
                    color="error"
                  />
                )}
              </Box>

              {/* Value & Contract */}
              <Box sx={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Market Value
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 700, color: "success.main" }}>
                    £{((player?.market_value ?? 0) / 1e6).toFixed(1)}M
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Weekly Wage
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    £{player.wage.toLocaleString()}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Contract
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    {player.contract_length} years
                  </Typography>
                </Box>
              </Box>
            </Box>

            {/* Overall Rating Circle */}
            <Box
              sx={{
                width: 100,
                height: 100,
                borderRadius: "50%",
                background: `conic-gradient(${overall >= 75 ? "#10b981" : overall >= 60 ? "#f59e0b" : "#ef4444"} ${overall}%, transparent 0)`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                position: "relative",
              }}
            >
              <Box
                sx={{
                  width: 80,
                  height: 80,
                  borderRadius: "50%",
                  bgcolor: "background.paper",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexDirection: "column",
                }}
              >
                <Typography variant="h4" sx={{ fontWeight: 700 }}>
                  {(overall ?? 0).toFixed(0)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  OVR
                </Typography>
              </Box>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Stat Cards */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "repeat(2, 1fr)", md: "repeat(4, 1fr)" },
          gap: 2,
          mb: 3,
        }}
      >
        {statCards.map((stat) => (
          <Card key={stat.label} sx={generalGlassCardSx}>
            <CardContent sx={{ p: 2, textAlign: "center" }}>
              <Avatar
                sx={{
                  width: 40,
                  height: 40,
                  bgcolor: alpha(stat.color, 0.15),
                  color: stat.color,
                  mx: "auto",
                  mb: 1,
                }}
              >
                {stat.icon}
              </Avatar>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {stat.value}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {stat.label}
              </Typography>
            </CardContent>
          </Card>
        ))}
      </Box>

      {/* Tabs */}
      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 3, "& .MuiTab-root": { fontWeight: 600 } }}
      >
        <Tab label="Attributes" />
        <Tab label="Form & History" />
      </Tabs>

      {/* Attributes Tab */}
      {tab === 0 && (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, gap: 3 }}>
          {/* Radar Chart */}
          <Card sx={generalGlassCardSx}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Attribute Overview
              </Typography>
              <Box sx={{ height: 350 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#475569" />
                    <PolarAngleAxis dataKey="category" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#64748b" }} />
                    <Radar
                      name="Attributes"
                      dataKey="value"
                      stroke="#06b6d4"
                      fill="#06b6d4"
                      fillOpacity={0.3}
                      strokeWidth={2.5}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>

          {/* Detailed Attributes */}
          <Card sx={generalGlassCardSx}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Detailed Attributes
              </Typography>
              <Box sx={{ maxHeight: 400, overflow: "auto" }}>
                {Object.entries(player.attributes).map(([category, attrs]) => (
                  <Box key={category} sx={{ mb: 3 }}>
                    <Typography
                      variant="subtitle2"
                      sx={{
                        fontWeight: 700,
                        textTransform: "uppercase",
                        color: "primary.main",
                        mb: 1,
                      }}
                    >
                      {category}
                    </Typography>
                    {Object.entries(attrs as Record<string, number>).map(([name, value]) => (
                      <Box key={name} sx={{ mb: 1 }}>
                        <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                          <Typography variant="body2" sx={{ textTransform: "capitalize" }}>
                            {name.replace(/_/g, " ")}
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {value}
                          </Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={value}
                          sx={{
                            height: 6,
                            borderRadius: 3,
                            bgcolor: (theme) => alpha(theme.palette.primary.main, 0.1),
                            "& .MuiLinearProgress-bar": {
                              borderRadius: 3,
                              bgcolor:
                                value >= 80 ? "success.main" : value >= 60 ? "warning.main" : "error.main",
                            },
                          }}
                        />
                      </Box>
                    ))}
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Box>
      )}

      {/* Form & History Tab */}
      {tab === 1 && (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, gap: 3 }}>
          {/* Recent Form */}
          <Card sx={generalGlassCardSx}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Recent Form
              </Typography>
              {player.form && player.form.length > 0 ? (
                <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap" }}>
                  {player.form.map((f, i) => {
                    const rating = f ?? 0;
                    const color = rating >= 7.5 ? "#10b981" : rating >= 6.5 ? "#fbbf24" : "#f43f5e";
                    return (
                      <Box
                        key={i}
                        sx={{
                          width: 48,
                          height: 48,
                          borderRadius: "50%",
                          border: `2px solid ${color}`,
                          boxShadow: `0 0 10px ${alpha(color, 0.3)}`,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          bgcolor: alpha(color, 0.1),
                          color: "#FFFFFF",
                          fontWeight: 700,
                          fontSize: "0.875rem",
                          transition: "all 0.2s ease-in-out",
                          "&:hover": {
                            transform: "scale(1.1)",
                            boxShadow: `0 0 15px ${alpha(color, 0.5)}`,
                          }
                        }}
                      >
                        {rating.toFixed(1)}
                      </Box>
                    );
                  })}
                </Box>
              ) : (
                <Typography color="text.secondary">No form data available</Typography>
              )}
            </CardContent>
          </Card>

          {/* Injury History */}
          <Card sx={generalGlassCardSx}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Injury History
              </Typography>
              {player.injury_history && player.injury_history.length > 0 ? (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {player.injury_history.map((injury: any, idx: number) => (
                    <Box
                      key={idx}
                      sx={{
                        p: 1.5,
                        borderRadius: 2,
                        bgcolor: alpha("#ef4444", 0.1),
                        border: "1px solid",
                        borderColor: alpha("#ef4444", 0.3),
                      }}
                    >
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {injury.type}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Recovery: {injury.recovery_time} days • {injury.date}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              ) : (
                <Typography color="text.secondary">No injury history</Typography>
              )}
            </CardContent>
          </Card>

          {/* Development History */}
          {player.stats?.development && player.stats.development.length > 0 && (
            <Card sx={{ ...generalGlassCardSx, gridColumn: { lg: "1 / -1" } }}>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Development History
                </Typography>
                <Box sx={{ height: 250 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={player.stats.development.slice(-10)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="attribute" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                      <YAxis tick={{ fill: "#9ca3af" }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#1e293b",
                          border: "none",
                          borderRadius: 8,
                        }}
                      />
                      <Bar dataKey="from" fill="#ef4444" name="From" />
                      <Bar dataKey="to" fill="#10b981" name="To" />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          )}
        </Box>
      )}
    </Box>
  );
};

export default PlayerDetail;
