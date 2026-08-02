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
  Paper,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  Chip,
} from "@mui/material";
import { Timeline, TimelineItem, TimelineSeparator, TimelineConnector, TimelineContent, TimelineDot } from "@mui/lab";
import { useSimulationStore } from "../store/simulationStore";
import { Link } from "react-router-dom";
import SeasonComparisonCharts from "../components/SeasonComparisonCharts";
import { getAllSeasonsOverview, type AllSeasonsOverviewResponse } from "../services/api";

// Theme-aware FINNOVA Card Style
const glassCardSx = {
  borderRadius: "20px !important",
  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important",
  "&:hover": {
    borderColor: "#6366f1 !important",
    boxShadow: "0 12px 32px 0 rgba(99, 102, 241, 0.15) !important",
  }
};



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
      id={`season-tabpanel-${index}`}
      aria-labelledby={`season-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

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

  const [tabValue, setTabValue] = useState(0);
  const [allSeasonsData, setAllSeasonsData] = useState<AllSeasonsOverviewResponse | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  useEffect(() => {
    fetchAvailableSeasons();
  }, [fetchAvailableSeasons]);

  useEffect(() => {
    const fetchAllSeasonsData = async () => {
      setOverviewLoading(true);
      try {
        const data = await getAllSeasonsOverview();
        setAllSeasonsData(data);
        setOverviewError(null);
      } catch (err) {
        console.error("Failed to fetch all seasons overview:", err);
        setOverviewError("Failed to load multi-season data");
      } finally {
        setOverviewLoading(false);
      }
    };
    fetchAllSeasonsData();
  }, []);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSeasonPillClick = (season: number) => {
    selectSeason(season);
    setTabValue(1); // Switch to Detailed tab when clicking a season pill
  };

  if (isLoading && !currentReport && !allSeasonsData) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Loading season data...</Typography>
      </Box>
    );
  }

  if (error && !allSeasonsData) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!currentReport && availableSeasons.length === 0 && !allSeasonsData) {
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
    <Box sx={{ p: { xs: 1, md: 0 } }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Season Reports
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Multi-season analysis and detailed season breakdowns
        </Typography>
      </Box>

      {/* Tab Switcher */}
      <Paper sx={{ ...glassCardSx, mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Overview" id="season-tab-0" aria-controls="season-tabpanel-0" />
          <Tab label="Detailed" id="season-tab-1" aria-controls="season-tabpanel-1" />
        </Tabs>
      </Paper>

      {/* Season Pill Bar */}
      <Box
        sx={{
          display: "flex",
          gap: 1,
          flexWrap: "wrap",
          mb: 3,
          p: 2,
          ...glassCardSx,
          borderRadius: 2
        }}
      >
        <Typography variant="subtitle2" color="text.secondary" sx={{ width: "100%", mb: 1 }}>
          Quick Navigation
        </Typography>
        {availableSeasons.map((season) => (
          <Chip
            key={season}
            label={season}
            onClick={() => handleSeasonPillClick(season)}
            variant={selectedSeason === season ? "filled" : "outlined"}
            color={selectedSeason === season ? "primary" : "default"}
            sx={{
              fontWeight: selectedSeason === season ? 700 : 500,
              transition: "all 0.2s",
              "&:hover": { transform: "translateY(-2px)" }
            }}
          />
        ))}
      </Box>

      {/* Overview Tab */}
      <TabPanel value={tabValue} index={0}>
        {overviewLoading ? (
          <Box sx={{ textAlign: "center", py: 4 }}>
            <CircularProgress />
            <Typography sx={{ mt: 2 }} color="text.secondary">Loading multi-season data...</Typography>
          </Box>
        ) : overviewError ? (
          <Alert severity="error">{overviewError}</Alert>
        ) : allSeasonsData ? (
          <SeasonComparisonCharts
            seasons={allSeasonsData.seasons}
            teamPositionTrends={allSeasonsData.team_position_trends}
          />
        ) : (
          <Typography color="text.secondary">No overview data available.</Typography>
        )}
      </TabPanel>

      {/* Detailed Tab */}
      <TabPanel value={tabValue} index={1}>
        {!currentReport ? (
          <Box sx={{ textAlign: "center", py: 4 }}>
            <Typography variant="h6" color="text.secondary">
              Select a season from the pills above to view details
            </Typography>
          </Box>
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <Typography variant="h5" sx={{ fontWeight: 600 }}>
              Season {currentReport.season_year} Summary
            </Typography>

            {championsName && (
              <Paper sx={{ ...glassCardSx, p: 2 }}>
                <Typography variant="h6">🏆 Champions: {championsName}</Typography>
                {championsManager && (
                  <Typography variant="body2" color="text.secondary">
                    Manager:{" "}
                    <Link to={`/manager-profiles/${championsManager.name}`} style={{ textDecoration: 'none', color: 'inherit', fontWeight: 'bold' }}>
                      {championsManager.name}
                    </Link>{" "}
                    (Experience: {championsManager.experience})
                  </Typography>
                )}
              </Paper>
            )}

            <TableContainer component={Paper} sx={glassCardSx}>
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

            <Typography variant="h5" sx={{ fontWeight: 600 }}>Team of the Season</Typography>
            <TableContainer component={Paper} sx={glassCardSx}>
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
                            (sum, category: Record<string, number>) => sum + Object.values(category || {}).reduce((catSum, val) => catSum + val, 0),
                            0
                          );
                          const totalAttributeCount = Object.values(player.attributes || {}).reduce(
                            (count, category: Record<string, number>) => count + Object.keys(category || {}).length,
                            0
                          );
                          return totalAttributeCount > 0 ? (totalAttributeSum / totalAttributeCount).toFixed(1) : "0.0";
                        })()}
                      </TableCell>
                      <TableCell align="right">£{((player.market_value ?? 0) / 1000000).toFixed(1)}M</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            {/* Timeline */}
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
          </Box>
        )}
      </TabPanel>
    </Box>
  );
};

export default SeasonReports;
