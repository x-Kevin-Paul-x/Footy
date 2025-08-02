import React from "react";
import {
  Typography,
  Box,
  Paper,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from "@mui/material";
import { Grid } from "@mui/material"; // Explicitly import Grid

const StatisticsAnalytics: React.FC = () => (
  <Box sx={{ p: 3, display: "flex", flexDirection: "column", gap: 4 }}>
    <Typography variant="h4">Statistics & Analytics</Typography>

    <FormControl sx={{ minWidth: 200 }}>
      <InputLabel id="filter-label">Filter</InputLabel>
      <Select labelId="filter-label" label="Filter" defaultValue="all">
        <MenuItem value="all">All</MenuItem>
        <MenuItem value="goals">Goals</MenuItem>
        <MenuItem value="assists">Assists</MenuItem>
        <MenuItem value="appearances">Appearances</MenuItem>
      </Select>
    </FormControl>

    <Grid container spacing={3}>
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2, textAlign: "center" }}>
          <Typography variant="h6">Bar Chart</Typography>
          <Typography variant="body2" color="text.secondary">
            [Bar Chart Placeholder]
          </Typography>
        </Paper>
      </Grid>
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2, textAlign: "center" }}>
          <Typography variant="h6">Pie Chart</Typography>
          <Typography variant="body2" color="text.secondary">
            [Pie Chart Placeholder]
          </Typography>
        </Paper>
      </Grid>
    </Grid>
  </Box>
);

export default StatisticsAnalytics;
