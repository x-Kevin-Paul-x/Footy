import React, { useEffect, useState } from "react";
import {
  Alert,
  alpha,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  List,
  ListItemButton,
  ListItemText,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getMlReport,
  getMlReports,
  type MlReport,
  type MlReportListItem,
} from "../services/api";

const glassCardSx = {
  borderRadius: "20px !important",
  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important",
  "&:hover": {
    borderColor: "#6366f1 !important",
    boxShadow: "0 12px 32px 0 rgba(99, 102, 241, 0.15) !important",
  }
};


const POLICY_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

function formatPercent(value: number | undefined | null) {
  return `${((value ?? 0) * 100).toFixed(0)}%`;
}

function formatBudget(value: number | undefined | null) {
  return `GBP ${((value ?? 0) / 1_000_000).toFixed(1)}M`;
}

const renderDeltaCell = (val: number | undefined | null, isPosition = false) => {
  const numVal = val ?? 0;
  if (numVal === 0) return <Typography variant="body2" sx={{ color: "text.secondary", fontWeight: 600 }}>0.00</Typography>;
  const isPositive = isPosition ? numVal < 0 : numVal > 0;
  const color = isPositive ? "#10b981" : "#f43f5e";
  const sign = numVal > 0 ? "+" : "";
  return (
    <Typography variant="body2" sx={{ color, fontWeight: 600 }}>
      {sign}{numVal.toFixed(2)}
    </Typography>
  );
};

const renderDeltaPercentCell = (val: number | undefined | null) => {
  const numVal = val ?? 0;
  if (numVal === 0) return <Typography variant="body2" sx={{ color: "text.secondary", fontWeight: 600 }}>0%</Typography>;
  const isPositive = numVal > 0;
  const color = isPositive ? "#10b981" : "#f43f5e";
  const sign = numVal > 0 ? "+" : "";
  return (
    <Typography variant="body2" sx={{ color, fontWeight: 600 }}>
      {sign}{(numVal * 100).toFixed(0)}%
    </Typography>
  );
};

