import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Typography,
  Box,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Avatar,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Chip,
  alpha,
  Skeleton,
} from "@mui/material";
import { useSimulationStore } from "../store/simulationStore";
import { getTeamHistory, type TeamHistoryEntry, type TeamDetail, type Player } from "../services/api";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";

// Icons
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";

const glassCardSx = {
  borderRadius: "16px",
  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important",
  "&:hover": {
    borderColor: "rgba(99, 102, 241, 0.25) !important",
    boxShadow: "0 12px 40px 0 rgba(99, 102, 241, 0.12) !important",
  }
};

const TeamDetails: React.FC = () => {
  const { teamName } = useParams<{ teamName: string }>();
  const { selectedSeason, currentReport, isLoading, error, fetchAvailableSeasons } = useSimulationStore();

  const [tab, setTab] = useState(0);
  const [team, setTeam] = useState<TeamDetail | null>(null);
  const [localLoading, setLocalLoading] = useState(true);
  const [localError, setLocalError] = useState<string | null>(null);
  const [historyData, setHistoryData] = useState<TeamHistoryEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    if (!selectedSeason) {
      fetchAvailableSeasons();
    }
  }, [selectedSeason, fetchAvailableSeasons]);

  useEffect(() => {
    if (currentReport && teamName) {
      setLocalLoading(true);
      setLocalError(null);
      const foundTeam = currentReport.all_teams_details.find((t) => t.name === teamName);
      if (foundTeam) {
        setTeam(foundTeam);
      } else {
        setLocalError(`Team "${teamName}" not found for season ${selectedSeason}.`);
      }
      setLocalLoading(false);
    } else if (!currentReport && !isLoading && !error && selectedSeason) {
      setLocalLoading(true);
    }
  }, [currentReport, teamName, selectedSeason, isLoading, error]);

  // Fetch history data when History tab is selected
  useEffect(() => {
    if (tab === 4 && teamName && historyData.length === 0) {
      setHistoryLoading(true);
      getTeamHistory(teamName)
        .then((response) => {
          setHistoryData(response.history);
        })
        .catch((e) => {
          console.error("Failed to fetch team history:", e);
        })
        .finally(() => {
          setHistoryLoading(false);
        });
    }
  }, [tab, teamName, historyData.length]);

  if (isLoading || localLoading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }} color="text.secondary">
          Loading team details for {teamName || "selected team"}...
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

  if (!team) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <Typography variant="h6">No team data available.</Typography>
        <Typography variant="body2">Please select a season or ensure the team name is correct.</Typography>
      </Box>
    );
  }

  // Roster processing
  const roster = team.players
    .map((player: Player) => ({
      name: player.name,
      position: player.age <= 18 ? `${player.position} (Youth)` : player.position,
      avatar: "",
      age: player.age,
      overall: player.attributes
        ? (() => {
          const totalAttributeSum = Object.values(player.attributes).reduce(
            (sum, category: Record<string, number>) =>
              sum + Object.values(category).reduce((catSum, val) => catSum + val, 0),
            0
          );
          const totalAttributeCount = Object.values(player.attributes).reduce(
            (count, category: Record<string, number>) => count + Object.keys(category).length,
            0
          );
          return totalAttributeCount > 0 ? totalAttributeSum / totalAttributeCount : 0;
        })()
        : 0,
      market_value: player.market_value,
    }))
    .sort((a, b) => {
      const posOrder = (pos: string) => (pos.startsWith("GK") ? 0 : 1);
      if (posOrder(a.position) !== posOrder(b.position)) return posOrder(a.position) - posOrder(b.position);
      if (a.position !== b.position) return a.position.localeCompare(b.position);
      return a.age - b.age;
    });

  // Finances
  const financials = team.financial_summary || { annual_revenue: 0, annual_expenses: 0, financial_health: "Unknown" };
  const finances = [
    { item: "Budget", value: `£${(team?.budget ?? 0).toLocaleString()}` },
    { item: "Squad Strength", value: (team?.squad_strength ?? 0).toFixed(1) },
    { item: "Annual Revenue", value: `£${(financials?.annual_revenue ?? 0).toLocaleString()}` },
    { item: "Annual Expenses", value: `£${(financials?.annual_expenses ?? 0).toLocaleString()}` },
    { item: "Financial Health", value: financials.financial_health },
  ];

  // Season Stats
  const teamSeasonStats = team.team_season_stats || {};
  const fixtures = [
    { label: "Matches Played", value: teamSeasonStats.played || 0 },
    { label: "Wins", value: teamSeasonStats.won || 0 },
    { label: "Draws", value: teamSeasonStats.drawn || 0 },
    { label: "Losses", value: teamSeasonStats.lost || 0 },
    { label: "Goals For", value: teamSeasonStats.gf || 0 },
    { label: "Goals Against", value: teamSeasonStats.ga || 0 },
  ];

  // Staff
  const staff = [
    { name: team.manager_name || "Unknown Manager", role: "Head Coach", type: "manager" },
    { name: "Physio", role: "Physio", type: "other" },
  ];

  // Custom tooltip for chart
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <Box
          sx={{
            bgcolor: "background.paper",
            p: 2,
            borderRadius: 2,
            boxShadow: 3,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            Season {label}
          </Typography>
          <Typography variant="body2">
            Position: <strong>{data.position}</strong>
          </Typography>
          <Typography variant="body2">
            Points: <strong>{data.points}</strong>
          </Typography>
          <Typography variant="body2" color="text.secondary">
            W{data.won} D{data.drawn} L{data.lost}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            GF {data.gf} • GA {data.ga} • GD {data.gd > 0 ? `+${data.gd}` : data.gd}
          </Typography>
        </Box>
      );
    }
    return null;
  };

  return (
    <Box sx={{ p: { xs: 1, md: 0 } }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          {team.name}
        </Typography>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <Chip label={`Manager: ${team.manager_name}`} size="small" variant="outlined" />
          <Chip label={`Formation: ${team.manager_formation}`} size="small" variant="outlined" />
          <Chip
            label={financials.financial_health}
            size="small"
            color={financials.financial_health === "Good" ? "success" : "warning"}
          />
        </Box>
      </Box>

      {/* Tabs */}
      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{
          mb: 3,
          "& .MuiTab-root": { fontWeight: 600 },
        }}
        variant="scrollable"
        scrollButtons="auto"
      >
        <Tab label="Roster" />
        <Tab label="Finances" />
        <Tab label="Season Stats" />
        <Tab label="Staff" />
        <Tab label="History" />
      </Tabs>

      {/* Roster Tab */}
      {tab === 0 && (
        <Card sx={glassCardSx}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell></TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Position</TableCell>
                  <TableCell align="right">Overall</TableCell>
                  <TableCell align="right">Value</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {roster.map((player, idx) => (
                  <TableRow key={idx} hover>
                    <TableCell>
                      <Avatar sx={{ width: 32, height: 32, fontSize: 14 }}>{player.name[0]}</Avatar>
                    </TableCell>
                    <TableCell>
                      <Link
                        to={`/player-profiles/${player.name}`}
                        style={{ textDecoration: "none", color: "inherit", fontWeight: 500 }}
                      >
                        {player.name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Chip label={player.position} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell align="right">
                      <Chip
                        label={player.overall ? (player.overall ?? 0).toFixed(1) : "N/A"}
                        size="small"
                        color={player.overall >= 70 ? "success" : player.overall >= 50 ? "warning" : "default"}
                      />
                    </TableCell>
                    <TableCell align="right">
                      {player.market_value ? `£${((player.market_value ?? 0) / 1000000).toFixed(1)}M` : "N/A"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      )}

      {/* Finances Tab */}
      {tab === 1 && (
        <Card sx={glassCardSx}>
          <CardContent>
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" }, gap: 3 }}>
              {finances.map((row, idx) => (
                <Box
                  key={idx}
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    bgcolor: "action.hover",
                    textAlign: "center",
                  }}
                >
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                    {row.item}
                  </Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    {row.value}
                  </Typography>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Season Stats Tab */}
      {tab === 2 && (
        <Card sx={glassCardSx}>
          <CardContent>
            <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 2 }}>
              {fixtures.map((stat, idx) => (
                <Box
                  key={idx}
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    bgcolor: "action.hover",
                    textAlign: "center",
                  }}
                >
                  <Typography variant="h4" sx={{ fontWeight: 700, color: "primary.main" }}>
                    {stat.value}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {stat.label}
                  </Typography>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Staff Tab */}
      {tab === 3 && (
        <Card sx={glassCardSx}>
          <CardContent>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {staff.map((member, idx) => (
                <Box
                  key={idx}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    p: 2,
                    borderRadius: 2,
                    bgcolor: "action.hover",
                  }}
                >
                  <Avatar sx={{ width: 48, height: 48 }}>{member.name[0]}</Avatar>
                  <Box sx={{ flex: 1 }}>
                    {member.type === "manager" ? (
                      <Link
                        to={`/manager-profiles/${member.name}`}
                        style={{ textDecoration: "none", color: "inherit" }}
                      >
                        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                          {member.name}
                        </Typography>
                      </Link>
                    ) : (
                      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                        {member.name}
                      </Typography>
                    )}
                    <Typography variant="body2" color="text.secondary">
                      {member.role}
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* History Tab */}
      {tab === 4 && (
        <Card sx={glassCardSx}>
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center", mb: 3 }}>
              <EmojiEventsIcon sx={{ color: "warning.main", mr: 1 }} />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Historical Performance
              </Typography>
            </Box>

            {historyLoading ? (
              <Box>
                <Skeleton variant="rectangular" height={300} sx={{ borderRadius: 2 }} />
              </Box>
            ) : historyData.length > 0 ? (
              <>
                {/* Position Chart */}
                <Box sx={{ height: 300, mb: 4 }}>
                  <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
                    League Position Over Time (lower is better)
                  </Typography>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={historyData}>
                      <defs>
                        <linearGradient id="positionGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#818cf8" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#818cf8" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis
                        dataKey="season"
                        stroke="#94a3b8"
                        tick={{ fill: "#94a3b8", fontSize: 12 }}
                      />
                      <YAxis
                        reversed
                        domain={[1, 20]}
                        stroke="#94a3b8"
                        tick={{ fill: "#94a3b8", fontSize: 12 }}
                        label={{
                          value: "Position",
                          angle: -90,
                          position: "insideLeft",
                          fill: "#94a3b8",
                        }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Area
                        type="monotone"
                        dataKey="position"
                        stroke="#818cf8"
                        strokeWidth={3}
                        fill="url(#positionGradient)"
                        dot={{ fill: "#818cf8", strokeWidth: 2, r: 5 }}
                        activeDot={{ r: 8, fill: "#a5b4fc" }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </Box>

                {/* Season Summary Cards */}
                <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
                  Season by Season
                </Typography>
                <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(5, 1fr)" }, gap: 2 }}>
                  {historyData.slice(-5).reverse().map((season, idx) => {
                    const prevSeason = historyData.find((h) => h.season === season.season - 1);
                    const posChange = prevSeason ? prevSeason.position - season.position : 0;

                    return (
                      <Box
                        key={season.season}
                        sx={{
                          p: 2,
                          borderRadius: 2,
                          bgcolor: idx === 0 ? alpha("#3b82f6", 0.15) : "action.hover",
                          border: idx === 0 ? "2px solid" : "none",
                          borderColor: "primary.main",
                        }}
                      >
                        <Typography variant="caption" color="text.secondary">
                          Season {season.season}
                        </Typography>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                          <Typography variant="h5" sx={{ fontWeight: 700 }}>
                            {season.position}
                            {season.position === 1 && <sup>st</sup>}
                            {season.position === 2 && <sup>nd</sup>}
                            {season.position === 3 && <sup>rd</sup>}
                            {season.position > 3 && <sup>th</sup>}
                          </Typography>
                          {posChange !== 0 && (
                            <Chip
                              size="small"
                              icon={posChange > 0 ? <TrendingUpIcon /> : <TrendingDownIcon />}
                              label={posChange > 0 ? `+${posChange}` : posChange}
                              color={posChange > 0 ? "success" : "error"}
                              sx={{ height: 22 }}
                            />
                          )}
                        </Box>
                        <Typography variant="body2" color="text.secondary">
                          {season.points} pts
                        </Typography>
                      </Box>
                    );
                  })}
                </Box>
              </>
            ) : (
              <Box sx={{ textAlign: "center", py: 4 }}>
                <Typography color="text.secondary">
                  No historical data available. Run multiple seasons to see trends.
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default TeamDetails;
