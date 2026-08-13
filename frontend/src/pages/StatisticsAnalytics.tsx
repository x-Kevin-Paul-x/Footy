import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Typography,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Chip,
  Avatar,
  alpha,
  ToggleButton,
  ToggleButtonGroup,
} from "@mui/material";
import { useSimulationStore } from "../store/simulationStore";
import type { Player } from "../services/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

// Icons
import SportsSoccerIcon from "@mui/icons-material/SportsSoccer";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import GroupsIcon from "@mui/icons-material/Groups";

const glassCardSx = {
  borderRadius: "20px !important",
  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important",
  "&:hover": {
    borderColor: "#6366f1 !important",
    boxShadow: "0 12px 32px 0 rgba(99, 102, 241, 0.15) !important",
  }
};

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4", "#ec4899", "#84cc16"];


const StatisticsAnalytics: React.FC = () => {
  const { selectedSeason, currentReport, isLoading, error, fetchAvailableSeasons } = useSimulationStore();
  const [filter, setFilter] = useState<"goals" | "assists" | "value">("goals");

  useEffect(() => {
    if (!selectedSeason) {
      fetchAvailableSeasons();
    }
  }, [selectedSeason, fetchAvailableSeasons]);

  if (isLoading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress size={48} />
        <Typography mt={2} color="text.secondary">Loading statistics...</Typography>
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

  if (!currentReport) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <Typography variant="h6">No data available.</Typography>
        <Typography variant="body2" color="text.secondary">
          Please run a simulation first.
        </Typography>
      </Box>
    );
  }

  // Extract all players
  const allPlayers: Player[] = [];
  currentReport.all_teams_details.forEach((team) => {
    allPlayers.push(...team.players);
  });

  // Top Scorers
  const topScorers = [...allPlayers]
    .sort((a, b) => (b.stats?.goals || 0) - (a.stats?.goals || 0))
    .slice(0, 10);

  // Top Assists
  const topAssists = [...allPlayers]
    .sort((a, b) => (b.stats?.assists || 0) - (a.stats?.assists || 0))
    .slice(0, 10);

  // Most Valuable
  const mostValuable = [...allPlayers]
    .sort((a, b) => b.market_value - a.market_value)
    .slice(0, 10);

  // Team stats
  const teamStats = currentReport.all_teams_details.map((team) => ({
    name: team.name.length > 12 ? team.name.slice(0, 12) + "..." : team.name,
    fullName: team.name,
    goals: team.team_season_stats?.gf || 0,
    conceded: team.team_season_stats?.ga || 0,
    budget: team.budget / 1e6,
  }));

  // Position distribution
  const positionCounts: Record<string, number> = {};
  allPlayers.forEach((p) => {
    const pos = p.position.charAt(0);
    positionCounts[pos] = (positionCounts[pos] || 0) + 1;
  });
  const positionData = Object.entries(positionCounts).map(([pos, count]) => ({
    name: pos === "G" ? "GK" : pos === "D" ? "DEF" : pos === "M" ? "MID" : "FWD",
    value: count,
  }));

  // Age distribution
  const ageGroups: Record<string, number> = { "16-20": 0, "21-25": 0, "26-30": 0, "31-35": 0, "36+": 0 };
  allPlayers.forEach((p) => {
    if (p.age <= 20) ageGroups["16-20"]++;
    else if (p.age <= 25) ageGroups["21-25"]++;
    else if (p.age <= 30) ageGroups["26-30"]++;
    else if (p.age <= 35) ageGroups["31-35"]++;
    else ageGroups["36+"]++;
  });
  const ageData = Object.entries(ageGroups).map(([range, count]) => ({ name: range, value: count }));

  // League stats summary
  const totalGoals = currentReport.season_stats?.total_goals || 0;
  const totalMatches = currentReport.season_stats?.total_matches || 0;
  const avgGoals = currentReport.season_stats?.average_goals_per_match || 0;

  const getFilteredData = () => {
    switch (filter) {
      case "goals":
        return topScorers;
      case "assists":
        return topAssists;
      case "value":
        return mostValuable;
      default:
        return topScorers;
    }
  };

  const getBarValue = (player: Player) => {
    switch (filter) {
      case "goals":
        return player.stats?.goals || 0;
      case "assists":
        return player.stats?.assists || 0;
      case "value":
        return player.market_value / 1e6;
      default:
        return 0;
    }
  };

  return (
    <Box sx={{ p: { xs: 1, md: 0 } }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Statistics & Analytics
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Season {selectedSeason} comprehensive data analysis
        </Typography>
      </Box>

      {/* Summary Cards */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" },
          gap: 3,
          mb: 4,
        }}
      >
        <Card sx={glassCardSx}>
          <CardContent sx={{ textAlign: "center", p: 3 }}>
            <Avatar sx={{ width: 48, height: 48, bgcolor: alpha("#3b82f6", 0.15), color: "#3b82f6", mx: "auto", mb: 1 }}>
              <SportsSoccerIcon />
            </Avatar>
            <Typography variant="h4" sx={{ fontWeight: 700 }}>
              {totalGoals}
            </Typography>
            <Typography variant="body2" color="text.secondary">Total Goals</Typography>
          </CardContent>
        </Card>
        <Card sx={glassCardSx}>
          <CardContent sx={{ textAlign: "center", p: 3 }}>
            <Avatar sx={{ width: 48, height: 48, bgcolor: alpha("#10b981", 0.15), color: "#10b981", mx: "auto", mb: 1 }}>
              <TrendingUpIcon />
            </Avatar>
            <Typography variant="h4" sx={{ fontWeight: 700 }}>
              {(avgGoals ?? 0).toFixed(2)}
            </Typography>
            <Typography variant="body2" color="text.secondary">Goals/Match</Typography>
          </CardContent>
        </Card>
        <Card sx={glassCardSx}>
          <CardContent sx={{ textAlign: "center", p: 3 }}>
            <Avatar sx={{ width: 48, height: 48, bgcolor: alpha("#f59e0b", 0.15), color: "#f59e0b", mx: "auto", mb: 1 }}>
              <EmojiEventsIcon />
            </Avatar>
            <Typography variant="h4" sx={{ fontWeight: 700 }}>
              {totalMatches}
            </Typography>
            <Typography variant="body2" color="text.secondary">Matches Played</Typography>
          </CardContent>
        </Card>
        <Card sx={glassCardSx}>
          <CardContent sx={{ textAlign: "center", p: 3 }}>
            <Avatar sx={{ width: 48, height: 48, bgcolor: alpha("#8b5cf6", 0.15), color: "#8b5cf6", mx: "auto", mb: 1 }}>
              <GroupsIcon />
            </Avatar>
            <Typography variant="h4" sx={{ fontWeight: 700 }}>
              {allPlayers.length}
            </Typography>
            <Typography variant="body2" color="text.secondary">Total Players</Typography>
          </CardContent>
        </Card>
      </Box>

      {/* Main Grid */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "2fr 1fr" },
          gap: 3,
          mb: 3,
        }}
      >
        {/* Top Players Chart */}
        <Card sx={glassCardSx}>
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Top 10 Players
              </Typography>
              <ToggleButtonGroup
                value={filter}
                exclusive
                onChange={(_, v) => v && setFilter(v)}
                size="small"
              >
                <ToggleButton value="goals">Goals</ToggleButton>
                <ToggleButton value="assists">Assists</ToggleButton>
                <ToggleButton value="value">Value</ToggleButton>
              </ToggleButtonGroup>
            </Box>
            <Box sx={{ height: 400 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                <BarChart
                  data={getFilteredData().map((p) => ({
                    name: p.name.split(" ").pop(),
                    fullName: p.name,
                    value: getBarValue(p),
                    team: p.team,
                  }))}
                  layout="vertical"
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" tick={{ fill: "#9ca3af" }} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fill: "#9ca3af", fontSize: 12 }}
                    width={80}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1e293b",
                      border: "none",
                      borderRadius: 8,
                    }}
                    formatter={(value) => {
                      const numericValue = typeof value === "number" ? value : Number(value ?? 0);
                      return filter === "value" ? `£${(numericValue ?? 0).toFixed(1)}M` : numericValue;
                    }}
                  />
                  <Bar
                    dataKey="value"
                    fill="#3b82f6"
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </Card>

        {/* Distribution Charts */}
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {/* Position Distribution */}
          <Card sx={glassCardSx}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Position Distribution
              </Typography>
              <Box sx={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                  <PieChart>
                    <Pie
                      data={positionData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={70}
                      label={({ name, value }) => `${name}: ${value}`}
                      labelLine={false}
                    >
                      {positionData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>

          {/* Age Distribution */}
          <Card sx={glassCardSx}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Age Distribution
              </Typography>
              <Box sx={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                  <BarChart data={ageData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 12 }} />
                    <YAxis tick={{ fill: "#9ca3af" }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1e293b",
                        border: "none",
                        borderRadius: 8,
                      }}
                    />
                    <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Box>
      </Box>

      {/* Team Comparison */}
      <Card sx={glassCardSx}>
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
            Team Goals Comparison
          </Typography>
          <Box sx={{ height: 350, overflow: "auto" }}>
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <BarChart data={teamStats.sort((a, b) => b.goals - a.goals)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#9ca3af", fontSize: 10 }}
                  interval={0}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis tick={{ fill: "#9ca3af" }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e293b",
                    border: "none",
                    borderRadius: 8,
                  }}
                  labelFormatter={(label) => {
                    const team = teamStats.find((t) => t.name === label);
                    return team?.fullName || label;
                  }}
                />
                <Legend />
                <Bar dataKey="goals" name="Goals Scored" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="conceded" name="Goals Conceded" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        </CardContent>
      </Card>

      {/* Top Players Quick List */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" },
          gap: 3,
          mt: 3,
        }}
      >
        {/* Top Scorers */}
        <Card sx={glassCardSx}>
          <CardContent>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, display: "flex", alignItems: "center", gap: 1 }}>
              <SportsSoccerIcon color="primary" /> Top Scorers
            </Typography>
            {topScorers.slice(0, 5).map((player, idx) => (
              <Box
                key={idx}
                component={Link}
                to={`/player-profiles/${player.name}`}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 2,
                  py: 1,
                  textDecoration: "none",
                  color: "inherit",
                  "&:hover": { bgcolor: "action.hover" },
                  borderRadius: 1,
                  px: 1,
                }}
              >
                <Typography sx={{ width: 20, fontWeight: 700, color: idx < 3 ? "warning.main" : "text.secondary" }}>
                  {idx + 1}
                </Typography>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography sx={{ fontWeight: 500 }} noWrap>
                    {player.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {player.team}
                  </Typography>
                </Box>
                <Chip label={player.stats?.goals || 0} size="small" color="primary" />
              </Box>
            ))}
          </CardContent>
        </Card>

        {/* Top Assists */}
        <Card sx={glassCardSx}>
          <CardContent>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, display: "flex", alignItems: "center", gap: 1 }}>
              <TrendingUpIcon color="success" /> Top Assists
            </Typography>
            {topAssists.slice(0, 5).map((player, idx) => (
              <Box
                key={idx}
                component={Link}
                to={`/player-profiles/${player.name}`}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 2,
                  py: 1,
                  textDecoration: "none",
                  color: "inherit",
                  "&:hover": { bgcolor: "action.hover" },
                  borderRadius: 1,
                  px: 1,
                }}
              >
                <Typography sx={{ width: 20, fontWeight: 700, color: idx < 3 ? "warning.main" : "text.secondary" }}>
                  {idx + 1}
                </Typography>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography sx={{ fontWeight: 500 }} noWrap>
                    {player.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {player.team}
                  </Typography>
                </Box>
                <Chip label={player.stats?.assists || 0} size="small" color="success" />
              </Box>
            ))}
          </CardContent>
        </Card>

        {/* Most Valuable */}
        <Card sx={glassCardSx}>
          <CardContent>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, display: "flex", alignItems: "center", gap: 1 }}>
              <EmojiEventsIcon color="warning" /> Most Valuable
            </Typography>
            {mostValuable.slice(0, 5).map((player, idx) => (
              <Box
                key={idx}
                component={Link}
                to={`/player-profiles/${player.name}`}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 2,
                  py: 1,
                  textDecoration: "none",
                  color: "inherit",
                  "&:hover": { bgcolor: "action.hover" },
                  borderRadius: 1,
                  px: 1,
                }}
              >
                <Typography sx={{ width: 20, fontWeight: 700, color: idx < 3 ? "warning.main" : "text.secondary" }}>
                  {idx + 1}
                </Typography>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography sx={{ fontWeight: 500 }} noWrap>
                    {player.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {player.team}
                  </Typography>
                </Box>
                <Chip
                  label={`£${((player?.market_value ?? 0) / 1e6).toFixed(0)}M`}
                  size="small"
                  sx={{ bgcolor: "warning.main", color: "warning.contrastText" }}
                />
              </Box>
            ))}
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
};

export default StatisticsAnalytics;
