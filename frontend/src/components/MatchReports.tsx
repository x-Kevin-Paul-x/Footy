import React, { useEffect, useState } from "react";
import { Typography, Box, CircularProgress, Alert, Grid, Card, CardActionArea, CardContent } from "@mui/material";
import { useSimulationStore } from "../store/simulationStore";
import { getMatchesBySeason } from "../services/api";
import { useNavigate } from "react-router-dom";

const MatchReports: React.FC = () => {
  const { selectedSeason, fetchAvailableSeasons, availableSeasons } = useSimulationStore();
  const [matches, setMatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (availableSeasons.length === 0) {
      fetchAvailableSeasons();
    }
  }, [availableSeasons, fetchAvailableSeasons]);

  useEffect(() => {
    const fetchMatches = async () => {
      if (selectedSeason) {
        setLoading(true);
        setError(null);
        try {
          const data = await getMatchesBySeason(selectedSeason);
          // Sort by date descending
          const sorted = [...data].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
          setMatches(sorted);
        } catch (err) {
          setError("Failed to fetch matches.");
        } finally {
          setLoading(false);
        }
      }
    };
    fetchMatches();
  }, [selectedSeason]);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Match Reports
      </Typography>
      {loading && <CircularProgress />}
      {error && <Alert severity="error">{error}</Alert>}
      {(() => {
        // Group matches by date
        const grouped: { [date: string]: any[] } = {};
        matches.forEach((match) => {
          let dateStr = "Unknown Date";
          if (match.date) {
            const parsed = new Date(match.date);
            dateStr = isNaN(parsed.getTime()) ? "Unknown Date" : parsed.toLocaleDateString();
          }
          if (!grouped[dateStr]) grouped[dateStr] = [];
          grouped[dateStr].push(match);
        });
        const sortedDates = Object.keys(grouped).sort((a, b) => new Date(b).getTime() - new Date(a).getTime());
        return (
          <Box>
            {sortedDates.map((date) => (
              <Box key={date} sx={{ mb: 3 }}>
                <Typography variant="h6" sx={{ mb: 1 }}>
                  {date}
                </Typography>
                {grouped[date].map((match) => (
                  <Box
                    key={match.match_id}
                    sx={{
                      p: 2,
                      mb: 1,
                      borderRadius: 2,
                      boxShadow: 1,
                      bgcolor: "background.paper",
                      cursor: "pointer",
                      "&:hover": { bgcolor: "action.hover" },
                    }}
                    onClick={() => navigate(`/match/${match.match_id}`)}
                  >
                    <Typography variant="body1">
                      {match.home_team_name} {match.home_goals ?? match.home_score ?? ""} - {match.away_goals ?? match.away_score ?? ""} {match.away_team_name}
                    </Typography>
                  </Box>
                ))}
              </Box>
            ))}
          </Box>
        );
      })()}
    </Box>
  );
};

export default MatchReports;
