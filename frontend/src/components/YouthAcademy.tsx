import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Typography,
  Box,
  Grid, // Added Grid
  Card,
  CardContent,
  LinearProgress,
  CircularProgress,
  Alert,
  Chip, // Added Chip for status
  Stack,
} from "@mui/material";
import { getAvailableSeasons, getSeasonReportData } from "../services/api";
import type { TeamDetail, Player } from "../services/api";

// Helper to get overall rating from attributes
const getOverallRating = (attributes: Player["attributes"]): number => {
  if (!attributes) return 0;
  let total = 0;
  let count = 0;
  for (const attrType in attributes) {
    for (const subAttr in attributes[attrType]) {
      total += attributes[attrType][subAttr];
      count += 1;
    }
  }
  return count > 0 ? total / count : 0;
};

const YouthAcademy: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [players, setPlayers] = useState<Player[]>([]);
  const [selectedSeason, setSelectedSeason] = useState<number | null>(null);
  const [availableSeasons, setAvailableSeasons] = useState<number[]>([]);

  useEffect(() => {
    const fetchSeasons = async () => {
      try {
        const seasons = await getAvailableSeasons();
        setAvailableSeasons(seasons);
        if (seasons.length > 0) {
          setSelectedSeason(Math.max(...seasons));
        }
      } catch (err: any) {
        setError(err.message || "Failed to fetch available seasons.");
      }
    };
    fetchSeasons();
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      if (selectedSeason === null) return;

      setLoading(true);
      setError(null);
      try {
        const report = await getSeasonReportData(selectedSeason);
        const youthPlayers: Player[] = report.all_teams_details
          .flatMap((team: TeamDetail) =>
            team.players.map((p) => ({ ...p, team: team.name })) // Add team name to player object
          )
          .filter((p: Player) => p.age <= 18);
        setPlayers(youthPlayers);
      } catch (err: any) {
        setError(err.message || "Failed to fetch youth academy data.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [selectedSeason]);

  if (loading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
        <Typography mt={2}>Loading youth academy data...</Typography>
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

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Youth Academy
      </Typography>

      {/* Season Selector (Optional, for future enhancement) */}
      {/* <FormControl sx={{ mb: 3, minWidth: 120 }}>
        <InputLabel>Season</InputLabel>
        <Select
          value={selectedSeason || ''}
          onChange={(e) => setSelectedSeason(Number(e.target.value))}
          label="Season"
        >
          {availableSeasons.map((season) => (
            <MenuItem key={season} value={season}>
              {season}
            </MenuItem>
          ))}
        </Select>
      </FormControl> */}

      {players.length === 0 ? (
        <Typography>No youth players found for this season.</Typography>
      ) : (
        <Grid container spacing={3}>
          {players.map((player, idx) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={idx}>
              <Card sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Typography variant="h6" component="div">
                    <Link to={`/player-profiles/${player.name}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                      {player.name}
                    </Link>
                  </Typography>
                  <Typography color="text.secondary">
                    {player.position} | Age: {player.age} | Team:{" "}
                    <Link to={`/team-details/${player.team}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                      {player.team}
                    </Link>
                  </Typography>
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2">
                      Potential: {Math.round(player.potential)}
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={Math.round(player.potential)}
                      sx={{ height: 8, borderRadius: 5 }}
                      color={player.potential > 80 ? "success" : "primary"}
                    />
                  </Box>
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="body2">
                      Overall Rating: {getOverallRating(player.attributes).toFixed(1)}
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={getOverallRating(player.attributes)}
                      sx={{ height: 8, borderRadius: 5 }}
                      color={getOverallRating(player.attributes) > 75 ? "success" : "primary"}
                    />
                  </Box>
                  <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
                    {player.is_injured ? (
                      <Chip
                        label={`Injured (${player.recovery_time} days)`}
                        color="error"
                        size="small"
                      />
                    ) : (
                      <Chip label="Fit" color="success" size="small" />
                    )}
                    <Chip
                      label={`Fitness: ${player.stats.fitness}%`}
                      color={player.stats.fitness < 50 ? "warning" : "info"}
                      size="small"
                    />
                  </Stack>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Contract: {player.contract_length} years | Wage: £{player.wage.toLocaleString()}
                  </Typography>
                  <Typography variant="body2">
                    Role: {player.squad_role}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
};

export default YouthAcademy;
