// MatchStats.tsx
import React from "react";
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Grid,
} from "@mui/material";

interface MatchStatsProps {
  stats: {
    home: {
      total: number;
      on_target: number;
      passes_attempted?: number;
      passes_completed?: number;
      fouls?: number;
      corners?: number;
      offsides?: number;
    };
    away: {
      total: number;
      on_target: number;
      passes_attempted?: number;
      passes_completed?: number;
      fouls?: number;
      corners?: number;
      offsides?: number;
    };
  };
  possession: {
    home: number;
    away: number;
  };
}

const MatchStats: React.FC<MatchStatsProps> = ({ stats, possession }) => {
  return (
    <Paper elevation={3} sx={{ p: 2, mb: 2 }}>
      <Typography variant="h6" gutterBottom>
        Match Statistics
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Stat</TableCell>
                  <TableCell align="center">Home</TableCell>
                  <TableCell align="center">Away</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>Possession</TableCell>
                  <TableCell align="center">{possession.home.toFixed(1)}%</TableCell>
                  <TableCell align="center">{possession.away.toFixed(1)}%</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Total Shots</TableCell>
                  <TableCell align="center">{stats.home.total}</TableCell>
                  <TableCell align="center">{stats.away.total}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Shots on Target</TableCell>
                  <TableCell align="center">{stats.home.on_target}</TableCell>
                  <TableCell align="center">{stats.away.on_target}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Passes Attempted</TableCell>
                  <TableCell align="center">{stats.home.passes_attempted ?? 0}</TableCell>
                  <TableCell align="center">{stats.away.passes_attempted ?? 0}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Passes Completed</TableCell>
                  <TableCell align="center">{stats.home.passes_completed ?? 0}</TableCell>
                  <TableCell align="center">{stats.away.passes_completed ?? 0}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Fouls</TableCell>
                  <TableCell align="center">{stats.home.fouls ?? 0}</TableCell>
                  <TableCell align="center">{stats.away.fouls ?? 0}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Corners</TableCell>
                  <TableCell align="center">{stats.home.corners ?? 0}</TableCell>
                  <TableCell align="center">{stats.away.corners ?? 0}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Offsides</TableCell>
                  <TableCell align="center">{stats.home.offsides ?? 0}</TableCell>
                  <TableCell align="center">{stats.away.offsides ?? 0}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default MatchStats;
