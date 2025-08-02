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
} from "@mui/material";
import { Grid } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import { useSimulationStore } from "../store/simulationStore";
import type { Player } from "../services/api";

const PlayerProfiles: React.FC = () => {
  const { selectedSeason, currentReport, isLoading, error, fetchAvailableSeasons } = useSimulationStore();
  const [allPlayers, setAllPlayers] = useState<Player[]>([]);
  const [filteredPlayers, setFilteredPlayers] = useState<Player[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [localLoading, setLocalLoading] = useState(true);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedSeason) {
      fetchAvailableSeasons();
    }
  }, [selectedSeason, fetchAvailableSeasons]);

  useEffect(() => {
    if (currentReport) {
      setLocalLoading(true);
      setLocalError(null);
      const playersFromReport: Player[] = [];
      currentReport.all_teams_details.forEach(team => {
        playersFromReport.push(...team.players);
      });
      // Sort players by market value in descending order and take the top 30
      const sortedPlayers = playersFromReport.sort((a, b) => b.market_value - a.market_value);
      setAllPlayers(sortedPlayers);
      setFilteredPlayers(sortedPlayers.slice(0, 30)); // Cap at 30
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
    setFilteredPlayers(filtered.slice(0, 30)); // Apply cap after filtering
  }, [searchTerm, allPlayers]);

  if (isLoading || localLoading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Loading all player profiles...</Typography>
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

  if (allPlayers.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <Typography variant="h6">No player data available.</Typography>
        <Typography variant="body2">Please select a season or run a simulation.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: { xs: 1, md: 3 } }}>
      <Typography variant="h4" gutterBottom tabIndex={0}>All Player Profiles</Typography>

      <TextField
        fullWidth
        label="Search Players"
        variant="outlined"
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        sx={{ mb: 3 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          ),
        }}
      />

      <Grid container spacing={3}>
        {filteredPlayers.map((player, idx) => (
          <Grid item xs={12} sm={6} md={4} key={idx}>
            <Card aria-label={`Profile for ${player.name}`}>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                  <Avatar sx={{ mr: 2 }}>{player.name[0]}</Avatar>
                  <Box>
                    <Typography variant="h6">
                      <Link to={`/player-profiles/${player.name}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                        {player.name}
                      </Link>
                    </Typography>
                    <Typography variant="subtitle2" color="text.secondary">
                      {player.position} | <Link to={`/team-details/${player.team}`} style={{ textDecoration: 'none', color: 'inherit' }}>{player.team}</Link>
                    </Typography>
                  </Box>
                </Box>
                <Typography variant="body2" sx={{ mb: 1 }}>
                  Goals: {player.stats.goals} | Assists: {player.stats.assists}
                </Typography>
                <Typography variant="body2" sx={{ mb: 1 }}>
                  Market Value: £{(player.market_value / 1000000).toFixed(1)}M
                </Typography>
                <Typography variant="body2" sx={{ mb: 1 }}>
                  Injury Status: {player.injury_history?.length ? "Injured" : "Fit"}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default PlayerProfiles;
