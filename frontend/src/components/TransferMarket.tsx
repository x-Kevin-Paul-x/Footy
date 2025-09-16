import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tooltip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
} from "@mui/material";
import { getSeasonReportData, getAvailableSeasons } from "../services/api";
import type { SeasonReport } from "../services/api";

/**
 * TransferMarket - read-only view showing completed transfers by season.
 * - Lazy fetches season report when user selects a season (or defaults to latest).
 * - Shows compact currency formatting (GBP) for fees.
 * - Provides a small "Details" dialog to inspect a transfer's raw data.
 */

const TransferMarket: React.FC = () => {
  const [seasons, setSeasons] = useState<number[]>([]);
  const [selectedSeason, setSelectedSeason] = useState<number | null>(null);
  const [transfers, setTransfers] = useState<any[]>([]);
  const [loadingSeasons, setLoadingSeasons] = useState(true);
  const [loadingTransfers, setLoadingTransfers] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailIdx, setDetailIdx] = useState<number | null>(null);

  useEffect(() => {
    const loadSeasons = async () => {
      try {
        const s = await getAvailableSeasons();
        const sorted = (s ?? []).slice().sort((a: number, b: number) => b - a);
        setSeasons(sorted);
        if (sorted.length) setSelectedSeason(sorted[0]);
      } catch (err) {
        setError("Failed to load available seasons.");
      } finally {
        setLoadingSeasons(false);
      }
    };
    loadSeasons();
  }, []);

  useEffect(() => {
    if (!selectedSeason) return;
    let cancelled = false;
    const loadTransfers = async () => {
      setLoadingTransfers(true);
      try {
        const report: SeasonReport = await getSeasonReportData(selectedSeason);
        if (cancelled) return;
        const data = report.transfers?.all_completed_transfers ?? [];
        setTransfers(data);
      } catch (err) {
        if (!cancelled) setError("Failed to load transfer data for season.");
      } finally {
        if (!cancelled) setLoadingTransfers(false);
      }
    };
    loadTransfers();
    return () => {
      cancelled = true;
    };
  }, [selectedSeason]);

  const handleSeasonChange = (year: number) => {
    setSelectedSeason(year);
    setTransfers([]); // clear while loading
    setError(null);
  };

  const normalize = (t: any) => {
    const player = t.player || t.name || t.player_name || t.player_fullname || "Unknown";
    const from = t.from || t.seller || t.old_team || t.from_team || "—";
    const to = t.to || t.buyer || t.new_team || t.to_team || "—";
    const fee =
      t.fee !== undefined
        ? Number(t.fee)
        : t.price !== undefined
        ? Number(t.price)
        : t.amount !== undefined
        ? Number(t.amount)
        : null;
    const date = t.date || t.completed_at || t.transferred_on || t.timestamp || null;
    const type = t.type || t.transfer_type || t.move_type || "";
    return { player, from, to, fee, date, type, raw: t };
  };

  const currencyFormatter = new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    notation: "compact",
    maximumFractionDigits: 1,
  });

  return (
    <Box sx={{ p: 3, maxWidth: 1000, mx: "auto" }}>
      <Typography variant="h4" gutterBottom>
        Transfer Market — Completed Transfers
      </Typography>

      {loadingSeasons ? (
        <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
          <CircularProgress size={20} />
          <Typography>Loading seasons...</Typography>
        </Box>
      ) : (
        <FormControl sx={{ mb: 2, minWidth: 160 }} size="small">
          <InputLabel id="season-select-label">Season</InputLabel>
          <Select
            labelId="season-select-label"
            value={selectedSeason ?? ""}
            label="Season"
            onChange={(e) => handleSeasonChange(Number(e.target.value))}
          >
            {seasons.map((y) => (
              <MenuItem key={y} value={y}>
                {y}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loadingTransfers ? (
        <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
          <CircularProgress size={20} />
          <Typography>Loading transfers...</Typography>
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table aria-label="completed transfers">
            <TableHead>
              <TableRow>
                <TableCell>Player</TableCell>
                <TableCell>From</TableCell>
                <TableCell>To</TableCell>
                <TableCell>Fee</TableCell>
                <TableCell>Date</TableCell>
                <TableCell>Type</TableCell>
                <TableCell align="right">Details</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {transfers.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7}>
                    <Typography variant="body2" sx={{ py: 2 }}>
                      No completed transfers for this season.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
              {transfers.map((t, idx) => {
                const n = normalize(t);
                return (
                  <TableRow key={idx} hover>
                    <TableCell>
                      <Tooltip title={n.player}>
                        <span>{n.player}</span>
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      <Tooltip title={n.from}>
                        <span>{n.from}</span>
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      <Tooltip title={n.to}>
                        <span>{n.to}</span>
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      {n.fee !== null && Number.isFinite(n.fee)
                        ? currencyFormatter.format(n.fee)
                        : "-"}
                    </TableCell>
                    <TableCell>{n.date ? String(n.date) : "-"}</TableCell>
                    <TableCell>{n.type || "-"}</TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        onClick={() => {
                          setDetailIdx(idx);
                          setDetailOpen(true);
                        }}
                      >
                        Details
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={detailOpen} onClose={() => setDetailOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Transfer Details</DialogTitle>
        <DialogContent>
          <DialogContentText component="pre" sx={{ whiteSpace: "pre-wrap" }}>
            {detailIdx !== null && transfers[detailIdx]
              ? JSON.stringify(transfers[detailIdx], null, 2)
              : "No details available."}
          </DialogContentText>
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default TransferMarket;
