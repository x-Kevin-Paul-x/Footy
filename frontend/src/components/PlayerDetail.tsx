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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from "@mui/material";
import { Timeline, TimelineItem, TimelineSeparator, TimelineConnector, TimelineContent, TimelineDot } from "@mui/lab";
import { useSimulationStore } from "../store/simulationStore";
import type { Player, PlayerAttribute } from "../services/api";

const PlayerDetail: React.FC = () => {
  const { playerName } = useParams<{ playerName: string }>();
  const { selectedSeason, currentReport, isLoading, error, fetchAvailableSeasons } = useSimulationStore();

  const [player, setPlayer] = useState<Player | null>(null);
  const [localLoading, setLocalLoading] = useState(true);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedSeason) {
      fetchAvailableSeasons(); // Ensure a season is selected
    }
  }, [selectedSeason, fetchAvailableSeasons]);

  useEffect(() => {
    if (currentReport && playerName) {
      setLocalLoading(true);
      setLocalError(null);
      let foundPlayer: Player | null = null;
      for (const teamDetail of currentReport.all_teams_details) {
        foundPlayer = teamDetail.players.find(p => p.name === playerName) || null;
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
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Loading player details for {playerName || "selected player"}...</Typography>
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
        <Typography variant="body2">Please select a season or ensure the player name is correct.</Typography>
      </Box>
    );
  }

  const getOverallRating = (attributes: Player["attributes"]) => {
    const totalAttributeSum = Object.values(attributes).reduce(
      (sum, category: Record<string, number>) => sum + Object.values(category).reduce((catSum, val) => catSum + val, 0),
      0
    );
    const totalAttributeCount = Object.values(attributes).reduce(
      (count, category: Record<string, number>) => count + Object.keys(category).length,
      0
    );
    return totalAttributeCount > 0 ? (totalAttributeSum / totalAttributeCount).toFixed(1) : "0.0";
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>Player Profile: {player.name}</Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
            <Avatar sx={{ mr: 2, width: 60, height: 60 }}>{player.name[0]}</Avatar>
            <Box>
              <Typography variant="h5">{player.name}</Typography>
              <Typography variant="subtitle1" color="text.secondary">
                {player.position} | <Link to={`/team-details/${player.team}`} style={{ textDecoration: 'none', color: 'inherit' }}>{player.team}</Link>
              </Typography>
              <Typography variant="body2">Age: {player.age} | Overall: {getOverallRating(player.attributes)}</Typography>
              <Typography variant="body2">Market Value: £{(player.market_value / 1000000).toFixed(1)}M</Typography>
              <Typography variant="body2">Wage: £{player.wage.toLocaleString()} | Contract: {player.contract_length} years</Typography>
            </Box>
          </Box>

          <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>Key Stats</Typography>
          <TableContainer component={Paper} sx={{ mb: 2 }}>
            <Table size="small">
              <TableBody>
                <TableRow>
                  <TableCell>Goals</TableCell>
                  <TableCell align="right">{player.stats.goals}</TableCell>
                  <TableCell>Assists</TableCell>
                  <TableCell align="right">{player.stats.assists}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Appearances</TableCell>
                  <TableCell align="right">{player.stats.appearances}</TableCell>
                  <TableCell>Clean Sheets</TableCell>
                  <TableCell align="right">{player.stats.clean_sheets}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Yellow Cards</TableCell>
                  <TableCell align="right">{player.stats.yellow_cards}</TableCell>
                  <TableCell>Red Cards</TableCell>
                  <TableCell align="right">{player.stats.red_cards}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Fitness</TableCell>
                  <TableCell align="right">{player.stats.fitness}%</TableCell>
                  <TableCell>Squad Role</TableCell>
                  <TableCell align="right">{player.squad_role}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>

          <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>Attributes</Typography>
          <TableContainer component={Paper} sx={{ mb: 2 }}>
            <Table size="small">
              <TableBody>
                {Object.entries(player.attributes).map(([categoryName, attributes]) => (
                  <React.Fragment key={categoryName}>
                    <TableRow>
                      <TableCell colSpan={2} sx={{ fontWeight: 'bold', backgroundColor: '#f0f0f0' }}>
                        {categoryName.toUpperCase()}
                      </TableCell>
                    </TableRow>
                    {Object.entries(attributes as PlayerAttribute).map(([attrName, attrValue]) => (
                      <TableRow key={attrName}>
                        <TableCell>{attrName}</TableCell>
                        <TableCell align="right">{attrValue}</TableCell>
                      </TableRow>
                    ))}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {player.form && player.form.length > 0 && (
            <>
              <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>Recent Form</Typography>
              <Timeline sx={{ mt: 1 }}>
                {player.form.map((form, i) => (
                  <TimelineItem key={i}>
                    <TimelineSeparator>
                      <TimelineDot />
                      {i < player.form.length - 1 && <TimelineConnector />}
                    </TimelineSeparator>
                    <TimelineContent>
                      <Typography variant="caption">Form: {form}</Typography>
                    </TimelineContent>
                  </TimelineItem>
                ))}
              </Timeline>
            </>
          )}

          {player.injury_history && player.injury_history.length > 0 && (
            <>
              <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>Injury History</Typography>
              <TableContainer component={Paper} sx={{ mb: 2 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Date</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Recovery Time</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {player.injury_history.map((injury, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{injury.date}</TableCell>
                        <TableCell>{injury.type}</TableCell>
                        <TableCell>{injury.recovery_time} days</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          )}

          {player.stats.development && player.stats.development.length > 0 && (
            <>
              <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>Development History</Typography>
              <TableContainer component={Paper} sx={{ mb: 2 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Attribute</TableCell>
                      <TableCell>From</TableCell>
                      <TableCell>To</TableCell>
                      <TableCell>Age</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {player.stats.development.map((dev, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{dev.attribute}</TableCell>
                        <TableCell>{dev.from}</TableCell>
                        <TableCell>{dev.to}</TableCell>
                        <TableCell>{dev.age}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default PlayerDetail;
