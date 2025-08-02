import React, { useEffect, useState } from "react";
import { Typography, Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, List, ListItem, ListItemText, CircularProgress, Alert, ListItemButton } from "@mui/material";
import { Link } from "react-router-dom";
import { getAvailableSeasons, getSeasonReportData } from "../services/api";
import type { SeasonReport } from "../services/api";

const LeagueOverview: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<SeasonReport | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const seasons = await getAvailableSeasons();
        const latestSeason = Math.max(...seasons);
        const reportData = await getSeasonReportData(latestSeason);
        setReport(reportData);
      } catch (err: any) {
        setError("Failed to fetch league overview data.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
        <Typography>Loading league overview...</Typography>
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

  if (!report) return null;

  // Standings: use report.table
  const standings = report.table.map(([team, stats]) => ({
    team,
    points: stats.points ?? 0,
  }));

  // Teams: use all_teams_details
  const teams = report.all_teams_details.map((t) => t.name);

  // Financial data: use budget and profit if available
  const financialData = report.all_teams_details.slice(0, 5).map((team) => ({
    label: team.name,
    value: team.budget,
  }));

  return (
    <Box sx={{ p: { xs: 1, md: 3 } }}>
      <Typography variant="h4" gutterBottom tabIndex={0}>League Overview</Typography>

      <Typography variant="h5" gutterBottom>Standings</Typography>
      <TableContainer component={Paper} sx={{ mb: 3 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Team</TableCell>
              <TableCell align="right">Points</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {standings.map((row) => (
              <TableRow key={row.team}>
                <TableCell>
                  <Link to={`/team-details/${row.team}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                    {row.team}
                  </Link>
                </TableCell>
                <TableCell align="right">{row.points}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="h5" gutterBottom>Financial Overview</Typography>
      <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
        <Paper sx={{ p: 2, flex: 1, textAlign: "center" }}>
          <Typography variant="body1">[BarChart Placeholder]</Typography>
          {financialData.map((item) => (
            <Typography key={item.label}>
              {item.label}: {item.value}M
            </Typography>
          ))}
        </Paper>
      </Box>

    </Box>
  );
};

export default LeagueOverview;
