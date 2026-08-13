import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  Button,
} from "@mui/material";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getSeasonReportData, getAvailableSeasons } from "../services/api";
import type { SeasonReport } from "../services/api";

// Icons
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import PriceCheckIcon from "@mui/icons-material/PriceCheck";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";

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
        const report: SeasonReport | null = await getSeasonReportData(selectedSeason);
        if (cancelled) return;
        const data = report?.transfers?.all_completed_transfers ?? [];
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
    const type = t.type || t.transfer_type || t.move_type || "Transfer";
    return { player, from, to, fee, date, type, raw: t };
  };

  const currencyFormatter = new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    notation: "compact",
    maximumFractionDigits: 1,
  });

  const normalizedTransfers = transfers.map(normalize);
  const totalSpent = normalizedTransfers.reduce((sum, t) => sum + (t.fee || 0), 0);
  const totalTransfers = normalizedTransfers.length;
  const avgFee = totalTransfers > 0 ? totalSpent / totalTransfers : 0;
  const biggestTransfer = normalizedTransfers.reduce(
    (max, t) => ((t.fee ?? 0) > (max.fee ?? 0) ? t : max),
    { player: "None", fee: 0, from: "—", to: "—", date: null, type: "Transfer", raw: null }
  );
  const biggestFee = biggestTransfer.fee ?? 0;

  const topTransfersChartData = normalizedTransfers
    .slice()
    .sort((a, b) => (b.fee ?? 0) - (a.fee ?? 0))
    .slice(0, 5)
    .map((t) => ({
      name: t.player.split(" ").pop(),
      fullName: t.player,
      fee: (t.fee ?? 0) / 1e6,
    }));

  return (
    <Box sx={{ p: { xs: 1, md: 0 } }}>
      <Box sx={{ mb: 4, display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, fontFamily: 'Outfit, sans-serif', mb: 1, color: "text.primary" }}>
            Transfer Market
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Completed transfer deals and season valuation statistics
          </Typography>
        </Box>
        
        {loadingSeasons ? (
          <CircularProgress size={24} />
        ) : (
          <FormControl sx={{ minWidth: 160 }} size="small">
            <InputLabel id="season-select-label" sx={{ color: "text.secondary" }}>Season</InputLabel>
            <Select
              labelId="season-select-label"
              value={selectedSeason ?? ""}
              label="Season"
              onChange={(e) => handleSeasonChange(Number(e.target.value))}
              sx={{ borderRadius: 9999, bgcolor: 'var(--bg-pill)', color: 'text.primary', border: '1px solid', borderColor: 'divider', fontWeight: 800, '& .MuiSelect-select': { color: 'text.primary' }, '& .MuiSvgIcon-root': { color: 'text.primary' } }}
            >
              {seasons.map((y) => (
                <MenuItem key={y} value={y} sx={{ fontWeight: 600 }}>
                  Season {y}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {loadingTransfers ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Grid container spacing={3}>
          {/* Left Column: Transfer Blocks List */}
          <Grid item xs={12} lg={7}>
            <Card className="finnova-card">
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 3, color: "text.primary" }}>
                  All Completed Deals ({totalTransfers})
                </Typography>
                
                {normalizedTransfers.length === 0 ? (
                  <Typography color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
                    No completed transfers for this season.
                  </Typography>
                ) : (
                  <Box sx={{ maxHeight: 600, overflowY: "auto", pr: 1 }}>
                    {normalizedTransfers.map((t, idx) => (
                      <Box key={idx} sx={{
                        p: 2,
                        mb: 2,
                        borderRadius: "14px",
                        bgcolor: 'var(--bg-subcard)',
                        border: '1px solid',
                        borderColor: 'divider',
                        transition: "all 0.2s ease-in-out",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        "&:hover": {
                          borderColor: "primary.main",
                          boxShadow: "0 4px 14px rgba(0,0,0,0.15)",
                          transform: "translateY(-2px)",
                          bgcolor: 'action.hover'
                        },
                      }}>
                        <Box sx={{ minWidth: 0, flex: 1 }}>
                          <Typography sx={{ fontWeight: 700, color: "text.primary" }} noWrap>
                            {t.player}
                          </Typography>

                          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.5, flexWrap: "wrap" }}>
                            <Typography variant="caption" color="text.secondary" noWrap>
                              {t.from}
                            </Typography>
                            <SwapHorizIcon sx={{ fontSize: 14, color: "primary.main" }} />
                            <Typography variant="caption" color="text.secondary" noWrap>
                              {t.to}
                            </Typography>
                          </Box>
                        </Box>
                        
                        <Box sx={{ textAlign: "right", ml: 2, display: "flex", alignItems: "center", gap: 2 }}>
                          <Box>
                            <Typography sx={{ fontWeight: 800, color: "primary.main" }}>
                              {t.fee !== null && Number.isFinite(t.fee)
                                ? currencyFormatter.format(t.fee)
                                : "Free"}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                              {t.type}
                            </Typography>
                          </Box>
                          <Button
                            size="small"
                            variant="outlined"
                            sx={{ borderRadius: "8px", textTransform: "none" }}
                            onClick={() => {
                              setDetailIdx(idx);
                              setDetailOpen(true);
                            }}
                          >
                            Details
                          </Button>
                        </Box>
                      </Box>
                    ))}
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Right Column: Statistics and Charts */}
          <Grid item xs={12} lg={5}>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
              {/* Stat Boxes */}
              <Card className="finnova-card">
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 3, color: "text.primary" }}>
                    Market Summary
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Box sx={{ p: 2, borderRadius: 2, bgcolor: "var(--bg-subcard)", border: "1px solid", borderColor: "divider" }}>
                        <PriceCheckIcon color="primary" sx={{ mb: 1 }} />
                        <Typography variant="subtitle2" color="text.secondary">Total Volume</Typography>
                        <Typography variant="h5" sx={{ fontWeight: 800, color: "text.primary" }}>
                          {currencyFormatter.format(totalSpent)}
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box sx={{ p: 2, borderRadius: 2, bgcolor: "var(--bg-subcard)", border: "1px solid", borderColor: "divider" }}>
                        <TrendingUpIcon color="success" sx={{ mb: 1 }} />
                        <Typography variant="subtitle2" color="text.secondary">Average Fee</Typography>
                        <Typography variant="h5" sx={{ fontWeight: 800, color: "text.primary" }}>
                          {currencyFormatter.format(avgFee)}
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={12}>
                      <Box sx={{ p: 2, borderRadius: 2, bgcolor: "var(--bg-subcard)", border: "1px solid", borderColor: "divider" }}>
                        <EmojiEventsIcon color="warning" sx={{ mb: 1 }} />
                        <Typography variant="subtitle2" color="text.secondary">Marquee Transfer</Typography>
                        <Typography variant="subtitle1" sx={{ fontWeight: 700, color: "text.primary", mt: 0.5 }}>
                          {biggestTransfer.player}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                          {biggestTransfer.from} → {biggestTransfer.to}
                        </Typography>
                        <Typography variant="h6" sx={{ fontWeight: 800, color: "warning.main", mt: 0.5 }}>
                          {biggestFee > 0 ? currencyFormatter.format(biggestFee) : "—"}
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* Chart */}
              {topTransfersChartData.length > 0 && (
                <Card className="finnova-card">
                  <CardContent sx={{ p: 3 }}>
                    <Typography variant="h6" sx={{ fontWeight: 700, mb: 3, color: "text.primary" }}>
                      Top 5 Transfer Fees (GBP Millions)
                    </Typography>
                    <Box sx={{ height: 260 }}>
                      <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                        <BarChart data={topTransfersChartData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                          <XAxis dataKey="name" tick={{ fill: "currentColor", fontSize: 11 }} />
                          <YAxis tick={{ fill: "currentColor" }} unit="M" />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: "var(--bg-cards)",
                              border: "1px solid var(--card-border)",
                              borderRadius: 12,
                              color: "var(--text-heading)"
                            }}
                            formatter={(value: any, _name: any, props: any) => [
                              `£${Number(value).toFixed(1)}M`,
                              props.payload.fullName,
                            ]}
                          />
                          <Bar
                            dataKey="fee"
                            fill="var(--btn-main)"
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </Box>
                  </CardContent>
                </Card>
              )}
            </Box>
          </Grid>
        </Grid>
      )}

      <Dialog open={detailOpen} onClose={() => setDetailOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ bgcolor: "background.paper", color: "text.primary", fontWeight: 700 }}>Transfer Record Details</DialogTitle>
        <DialogContent sx={{ bgcolor: "background.paper" }}>
          <DialogContentText component="pre" sx={{ whiteSpace: "pre-wrap", color: "text.secondary", p: 2, bgcolor: "var(--bg-subcard)", border: "1px solid", borderColor: "divider", borderRadius: "8px" }}>
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
