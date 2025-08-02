import React, { useEffect } from "react";
import {
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from "@mui/material";
import { Timeline, TimelineItem, TimelineSeparator, TimelineConnector, TimelineContent, TimelineDot } from "@mui/lab";
import { useSimulationStore } from "../store/simulationStore";
import { Link } from "react-router-dom";

const SeasonReports: React.FC = () => {
  const {
    availableSeasons,
    selectedSeason,
    currentReport,
    isLoading,
    error,
    fetchAvailableSeasons,
    selectSeason,
  } = useSimulationStore();

  useEffect(() => {
    fetchAvailableSeasons();
  }, [fetchAvailableSeasons]);

  if (isLoading && !currentReport) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Loading season data...</Typography>
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

  if (!currentReport && availableSeasons.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <Typography variant="h6">No season data available.</Typography>
        <Typography variant="body2">Run a simulation to generate reports.</Typography>
      </Box>
    );
  }

  const leagueTable = currentReport?.table || [];
  const bestPlayers = currentReport?.best_players || [];
  const championsManager = currentReport?.champions_manager;
  const championsName = currentReport?.champions;

  return (
    <Box sx={{ p: 3, display: "flex", flexDirection: "column", gap: 4 }}>
      <Typography variant="h4">Season Reports</Typography>

      <FormControl sx={{ minWidth: 120 }}>
        <InputLabel id="season-select-label">Select Season</InputLabel>
        <Select
          labelId="season-select-label"
          value={selectedSeason || ""}
          label="Select Season"
          onChange={(e) => selectSeason(e.target.value as number)}
        >
          {availableSeasons.map((season) => (
            <MenuItem key={season} value={season}>
              {season}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {currentReport && (
        <>
          <Typography variant="h5">Season {currentReport.season_year} Summary</Typography>

          {championsName && (
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6">Champions: {championsName}</Typography>
              {championsManager && (
                <Typography variant="body2">
                  Manager:{" "}
                  <Link to={`/manager-profiles/${championsManager.name}`} style={{ textDecoration: 'none', color: 'inherit', fontWeight: 'bold' }}>
                    {championsManager.name}
                  </Link>{" "}
                  (Experience: {championsManager.experience})
                </Typography>
              )}
            </Paper>
          )}

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Pos</TableCell>
                  <TableCell>Team</TableCell>
                  <TableCell align="right">Pld</TableCell>
                  <TableCell align="right">W</TableCell>
                  <TableCell align="right">D</TableCell>
                  <TableCell align="right">L</TableCell>
                  <TableCell align="right">GF</TableCell>
                  <TableCell align="right">GA</TableCell>
                  <TableCell align="right">GD</TableCell>
                  <TableCell align="right">Pts</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {leagueTable.map((entry, index) => (
                  <TableRow key={entry[0]}>
                    <TableCell>{index + 1}</TableCell>
                    <TableCell>
                      <Link to={`/team-details/${entry[0]}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                        {entry[0]}
                      </Link>
                    </TableCell>
                    <TableCell align="right">{entry[1].played}</TableCell>
                    <TableCell align="right">{entry[1].won}</TableCell>
                    <TableCell align="right">{entry[1].drawn}</TableCell>
                    <TableCell align="right">{entry[1].lost}</TableCell>
                    <TableCell align="right">{entry[1].gf}</TableCell>
                    <TableCell align="right">{entry[1].ga}</TableCell>
                    <TableCell align="right">{entry[1].gd}</TableCell>
                    <TableCell align="right">{entry[1].points}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          <Typography variant="h5">Team of the Season</Typography>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Position</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Team</TableCell>
                  <TableCell align="right">Age</TableCell>
                  <TableCell align="right">Rating</TableCell>
                  <TableCell align="right">Value</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {bestPlayers.map((player, index) => (
                  <TableRow key={index}>
                    <TableCell>{player.position}</TableCell>
                    <TableCell>
                      <Link to={`/player-profiles/${player.name}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                        {player.name}
                      </Link>
                    </TableCell>
                    <TableCell>{player.team}</TableCell>
                    <TableCell align="right">{player.age}</TableCell>
                    <TableCell align="right">
                      {(() => {
                        const totalAttributeSum = Object.values(player.attributes || {}).reduce(
                          (sum, category: Record<string, number>) => sum + Object.values(category).reduce((catSum, val) => catSum + val, 0),
                          0
                        );
                        const totalAttributeCount = Object.values(player.attributes || {}).reduce(
                          (count, category: Record<string, number>) => count + Object.keys(category).length,
                          0
                        );
                        return totalAttributeCount > 0 ? (totalAttributeSum / totalAttributeCount).toFixed(1) : "0.0";
                      })()}
                    </TableCell>
                    <TableCell align="right">£{(player.market_value / 1000000).toFixed(1)}M</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {/* Placeholder for other reports like financial summary, injury report, youth prospects */}
          <Paper sx={{ p: 2, textAlign: "center" }}>
            <Typography variant="h6">Additional Season Insights</Typography>
            <Typography variant="body2" color="text.secondary">
              [Financial Summary, Injury Report, Youth Prospects - To be implemented]
            </Typography>
          </Paper>

          {/* Timeline can be adapted for key season events if available in report */}
          <Timeline position="alternate">
            <TimelineItem>
              <TimelineSeparator>
                <TimelineDot color="primary" />
                <TimelineConnector />
              </TimelineSeparator>
              <TimelineContent>Season {currentReport.season_year} Started</TimelineContent>
            </TimelineItem>
            <TimelineItem>
              <TimelineSeparator>
                <TimelineDot color="secondary" />
                <TimelineConnector />
              </TimelineSeparator>
              <TimelineContent>Mid-Season Transfer Window</TimelineContent>
            </TimelineItem>
            <TimelineItem>
              <TimelineSeparator>
                <TimelineDot />
              </TimelineSeparator>
              <TimelineContent>Season {currentReport.season_year} Concluded</TimelineContent>
            </TimelineItem>
          </Timeline>
        </>
      )}
    </Box>
  );
};

export default SeasonReports;
