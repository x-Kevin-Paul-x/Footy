import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, Typography, Box, CircularProgress, Alert } from "@mui/material";
import { useSimulationStore } from "../store/simulationStore";
import type { SeasonReport } from "../services/api";

const Dashboard: React.FC = () => {
  const { selectedSeason, currentReport, isLoading, error, fetchAvailableSeasons } = useSimulationStore();
  const [localLoading, setLocalLoading] = useState(true);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedSeason) {
      fetchAvailableSeasons();
    }
  }, [selectedSeason, fetchAvailableSeasons]);

  useEffect(() => {
    if (currentReport) {
      setLocalLoading(false);
      setLocalError(null);
    } else if (!currentReport && !isLoading && !error && selectedSeason) {
      setLocalLoading(true);
    }
  }, [currentReport, isLoading, error, selectedSeason]);

  if (isLoading || localLoading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
        <Typography mt={2}>Loading dashboard...</Typography>
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

  if (!currentReport) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <Typography variant="h6">No dashboard data available.</Typography>
        <Typography variant="body2">Please select a season or run a simulation.</Typography>
      </Box>
    );
  }

  const summaryData = [
    { title: "Total Teams", value: currentReport.table.length },
    { title: "Matches Played", value: currentReport.season_stats.total_matches },
    { title: "Goals Scored", value: currentReport.season_stats.total_goals },
    { title: "Active Players", value: currentReport.all_teams_details.reduce((acc, t) => acc + t.players.length, 0) },
  ];

  // Recent matches: show last 3 from transfers.all_completed_transfers if available
  const recentMatches = (currentReport.transfers.all_completed_transfers || [])
    .slice(-3)
    .map((match: any) => ({
      home: match.home_team || "N/A",
      away: match.away_team || "N/A",
      score: match.score || "N/A",
    }));

  return (
    <Box sx={{ p: { xs: 1, md: 3 } }}>
      <Typography variant="h4" gutterBottom tabIndex={0}>Dashboard</Typography>
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 3 }}>
        {summaryData.map((item) => (
          <Card key={item.title} sx={{ minWidth: 200, flex: "1 1 200px" }} aria-label={item.title}>
            <CardContent>
              <Typography variant="h6">{item.title}</Typography>
              <Typography variant="h4">{item.value}</Typography>
            </CardContent>
          </Card>
        ))}
      </Box>
      <Typography variant="h5" gutterBottom>Recent Matches</Typography>
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
        {recentMatches.length === 0 ? (
          <Typography>No recent matches available.</Typography>
        ) : (
          recentMatches.map((match, idx) => (
            <Card key={idx} sx={{ minWidth: 200, flex: "1 1 200px" }}>
              <CardContent>
                <Typography variant="subtitle1">
                  <Link to={`/team-details/${match.home}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                    {match.home}
                  </Link>{" "}
                  vs{" "}
                  <Link to={`/team-details/${match.away}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                    {match.away}
                  </Link>
                </Typography>
                <Typography variant="body1">Score: {match.score}</Typography>
              </CardContent>
            </Card>
          ))
        )}
      </Box>
    </Box>
  );
};

export default Dashboard;
