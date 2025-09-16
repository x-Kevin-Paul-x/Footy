import React, { useEffect, useState } from "react";
import { Typography, Box, CircularProgress, Alert, Paper, Grid } from "@mui/material";
import { getAvailableSeasons, getSeasonReportData } from "../services/api";
import type { SeasonReport } from "../services/api";
import StandingsTable from "./StandingsTable";
import type { StandingRow } from "./StandingsTable";
import FinancialChart from "./FinancialChart";

/**
 * LeagueOverview
 * - Produces an accessible, responsive standings table and a compact financial overview.
 * - Normalizes backend season report data into the presentational components' expected shape.
 */
const LeagueOverview: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<SeasonReport | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const seasons = await getAvailableSeasons();
        const latestSeason = Math.max(...seasons);
        const reportData = await getSeasonReportData(latestSeason);
        setReport(reportData);
      } catch (err: any) {
        setError("Failed to fetch league overview data.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
        <Typography>Loading league overview...</Typography>
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
      const w = getNum(stats, "w", "W", "wins");
      const d = getNum(stats, "d", "D", "draws");
      const l = getNum(stats, "l", "L", "losses");
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
    // safety: sort by points desc then gd then gf
    .sort((a, b) => {
      if (b.points !== a.points) return b.points - a.points;
      if (b.gd !== a.gd) return b.gd - a.gd;
      return b.gf - a.gf;
    })
    // recompute positions after sort
    .map((r, i) => ({ ...r, position: i + 1 }));

  // Financial metrics: compute several metrics safely (budget, profit, market value, transfer spend, wage bill)
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
    { key: "budgets", label: "Budget / Cash", items: budgets },
    { key: "profits", label: "Net Profit (season)", items: profits },
    { key: "marketValues", label: "Market Value (squad)", items: marketValues },
    { key: "transferSpends", label: "Transfer Spend (season)", items: transferSpends },
    { key: "wageBills", label: "Wage Bill", items: wageBills },
  ];

  return (
    <Box sx={{ p: { xs: 1, md: 3 } }}>
      <Typography variant="h4" gutterBottom tabIndex={0}>
        League Overview — {report.season_year}
      </Typography>

      <Typography variant="h5" gutterBottom>
        Standings
      </Typography>
      <StandingsTable rows={rows} />

      <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
        Financial Overview
      </Typography>

      {/* Render each metric as a compact chart block */}
      <Box sx={{ display: "grid", gap: 2 }}>
        {allMetrics.map((m) => (
          <Paper key={m.key} sx={{ p: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              {m.label}
            </Typography>
            <FinancialChart items={m.items} />
          </Paper>
        ))}
      </Box>
    </Box>
  );
};

export default LeagueOverview;
