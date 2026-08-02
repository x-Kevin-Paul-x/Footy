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
  Tabs,
  Tab,
  Chip,
  alpha,
  LinearProgress,
} from "@mui/material";
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
  Tooltip,
  CartesianGrid,
} from "recharts";
import { useSimulationStore } from "../store/simulationStore";
import { getAllSeasonsOverview, type AllSeasonsOverviewResponse } from "../services/api";

// Icons
import PersonIcon from "@mui/icons-material/Person";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import SportsSoccerIcon from "@mui/icons-material/SportsSoccer";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import GroupsIcon from "@mui/icons-material/Groups";

// Glassmorphism card style
const glassCardSx = {
  borderRadius: "16px",
  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important",
};

interface ManagerData {
  name: string;
  team: string;
  formation: string;
  experience: number;
  teamStats: {
    played: number;
    won: number;
    drawn: number;
    lost: number;
    gf: number;
    ga: number;
    points: number;
    position: number;
  };
  squadStats: {
    totalPlayers: number;
    avgAge: number;
    avgRating: number;
    totalValue: number;
  };
  careerHistory: {
    season: number;
    team: string;
    position: number;
    points: number;
    won: number;
    drawn: number;
    lost: number;
  }[];
  titlesWon: number;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`manager-tabpanel-${index}`}
      aria-labelledby={`manager-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const ManagerDetail: React.FC = () => {
  const { managerName } = useParams<{ managerName: string }>();
  const { availableSeasons, currentReport, fetchAvailableSeasons, selectSeason } = useSimulationStore();

  const [manager, setManager] = useState<ManagerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [allSeasonsData, setAllSeasonsData] = useState<AllSeasonsOverviewResponse | null>(null);

  useEffect(() => {
    fetchAvailableSeasons();
    getAllSeasonsOverview().then(setAllSeasonsData).catch(console.error);
  }, [fetchAvailableSeasons]);

  useEffect(() => {
    // Auto-select the latest season
    if (availableSeasons.length > 0 && !currentReport) {
      selectSeason(Math.max(...availableSeasons));
    }
  }, [availableSeasons, currentReport, selectSeason]);

  useEffect(() => {
    if (currentReport && managerName) {
      setLoading(true);
      setError(null);

      // Find the team managed by this manager
      const team = currentReport.all_teams_details.find(
        (t) => t.manager_name === managerName
      );

      if (team) {
        // Find team's position in table
        const tableEntry = currentReport.table.find(([teamName]) => teamName === team.name);
        const position = tableEntry
          ? currentReport.table.indexOf(tableEntry) + 1
          : 20;
        const stats = tableEntry ? tableEntry[1] : {};

        // Calculate squad stats
        const players = team.players || [];
        const totalValue = players.reduce((sum, p) => sum + (p.market_value || 0), 0);
        const avgAge = players.length > 0
          ? players.reduce((sum, p) => sum + p.age, 0) / players.length
          : 0;
        const avgRating = team.squad_strength || 0;

        // Build career history from all seasons
        const careerHistory: ManagerData["careerHistory"] = [];
        let titlesWon = 0;

        if (allSeasonsData) {
          for (const seasonData of allSeasonsData.seasons) {
            // Check if this manager won the title
            if (seasonData.champions === team.name) {
              titlesWon++;
            }

            // Get team position for this season from trends
            const teamTrends = allSeasonsData.team_position_trends[team.name];
            const seasonTrend = teamTrends?.find(t => t.season === seasonData.season_year);

            if (seasonTrend) {
              careerHistory.push({
                season: seasonData.season_year,
                team: team.name,
                position: seasonTrend.position,
                points: seasonTrend.points,
                won: 0, // Not available in trends
                drawn: 0,
                lost: 0,
              });
            }
          }
        }

        setManager({
          name: managerName,
          team: team.name,
          formation: team.manager_formation || "4-4-2",
          experience: Math.floor(Math.random() * 15) + 5, // Simulated
          teamStats: {
            played: Number(stats.played) || 0,
            won: Number(stats.won) || 0,
            drawn: Number(stats.drawn) || 0,
            lost: Number(stats.lost) || 0,
            gf: Number(stats.gf) || 0,
            ga: Number(stats.ga) || 0,
            points: Number(stats.points) || 0,
            position,
          },
          squadStats: {
            totalPlayers: players.length,
            avgAge: Math.round(avgAge * 10) / 10,
            avgRating: Math.round(avgRating * 10) / 10,
            totalValue,
          },
          careerHistory: careerHistory.sort((a, b) => b.season - a.season),
          titlesWon,
        });
        setLoading(false);
      } else {
        setError(`Manager "${managerName}" not found.`);
        setLoading(false);
      }
    }
  }, [currentReport, managerName, allSeasonsData]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  if (loading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }} color="text.secondary">
          Loading manager profile...
        </Typography>
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

  if (!manager) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <Typography variant="h6">No manager data available.</Typography>
      </Box>
    );
  }

  // Radar chart data for tactical style
  const tacticalData = [
    { aspect: "Attack", value: Math.round(((manager.teamStats?.gf ?? 0) / Math.max(manager.teamStats?.played ?? 1, 1)) * 30) },
    { aspect: "Defense", value: Math.round((1 - (manager.teamStats?.ga ?? 0) / Math.max((manager.teamStats?.played ?? 1) * 3, 1)) * 100) },
    { aspect: "Possession", value: Math.random() * 30 + 50 },
    { aspect: "Discipline", value: Math.random() * 20 + 70 },
    { aspect: "Youth Dev", value: Math.random() * 30 + 50 },
    { aspect: "Experience", value: (manager.experience ?? 0) * 6 },
  ];

  // Season performance bar chart
  const seasonPerformanceData = (manager.careerHistory || []).slice(0, 5).reverse().map(h => ({
    season: h.season?.toString() || "",
    position: h.position,
    points: h.points,
  }));

  const winRate = (manager.teamStats && manager.teamStats.played > 0)
    ? (((manager.teamStats.won ?? 0) / manager.teamStats.played) * 100).toFixed(1)
    : "0";

  return (
    <Box sx={{ p: { xs: 1, md: 0 } }}>
      {/* Header */}
      <Card sx={{ ...glassCardSx, mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 3, flexWrap: "wrap" }}>
            <Avatar
              sx={{
                width: 80,
                height: 80,
                fontSize: 32,
                bgcolor: "primary.main",
              }}
            >
              {manager.name[0]}
            </Avatar>
            <Box sx={{ flex: 1, minWidth: 200 }}>
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                {manager.name}
              </Typography>
              <Box sx={{ display: "flex", gap: 1, mt: 1, flexWrap: "wrap" }}>
                <Chip
                  icon={<GroupsIcon />}
                  label={
                    <Link
                      to={`/team-details/${manager.team}`}
                      style={{ textDecoration: "none", color: "inherit" }}
                    >
                      {manager.team}
                    </Link>
                  }
                  variant="outlined"
                />
                <Chip label={`Formation: ${manager.formation}`} variant="outlined" />
                <Chip label={`${manager.experience} years exp.`} color="primary" />
                {manager.titlesWon > 0 && (
                  <Chip
                    icon={<EmojiEventsIcon />}
                    label={`${manager.titlesWon} Title${manager.titlesWon > 1 ? "s" : ""}`}
                    color="warning"
                  />
                )}
              </Box>
            </Box>
            {/* Quick Stats */}
            <Box sx={{ display: "flex", gap: 2 }}>
              <Box sx={{ textAlign: "center", p: 1.5, bgcolor: "action.hover", borderRadius: 2 }}>
                <Typography variant="h5" sx={{ fontWeight: 700, color: "success.main" }}>
                  {winRate}%
                </Typography>
                <Typography variant="caption" color="text.secondary">Win Rate</Typography>
              </Box>
              <Box sx={{ textAlign: "center", p: 1.5, bgcolor: "action.hover", borderRadius: 2 }}>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  #{manager.teamStats.position}
                </Typography>
                <Typography variant="caption" color="text.secondary">Current Pos</Typography>
              </Box>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Card sx={{ ...glassCardSx, mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tab label="Overview" />
          <Tab label="Tactics" />
          <Tab label="Career History" />
          <Tab label="Squad" />
        </Tabs>
      </Card>

      {/* Overview Tab */}
      <TabPanel value={tabValue} index={0}>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 3 }}>
          {/* Season Record */}
          <Card sx={glassCardSx}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                <SportsSoccerIcon sx={{ color: "primary.main", mr: 1 }} />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>Current Season Record</Typography>
              </Box>
              <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 2, mb: 3 }}>
                <Box sx={{ textAlign: "center", p: 2, bgcolor: "success.dark", borderRadius: 2, color: "white" }}>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>{manager.teamStats.won}</Typography>
                  <Typography variant="body2">Wins</Typography>
                </Box>
                <Box sx={{ textAlign: "center", p: 2, bgcolor: "grey.700", borderRadius: 2, color: "white" }}>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>{manager.teamStats.drawn}</Typography>
                  <Typography variant="body2">Draws</Typography>
                </Box>
                <Box sx={{ textAlign: "center", p: 2, bgcolor: "error.dark", borderRadius: 2, color: "white" }}>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>{manager.teamStats.lost}</Typography>
                  <Typography variant="body2">Losses</Typography>
                </Box>
              </Box>
              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                <Typography variant="body2" color="text.secondary">Goals For</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>{manager.teamStats.gf}</Typography>
              </Box>
              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                <Typography variant="body2" color="text.secondary">Goals Against</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>{manager.teamStats.ga}</Typography>
              </Box>
              <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                <Typography variant="body2" color="text.secondary">Goal Difference</Typography>
                <Typography
                  variant="body2"
                  sx={{ fontWeight: 600, color: manager.teamStats.gf - manager.teamStats.ga >= 0 ? "success.main" : "error.main" }}
                >
                  {manager.teamStats.gf - manager.teamStats.ga >= 0 ? "+" : ""}
                  {manager.teamStats.gf - manager.teamStats.ga}
                </Typography>
              </Box>
            </CardContent>
          </Card>

          {/* Points Progress */}
          <Card sx={glassCardSx}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                <TrendingUpIcon sx={{ color: "warning.main", mr: 1 }} />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>Points Progress</Typography>
              </Box>
              <Box sx={{ textAlign: "center", mb: 3 }}>
                <Typography variant="h2" sx={{ fontWeight: 700, color: "primary.main" }}>
                  {manager.teamStats?.points ?? 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Points from {manager.teamStats?.played ?? 0} matches
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Points per game: {((manager.teamStats?.points ?? 0) / Math.max(manager.teamStats?.played ?? 1, 1)).toFixed(2)}
              </Typography>
              <LinearProgress
                variant="determinate"
                value={Math.min(100, ((manager.teamStats?.points ?? 0) / Math.max(1, (manager.teamStats?.played ?? 1) * 3)) * 100)}
                sx={{
                  height: 10,
                  borderRadius: 5,
                  bgcolor: "action.hover",
                  "& .MuiLinearProgress-bar": { borderRadius: 5 },
                }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                {(((manager.teamStats?.points ?? 0) / Math.max((manager.teamStats?.played ?? 1) * 3, 1)) * 100).toFixed(0)}% of maximum points
              </Typography>
            </CardContent>
          </Card>
        </Box>
      </TabPanel>

      {/* Tactics Tab */}
      <TabPanel value={tabValue} index={1}>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 3 }}>
          <Card sx={glassCardSx}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Tactical Profile</Typography>
              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={tacticalData}>
                    <PolarGrid stroke="#374151" />
                    <PolarAngleAxis dataKey="aspect" tick={{ fill: "#9ca3af", fontSize: 12 }} />
                    <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                    <Radar
                      name="Style"
                      dataKey="value"
                      stroke="#6366f1"
                      fill="#6366f1"
                      fillOpacity={0.3}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>

          <Card sx={glassCardSx}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Formation Details</Typography>
              <Box sx={{ p: 3, bgcolor: "action.hover", borderRadius: 2, textAlign: "center", mb: 3 }}>
                <Typography variant="h3" sx={{ fontWeight: 700, color: "primary.main" }}>
                  {manager.formation}
                </Typography>
                <Typography variant="body2" color="text.secondary">Preferred Formation</Typography>
              </Box>
              <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>Tactical Tendencies</Typography>
              {[
                { label: "Attacking", value: 65, color: "error.main" },
                { label: "Pressing", value: 70, color: "warning.main" },
                { label: "Possession", value: 55, color: "info.main" },
                { label: "Counter-Attack", value: 50, color: "success.main" },
              ].map(tendency => (
                <Box key={tendency.label} sx={{ mb: 1.5 }}>
                  <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                    <Typography variant="body2">{tendency.label}</Typography>
                    <Typography variant="body2">{tendency.value}%</Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={tendency.value}
                    sx={{
                      height: 6,
                      borderRadius: 3,
                      bgcolor: "action.hover",
                      "& .MuiLinearProgress-bar": { bgcolor: tendency.color, borderRadius: 3 },
                    }}
                  />
                </Box>
              ))}
            </CardContent>
          </Card>
        </Box>
      </TabPanel>

      {/* Career History Tab */}
      <TabPanel value={tabValue} index={2}>
        <Card sx={glassCardSx}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>Season Performance</Typography>
            {seasonPerformanceData.length > 0 ? (
              <Box sx={{ height: 300, mb: 4 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={seasonPerformanceData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="season" tick={{ fill: "#9ca3af", fontSize: 12 }} />
                    <YAxis tick={{ fill: "#9ca3af" }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1e293b",
                        border: "none",
                        borderRadius: 8,
                      }}
                    />
                    <Bar dataKey="points" name="Points" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            ) : (
              <Typography color="text.secondary">No career history available.</Typography>
            )}

            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>Season by Season</Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
              {manager.careerHistory.slice(0, 6).map((season, idx) => (
                <Box
                  key={season.season}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    p: 2,
                    borderRadius: 2,
                    bgcolor: idx === 0 ? alpha("#3b82f6", 0.15) : "action.hover",
                    border: idx === 0 ? "2px solid" : "none",
                    borderColor: "primary.main",
                  }}
                >
                  <Typography sx={{ width: 60, fontWeight: 700 }}>{season.season}</Typography>
                  <Typography sx={{ flex: 1 }}>{season.team}</Typography>
                  <Chip
                    label={`#${season.position}`}
                    size="small"
                    color={season.position <= 4 ? "success" : season.position <= 10 ? "primary" : "default"}
                    sx={{ mr: 1 }}
                  />
                  <Chip label={`${season.points} pts`} size="small" variant="outlined" />
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      </TabPanel>

      {/* Squad Tab */}
      <TabPanel value={tabValue} index={3}>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 3 }}>
          <Card sx={glassCardSx}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>Squad Overview</Typography>
              <Box sx={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 2 }}>
                {[
                  { label: "Total Players", value: manager.squadStats?.totalPlayers ?? 0, icon: <GroupsIcon /> },
                  { label: "Avg Age", value: `${(manager.squadStats?.avgAge ?? 0).toFixed(1)} yrs`, icon: <PersonIcon /> },
                  { label: "Avg Rating", value: (manager.squadStats?.avgRating ?? 0).toFixed(1), icon: <TrendingUpIcon /> },
                  { label: "Total Value", value: `£${((manager.squadStats?.totalValue ?? 0) / 1e6).toFixed(0)}M`, icon: <SportsSoccerIcon /> },
                ].map((stat) => (
                  <Box
                    key={stat.label}
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      bgcolor: "action.hover",
                      textAlign: "center",
                    }}
                  >
                    <Box sx={{ color: "primary.main", mb: 1 }}>{stat.icon}</Box>
                    <Typography variant="h5" sx={{ fontWeight: 700 }}>{stat.value}</Typography>
                    <Typography variant="caption" color="text.secondary">{stat.label}</Typography>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>

          <Card sx={glassCardSx}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>Squad Management</Typography>
              <Link
                to={`/team-details/${manager.team}`}
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <Box
                  sx={{
                    p: 3,
                    borderRadius: 2,
                    bgcolor: "primary.main",
                    color: "primary.contrastText",
                    textAlign: "center",
                    transition: "transform 0.2s",
                    "&:hover": { transform: "scale(1.02)" },
                  }}
                >
                  <GroupsIcon sx={{ fontSize: 48, mb: 1 }} />
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>View Full Squad</Typography>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>
                    See detailed roster and player stats
                  </Typography>
                </Box>
              </Link>
            </CardContent>
          </Card>
        </Box>
      </TabPanel>
    </Box>
  );
};

export default ManagerDetail;
