import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Typography, Box, CircularProgress, Alert, Grid, Paper } from "@mui/material";
import { getMatchDetails } from "../services/api";
import FormationViewer from "./FormationViewer";
import MatchStats from "./MatchStats";
import { Timeline, TimelineItem, TimelineSeparator, TimelineConnector, TimelineContent, TimelineDot } from "@mui/lab";

const MatchDetail: React.FC = () => {
  const { matchId } = useParams<{ matchId: string }>();
  const [match, setMatch] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMatch = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getMatchDetails(Number(matchId));
        setMatch(data);
      } catch (err) {
        setError("Failed to fetch match details.");
      } finally {
        setLoading(false);
      }
    };
    fetchMatch();
  }, [matchId]);

  // Dummy formation data
  const homePlayers = [
    { name: "Player 1", position: "GK", x: 0.5, y: 0.9 },
    { name: "Player 2", position: "LB", x: 0.2, y: 0.7 },
    { name: "Player 3", position: "CB", x: 0.4, y: 0.7 },
    { name: "Player 4", position: "CB", x: 0.6, y: 0.7 },
    { name: "Player 5", position: "RB", x: 0.8, y: 0.7 },
    { name: "Player 6", position: "LM", x: 0.2, y: 0.5 },
    { name: "Player 7", position: "CM", x: 0.4, y: 0.5 },
    { name: "Player 8", position: "CM", x: 0.6, y: 0.5 },
    { name: "Player 9", position: "RM", x: 0.8, y: 0.5 },
    { name: "Player 10", position: "ST", x: 0.4, y: 0.3 },
    { name: "Player 11", position: "ST", x: 0.6, y: 0.3 },
  ];

  const awayPlayers = [
    { name: "Player 1", position: "GK", x: 0.5, y: 0.1 },
    { name: "Player 2", position: "LB", x: 0.2, y: 0.3 },
    { name: "Player 3", position: "CB", x: 0.4, y: 0.3 },
    { name: "Player 4", position: "CB", x: 0.6, y: 0.3 },
    { name: "Player 5", position: "RB", x: 0.8, y: 0.3 },
    { name: "Player 6", position: "LM", x: 0.2, y: 0.5 },
    { name: "Player 7", position: "CM", x: 0.4, y: 0.5 },
    { name: "Player 8", position: "CM", x: 0.6, y: 0.5 },
    { name: "Player 9", position: "RM", x: 0.8, y: 0.5 },
    { name: "Player 10", position: "ST", x: 0.4, y: 0.7 },
    { name: "Player 11", position: "ST", x: 0.6, y: 0.7 },
  ];

  if (loading) return <CircularProgress />;
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!match) return null;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        {match.home_team_name} {match.home_goals} - {match.away_goals} {match.away_team_name}
      </Typography>
      <Typography variant="subtitle1" gutterBottom>
        {new Date(match.date).toLocaleDateString()}
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <MatchStats
            stats={{
              home: {
                total: match.shots.home?.total ?? 0,
                on_target: match.shots.home?.on_target ?? 0,
                passes_attempted: match.home_passes_attempted ?? 0,
                passes_completed: match.home_passes_completed ?? 0,
                fouls: match.home_fouls ?? 0,
                corners: match.home_corners ?? 0,
                offsides: match.home_offsides ?? 0,
              },
              away: {
                total: match.shots.away?.total ?? 0,
                on_target: match.shots.away?.on_target ?? 0,
                passes_attempted: match.away_passes_attempted ?? 0,
                passes_completed: match.away_passes_completed ?? 0,
                fouls: match.away_fouls ?? 0,
                corners: match.away_corners ?? 0,
                offsides: match.away_offsides ?? 0,
              },
            }}
            possession={{
              home: match.home_possession ?? 50,
              away: match.away_possession ?? 50,
            }}
          />
        </Grid>
        <Grid item xs={12}>
          <Paper elevation={2} sx={{ p: 2 }}>
            <Typography variant="h6">Match Events</Typography>
            <Timeline position="alternate">
              {match.events.map((event: any, idx: number) => (
                <TimelineItem key={idx}>
                  <TimelineSeparator>
                    <TimelineDot />
                    <TimelineConnector />
                  </TimelineSeparator>
                  <TimelineContent>
                    <Typography>
                      {event.minute}' - {event.details}
                    </Typography>
                  </TimelineContent>
                </TimelineItem>
              ))}
            </Timeline>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <FormationViewer teamName={match.home_team_name} formation="4-4-2" players={homePlayers} />
        </Grid>
        <Grid item xs={12} md={6}>
          <FormationViewer teamName={match.away_team_name} formation="4-3-3" players={awayPlayers} />
        </Grid>
      </Grid>
    </Box>
  );
};

export default MatchDetail;
