import React from "react";
import { Box, Typography, LinearProgress } from "@mui/material";

interface Item {
  label: string;
  value: number;
}

interface FinancialChartProps {
  items: Item[]; // already sorted or trimmed by caller
  maxValue?: number; // optional override for scaling
}

/**
 * Lightweight financial "bar chart" using MUI LinearProgress.
 * Keeps bundle small and avoids adding a chart lib.
 */
const FinancialChart: React.FC<FinancialChartProps> = ({ items, maxValue }) => {
  const computedMax = items.length ? Math.max(...items.map((i) => i.value)) : 0;
  const max = (maxValue ?? computedMax) || 1;

  // Compact number formatter (e.g. 1.3B, 780M) for cleaner display
  const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });

  return (
    <Box>
      {items.map((it) => {
        const pct = Math.round((it.value / max) * 100);
        const formatted = compact.format(it.value);
        return (
          <Box key={it.label} sx={{ mb: 1.5 }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 0.5 }}>
              <Typography variant="body2" sx={{ fontWeight: 600, color: "text.primary" }}>{it.label}</Typography>
              <Typography variant="body2" sx={{ fontWeight: 800, color: "#4f46e5" }}>
                {formatted}
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={pct}
              aria-label={`${it.label} ${formatted}`}
              sx={{
                height: 7,
                borderRadius: 4,
                bgcolor: '#f1f5f9',
                '& .MuiLinearProgress-bar': {
                  borderRadius: 4,
                  background: 'linear-gradient(90deg, #4f46e5 0%, #6366f1 100%)'
                }
              }}
            />
          </Box>
        );
      })}
      {items.length === 0 && <Typography variant="body2" sx={{ color: "#64748b" }}>No financial data available</Typography>}
    </Box>
  );
};

export default FinancialChart;

