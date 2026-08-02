import React from "react";
import { Typography, Card, CardContent, Box, useTheme, Avatar } from "@mui/material";
import BarChartIcon from "@mui/icons-material/BarChart";

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

interface StatRowProps {
  label: string;
  homeVal: number;
  awayVal: number;
  isPercentage?: boolean;
}

const StatRow: React.FC<StatRowProps> = ({ label, homeVal, awayVal, isPercentage }) => {
  const theme = useTheme();
  const total = homeVal + awayVal || 1;
  const homePercent = Math.min(100, Math.max(0, (homeVal / total) * 100));

  return (
    <Box sx={{ mb: 2.5 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 0.8 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 800, color: "text.primary", minWidth: 60, textAlign: "left" }}>
          {isPercentage ? `${homeVal.toFixed(1)}%` : homeVal}
        </Typography>
        <Typography variant="caption" sx={{ fontWeight: 700, color: "text.secondary", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          {label}
        </Typography>
        <Typography variant="subtitle2" sx={{ fontWeight: 800, color: "text.primary", minWidth: 60, textAlign: "right" }}>
          {isPercentage ? `${awayVal.toFixed(1)}%` : awayVal}
        </Typography>
      </Box>

      {/* Dual Progress Bar */}
      <Box
        sx={{
          display: "flex",
          gap: "4px",
          height: 8,
          borderRadius: 9999,
          overflow: "hidden",
          bgcolor: theme.palette.mode === "dark" ? "rgba(255,255,255,0.06)" : "#f1f5f9",
          p: "1px"
        }}
      >
        {/* Home side bar */}
        <Box sx={{ flex: 1, display: "flex", justifyContent: "flex-end" }}>
          <Box
            sx={{
              width: `${homePercent}%`,
              height: "100%",
              background: "linear-gradient(90deg, #6366f1 0%, #4f46e5 100%)",
              borderRadius: "4px 0 0 4px",
              boxShadow: "0 2px 6px rgba(79, 70, 229, 0.3)"
            }}
          />
        </Box>
        {/* Away side bar */}
        <Box sx={{ flex: 1 }}>
          <Box
            sx={{
              width: `${100 - homePercent}%`,
              height: "100%",
              background: "linear-gradient(90deg, #f43f5e 0%, #e11d48 100%)",
              borderRadius: "0 4px 4px 0",
              boxShadow: "0 2px 6px rgba(244, 63, 94, 0.3)"
            }}
          />
        </Box>
      </Box>
    </Box>
  );
};

const MatchStats: React.FC<MatchStatsProps> = ({ stats, possession }) => {
  const theme = useTheme();

  const homePassAccuracy = stats.home.passes_attempted && stats.home.passes_attempted > 0
    ? (stats.home.passes_completed ?? 0) / stats.home.passes_attempted * 100
    : 0;

  const awayPassAccuracy = stats.away.passes_attempted && stats.away.passes_attempted > 0
    ? (stats.away.passes_completed ?? 0) / stats.away.passes_attempted * 100
    : 0;

  return (
    <Card
      sx={{
        bgcolor: "background.paper",
        border: 1,
        borderColor: "divider",
        borderRadius: "20px",
        boxShadow: theme.palette.mode === "dark" ? "0 10px 30px rgba(0,0,0,0.3)" : "0 10px 30px -5px rgba(0,0,0,0.04)"
      }}
    >
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 3 }}>
          <Avatar sx={{ bgcolor: "rgba(79, 70, 229, 0.1)", color: "#4f46e5", width: 40, height: 40 }}>
            <BarChartIcon />
          </Avatar>
          <Typography variant="h6" sx={{ fontWeight: 800, fontFamily: "Outfit, sans-serif" }}>
            Match Statistics Overview
          </Typography>
        </Box>
        
        <StatRow
          label="Possession"
          homeVal={possession?.home ?? 50}
          awayVal={possession?.away ?? 50}
          isPercentage
        />
        
        <StatRow
          label="Total Shots"
          homeVal={stats.home.total}
          awayVal={stats.away.total}
        />
        
        <StatRow
          label="Shots on Target"
          homeVal={stats.home.on_target}
          awayVal={stats.away.on_target}
        />
        
        <StatRow
          label="Pass Accuracy"
          homeVal={homePassAccuracy}
          awayVal={awayPassAccuracy}
          isPercentage
        />
        
        <StatRow
          label="Fouls"
          homeVal={stats.home.fouls ?? 0}
          awayVal={stats.away.fouls ?? 0}
        />
        
        <StatRow
          label="Corners"
          homeVal={stats.home.corners ?? 0}
          awayVal={stats.away.corners ?? 0}
        />
        
        <StatRow
          label="Offsides"
          homeVal={stats.home.offsides ?? 0}
          awayVal={stats.away.offsides ?? 0}
        />
      </CardContent>
    </Card>
  );
};

export default MatchStats;
