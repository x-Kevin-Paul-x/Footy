import React from "react";
import {
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Paper,
  TableContainer,
  Typography,
  Box,
} from "@mui/material";
import TeamCell from "./TeamCell";
import FormChips from "./FormChips";

export interface StandingRow {
  position: number;
  id: string | number;
  name: string;
  crestUrl?: string | null;
  pld: number;
  w: number;
  d: number;
  l: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
  form?: string | string[];
}

interface StandingsTableProps {
  rows: StandingRow[];
}

/**
 * Presentational standings table. Keeps accessibility and keyboard focus in mind.
 */
const StandingsTable: React.FC<StandingsTableProps> = ({ rows }) => {
  return (
    <TableContainer component={Paper} sx={{ mb: 3 }}>
      <Table size="small" aria-label="league standings">
        <TableHead>
          <TableRow>
            <TableCell align="center">Pos</TableCell>
            <TableCell>Team</TableCell>
            <TableCell align="center">Pld</TableCell>
            <TableCell align="center">W</TableCell>
            <TableCell align="center">D</TableCell>
            <TableCell align="center">L</TableCell>
            <TableCell align="center">GF</TableCell>
            <TableCell align="center">GA</TableCell>
            <TableCell align="center">GD</TableCell>
            <TableCell align="center">Pts</TableCell>
            <TableCell align="center">Form</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={`${r.id}-${r.position}`} hover tabIndex={0}>
              <TableCell align="center">
                <Typography variant="body2">{r.position}</Typography>
              </TableCell>
              <TableCell>
                <TeamCell id={r.id} name={r.name} crestUrl={r.crestUrl} />
              </TableCell>
              <TableCell align="center">{r.pld}</TableCell>
              <TableCell align="center">{r.w}</TableCell>
              <TableCell align="center">{r.d}</TableCell>
              <TableCell align="center">{r.l}</TableCell>
              <TableCell align="center">{r.gf}</TableCell>
              <TableCell align="center">{r.ga}</TableCell>
              <TableCell align="center">{r.gd}</TableCell>
              <TableCell align="center">
                <Typography fontWeight={600}>{r.points}</Typography>
              </TableCell>
              <TableCell align="center">
                <FormChips form={r.form ?? ""} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default StandingsTable;
