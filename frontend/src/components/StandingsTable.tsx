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

import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";

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

const getRowBorder = (pos: number) => {
  if (pos === 1) return '4px solid #fbbf24';
  if (pos >= 2 && pos <= 4) return '4px solid #38bdf8';
  if (pos === 5) return '4px solid #34d399';
  if (pos >= 18) return '4px solid #f43f5e';
  return '4px solid transparent';
};

const getRowBg = (pos: number) => {
  if (pos === 1) return 'rgba(251, 191, 36, 0.04)';
  if (pos >= 2 && pos <= 4) return 'rgba(56, 189, 248, 0.02)';
  if (pos === 5) return 'rgba(52, 211, 153, 0.02)';
  if (pos >= 18) return 'rgba(244, 63, 94, 0.02)';
  return 'transparent';
};

/**
 * Presentational standings table. Keeps accessibility and keyboard focus in mind.
 */
const StandingsTable: React.FC<StandingsTableProps> = ({ rows }) => {
  return (
    <TableContainer component={Paper} sx={{ mb: 3, border: '1px solid rgba(255,255,255,0.05)', overflow: 'hidden' }}>
      <Table size="small" aria-label="league standings">
        <TableHead sx={{ bgcolor: 'rgba(255,255,255,0.02)' }}>
          <TableRow>
            <TableCell align="center" sx={{ fontWeight: 700, py: 1.5 }}>Pos</TableCell>
            <TableCell sx={{ fontWeight: 700 }}>Team</TableCell>
            <TableCell align="center" sx={{ fontWeight: 700 }}>Pld</TableCell>
            <TableCell align="center" sx={{ fontWeight: 700 }}>W</TableCell>
            <TableCell align="center" sx={{ fontWeight: 700 }}>D</TableCell>
            <TableCell align="center" sx={{ fontWeight: 700 }}>L</TableCell>
            <TableCell align="center" sx={{ fontWeight: 700 }}>GF</TableCell>
            <TableCell align="center" sx={{ fontWeight: 700 }}>GA</TableCell>
            <TableCell align="center" sx={{ fontWeight: 700 }}>GD</TableCell>
            <TableCell align="center" sx={{ fontWeight: 700 }}>Pts</TableCell>
            <TableCell align="center" sx={{ fontWeight: 700, pr: 2 }}>Form</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((r) => (
            <TableRow 
              key={`${r.id}-${r.position}`} 
              hover 
              tabIndex={0}
              sx={{
                borderLeft: getRowBorder(r.position),
                bgcolor: getRowBg(r.position),
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  bgcolor: 'rgba(56, 189, 248, 0.08) !important',
                  boxShadow: 'inset 0 0 10px rgba(56, 189, 248, 0.1)',
                }
              }}
            >
              <TableCell align="center" sx={{ py: 1.2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                  {r.position === 1 ? (
                    <EmojiEventsIcon sx={{ fontSize: 16, color: '#fbbf24', filter: 'drop-shadow(0 0 4px rgba(251,191,36,0.6))' }} />
                  ) : (
                    <Typography variant="body2" sx={{ fontWeight: r.position <= 5 || r.position >= 18 ? 700 : 500 }}>
                      {r.position}
                    </Typography>
                  )}
                </Box>
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
              <TableCell align="center" sx={{ color: r.gd > 0 ? 'success.light' : r.gd < 0 ? 'error.light' : 'text.secondary', fontWeight: 600 }}>
                {r.gd > 0 ? `+${r.gd}` : r.gd}
              </TableCell>
              <TableCell align="center">
                <Typography sx={{ fontWeight: 800, color: r.position === 1 ? '#fbbf24' : 'text.primary' }}>{r.points}</Typography>
              </TableCell>
              <TableCell align="center" sx={{ pr: 2 }}>
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
