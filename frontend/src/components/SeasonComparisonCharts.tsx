import React from "react";
import {
    Box,
    Card,
    CardContent,
    Typography,
    Chip,
    useTheme,
} from "@mui/material";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    BarChart,
    Bar,
    Legend,
} from "recharts";
import type { SeasonSummary, TeamPositionEntry } from "../services/api";

// Icons
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import SportsSoccerIcon from "@mui/icons-material/SportsSoccer";
import ShieldIcon from "@mui/icons-material/Shield";

// Glassmorphism card style
const glassCardSx = {
    borderRadius: "16px",
    transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important",
    "&:hover": {
        borderColor: "rgba(99, 102, 241, 0.25) !important",
        boxShadow: "0 12px 40px 0 rgba(99, 102, 241, 0.12) !important",
    }
};


const TEAM_COLORS = [
    "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444",
    "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#6366f1",
];

interface SeasonComparisonChartsProps {
    seasons: SeasonSummary[];
    teamPositionTrends: Record<string, TeamPositionEntry[]>;
    selectedTeams?: string[];
}

const SeasonComparisonCharts: React.FC<SeasonComparisonChartsProps> = ({
    seasons,
    teamPositionTrends,
    selectedTeams,
}) => {
    const theme = useTheme();

    // Sort seasons by year ascending for charts
    const sortedSeasons = [...seasons].sort((a, b) => a.season_year - b.season_year);

    // Get top 6 teams for position trend (most consistent top performers)
    const teamNames = Object.keys(teamPositionTrends);
    const topTeams = selectedTeams || teamNames
        .map(team => ({
            team,
            avgPosition: teamPositionTrends[team].reduce((sum, e) => sum + e.position, 0) /
                teamPositionTrends[team].length
        }))
        .sort((a, b) => a.avgPosition - b.avgPosition)
        .slice(0, 6)
        .map(t => t.team);

    // Build position trend data for line chart
    const positionTrendData = sortedSeasons.map(s => {
        const dataPoint: Record<string, any> = { season: s.season_year };
        topTeams.forEach(team => {
            const entry = teamPositionTrends[team]?.find(e => e.season === s.season_year);
            dataPoint[team] = entry?.position || null;
        });
        return dataPoint;
    });

    // Goals & Transfers comparison data
    const goalsTransfersData = sortedSeasons.map(s => ({
        season: s.season_year.toString(),
        goals: s.total_goals,
        transfers: s.transfers_completed,
        avgGoals: Number((s?.avg_goals_per_match ?? 0).toFixed(2)),
    }));

    return (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {/* Season Highlights Cards */}
            <Box
                sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" },
                    gap: 2,
                }}
            >
                {sortedSeasons.slice(-1).map(season => (
                    <React.Fragment key={season.season_year}>
                        {/* Champions Card */}
                        <Card sx={{ ...glassCardSx, p: 0 }}>
                            <CardContent sx={{ p: 2, textAlign: "center" }}>
                                <EmojiEventsIcon sx={{ fontSize: 32, color: "warning.main", mb: 1 }} />
                                <Typography variant="subtitle2" color="text.secondary">
                                    {season.season_year} Champions
                                </Typography>
                                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                                    {season.champions}
                                </Typography>
                                <Chip
                                    label={`${season.champion_points} pts`}
                                    size="small"
                                    sx={{ mt: 1, bgcolor: "warning.main", color: "warning.contrastText" }}
                                />
                            </CardContent>
                        </Card>

                        {/* Top Scorer Card */}
                        <Card sx={{ ...glassCardSx, p: 0 }}>
                            <CardContent sx={{ p: 2, textAlign: "center" }}>
                                <SportsSoccerIcon sx={{ fontSize: 32, color: "primary.main", mb: 1 }} />
                                <Typography variant="subtitle2" color="text.secondary">
                                    Top Scorer {season.season_year}
                                </Typography>
                                <Typography variant="h6" sx={{ fontWeight: 700 }} noWrap>
                                    {season.top_scorer?.name || "N/A"}
                                </Typography>
                                <Chip
                                    label={`${season.top_scorer?.goals || 0} goals`}
                                    size="small"
                                    color="primary"
                                    sx={{ mt: 1 }}
                                />
                            </CardContent>
                        </Card>

                        {/* Best Defense Card */}
                        <Card sx={{ ...glassCardSx, p: 0 }}>
                            <CardContent sx={{ p: 2, textAlign: "center" }}>
                                <ShieldIcon sx={{ fontSize: 32, color: "success.main", mb: 1 }} />
                                <Typography variant="subtitle2" color="text.secondary">
                                    Best Defense {season.season_year}
                                </Typography>
                                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                                    {season.best_defense?.team || "N/A"}
                                </Typography>
                                <Chip
                                    label={`${season.best_defense?.goals_conceded || 0} conceded`}
                                    size="small"
                                    color="success"
                                    sx={{ mt: 1 }}
                                />
                            </CardContent>
                        </Card>
                    </React.Fragment>
                ))}
            </Box>

            {/* Position Trends Chart */}
            <Card sx={glassCardSx}>
                <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                        League Position Trends
                    </Typography>
                    <Box sx={{ height: 350 }}>
                        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                            <LineChart data={positionTrendData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                <XAxis
                                    dataKey="season"
                                    tick={{ fill: "#9ca3af", fontSize: 12 }}
                                />
                                <YAxis
                                    reversed
                                    domain={[1, 20]}
                                    tick={{ fill: "#9ca3af" }}
                                    label={{ value: 'Position', angle: -90, position: 'insideLeft', fill: '#9ca3af' }}
                                />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: theme.palette.mode === "dark" ? "#1e293b" : "#ffffff",
                                        border: "none",
                                        borderRadius: 8,
                                    }}
                                    formatter={(value, name) => {
                                        const numericValue = typeof value === "number" ? value : Number(value ?? 0);
                                        return [`#${numericValue}`, String(name)];
                                    }}
                                />
                                <Legend />
                                {topTeams.map((team, idx) => (
                                    <Line
                                        key={team}
                                        type="monotone"
                                        dataKey={team}
                                        stroke={TEAM_COLORS[idx % TEAM_COLORS.length]}
                                        strokeWidth={2}
                                        dot={{ r: 4 }}
                                        connectNulls
                                    />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    </Box>
                </CardContent>
            </Card>

            {/* Goals & Transfers By Season */}
            <Card sx={glassCardSx}>
                <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                        Goals & Transfers by Season
                    </Typography>
                    <Box sx={{ height: 300 }}>
                        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                            <BarChart data={goalsTransfersData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                <XAxis
                                    dataKey="season"
                                    tick={{ fill: "#9ca3af", fontSize: 12 }}
                                />
                                <YAxis tick={{ fill: "#9ca3af" }} />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: theme.palette.mode === "dark" ? "#1e293b" : "#ffffff",
                                        border: "none",
                                        borderRadius: 8,
                                    }}
                                />
                                <Legend />
                                <Bar
                                    dataKey="goals"
                                    name="Total Goals"
                                    fill="#10b981"
                                    radius={[4, 4, 0, 0]}
                                />
                                <Bar
                                    dataKey="transfers"
                                    name="Transfers"
                                    fill="#3b82f6"
                                    radius={[4, 4, 0, 0]}
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </Box>
                </CardContent>
            </Card>
        </Box>
    );
};

export default SeasonComparisonCharts;
