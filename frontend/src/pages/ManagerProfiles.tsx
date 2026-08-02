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
  Chip,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import PersonIcon from "@mui/icons-material/Person";
import GroupsIcon from "@mui/icons-material/Groups";
import { useSimulationStore } from "../store/simulationStore";

const glassCardSx = {
  borderRadius: "20px !important",
  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important",
  "&:hover": {
    borderColor: "#6366f1 !important",
    boxShadow: "0 12px 32px 0 rgba(99, 102, 241, 0.15) !important",
    transform: "translateY(-4px) !important",
  }
};


interface ManagerProfileData {
  name: string;
  formation: string;
  team: string;
  points?: number;
  position?: number;
}

const ManagerProfiles: React.FC = () => {
  const { selectedSeason, currentReport, isLoading, error, fetchAvailableSeasons, availableSeasons, selectSeason } =
    useSimulationStore();
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
    if (availableSeasons.length > 0 && !currentReport) {
      selectSeason(Math.max(...availableSeasons));
    }
  }, [availableSeasons, currentReport, selectSeason]);

  useEffect(() => {
    if (currentReport) {
      setLocalLoading(true);
      setLocalError(null);
      const managersFromReport: ManagerProfileData[] = [];

      currentReport.all_teams_details.forEach((team) => {
        if (team.manager_name) {
          // Find team position from table
          const tableEntry = currentReport.table.find(([teamName]) => teamName === team.name);
          const position = tableEntry
            ? currentReport.table.indexOf(tableEntry) + 1
            : 20;
          const stats = tableEntry ? tableEntry[1] : {};

          managersFromReport.push({
            name: team.manager_name,
            formation: team.manager_formation,
            team: team.name,
            points: typeof stats.points === 'number' ? stats.points : 0,
            position,
          });
        }
      });

      // Sort by position
      managersFromReport.sort((a, b) => (a.position || 20) - (b.position || 20));

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
        <Typography sx={{ mt: 2 }} color="text.secondary">
          Loading manager profiles...
        </Typography>
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
        <Typography variant="body2" color="text.secondary">
          Please run a simulation to generate data.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: { xs: 1, md: 0 } }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Manager Profiles
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {filteredManagers.length} managers • Season {currentReport?.season_year || selectedSeason}
        </Typography>
      </Box>

      {/* Search */}
      <Card sx={{ ...glassCardSx, mb: 3, "&:hover": { transform: "none" } }}>
        <CardContent sx={{ p: 2 }}>
          <TextField
            fullWidth
            placeholder="Search by name, team, or formation..."
            variant="outlined"
            size="small"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon color="action" />
                </InputAdornment>
              ),
            }}
            sx={{
              "& .MuiOutlinedInput-root": { bgcolor: "action.hover" },
            }}
          />
        </CardContent>
      </Card>

      {/* Manager Grid */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)", lg: "repeat(4, 1fr)" },
          gap: 2,
        }}
      >
        {filteredManagers
          .filter((manager) => manager && typeof manager.name === "string")
          .map((manager, idx) => (
            <Card key={idx} sx={glassCardSx}>
              <CardContent sx={{ p: 2.5 }}>
                <Box sx={{ display: "flex", gap: 2 }}>
                  <Avatar
                    sx={{
                      width: 56,
                      height: 56,
                      bgcolor: manager.position === 1 ? "warning.main" : "primary.main",
                      fontSize: 24,
                      fontWeight: 700,
                    }}
                  >
                    {manager.name[0]}
                  </Avatar>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Link
                      to={`/manager-profiles/${manager.name}`}
                      style={{ textDecoration: "none", color: "inherit" }}
                    >
                      <Typography variant="h6" sx={{ fontWeight: 600, lineHeight: 1.2 }} noWrap>
                        {manager.name}
                      </Typography>
                    </Link>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mt: 0.5 }}>
                      <GroupsIcon sx={{ fontSize: 14, color: "text.secondary" }} />
                      <Link
                        to={`/team-details/${manager.team}`}
                        style={{ textDecoration: "none", color: "inherit" }}
                      >
                        <Typography variant="body2" color="text.secondary" noWrap>
                          {manager.team}
                        </Typography>
                      </Link>
                    </Box>
                  </Box>
                </Box>

                <Box sx={{ display: "flex", gap: 1, mt: 2, flexWrap: "wrap" }}>
                  <Chip
                    label={manager.formation}
                    size="small"
                    variant="outlined"
                    sx={{ fontWeight: 500 }}
                  />
                  <Chip
                    label={`#${manager.position}`}
                    size="small"
                    color={
                      manager.position === 1
                        ? "warning"
                        : (manager.position || 20) <= 4
                          ? "success"
                          : (manager.position || 20) <= 10
                            ? "primary"
                            : "default"
                    }
                    sx={{ fontWeight: 600 }}
                  />
                  <Chip
                    label={`${manager.points} pts`}
                    size="small"
                    variant="outlined"
                    sx={{ fontWeight: 500 }}
                  />
                </Box>

                <Box sx={{ mt: 2 }}>
                  <Link
                    to={`/manager-profiles/${manager.name}`}
                    style={{ textDecoration: "none" }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 1,
                        p: 1,
                        borderRadius: 1,
                        bgcolor: "action.hover",
                        color: "primary.main",
                        transition: "all 0.2s",
                        "&:hover": { bgcolor: "primary.main", color: "white" },
                      }}
                    >
                      <PersonIcon sx={{ fontSize: 16 }} />
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        View Profile
                      </Typography>
                    </Box>
                  </Link>
                </Box>
              </CardContent>
            </Card>
          ))}
      </Box>
    </Box>
  );
};

export default ManagerProfiles;