const MlBenchmarks: React.FC = () => {
  const [reports, setReports] = useState<MlReportListItem[]>([]);
  const [selectedReportName, setSelectedReportName] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<MlReport | null>(null);
  const [isLoadingReports, setIsLoadingReports] = useState(true);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadReports = async () => {
      setIsLoadingReports(true);
      try {
        const nextReports = await getMlReports();
        setReports(nextReports);
        setError(null);

        if (nextReports.length > 0) {
          const firstReport = nextReports[0].file_name;
          setSelectedReportName(firstReport);
          setIsLoadingReport(true);
          const report = await getMlReport(firstReport);
          setSelectedReport(report);
        }
      } catch (err) {
        console.error("Failed to load ML reports", err);
        setError("Failed to load AI benchmark reports.");
      } finally {
        setIsLoadingReports(false);
        setIsLoadingReport(false);
      }
    };

    loadReports();
  }, []);

  const handleSelectReport = async (reportName: string) => {
    setSelectedReportName(reportName);
    setIsLoadingReport(true);
    try {
      const report = await getMlReport(reportName);
      setSelectedReport(report);
      setError(null);
    } catch (err) {
      console.error("Failed to load selected ML report", err);
      setError("Failed to load the selected benchmark report.");
    } finally {
      setIsLoadingReport(false);
    }
  };

  const policyRows = selectedReport
    ? Object.values(selectedReport.policies).sort((left, right) => right.avg_reward - left.avg_reward)
    : [];

  const rewardChartData = policyRows.map((policy) => ({
    policy: policy.policy_name,
    reward: Number((policy.avg_reward ?? 0).toFixed(2)),
    points: Number((policy.avg_points ?? 0).toFixed(2)),
    positionScore: Number((21 - (policy.avg_position ?? 21)).toFixed(2)),
  }));

  const actionMixChartData = policyRows.map((policy) => ({
    policy: policy.policy_name,
    doNothing: Number((((policy.action_share?.do_nothing || 0)) * 100).toFixed(1)),
    scouting: Number((((policy.action_share?.invest_in_scouting || 0)) * 100).toFixed(1)),
    cheap: Number((((policy.action_share?.buy_cheap_or_youth || 0)) * 100).toFixed(1)),
    prime: Number((((policy.action_share?.buy_value_or_prime || 0)) * 100).toFixed(1)),
    star: Number((((policy.action_share?.buy_star || 0)) * 100).toFixed(1)),
  }));

  const comparisonRows = selectedReport
    ? Object.entries(selectedReport.comparisons).map(([policyName, comparison]) => ({
        policyName,
        ...comparison,
      }))
    : [];

  const runtimeWarnings = selectedReport?.runtime?.warnings
    ? Object.values(selectedReport.runtime.warnings)
    : [];

  return (
    <Box sx={{ p: { xs: 1, md: 0 } }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          AI Benchmarks
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Inspect RL evaluation artifacts directly in the app so checkpoint quality is easier to demo.
        </Typography>
      </Box>

      {error && (
        <Box sx={{ mb: 3 }}>
          <Alert severity="error">{error}</Alert>
        </Box>
      )}

      {isLoadingReports ? (
        <Box sx={{ textAlign: "center", py: 6 }}>
          <CircularProgress />
          <Typography sx={{ mt: 2 }} color="text.secondary">
            Loading benchmark reports...
          </Typography>
        </Box>
      ) : reports.length === 0 ? (
        <Alert severity="info">
          No benchmark reports found in ml/reports yet. Run train_rl.py eval or train_rl.py compare first.
        </Alert>
      ) : (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", xl: "320px 1fr" },
            gap: 3,
            alignItems: "start",
          }}
        >
          <Card sx={glassCardSx}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Saved Reports
              </Typography>
              <List sx={{ p: 0 }}>
                {reports.map((report) => (
                  <ListItemButton
                    key={report.file_name}
                    selected={selectedReportName === report.file_name}
                    onClick={() => handleSelectReport(report.file_name)}
                    sx={{
                      mb: 1,
                      borderRadius: 2,
                      border: (theme) => `1px solid ${alpha(theme.palette.divider, 0.08)}`,
                    }}
                  >
                    <ListItemText
                      primary={report.file_name.replace(/\.json$/i, "")}
                      secondary={`${report.report_type} • ${report.policy_count} policies`}
                      primaryTypographyProps={{ fontWeight: 600 }}
                    />
                  </ListItemButton>
                ))}
              </List>
            </CardContent>
          </Card>

          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {isLoadingReport || !selectedReport ? (
              <Card sx={glassCardSx}>
                <CardContent sx={{ textAlign: "center", py: 6 }}>
                  <CircularProgress />
                </CardContent>
              </Card>
            ) : (
              <>
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", md: "repeat(4, 1fr)" },
                    gap: 2,
                  }}
                >
                  <Card sx={glassCardSx}>
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Primary Policy
                      </Typography>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>
                        {selectedReport.summary.primary_policy}
                      </Typography>
                    </CardContent>
                  </Card>
                  <Card sx={glassCardSx}>
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Best Reward
                      </Typography>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>
                        {selectedReport.summary.best_policy_by_reward}
                      </Typography>
                    </CardContent>
                  </Card>
                  <Card sx={glassCardSx}>
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Best League Finish
                      </Typography>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>
                        {selectedReport.summary.best_policy_by_position}
                      </Typography>
                    </CardContent>
                  </Card>
                  <Card sx={glassCardSx}>
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Episodes
                      </Typography>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>
                        {String(selectedReport.config.episodes || "n/a")}
                      </Typography>
                    </CardContent>
                  </Card>
                </Box>

                {runtimeWarnings.length > 0 && (
                  <Alert severity="warning">
                    {runtimeWarnings.join(" ")}
                  </Alert>
                )}

                <Card sx={glassCardSx}>
                  <CardContent>
                    <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2, gap: 2, flexWrap: "wrap" }}>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        Report Context
                      </Typography>
                      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                        <Chip label={selectedReport.report_type} color="primary" variant="outlined" />
                        <Chip label={`Generated ${new Date(selectedReport.generated_at).toLocaleString()}`} variant="outlined" />
                        <Chip label={`Teams ${String(selectedReport.config.num_teams || "n/a")}`} variant="outlined" />
                        <Chip label={`Fast mode ${selectedReport.config.fast_mode ? "on" : "off"}`} variant="outlined" />
                      </Box>
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      Use this page to compare checkpoints by reward, league finish, and action profile without opening raw JSON files.
                    </Typography>
                  </CardContent>
                </Card>

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", xl: "1.2fr 1fr" },
                    gap: 3,
                  }}
                >
                  <Card sx={glassCardSx}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Policy Ranking Snapshot
                      </Typography>
                      <Box sx={{ height: 320 }}>
                        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                          <BarChart data={rewardChartData} margin={{ top: 16, right: 16, left: 0, bottom: 16 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#475569" opacity={0.2} />
                            <XAxis dataKey="policy" tick={{ fill: "#94a3b8" }} />
                            <YAxis tick={{ fill: "#94a3b8" }} />
                            <Tooltip />
                            <Legend />
                            <Bar dataKey="reward" name="Avg Reward" fill="#3b82f6" radius={[6, 6, 0, 0]} />
                            <Bar dataKey="points" name="Avg Points" fill="#10b981" radius={[6, 6, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </Box>
                    </CardContent>
                  </Card>

                  <Card sx={glassCardSx}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Action Mix
                      </Typography>
                      <Box sx={{ height: 320 }}>
                        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                          <BarChart data={actionMixChartData} layout="vertical" margin={{ top: 16, right: 16, left: 8, bottom: 16 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#475569" opacity={0.2} />
                            <XAxis type="number" tick={{ fill: "#94a3b8" }} unit="%" />
                            <YAxis type="category" dataKey="policy" tick={{ fill: "#94a3b8" }} width={80} />
                            <Tooltip formatter={(value) => `${value}%`} />
                            <Legend />
                            <Bar dataKey="doNothing" stackId="actions" name="Do nothing" fill="#64748b" />
                            <Bar dataKey="scouting" stackId="actions" name="Scouting" fill="#06b6d4" />
                            <Bar dataKey="cheap" stackId="actions" name="Cheap or youth" fill="#f59e0b" />
                            <Bar dataKey="prime" stackId="actions" name="Prime value" fill="#10b981" />
                            <Bar dataKey="star" stackId="actions" name="Star" fill="#ef4444" />
                          </BarChart>
                        </ResponsiveContainer>
                      </Box>
                    </CardContent>
                  </Card>
                </Box>

                <Card sx={glassCardSx}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Policy Metrics
                    </Typography>
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Policy</TableCell>
                            <TableCell align="right">Avg Reward</TableCell>
                            <TableCell align="right">Reward Std</TableCell>
                            <TableCell align="right">Avg Position</TableCell>
                            <TableCell align="right">Avg Points</TableCell>
                            <TableCell align="right">Top 4 Rate</TableCell>
                            <TableCell align="right">Title Rate</TableCell>
                            <TableCell align="right">Avg Budget</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {policyRows.map((policy, index) => (
                            <TableRow key={policy.policy_name}>
                              <TableCell>
                                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                  <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: POLICY_COLORS[index % POLICY_COLORS.length] }} />
                                  {policy.policy_name}
                                </Box>
                              </TableCell>
                              <TableCell align="right">{(policy.avg_reward ?? 0).toFixed(2)}</TableCell>
                              <TableCell align="right">{(policy.std_reward ?? 0).toFixed(2)}</TableCell>
                              <TableCell align="right">{(policy.avg_position ?? 0).toFixed(2)}</TableCell>
                              <TableCell align="right">{(policy.avg_points ?? 0).toFixed(2)}</TableCell>
                              <TableCell align="right">{formatPercent(policy.top_4_rate)}</TableCell>
                              <TableCell align="right">{formatPercent(policy.title_rate)}</TableCell>
                              <TableCell align="right">{formatBudget(policy.avg_budget)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </CardContent>
                </Card>

                <Card sx={glassCardSx}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Delta vs {selectedReport.summary.primary_policy}
                    </Typography>
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Policy</TableCell>
                            <TableCell align="right">Reward Delta</TableCell>
                            <TableCell align="right">Points Delta</TableCell>
                            <TableCell align="right">Position Delta</TableCell>
                            <TableCell align="right">Top 4 Delta</TableCell>
                            <TableCell align="right">Title Delta</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {comparisonRows.map((comparison) => (
                            <TableRow key={comparison.policyName}>
                              <TableCell sx={{ fontWeight: 600 }}>{comparison.policyName}</TableCell>
                              <TableCell align="right">{renderDeltaCell(comparison.reward_delta)}</TableCell>
                              <TableCell align="right">{renderDeltaCell(comparison.points_delta)}</TableCell>
                              <TableCell align="right">{renderDeltaCell(comparison.position_delta, true)}</TableCell>
                              <TableCell align="right">{renderDeltaPercentCell(comparison.top_4_rate_delta)}</TableCell>
                              <TableCell align="right">{renderDeltaPercentCell(comparison.title_rate_delta)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </CardContent>
                </Card>
              </>
            )}
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default MlBenchmarks;