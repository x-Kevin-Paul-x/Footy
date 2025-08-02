import React, { useEffect, useState } from "react";
import {
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Card,
  CardContent,
  Stack,
  CircularProgress,
  Alert
} from "@mui/material";
import { getAvailableSeasons, getSeasonReportData } from "../services/api";
import type { TeamDetail, Player } from "../services/api";

const YouthAcademy: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [players, setPlayers] = useState<Player[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const seasons = await getAvailableSeasons();
        const latestSeason = Math.max(...seasons);
        const report = await getSeasonReportData(latestSeason);
        // Filter youth players (age <= 18) from all teams
        const youthPlayers: Player[] =
          report.all_teams_details
            .flatMap((team: TeamDetail) => team.players)
            .filter((p: Player) => p.age <= 18);
        setPlayers(youthPlayers);
      } catch (err: any) {
        setError(err.message || "Failed to fetch youth academy data.");
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
      <Typography variant="h4" gutterBottom>Youth Academy</Typography>

      <Stack spacing={3}>
        {/* Player List Table */}
        <TableContainer component={Box}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Age</TableCell>
                <TableCell>Position</TableCell>
                <TableCell>Development</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {players.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4}>
                    <Typography>No youth players found.</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                players.map((player, idx) => {
                  // Example progress: use potential as progress
                  const progress = Math.round(player.potential);
                  return (
                    <TableRow key={idx}>
                      <TableCell>{player.name}</TableCell>
                      <TableCell>{player.age}</TableCell>
                      <TableCell>{player.position}</TableCell>
                      <TableCell sx={{ minWidth: 120 }}>
                        <Box sx={{ display: "flex", alignItems: "center" }}>
                          <LinearProgress
                            variant="determinate"
                            value={progress}
                            sx={{ width: 80, mr: 1 }}
                            color={progress > 80 ? "success" : "primary"}
                          />
                          <Typography variant="caption">{progress}%</Typography>
                        </Box>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Player Card Example */}
        <Card sx={{ maxWidth: 320 }}>
          <CardContent>
            <Typography variant="h6">Featured Player</Typography>
            {players.length === 0 ? (
              <Typography>No featured player available.</Typography>
            ) : (
              <>
                <Typography>Name: {players[0].name}</Typography>
                <Typography>Age: {players[0].age}</Typography>
                <Typography>Position: {players[0].position}</Typography>
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2">Development Tracker</Typography>
                  <LinearProgress
                    variant="determinate"
                    value={Math.round(players[0].potential)}
                    sx={{ height: 10, borderRadius: 5 }}
                    color={players[0].potential > 80 ? "success" : "primary"}
                  />
                  <Typography variant="caption">{Math.round(players[0].potential)}%</Typography>
                </Box>
              </>
            )}
          </CardContent>
        </Card>
      </Stack>
    </Box>
  );
};

export default YouthAcademy;