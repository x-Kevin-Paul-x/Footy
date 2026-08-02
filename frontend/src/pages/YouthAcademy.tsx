import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  LinearProgress,
  CircularProgress,
  Alert,
  Chip,
  Stack,
  alpha,
} from "@mui/material";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";
import FitnessCenterIcon from "@mui/icons-material/FitnessCenter";
import StarsIcon from "@mui/icons-material/Stars";
import { getAvailableSeasons, getSeasonReportData } from "../services/api";
import type { TeamDetail, Player } from "../services/api";

// Position color definitions
const getPositionColor = (position: string): string => {
  if (!position) return "#8b5cf6";
  if (position.startsWith("GK")) return "#a78bfa"; // violet/purple
  if (position.startsWith("D")) return "#06b6d4"; // cyan
  if (position.startsWith("M")) return "#10b981"; // emerald
  if (position.startsWith("F") || position.startsWith("S")) return "#f43f5e"; // rose/crimson
  return "#8b5cf6";
};

// Dynamic FINNOVA Card Style with Top Border Indicator and Position Color Accent
const getPlayerCardSx = (position: string) => {
  const color = getPositionColor(position);
  return {
    position: "relative" as const,
    borderRadius: "20px",
    transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
    overflow: "hidden",
    height: "100%",
    display: "flex",
    flexDirection: "column",
    "&::before": {
      content: '""',
      position: "absolute",
      top: 0,
      left: 0,
      right: 0,
      height: 4,
      background: `linear-gradient(90deg, ${color}, ${alpha(color, 0.4)})`,
    },
    "&:hover": {
      transform: "translateY(-4px)",
      borderColor: color,
      boxShadow: `0 12px 32px 0 ${alpha(color, 0.15)}`,
    },
  };
};


const getOverallRating = (attributes: Player["attributes"]): number => {
  if (!attributes) return 0;
  let total = 0;
  let count = 0;
  for (const attrType in attributes) {
    if (attributes[attrType]) {
      for (const subAttr in attributes[attrType]) {
        total += attributes[attrType][subAttr] || 0;
        count += 1;
      }
    }
  }
  return count > 0 ? total / count : 0;
};

const YouthAcademy: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [players, setPlayers] = useState<Player[]>([]);
  const [_selectedSeason, setSelectedSeason] = useState<number | null>(null);
  const [_availableSeasons, setAvailableSeasons] = useState<number[]>([]);

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
      if (_selectedSeason === null) return;

      setLoading(true);
      setError(null);
      try {
        const report = await getSeasonReportData(_selectedSeason);
        const youthPlayers: Player[] = report.all_teams_details
          .flatMap((team: TeamDetail) =>
            (team.players || []).map((p) => ({ ...p, team: team.name }))
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
  }, [_selectedSeason]);

  if (loading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress size={48} />
        <Typography mt={2} color="text.secondary">Loading youth academy prospects...</Typography>
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
    <Box sx={{ p: { xs: 1, md: 0 } }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Youth Academy
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Future stars under 19 developing in the squad systems
        </Typography>
      </Box>

      {players.length === 0 ? (
        <Typography color="text.secondary">No youth players found for this season.</Typography>
      ) : (
        <Grid container spacing={3}>
          {players.map((player, idx) => {
            const overall = getOverallRating(player.attributes);
            const posColor = getPositionColor(player.position);
            return (
              <Grid item xs={12} sm={6} md={4} lg={3} key={idx}>
                <Card sx={getPlayerCardSx(player.position)}>
                  <CardContent sx={{ flexGrow: 1, p: 3, display: "flex", flexDirection: "column", height: "100%" }}>
                    <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 2 }}>
                      <Box>
                        <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
                          <Link to={`/player-profiles/${player.name}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                            {player.name}
                          </Link>
                        </Typography>
                        <Chip
                          label={player.position}
                          size="small"
                          sx={{
                            bgcolor: alpha(posColor, 0.15),
                            color: posColor,
                            fontWeight: 700,
                            border: `1px solid ${alpha(posColor, 0.3)}`,
                          }}
                        />
                      </Box>
                      <Box sx={{ textAlign: "right" }}>
                        <Typography variant="h4" sx={{ fontWeight: 800, color: posColor, lineHeight: 1 }}>
                          {(overall ?? 0).toFixed(0)}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          OVERALL
                        </Typography>
                      </Box>
                    </Box>

                    <Typography color="text.secondary" variant="body2" sx={{ mb: 3 }}>
                      Age: {player.age} | Team:{" "}
                      <Link to={`/team-details/${player.team}`} style={{ textDecoration: 'none', color: 'inherit', fontWeight: 600 }}>
                        {player.team}
                      </Link>
                    </Typography>

                    <Stack spacing={2} sx={{ mb: 3, flexGrow: 1 }}>
                      <Box>
                        <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                          <Typography variant="body2" color="text.secondary" sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                            <StarsIcon sx={{ fontSize: 16, color: "warning.main" }} /> Potential
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {Math.round(player.potential ?? 0)}
                          </Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={Math.round(player.potential ?? 0)}
                          sx={{
                            height: 6,
                            borderRadius: 3,
                            bgcolor: "rgba(255,255,255,0.05)",
                            "& .MuiLinearProgress-bar": {
                              borderRadius: 3,
                              background: `linear-gradient(90deg, ${posColor}, #fbbf24)`,
                            }
                          }}
                        />
                      </Box>

                      <Box>
                        <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                          <Typography variant="body2" color="text.secondary" sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                            <FitnessCenterIcon sx={{ fontSize: 16, color: "info.main" }} /> Fitness
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {player.stats?.fitness ?? 0}%
                          </Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={player.stats?.fitness ?? 0}
                          sx={{
                            height: 6,
                            borderRadius: 3,
                            bgcolor: "rgba(255,255,255,0.05)",
                            "& .MuiLinearProgress-bar": {
                              borderRadius: 3,
                              bgcolor: (player.stats?.fitness ?? 0) < 50 ? "warning.main" : "info.main",
                            }
                          }}
                        />
                      </Box>
                    </Stack>

                    <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                      {player.is_injured ? (
                        <Chip
                          icon={<LocalHospitalIcon />}
                          label={`Injured (${player.recovery_time}d)`}
                          color="error"
                          size="small"
                          sx={{ fontWeight: 600 }}
                        />
                      ) : (
                        <Chip label="Fit & Ready" color="success" size="small" variant="outlined" sx={{ fontWeight: 600 }} />
                      )}
                      <Chip
                        label={player.squad_role || "Prospect"}
                        size="small"
                        variant="outlined"
                        sx={{ color: "text.secondary", borderColor: "rgba(255,255,255,0.1)" }}
                      />
                    </Stack>

                    <Box sx={{ pt: 2, borderTop: "1px solid rgba(255, 255, 255, 0.05)", display: "flex", justifyContent: "space-between" }}>
                      <Typography variant="caption" color="text.secondary">
                        Contract: {player.contract_length ?? 0} yrs
                      </Typography>
                      <Typography variant="caption" sx={{ fontWeight: 600, color: "emerald.main" }}>
                        Wage: £{(player.wage ?? 0).toLocaleString()}/w
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}
    </Box>
  );
};

export default YouthAcademy;
