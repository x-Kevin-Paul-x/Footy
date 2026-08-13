import React, { useEffect, useState } from "react";
import {
  Alert,
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
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Slider,
  Tabs,
  Tab,
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
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RefreshIcon from "@mui/icons-material/Refresh";
import DownloadIcon from "@mui/icons-material/Download";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import {
  getMlReport,
  getMlReports,
  getMlModels,
  runMlEvaluation,
  type MlReport,
  type MlReportListItem,
  type MlModelItem,
} from "../services/api";

const glassCardSx = {
  borderRadius: "20px !important",
  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important",
  border: "1px solid rgba(255, 255, 255, 0.12)",
  "&:hover": {
    borderColor: "#6366f1 !important",
    boxShadow: "0 12px 32px 0 rgba(99, 102, 241, 0.18) !important",
  },
};

const POLICY_COLORS = [
  "#6366f1", // primary DQN (indigo)
  "#10b981", // green (youth/best)
  "#f59e0b", // amber
  "#ef4444", // rose
  "#8b5cf6", // purple
  "#06b6d4", // cyan
];

function formatPercent(value: number | undefined | null) {
  return `${((value ?? 0) * 100).toFixed(0)}%`;
}

function formatBudget(value: number | undefined | null) {
  return `£${((value ?? 0) / 1_000_000).toFixed(1)}M`;
}

const renderDeltaCell = (val: number | undefined | null, isPosition = false) => {
  const numVal = val ?? 0;
  if (numVal === 0)
    return (
      <Typography variant="body2" sx={{ color: "text.secondary", fontWeight: 700 }}>
        0.00
      </Typography>
    );
  const isPositive = isPosition ? numVal < 0 : numVal > 0;
  const color = isPositive ? "#10b981" : "#f43f5e";
  const sign = numVal > 0 ? "+" : "";
  return (
    <Chip
      size="small"
      label={`${sign}${numVal.toFixed(2)}`}
      sx={{
        bgcolor: `${color}18`,
        color,
        fontWeight: 800,
        fontSize: "0.75rem",
        height: 22,
        borderRadius: 1.5,
      }}
    />
  );
};

const renderDeltaPercentCell = (val: number | undefined | null) => {
  const numVal = val ?? 0;
  if (numVal === 0)
    return (
      <Typography variant="body2" sx={{ color: "text.secondary", fontWeight: 700 }}>
        0%
      </Typography>
    );
  const isPositive = numVal > 0;
  const color = isPositive ? "#10b981" : "#f43f5e";
  const sign = numVal > 0 ? "+" : "";
  return (
    <Chip
      size="small"
      label={`${sign}${(numVal * 100).toFixed(0)}%`}
      sx={{
        bgcolor: `${color}18`,
        color,
        fontWeight: 800,
        fontSize: "0.75rem",
        height: 22,
        borderRadius: 1.5,
      }}
    />
  );
};

const MlBenchmarks: React.FC = () => {
  const [reports, setReports] = useState<MlReportListItem[]>([]);
  const [selectedReportName, setSelectedReportName] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<MlReport | null>(null);
  const [isLoadingReports, setIsLoadingReports] = useState(true);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Active Tab: 0 = Overview & Radar, 1 = Action Decisions, 2 = Delta Matrix, 3 = Full Table
  const [activeTab, setActiveTab] = useState(0);

  // Evaluation Runner Modal state
  const [runnerOpen, setRunnerOpen] = useState(false);
  const [availableModels, setAvailableModels] = useState<MlModelItem[]>([]);
  const [selectedModelForEval, setSelectedModelForEval] = useState<string>("backend/src/ml/models/dqn_best.pt");
  const [evalEpisodes, setEvalEpisodes] = useState<number>(10);
  const [evalTeams, setEvalTeams] = useState<number>(6);
  const [evalSeasonLength, setEvalSeasonLength] = useState<number>(20);
  const [isRunningEval, setIsRunningEval] = useState(false);
  const [evalSuccessMsg, setEvalSuccessMsg] = useState<string | null>(null);

  const fetchReports = async (selectLatest = false) => {
    setIsLoadingReports(true);
    try {
      const nextReports = await getMlReports();
      setReports(nextReports);
      setError(null);

      if (nextReports.length > 0) {
        const targetReport = selectLatest ? nextReports[0].file_name : (selectedReportName || nextReports[0].file_name);
        setSelectedReportName(targetReport);
        setIsLoadingReport(true);
        const report = await getMlReport(targetReport);
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

  useEffect(() => {
    fetchReports();
    getMlModels()
      .then((models) => {
        setAvailableModels(models);
        if (models.length > 0) {
          setSelectedModelForEval(models[0].path);
        }
      })
      .catch(() => {});
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

  const handleRunEvaluation = async () => {
    setIsRunningEval(true);
    setEvalSuccessMsg(null);
    try {
      const report = await runMlEvaluation({
        models: [selectedModelForEval],
        episodes: evalEpisodes,
        teams: evalTeams,
        season_length: evalSeasonLength,
        fast_mode: true,
      });
      setEvalSuccessMsg(`Benchmark completed in ${report.runtime?.elapsed_seconds ?? 'a few'}s!`);
      await fetchReports(true);
      setRunnerOpen(false);
    } catch (err) {
      console.error("Benchmark failed", err);
      setError("Failed to run evaluation benchmark.");
    } finally {
      setIsRunningEval(false);
    }
  };

  const handleExportJSON = () => {
    if (!selectedReport) return;
    const blob = new Blob([JSON.stringify(selectedReport, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selectedReport.report_name || "benchmark"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const policyRows = selectedReport
    ? Object.values(selectedReport.policies).sort((a, b) => (b.avg_reward ?? 0) - (a.avg_reward ?? 0))
    : [];

  const rewardChartData = policyRows.map((policy) => ({
    policy: policy.policy_name,
    reward: Number((policy.avg_reward ?? 0).toFixed(2)),
    points: Number((policy.avg_points ?? 0).toFixed(1)),
    positionScore: Number((21 - (policy.avg_position ?? 21)).toFixed(1)),
    top4Rate: Number(((policy.top_4_rate ?? 0) * 100).toFixed(0)),
    titleRate: Number(((policy.title_rate ?? 0) * 100).toFixed(0)),
  }));

  const actionMixChartData = policyRows.map((policy) => ({
    policy: policy.policy_name,
    doNothing: Number((((policy.action_share?.do_nothing || 0)) * 100).toFixed(1)),
    scouting: Number((((policy.action_share?.invest_in_scouting || 0)) * 100).toFixed(1)),
    cheap: Number((((policy.action_share?.buy_cheap_or_youth || 0)) * 100).toFixed(1)),
    prime: Number((((policy.action_share?.buy_value_or_prime || 0)) * 100).toFixed(1)),
    star: Number((((policy.action_share?.buy_star || 0)) * 100).toFixed(1)),
  }));

  // Radar metrics normalization (scale 0-100)
  const radarData = [
    {
      metric: "Points",
      ...policyRows.reduce((acc, p) => ({ ...acc, [p.policy_name]: Math.min(100, (p.avg_points ?? 0) * 1.5) }), {}),
    },
    {
      metric: "Top 4 Rate",
      ...policyRows.reduce((acc, p) => ({ ...acc, [p.policy_name]: (p.top_4_rate ?? 0) * 100 }), {}),
    },
    {
      metric: "Title Rate",
      ...policyRows.reduce((acc, p) => ({ ...acc, [p.policy_name]: (p.title_rate ?? 0) * 100 }), {}),
    },
    {
      metric: "Reward",
      ...policyRows.reduce((acc, p) => ({ ...acc, [p.policy_name]: Math.max(0, Math.min(100, ((p.avg_reward ?? 0) + 20) * 2.5)) }), {}),
    },
    {
      metric: "Budget ROI",
      ...policyRows.reduce((acc, p) => ({ ...acc, [p.policy_name]: Math.min(100, Math.max(10, ((p.avg_budget ?? 0) / 100_000_000) * 100)) }), {}),
    },
  ];

  const comparisonRows = selectedReport
    ? Object.entries(selectedReport.comparisons || {}).map(([policyName, comparison]) => ({
        policyName,
        ...comparison,
      }))
    : [];

  return (
    <Box sx={{ p: { xs: 1, md: 0 } }}>
      {/* Header Banner */}
      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", md: "row" },
          alignItems: { xs: "flex-start", md: "center" },
          justifyContent: "space-between",
          gap: 2,
          mb: 3.5,
        }}
      >
        <Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <SmartToyIcon sx={{ fontSize: 32, color: "#028391" }} />
            <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: "-0.02em" }}>
              AI Reinforcement Learning Benchmarks
            </Typography>
          </Box>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
            Action-Masked Dueling Double-DQN Agent Performance & Policy Evaluation Matrix
          </Typography>
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => fetchReports()}
            sx={{ borderRadius: 2.5, textTransform: "none", fontWeight: 700 }}
          >
            Refresh
          </Button>

          {selectedReport && (
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={handleExportJSON}
              sx={{ borderRadius: 2.5, textTransform: "none", fontWeight: 700 }}
            >
              Export JSON
            </Button>
          )}

          <Button
            variant="contained"
            startIcon={<PlayArrowIcon />}
            onClick={() => setRunnerOpen(true)}
            sx={{
              borderRadius: 2.5,
              textTransform: "none",
              fontWeight: 800,
              bgcolor: "primary.main",
              "&:hover": { bgcolor: "var(--btn-hover)" },
            }}
          >
            Run New Benchmark
          </Button>
        </Box>
      </Box>

      {evalSuccessMsg && (
        <Alert severity="success" sx={{ mb: 3, borderRadius: 2 }} onClose={() => setEvalSuccessMsg(null)}>
          {evalSuccessMsg}
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {isLoadingReports ? (
        <Box sx={{ textAlign: "center", py: 8 }}>
          <CircularProgress size={48} />
          <Typography sx={{ mt: 2 }} color="text.secondary">
            Loading AI benchmark checkpoints and evaluation runs...
          </Typography>
        </Box>
      ) : reports.length === 0 ? (
        <Card sx={{ ...glassCardSx, p: 4, textAlign: "center" }}>
          <SmartToyIcon sx={{ fontSize: 64, color: "#028391", mb: 2 }} />
          <Typography variant="h6" sx={{ fontWeight: 800 }}>
            No Benchmark Reports Yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3, maxWidth: 500, mx: "auto" }}>
            Trigger an automated evaluation comparing your Action-Masked DQN against Random, Do Nothing, and Youth Focus heuristics.
          </Typography>
          <Button
            variant="contained"
            startIcon={<PlayArrowIcon />}
            onClick={() => setRunnerOpen(true)}
            sx={{ borderRadius: 2.5, fontWeight: 800, bgcolor: "#028391" }}
          >
            Run Initial Benchmark Now
          </Button>
        </Card>
      ) : (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", lg: "300px 1fr" },
            gap: 3,
            alignItems: "start",
          }}
        >
          {/* Left Column: Report List Sidebar */}
          <Card sx={glassCardSx}>
            <CardContent sx={{ p: 2.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 1.5, display: "flex", alignItems: "center", gap: 1 }}>
                Saved Reports ({reports.length})
              </Typography>
              <List sx={{ p: 0 }}>
                {reports.map((report) => {
                  const isSelected = selectedReportName === report.file_name;
                  return (
                    <ListItemButton
                      key={report.file_name}
                      selected={isSelected}
                      onClick={() => handleSelectReport(report.file_name)}
                      sx={{
                        mb: 1,
                        borderRadius: 2.5,
                        border: "1px solid",
                        borderColor: isSelected ? "primary.main" : "divider",
                        bgcolor: isSelected ? "action.selected" : "transparent",
                        transition: "all 0.2s",
                        "&:hover": {
                          borderColor: "primary.main",
                          transform: "translateX(4px)",
                        },
                      }}
                    >
                      <ListItemText
                        primary={report.file_name.replace(/\.json$/i, "")}
                        secondary={
                          <Box component="span" sx={{ display: "flex", gap: 0.8, mt: 0.5, alignItems: "center" }}>
                            <Chip
                              label={report.report_type}
                              size="small"
                              sx={{ fontSize: "0.65rem", height: 18, fontWeight: 700 }}
                            />
                            <Typography variant="caption" color="text.secondary">
                              {report.policy_count} policies
                            </Typography>
                          </Box>
                        }
                        primaryTypographyProps={{ fontWeight: 700, fontSize: "0.85rem", noWrap: true }}
                      />
                    </ListItemButton>
                  );
                })}
              </List>
            </CardContent>
          </Card>

          {/* Right Column: Detailed Analytics & Charts */}
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {isLoadingReport || !selectedReport ? (
              <Card sx={glassCardSx}>
                <CardContent sx={{ textAlign: "center", py: 8 }}>
                  <CircularProgress />
                  <Typography sx={{ mt: 2 }} color="text.secondary">
                    Loading benchmark metrics...
                  </Typography>
                </CardContent>
              </Card>
            ) : (
              <>
                {/* Top 4 Summary Cards */}
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", xl: "repeat(4, 1fr)" },
                    gap: 2,
                  }}
                >
                  <Card sx={glassCardSx}>
                    <CardContent sx={{ p: 2 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                        PRIMARY POLICY
                      </Typography>
                      <Typography variant="h6" noWrap sx={{ fontWeight: 900, color: "#6366f1", mt: 0.5 }}>
                        {selectedReport.summary.primary_policy}
                      </Typography>
                      <Chip label="DQN Agent" size="small" sx={{ mt: 1, height: 20, fontSize: "0.65rem", fontWeight: 700 }} />
                    </CardContent>
                  </Card>

                  <Card sx={glassCardSx}>
                    <CardContent sx={{ p: 2 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                        BEST REWARD
                      </Typography>
                      <Typography variant="h6" noWrap sx={{ fontWeight: 900, color: "#10b981", mt: 0.5 }}>
                        {selectedReport.summary.best_policy_by_reward}
                      </Typography>
                      <Chip
                        icon={<EmojiEventsIcon sx={{ fontSize: "14px !important" }} />}
                        label="Top ROI"
                        size="small"
                        sx={{ mt: 1, height: 20, fontSize: "0.65rem", fontWeight: 700, bgcolor: "rgba(16, 185, 129, 0.1)", color: "#10b981" }}
                      />
                    </CardContent>
                  </Card>

                  <Card sx={glassCardSx}>
                    <CardContent sx={{ p: 2 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                        BEST LEAGUE FINISH
                      </Typography>
                      <Typography variant="h6" noWrap sx={{ fontWeight: 900, color: "#F7A400", mt: 0.5 }}>
                        {selectedReport.summary.best_policy_by_position}
                      </Typography>
                      <Chip
                        icon={<TrendingUpIcon sx={{ fontSize: "14px !important" }} />}
                        label="Rank Champion"
                        size="small"
                        sx={{ mt: 1, height: 20, fontSize: "0.65rem", fontWeight: 700, bgcolor: "rgba(247, 164, 0, 0.1)", color: "#F7A400" }}
                      />
                    </CardContent>
                  </Card>

                  <Card sx={glassCardSx}>
                    <CardContent sx={{ p: 2 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                        TEST RUNTIME
                      </Typography>
                      <Typography variant="h6" sx={{ fontWeight: 900, mt: 0.5 }}>
                        {selectedReport.runtime?.elapsed_seconds ?? "—"}s
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                        {String(selectedReport.config.episodes || selectedReport.runtime?.episodes_per_policy || 10)} episodes / policy
                      </Typography>
                    </CardContent>
                  </Card>
                </Box>

                {/* Navigation Tabs */}
                <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
                  <Tabs value={activeTab} onChange={(_, val) => setActiveTab(val)}>
                    <Tab label="Performance & Charts" sx={{ fontWeight: 700, textTransform: "none" }} />
                    <Tab label="Action Decision Mix" sx={{ fontWeight: 700, textTransform: "none" }} />
                    <Tab label="Head-to-Head Comparison" sx={{ fontWeight: 700, textTransform: "none" }} />
                    <Tab label="Full Policy Table" sx={{ fontWeight: 700, textTransform: "none" }} />
                  </Tabs>
                </Box>

                {/* TAB 0: Performance & Radar */}
                {activeTab === 0 && (
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns: { xs: "1fr", lg: "1.2fr 0.8fr" },
                        gap: 3,
                      }}
                    >
                      {/* Bar Chart: Reward & Points */}
                      <Card sx={glassCardSx}>
                        <CardContent>
                          <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 2 }}>
                            Cumulative Reward & League Points
                          </Typography>
                          <Box sx={{ width: "100%", height: 320 }}>
                            <ResponsiveContainer>
                              <BarChart data={rewardChartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                                <XAxis dataKey="policy" tick={{ fontSize: 11, fontWeight: 600 }} />
                                <YAxis tick={{ fontSize: 11 }} />
                                <Tooltip
                                  contentStyle={{
                                    backgroundColor: "rgba(15, 23, 42, 0.95)",
                                    borderRadius: 12,
                                    border: "none",
                                    boxShadow: "0 8px 24px rgba(0,0,0,0.3)",
                                    color: "#fff",
                                  }}
                                />
                                <Legend />
                                <Bar dataKey="reward" name="Avg Reward" fill="#6366f1" radius={[6, 6, 0, 0]} />
                                <Bar dataKey="points" name="Avg Points" fill="#10b981" radius={[6, 6, 0, 0]} />
                              </BarChart>
                            </ResponsiveContainer>
                          </Box>
                        </CardContent>
                      </Card>

                      {/* Radar Chart: Multi-dimensional Policy Profile */}
                      <Card sx={glassCardSx}>
                        <CardContent>
                          <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 1 }}>
                            Multi-Dimensional Policy Radar
                          </Typography>
                          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 2 }}>
                            Comparison across Points, Title Rate, Top 4, and Budget Preservation
                          </Typography>
                          <Box sx={{ width: "100%", height: 300 }}>
                            <ResponsiveContainer>
                              <RadarChart data={radarData}>
                                <PolarGrid opacity={0.2} />
                                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fontWeight: 700 }} />
                                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9 }} />
                                {policyRows.map((policy, idx) => (
                                  <Radar
                                    key={policy.policy_name}
                                    name={policy.policy_name}
                                    dataKey={policy.policy_name}
                                    stroke={POLICY_COLORS[idx % POLICY_COLORS.length]}
                                    fill={POLICY_COLORS[idx % POLICY_COLORS.length]}
                                    fillOpacity={idx === 0 ? 0.35 : 0.1}
                                  />
                                ))}
                                <Legend wrapperStyle={{ fontSize: 11 }} />
                                <Tooltip />
                              </RadarChart>
                            </ResponsiveContainer>
                          </Box>
                        </CardContent>
                      </Card>
                    </Box>

                    {/* Win Rate & Top-4 Rate Cards */}
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" },
                        gap: 2,
                      }}
                    >
                      {policyRows.map((p, idx) => (
                        <Card
                          key={p.policy_name}
                          sx={{
                            ...glassCardSx,
                            borderTop: `4px solid ${POLICY_COLORS[idx % POLICY_COLORS.length]}`,
                          }}
                        >
                          <CardContent>
                            <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
                              {p.policy_name}
                            </Typography>
                            <Box sx={{ display: "flex", justifyContent: "space-between", mt: 1.5 }}>
                              <Box>
                                <Typography variant="caption" color="text.secondary">
                                  Top 4 Finish
                                </Typography>
                                <Typography variant="h6" sx={{ fontWeight: 800, color: "#10b981" }}>
                                  {formatPercent(p.top_4_rate)}
                                </Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary">
                                  Title Rate
                                </Typography>
                                <Typography variant="h6" sx={{ fontWeight: 800, color: "#F7A400" }}>
                                  {formatPercent(p.title_rate)}
                                </Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary">
                                  End Budget
                                </Typography>
                                <Typography variant="h6" sx={{ fontWeight: 800 }}>
                                  {formatBudget(p.avg_budget)}
                                </Typography>
                              </Box>
                            </Box>
                          </CardContent>
                        </Card>
                      ))}
                    </Box>
                  </Box>
                )}

                {/* TAB 1: Action Decision Distribution */}
                {activeTab === 1 && (
                  <Card sx={glassCardSx}>
                    <CardContent>
                      <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 1 }}>
                        Action Decision Allocation (% of Transfer Decisions)
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 3 }}>
                        Demonstrates how the Action-Masked DQN selectively buys value or youth vs. doing nothing when budget is restricted.
                      </Typography>

                      <Box sx={{ width: "100%", height: 360 }}>
                        <ResponsiveContainer>
                          <BarChart data={actionMixChartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                            <XAxis dataKey="policy" tick={{ fontSize: 11, fontWeight: 700 }} />
                            <YAxis unit="%" tick={{ fontSize: 11 }} />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: "rgba(15, 23, 42, 0.95)",
                                borderRadius: 12,
                                border: "none",
                                color: "#fff",
                              }}
                            />
                            <Legend />
                            <Bar dataKey="doNothing" name="Do Nothing" stackId="a" fill="#64748b" />
                            <Bar dataKey="scouting" name="Invest Scouting" stackId="a" fill="#028391" />
                            <Bar dataKey="cheap" name="Buy Youth / Cheap" stackId="a" fill="#10b981" />
                            <Bar dataKey="prime" name="Buy Prime / Value" stackId="a" fill="#3b82f6" />
                            <Bar dataKey="star" name="Buy Star Player" stackId="a" fill="#f59e0b" radius={[6, 6, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </Box>
                    </CardContent>
                  </Card>
                )}

                {/* TAB 2: Head-to-Head Comparison Matrix */}
                {activeTab === 2 && (
                  <Card sx={glassCardSx}>
                    <CardContent>
                      <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 1 }}>
                        Head-to-Head Delta vs. Baselines
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 2 }}>
                        Relative lift in points, league position, and championship odds compared to standard heuristics.
                      </Typography>

                      {comparisonRows.length === 0 ? (
                        <Alert severity="info">No direct delta comparisons recorded in this report.</Alert>
                      ) : (
                        <TableContainer>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell sx={{ fontWeight: 800 }}>Comparison Baseline</TableCell>
                                <TableCell sx={{ fontWeight: 800 }}>Reward Δ</TableCell>
                                <TableCell sx={{ fontWeight: 800 }}>Points Δ</TableCell>
                                <TableCell sx={{ fontWeight: 800 }}>Position Δ</TableCell>
                                <TableCell sx={{ fontWeight: 800 }}>Top 4 Rate Δ</TableCell>
                                <TableCell sx={{ fontWeight: 800 }}>Title Rate Δ</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {comparisonRows.map((row) => (
                                <TableRow key={row.policyName} hover>
                                  <TableCell sx={{ fontWeight: 700 }}>
                                    <Chip label={`vs ${row.policyName}`} size="small" sx={{ fontWeight: 700 }} />
                                  </TableCell>
                                  <TableCell>{renderDeltaCell(row.reward_delta)}</TableCell>
                                  <TableCell>{renderDeltaCell(row.points_delta)}</TableCell>
                                  <TableCell>{renderDeltaCell(row.position_delta, true)}</TableCell>
                                  <TableCell>{renderDeltaPercentCell(row.top_4_rate_delta)}</TableCell>
                                  <TableCell>{renderDeltaPercentCell(row.title_rate_delta)}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* TAB 3: Full Policy Table */}
                {activeTab === 3 && (
                  <Card sx={glassCardSx}>
                    <CardContent>
                      <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 2 }}>
                        Detailed Policy Metrics Table
                      </Typography>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell sx={{ fontWeight: 800 }}>Policy</TableCell>
                              <TableCell sx={{ fontWeight: 800 }}>Avg Reward</TableCell>
                              <TableCell sx={{ fontWeight: 800 }}>Avg Points</TableCell>
                              <TableCell sx={{ fontWeight: 800 }}>Avg Finish</TableCell>
                              <TableCell sx={{ fontWeight: 800 }}>Top 4 %</TableCell>
                              <TableCell sx={{ fontWeight: 800 }}>Title %</TableCell>
                              <TableCell sx={{ fontWeight: 800 }}>End Budget</TableCell>
                              <TableCell sx={{ fontWeight: 800 }}>Squad Size</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {policyRows.map((p) => (
                              <TableRow key={p.policy_name} hover>
                                <TableCell sx={{ fontWeight: 700 }}>{p.policy_name}</TableCell>
                                <TableCell sx={{ fontWeight: 700, color: "#6366f1" }}>
                                  {(p.avg_reward ?? 0).toFixed(2)}
                                </TableCell>
                                <TableCell sx={{ fontWeight: 700 }}>
                                  {(p.avg_points ?? 0).toFixed(1)}
                                </TableCell>
                                <TableCell>
                                  {(p.avg_position ?? 0).toFixed(1)}
                                </TableCell>
                                <TableCell>{formatPercent(p.top_4_rate)}</TableCell>
                                <TableCell>{formatPercent(p.title_rate)}</TableCell>
                                <TableCell>{formatBudget(p.avg_budget)}</TableCell>
                                <TableCell>{(p.avg_squad_size ?? 0).toFixed(1)}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </Box>
        </Box>
      )}

      {/* Benchmark Runner Modal */}
      <Dialog
        open={runnerOpen}
        onClose={() => !isRunningEval && setRunnerOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 3.5,
            p: 1.5,
            bgcolor: "background.paper",
            backgroundImage: "none",
          },
        }}
      >
        <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <PlayArrowIcon sx={{ color: "#028391" }} />
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 800, lineHeight: 1.2 }}>
              Run AI Policy Evaluation
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Benchmark Action-Masked DQN against heuristic manager policies
            </Typography>
          </Box>
        </DialogTitle>

        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2.5, pt: 2 }}>
          <FormControl fullWidth size="small">
            <InputLabel id="eval-model-label">Model Checkpoint</InputLabel>
            <Select
              labelId="eval-model-label"
              value={selectedModelForEval}
              label="Model Checkpoint"
              onChange={(e) => setSelectedModelForEval(e.target.value)}
            >
              {availableModels.length > 0 ? (
                availableModels.map((m) => (
                  <MenuItem key={m.path} value={m.path}>
                    {m.name} (PyTorch Checkpoint)
                  </MenuItem>
                ))
              ) : (
                <MenuItem value="backend/src/ml/models/dqn_best.pt">dqn_best.pt</MenuItem>
              )}
            </Select>
          </FormControl>

          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
              Evaluation Episodes ({evalEpisodes} seasons per policy)
            </Typography>
            <Slider
              value={evalEpisodes}
              min={2}
              max={30}
              step={2}
              onChange={(_, val) => setEvalEpisodes(val as number)}
              valueLabelDisplay="auto"
            />
          </Box>

          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}>
            <TextField
              size="small"
              type="number"
              label="Teams in League"
              value={evalTeams}
              onChange={(e) => setEvalTeams(Number(e.target.value))}
            />
            <TextField
              size="small"
              type="number"
              label="Matches / Season"
              value={evalSeasonLength}
              onChange={(e) => setEvalSeasonLength(Number(e.target.value))}
            />
          </Box>

          <Alert severity="info" sx={{ borderRadius: 2 }}>
            Evaluation runs in Turbo Mode and benchmarks against <strong>Random</strong>, <strong>Youth Focus</strong>, and <strong>Do Nothing</strong> baselines.
          </Alert>
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button disabled={isRunningEval} onClick={() => setRunnerOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="contained"
            disabled={isRunningEval}
            startIcon={isRunningEval ? <CircularProgress size={18} color="inherit" /> : <PlayArrowIcon />}
            onClick={handleRunEvaluation}
            sx={{ fontWeight: 800, bgcolor: "#028391" }}
          >
            {isRunningEval ? "Evaluating..." : "Start Benchmark"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MlBenchmarks;