import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Typography,
  Box,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Paper,
  Stack,
  CircularProgress,
  Alert
} from "@mui/material";
import {
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot
} from "@mui/lab";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useSimulationStore } from "../store/simulationStore";
import type { SeasonReport, Player } from "../services/api";

interface MatchResult {
  date: string;
  homeTeam: string;
  awayTeam: string;
  score: string;
}

interface Highlight {
  time: string;
  event: string;
  playerName?: string; // Optional player name for linking
}

const MatchReports: React.FC = () => {
  const { selectedSeason, currentReport, isLoading, error, fetchAvailableSeasons } = useSimulationStore();
  const [matchResults, setMatchResults] = useState<MatchResult[]>([]);
  const [highlights, setHighlights] = useState<Highlight[]>([]);
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

      // Placeholder for match results - actual match data is not directly in SeasonReport
      // This will need backend changes to expose match reports per season
      const demoMatchResults: MatchResult[] = currentReport.table.slice(0, 5).map((entry) => ({
        date: "N/A", // Date not available in table entry
        homeTeam: entry[0], // Using team name as home team for demo
        awayTeam: "Opponent", // Placeholder
        score: `${entry[1].gf}-${entry[1].ga}` // Goals For - Goals Against
      }));

      // Example highlights: Use best_players for demo
      const demoHighlights: Highlight[] = [];
      if (currentReport.best_players && currentReport.best_players.length > 0) {
        currentReport.best_players.slice(0, 3).forEach((p: Player, idx: number) => {
          demoHighlights.push({
            time: `${(idx + 1) * 15}'`,
            event: `Goal by ${p.name} (${p.team})`,
            playerName: p.name,
          });
        });
      }

      setMatchResults(demoMatchResults);
      setHighlights(demoHighlights);
      setLocalLoading(false);
    } else if (!currentReport && !isLoading && !error && selectedSeason) {
      setLocalLoading(true);
    }
  }, [currentReport, isLoading, error, selectedSeason]);

  if (isLoading || localLoading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
        <Typography mt={2}>Loading match reports...</Typography>
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

  return (
    <Box sx={{ p: { xs: 1, md: 3 } }}>
      <Typography variant="h4" gutterBottom tabIndex={0}>Match Reports</Typography>

      <Stack spacing={3}>
        {/* Results Accordion */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography>Recent Match Results (Placeholder)</Typography>
          </AccordionSummary>
          <AccordionDetails>
            {matchResults.length === 0 ? (
              <Typography>No match results found for this season.</Typography>
            ) : (
              matchResults.map((result, idx) => (
                <Box key={idx} sx={{ mb: 2 }}>
                  <Typography variant="subtitle1">
                    <Link to={`/team-details/${result.homeTeam}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                      {result.homeTeam}
                    </Link>{" "}
                    vs{" "}
                    <Link to={`/team-details/${result.awayTeam}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                      {result.awayTeam}
                    </Link>
                  </Typography>
                  <Typography variant="body2">{result.date} — Score: {result.score}</Typography>
                </Box>
              ))
            )}
          </AccordionDetails>
        </Accordion>

        {/* Stats Chart Placeholder */}
        <Paper elevation={2} sx={{ p: 2 }}>
          <Typography variant="h6">Stats Chart</Typography>
          <Box sx={{ height: 120, bgcolor: "#f5f5f5", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Typography color="text.secondary">[Chart Placeholder]</Typography>
          </Box>
        </Paper>

        {/* Timeline Highlights */}
        <Box>
          <Typography variant="h6" gutterBottom>Match Highlights (Placeholder)</Typography>
          <Timeline position="right">
            {highlights.length === 0 ? (
              <Typography>No highlights available for this season.</Typography>
            ) : (
              highlights.map((h, idx) => (
                <TimelineItem key={idx}>
                  <TimelineSeparator>
                    <TimelineDot color="primary" />
                    {idx < highlights.length - 1 && <TimelineConnector />}
                  </TimelineSeparator>
                  <TimelineContent>
                    <Typography variant="body2">
                      {h.time} - {h.event}{" "}
                      {h.playerName && (
                        <Link to={`/player-profiles/${h.playerName}`} style={{ textDecoration: 'none', color: 'inherit', fontWeight: 'bold' }}>
                          ({h.playerName})
                        </Link>
                      )}
                    </Typography>
                  </TimelineContent>
                </TimelineItem>
              ))
            )}
          </Timeline>
        </Box>
      </Stack>
    </Box>
  );
};

export default MatchReports;
