import React, { useEffect, useState } from "react";
import { 
  Typography, 
  Box, 
  CircularProgress, 
  Alert, 
  Paper, 
  MenuItem, 
  Select, 
  FormControl 
} from "@mui/material";

import { getAvailableSeasons, getSeasonReportData } from "../services/api";
import type { SeasonReport } from "../services/api";
import StandingsTable from "../components/StandingsTable";
import type { StandingRow } from "../components/StandingsTable";
import FinancialChart from "../components/FinancialChart";

/**
 * LeagueOverview
 * - Produces an accessible, responsive standings table and a compact financial overview.
 * - Supports season selection filter.
 * - Normalizes backend season report data into the presentational components' expected shape.
 */
const LeagueOverview: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<SeasonReport | null>(null);
  const [seasonsList, setSeasonsList] = useState<number[]>([]);
  const [selectedSeason, setSelectedSeason] = useState<number | ''>('');

  useEffect(() => {
    const fetchSeasons = async () => {
      try {
        const seasons = await getAvailableSeasons();
        const sorted = seasons.sort((a, b) => b - a);
        setSeasonsList(sorted);
        if (sorted.length > 0) {
          setSelectedSeason(sorted[0]);
        } else {
          setLoading(false);
        }
      } catch (err: any) {
        setError("Failed to fetch available seasons.");
        setLoading(false);
      }
    };
    fetchSeasons();
  }, []);

  useEffect(() => {
    if (selectedSeason === '') return;
    const fetchReport = async () => {
      setLoading(true);
      try {
        const reportData = await getSeasonReportData(selectedSeason);
        setReport(reportData);
        setError(null);
      } catch (err: any) {
        setError(`Failed to fetch report for Season ${selectedSeason}`);
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [selectedSeason]);

  if (loading && seasonsList.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress size={40} />
        <Typography mt={2} color="text.secondary">Loading available seasons...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ bgcolor: 'rgba(244, 63, 94, 0.1)', color: '#f43f5e', border: '1px solid rgba(244, 63, 94, 0.2)' }}>
          {error}
        </Alert>
      </Box>
    );
  }

  if (seasonsList.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">No seasons have been simulated yet. Run a simulation from the Dashboard to see standings.</Alert>
      </Box>
    );
  }

  if (!report) return null;

  // Helper to safely read numeric stats from the stats object
  const getNum = (stats: Record<string, any>, ...keys: string[]) => {
    for (const k of keys) {
      if (stats && Object.prototype.hasOwnProperty.call(stats, k) && stats[k] !== null && stats[k] !== undefined) {
        const val = Number(stats[k]);
        return Number.isFinite(val) ? val : 0;
      }
    }
    return 0;
  };

  // Normalize standings rows using report.table and all_teams_details
  const teamDetailsByName = new Map<string, any>();
  report.all_teams_details?.forEach((t) => teamDetailsByName.set(t.name, t));

  const rows: StandingRow[] = report.table
    .map(([teamKey, stats], idx) => {
      const teamName = String(teamKey);
      const teamDetail = teamDetailsByName.get(teamName);
      const w = getNum(stats, "won", "w", "W", "wins");
      const d = getNum(stats, "drawn", "d", "D", "draws");
      const l = getNum(stats, "lost", "l", "L", "losses");
      const pld = getNum(stats, "played", "p", "pld") || (w + d + l);
      const gf = getNum(stats, "gf", "goals_for", "for");
      const ga = getNum(stats, "ga", "goals_against", "against");
      const gd = getNum(stats, "gd", "goal_difference") || (gf - ga);
      const points = getNum(stats, "points", "pts", "P");
      const form = stats?.form ?? stats?.last5 ?? stats?.recent_form ?? "";

      return {
        position: idx + 1,
        id: teamDetail?.id ?? teamName,
        name: teamDetail?.name ?? teamName,
        crestUrl: teamDetail?.crest ?? null,
        pld,
        w,
        d,
        l,
        gf,
        ga,
        gd,
        points,
        form,
      } as StandingRow;
    })
    .sort((a, b) => {
      if (b.points !== a.points) return b.points - a.points;
      if (b.gd !== a.gd) return b.gd - a.gd;
      return b.gf - a.gf;
    })
    .map((r, i) => ({ ...r, position: i + 1 }));

  // Financial metrics
  const teamDetails = report.all_teams_details ?? [];

  const metricFor = (fn: (t: any) => number) =>
    teamDetails
      .map((t) => ({ label: t.name, value: Number(fn(t)) || 0 }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6);

  const budgets = metricFor((t) => t.budget ?? t.financial_summary?.annual_revenue ?? 0);
  const profits = metricFor((t) => (t.financial_summary?.annual_revenue ?? 0) - (t.financial_summary?.annual_expenses ?? 0));
  const marketValues = metricFor((t) => t.team_season_stats?.market_value ?? t.team_season_stats?.squad_value ?? 0);
  const transferSpends = metricFor((t) => t.team_season_stats?.transfer_spend ?? t.team_season_stats?.spend ?? 0);
  const wageBills = metricFor((t) => t.team_season_stats?.wage_bill ?? t.team_season_stats?.wages ?? 0);

  const allMetrics: { key: string; label: string; items: { label: string; value: number }[] }[] = [
    { key: "budgets", label: "Budget / Cash Reserves", items: budgets },
    { key: "profits", label: "Net Profits (Season)", items: profits },
    { key: "marketValues", label: "Squad Market Value", items: marketValues },
    { key: "transferSpends", label: "Transfer Spending (Season)", items: transferSpends },
    { key: "wageBills", label: "Wage Bills", items: wageBills },
  ];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3.5 }}>
      {/* Header & Season Filter Pill Bar */}
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, fontFamily: 'Outfit, sans-serif', color: '#0f172a', letterSpacing: '-0.03em' }}>
            League Overview & Standings
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
            Comprehensive table, team stats, and financial health for Season {selectedSeason}
          </Typography>
        </Box>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <Select
            value={selectedSeason}
            onChange={(e) => setSelectedSeason(e.target.value as number)}
            sx={{
              borderRadius: 9999,
              bgcolor: '#F6DCAC',
              color: '#01204E',
              fontWeight: 800,
              boxShadow: '0 4px 12px rgba(1, 32, 78, 0.05)',
              border: '1px solid rgba(1, 32, 78, 0.15)',
              '& .MuiSelect-select': { py: 1, px: 2 }
            }}
          >
            {seasonsList.map((s) => (
              <MenuItem key={s} value={s} sx={{ fontWeight: 600 }}>
                Season {s}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Main content grid */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '3fr 2fr' }, gap: 4, alignItems: 'start' }}>
        {/* Standings Table Block */}
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>
            Season {report.season_year} Standings
          </Typography>
          {loading ? (
            <Box sx={{ py: 6, display: 'flex', justifyContent: 'center' }}>
              <CircularProgress size={30} />
            </Box>
          ) : (
            <StandingsTable rows={rows} />
          )}
        </Box>

        {/* Financial Charts Block */}
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>
            Financial Breakdown
          </Typography>
          
          {loading ? (
            <Box sx={{ py: 6, display: 'flex', justifyContent: 'center' }}>
              <CircularProgress size={30} />
            </Box>
          ) : (
            <Box sx={{ display: "grid", gap: 3 }}>
              {allMetrics.map((m) => (
                <Paper 
                  key={m.key} 
                  sx={{ 
                    p: 2.5,
                    bgcolor: '#F6DCAC',
                    border: '1px solid rgba(255, 255, 255, 0.5)',
                    borderRadius: 4,
                    boxShadow: '12px 18px 36px rgba(1, 32, 78, 0.08), inset 0 1px 2px rgba(255, 255, 255, 0.9)'
                  }}
                >
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#475569', mb: 2, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {m.label}
                  </Typography>
                  <FinancialChart items={m.items} />
                </Paper>

              ))}
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default LeagueOverview;
