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
interface ManagerProfileData {
  name: string;
  formation: string;
  team: string;
}

const ManagerProfiles: React.FC = () => {
  const { selectedSeason, currentReport, isLoading, error, fetchAvailableSeasons } = useSimulationStore();
  const [allManagers, setAllManagers] = useState<ManagerProfileData[]>([]);
  const [filteredManagers, setFilteredManagers] = useState<ManagerProfileData[]>([]);
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
      const managersFromReport: ManagerProfileData[] = [];
      currentReport.all_teams_details.forEach(team => {
        // eslint-disable-next-line no-console
        if (team.manager_name) {
          managersFromReport.push({
            name: team.manager_name,
            formation: team.manager_formation,
            team: team.name, // Add team name
          });
        }
      });
      setAllManagers(managersFromReport);
      setFilteredManagers(managersFromReport);
      setLocalLoading(false);
    } else if (!currentReport && !isLoading && !error && selectedSeason) {
      setLocalLoading(true);
    }
  }, [currentReport, isLoading, error, selectedSeason]);

  useEffect(() => {
    const lowercasedSearchTerm = searchTerm.toLowerCase();
    const filtered = allManagers.filter(
      (manager) =>
        manager &&
        typeof manager.name === "string" &&
        typeof manager.formation === "string" &&
        typeof manager.team === "string" &&
        (manager.name.toLowerCase().includes(lowercasedSearchTerm) ||
        manager.formation.toLowerCase().includes(lowercasedSearchTerm) ||
        manager.team.toLowerCase().includes(lowercasedSearchTerm))
    );
    setFilteredManagers(filtered);
  }, [searchTerm, allManagers]);

  if (isLoading || localLoading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Loading all manager profiles...</Typography>
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

  if (allManagers.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <Typography variant="h6">No manager data available.</Typography>
        <Typography variant="body2">Please select a season or run a simulation.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: { xs: 1, md: 3 } }}>
      <Typography variant="h4" gutterBottom tabIndex={0}>All Manager Profiles</Typography>

      <TextField
        fullWidth
        label="Search Managers"
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
        {filteredManagers
          .filter((manager) => manager && typeof manager.name === "string")
          .map((manager, idx) => (
            <Grid item xs={12} sm={6} md={4} key={idx}>
              <Card aria-label={`Profile for ${manager.name}`}>
                <CardContent>
                  <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                    <Avatar sx={{ mr: 2 }}>{manager.name[0]}</Avatar>
                    <Box>
                      <Typography variant="h6">
                        <Link to={`/manager-profiles/${manager.name}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                          {manager.name}
                        </Link>
                      </Typography>
                      <Typography variant="subtitle2" color="text.secondary">
                        {manager.formation} | <Link to={`/team-details/${manager.team}`} style={{ textDecoration: 'none', color: 'inherit' }}>{manager.team}</Link>
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
      </Grid>
    </Box>
  );
};

export default ManagerProfiles;
