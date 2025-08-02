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
  Paper,
  CircularProgress,
  Alert,
} from "@mui/material";
import { Timeline, TimelineItem, TimelineSeparator, TimelineConnector, TimelineContent, TimelineDot } from "@mui/lab";
import { useSimulationStore } from "../store/simulationStore";
import type { TeamDetail, Player } from "../services/api";

const TeamDetails: React.FC = () => {
  const { teamName } = useParams<{ teamName: string }>();
  const { selectedSeason, currentReport, isLoading, error, fetchAvailableSeasons } = useSimulationStore();

  const [tab, setTab] = useState(0);
  const [team, setTeam] = useState<TeamDetail | null>(null);
  const [localLoading, setLocalLoading] = useState(true);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedSeason) {
      fetchAvailableSeasons(); // Ensure a season is selected
    }
  }, [selectedSeason, fetchAvailableSeasons]);

  useEffect(() => {
    if (currentReport && teamName) {
      setLocalLoading(true);
      setLocalError(null);
      const foundTeam = currentReport.all_teams_details.find(t => t.name === teamName);
      if (foundTeam) {
        setTeam(foundTeam);
      } else {
        setLocalError(`Team "${teamName}" not found for season ${selectedSeason}.`);
      }
      setLocalLoading(false);
    } else if (!currentReport && !isLoading && !error && selectedSeason) {
      // If no report but a season is selected, it means report is still loading or failed
      setLocalLoading(true);
    }
  }, [currentReport, teamName, selectedSeason, isLoading, error]);

  if (isLoading || localLoading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Loading team details for {teamName || "selected team"}...</Typography>
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

  // Roster
  const roster = team.players.map((player: Player) => ({
    name: player.name,
    position: player.position,
    avatar: "", // Placeholder for avatar
  }));

  // Finances
  const financials = team.financial_summary || { annual_revenue: 0, annual_expenses: 0, financial_health: "Unknown" };
  const finances = [
    { item: "Budget", value: `£${team.budget.toLocaleString()}` },
    { item: "Squad Strength", value: team.squad_strength.toFixed(1) },
    { item: "Annual Revenue", value: `£${financials.annual_revenue.toLocaleString()}` },
    { item: "Annual Expenses", value: `£${financials.annual_expenses.toLocaleString()}` },
    { item: "Financial Health", value: financials.financial_health },
  ];

  // Fixtures (using team_season_stats for basic match info)
  const teamSeasonStats = team.team_season_stats || {};
  const fixtures = [
    { date: "Matches Played", value: teamSeasonStats.played || 0 },
    { date: "Wins", value: teamSeasonStats.won || 0 },
    { date: "Draws", value: teamSeasonStats.drawn || 0 },
    { date: "Losses", value: teamSeasonStats.lost || 0 },
    { date: "Goals For", value: teamSeasonStats.gf || 0 },
    { date: "Goals Against", value: teamSeasonStats.ga || 0 },
  ];

  // Staff (placeholder, as not all staff roles are present in API)
  const staff = [
    { name: team.manager_name || "Unknown Manager", role: "Head Coach", avatar: "", type: "manager" },
    { name: "Physio", role: "Physio", avatar: "", type: "other" }, // Placeholder, no dedicated page yet
    // Add other staff roles if available from backend
  ];

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>Team Details: {team.name}</Typography>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Roster" />
        <Tab label="Finances" />
        <Tab label="Season Stats" />
        <Tab label="Staff" />
      </Tabs>

      {tab === 0 && (
        <TableContainer component={Paper} sx={{ mb: 2 }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Avatar</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Position</TableCell>
                <TableCell align="right">Overall</TableCell>
                <TableCell align="right">Value</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {roster.map((player, idx) => (
                <TableRow key={idx}>
                  <TableCell>
                    <Avatar>{player.name[0]}</Avatar>
                  </TableCell>
                  <TableCell>
                    <Link to={`/player-profiles/${player.name}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                      {player.name}
                    </Link>
                  </TableCell>
                  <TableCell>{player.position}</TableCell>
                  <TableCell align="right">
                    {(() => {
                      const fullPlayer = team.players.find(p => p.name === player.name);
                      if (!fullPlayer || !fullPlayer.attributes) return "N/A";
                      const totalAttributeSum = Object.values(fullPlayer.attributes).reduce(
                        (sum, category: Record<string, number>) => sum + Object.values(category).reduce((catSum, val) => catSum + val, 0),
                        0
                      );
                      const totalAttributeCount = Object.values(fullPlayer.attributes).reduce(
                        (count, category: Record<string, number>) => count + Object.keys(category).length,
                        0
                      );
                      return totalAttributeCount > 0 ? (totalAttributeSum / totalAttributeCount).toFixed(1) : "0.0";
                    })()}
                  </TableCell>
                  <TableCell align="right">
                    {(() => {
                      const fullPlayer = team.players.find(p => p.name === player.name);
                      return fullPlayer ? `£${(fullPlayer.market_value / 1000000).toFixed(1)}M` : "N/A";
                    })()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {tab === 1 && (
        <TableContainer component={Paper} sx={{ mb: 2 }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Item</TableCell>
                <TableCell>Value</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {finances.map((row, idx) => (
                <TableRow key={idx}>
                  <TableCell>{row.item}</TableCell>
                  <TableCell>{row.value}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {tab === 2 && (
        <TableContainer component={Paper} sx={{ mb: 2 }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Statistic</TableCell>
                <TableCell>Value</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {fixtures.map((stat, idx) => (
                <TableRow key={idx}>
                  <TableCell>{stat.date}</TableCell>
                  <TableCell>{stat.value}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {tab === 3 && (
        <TableContainer component={Paper} sx={{ mb: 2 }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Avatar</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Role</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {staff.map((member, idx) => (
                <TableRow key={idx}>
                  <TableCell>
                    <Avatar>{member.name[0]}</Avatar>
                  </TableCell>
                  <TableCell>
                    {member.type === "manager" ? (
                      <Link to={`/manager-profiles/${member.name}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                        {member.name}
                      </Link>
                    ) : (
                      member.name
                    )}
                  </TableCell>
                  <TableCell>{member.role}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default TeamDetails;
