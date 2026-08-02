import React, { useState } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  useTheme,
  ToggleButton,
  ToggleButtonGroup,
  Avatar,
  Tooltip,
  Stack,
} from "@mui/material";
import GridViewIcon from "@mui/icons-material/GridView";
import ViewListIcon from "@mui/icons-material/ViewList";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";

interface PlayerPosition {
  name: string;
  position: string;
  x: number;
  y: number;
  number?: number;
  isInjured?: boolean;
  hasCard?: "yellow" | "red";
  rating?: number;
}

interface FormationViewerProps {
  teamName: string;
  formation: string;
  players: PlayerPosition[];
  teamColor?: string;
}

const pitchWidth = 600;
const pitchHeight = 420;

// SVG 3D Jersey Component with collar, sleeve stripes, and drop shadow
const JerseyIcon: React.FC<{ mainColor: string; accentColor?: string; number: number | string }> = ({
  mainColor,
  accentColor = "#FFFFFF",
  number,
}) => (
  <svg
    width="44"
    height="44"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ filter: "drop-shadow(0px 4px 8px rgba(0,0,0,0.5))" }}
  >
    {/* Main Shirt Body */}
    <path
      d="M4.5 6.5L8 3.5H16L19.5 6.5V10.5L17.5 9.8V20.5H6.5V9.8L4.5 10.5V6.5Z"
      fill={mainColor}
      stroke={accentColor}
      strokeWidth="1.2"
    />
    {/* V-neck Collar */}
    <path d="M9.5 3.5C9.5 5.5 14.5 5.5 14.5 3.5" stroke={accentColor} strokeWidth="1.2" fill="#0f172a" />
    {/* Sleeve Trim */}
    <path d="M4.5 9.5H6.5M17.5 9.5H19.5" stroke={accentColor} strokeWidth="1.2" />
    {/* Vertical Mesh Lines */}
    <path d="M10 20.5V14H14V20.5" stroke="rgba(255,255,255,0.2)" strokeWidth="0.5" />
    {/* Player Number */}
    <text
      x="50%"
      y="62%"
      dominantBaseline="middle"
      textAnchor="middle"
      fill="#FFFFFF"
      fontSize="7.5"
      fontWeight="900"
      fontFamily="'Outfit', 'Inter', sans-serif"
    >
      {number}
    </text>
  </svg>
);

const PositionBadgeColor = (pos: string) => {
  if (pos.startsWith("GK")) return "#a78bfa";
  if (pos.startsWith("D") || pos.includes("B")) return "#06b6d4";
  if (pos.startsWith("M") || pos.includes("M")) return "#10b981";
  if (pos.startsWith("F") || pos.startsWith("S") || pos.includes("T") || pos.includes("W")) return "#f43f5e";
  return "#8b5cf6";
};

const FormationViewer: React.FC<FormationViewerProps> = ({
  teamName,
  formation,
  players,
  teamColor = "#4f46e5",
}) => {
  const theme = useTheme();
  const [viewMode, setViewMode] = useState<"pitch" | "list">("pitch");

  return (
    <Card
      sx={{
        bgcolor: "background.paper",
        border: 1,
        borderColor: "divider",
        borderRadius: "24px",
        boxShadow: theme.palette.mode === "dark" ? "0 10px 30px rgba(0,0,0,0.3)" : "0 10px 30px -5px rgba(0,0,0,0.04)"
      }}
    >
      <CardContent sx={{ p: 3 }}>
        {/* Header Bar */}
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2.5, flexWrap: "wrap", gap: 1.5 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <Avatar
              sx={{
                width: 36,
                height: 36,
                background: `linear-gradient(135deg, ${teamColor} 0%, #1e1b4b 100%)`,
                color: "#fff",
                fontWeight: 900,
                fontSize: "0.8rem",
                boxShadow: "0 4px 10px rgba(0,0,0,0.2)"
              }}
            >
              {teamName ? teamName.substring(0, 3).toUpperCase() : "FC"}
            </Avatar>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 800, fontFamily: "Outfit, sans-serif", lineHeight: 1.2 }}>
                {teamName}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                Lineup & Tactical Setup
              </Typography>
            </Box>
          </Box>

          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip
              label={`System: ${formation}`}
              size="small"
              sx={{
                fontWeight: 800,
                bgcolor: "rgba(79, 70, 229, 0.12)",
                color: "#4f46e5",
                borderRadius: 9999,
                px: 1,
                fontSize: "0.75rem"
              }}
            />

            <ToggleButtonGroup
              value={viewMode}
              exclusive
              onChange={(_, next) => next && setViewMode(next)}
              size="small"
              sx={{ borderRadius: 9999, height: 32 }}
            >
              <ToggleButton value="pitch" sx={{ borderRadius: "9999px 0 0 9999px", px: 1.5 }}>
                <Tooltip title="Tactical 2D Pitch View"><GridViewIcon fontSize="small" /></Tooltip>
              </ToggleButton>
              <ToggleButton value="list" sx={{ borderRadius: "0 9999px 9999px 0", px: 1.5 }}>
                <Tooltip title="Squad Lineup List View"><ViewListIcon fontSize="small" /></Tooltip>
              </ToggleButton>
            </ToggleButtonGroup>
          </Box>
        </Box>

        {/* 2D HIGH-DEFINITION BROADCAST PITCH VIEW */}
        {viewMode === "pitch" ? (
          <Box
            sx={{
              position: "relative",
              width: "100%",
              maxWidth: pitchWidth,
              height: pitchHeight,
              background: `repeating-linear-gradient(
                90deg,
                #0f2e16,
                #0f2e16 35px,
                #13381a 35px,
                #13381a 70px
              )`,
              borderRadius: "20px",
              mx: "auto",
              boxShadow: "0 16px 40px rgba(0, 0, 0, 0.4), inset 0 0 50px rgba(0,0,0,0.5)",
              overflow: "hidden",
              border: "2px solid rgba(255, 255, 255, 0.12)",
            }}
          >
            {/* Corner Arcs */}
            <Box sx={{ position: "absolute", top: 0, left: 0, width: 24, height: 24, borderBottomRightRadius: 24, border: "1.5px solid rgba(255,255,255,0.25)" }} />
            <Box sx={{ position: "absolute", top: 0, right: 0, width: 24, height: 24, borderBottomLeftRadius: 24, border: "1.5px solid rgba(255,255,255,0.25)" }} />
            <Box sx={{ position: "absolute", bottom: 0, left: 0, width: 24, height: 24, borderTopRightRadius: 24, border: "1.5px solid rgba(255,255,255,0.25)" }} />
            <Box sx={{ position: "absolute", bottom: 0, right: 0, width: 24, height: 24, borderTopLeftRadius: 24, border: "1.5px solid rgba(255,255,255,0.25)" }} />

            {/* Touchlines Outer Boundary */}
            <Box
              sx={{
                position: "absolute",
                top: 16,
                bottom: 16,
                left: 16,
                right: 16,
                border: "1.5px solid rgba(255, 255, 255, 0.3)",
              }}
            />

            {/* Halfway Line */}
            <Box
              sx={{
                position: "absolute",
                top: 16,
                bottom: 16,
                left: "50%",
                width: "1.5px",
                bgcolor: "rgba(255, 255, 255, 0.3)",
                transform: "translateX(-50%)",
              }}
            />

            {/* Center Circle */}
            <Box
              sx={{
                position: "absolute",
                top: "50%",
                left: "50%",
                width: 96,
                height: 96,
                border: "1.5px solid rgba(255, 255, 255, 0.3)",
                borderRadius: "50%",
                transform: "translate(-50%, -50%)",
              }}
            />

            {/* Center Spot */}
            <Box
              sx={{
                position: "absolute",
                top: "50%",
                left: "50%",
                width: 6,
                height: 6,
                bgcolor: "rgba(255, 255, 255, 0.7)",
                borderRadius: "50%",
                transform: "translate(-50%, -50%)",
              }}
            />

            {/* Penalty Area Left */}
            <Box
              sx={{
                position: "absolute",
                top: "20%",
                bottom: "20%",
                left: 16,
                width: 80,
                border: "1.5px solid rgba(255, 255, 255, 0.3)",
                borderLeft: "none",
              }}
            />

            {/* Penalty Area Right */}
            <Box
              sx={{
                position: "absolute",
                top: "20%",
                bottom: "20%",
                right: 16,
                width: 80,
                border: "1.5px solid rgba(255, 255, 255, 0.3)",
                borderRight: "none",
              }}
            />

            {/* Goal Net Silhouette Left */}
            <Box
              sx={{
                position: "absolute",
                top: "38%",
                bottom: "38%",
                left: 4,
                width: 12,
                border: "1px dashed rgba(255,255,255,0.4)",
                bgcolor: "rgba(255,255,255,0.05)"
              }}
            />

            {/* Goal Net Silhouette Right */}
            <Box
              sx={{
                position: "absolute",
                top: "38%",
                bottom: "38%",
                right: 4,
                width: 12,
                border: "1px dashed rgba(255,255,255,0.4)",
                bgcolor: "rgba(255,255,255,0.05)"
              }}
            />

            {/* Players Mapping */}
            {players.map((p, idx) => {
              const xPos = Math.max(0.08, Math.min(p.x, 0.92)) * pitchWidth;
              const yPos = Math.max(0.08, Math.min(p.y, 0.92)) * pitchHeight;
              const posColor = PositionBadgeColor(p.position);
              const jerseyMainColor = p.position.startsWith("GK") ? "#f59e0b" : teamColor;

              return (
                <Tooltip
                  key={idx}
                  title={
                    <Box sx={{ p: 0.5, textAlign: "center" }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>{p.name}</Typography>
                      <Typography variant="caption" sx={{ color: posColor, fontWeight: 700 }}>
                        {p.position} • #{p.number ?? idx + 1}
                      </Typography>
                    </Box>
                  }
                  arrow
                  placement="top"
                >
                  <Box
                    sx={{
                      position: "absolute",
                      left: `${xPos - 22}px`,
                      top: `${yPos - 22}px`,
                      cursor: "pointer",
                      transition: "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
                      zIndex: 5,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      "&:hover": {
                        transform: "scale(1.25) translateY(-4px)",
                        zIndex: 20,
                      },
                    }}
                  >
                    {/* Jersey SVG */}
                    <JerseyIcon
                      mainColor={p.isInjured ? "#f43f5e" : jerseyMainColor}
                      number={p.number ?? idx + 1}
                    />

                    {/* Booking Card Indicator */}
                    {p.hasCard && (
                      <Box
                        sx={{
                          position: "absolute",
                          top: -2,
                          right: 2,
                          width: 10,
                          height: 14,
                          bgcolor: p.hasCard === "yellow" ? "#fbbf24" : "#f43f5e",
                          borderRadius: "1.5px",
                          boxShadow: "0 2px 6px rgba(0,0,0,0.6)",
                          border: "1px solid #fff",
                        }}
                      />
                    )}

                    {/* Injury Badge */}
                    {p.isInjured && (
                      <Box
                        sx={{
                          position: "absolute",
                          bottom: 14,
                          right: -2,
                          bgcolor: "#e11d48",
                          borderRadius: "50%",
                          width: 15,
                          height: 15,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          boxShadow: "0 2px 6px rgba(0,0,0,0.6)",
                          border: "1px solid #fff",
                        }}
                      >
                        <LocalHospitalIcon sx={{ fontSize: 10, color: "#fff" }} />
                      </Box>
                    )}

                    {/* Player Name Pill */}
                    <Box
                      sx={{
                        position: "absolute",
                        bottom: -18,
                        whiteSpace: "nowrap",
                        bgcolor: "rgba(11, 15, 25, 0.9)",
                        backdropFilter: "blur(6px)",
                        px: 1,
                        py: 0.2,
                        borderRadius: 9999,
                        border: "1px solid rgba(255, 255, 255, 0.15)",
                        boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
                        display: "flex",
                        alignItems: "center",
                        gap: 0.5
                      }}
                    >
                      <Box
                        sx={{
                          width: 6,
                          height: 6,
                          borderRadius: "50%",
                          bgcolor: posColor
                        }}
                      />
                      <Typography sx={{ fontSize: 10, fontWeight: 700, color: "#f8fafc" }}>
                        {p.name.split(" ").pop()}
                      </Typography>
                    </Box>
                  </Box>
                </Tooltip>
              );
            })}
          </Box>
        ) : (
          /* SQUAD LINEUP LIST VIEW */
          <Stack spacing={1.5} sx={{ mt: 1 }}>
            {players.map((p, idx) => {
              const posColor = PositionBadgeColor(p.position);
              return (
                <Box
                  key={idx}
                  sx={{
                    p: 1.5,
                    px: 2,
                    borderRadius: "14px",
                    bgcolor: theme.palette.mode === "dark" ? "rgba(255,255,255,0.03)" : "#f8fafc",
                    border: 1,
                    borderColor: "divider",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between"
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                    <Avatar
                      sx={{
                        width: 32,
                        height: 32,
                        bgcolor: posColor,
                        color: "#fff",
                        fontWeight: 900,
                        fontSize: "0.8rem"
                      }}
                    >
                      {p.number ?? idx + 1}
                    </Avatar>
                    <Box>
                      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                        {p.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                        Squad Member
                      </Typography>
                    </Box>
                  </Box>

                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    {p.isInjured && (
                      <Chip label="Injured" size="small" color="error" icon={<LocalHospitalIcon sx={{ fontSize: 12 }} />} />
                    )}
                    {p.hasCard && (
                      <Chip
                        label={p.hasCard === "yellow" ? "Yellow Card" : "Red Card"}
                        size="small"
                        sx={{ bgcolor: p.hasCard === "yellow" ? "#fbbf24" : "#f43f5e", color: "#000", fontWeight: 700 }}
                      />
                    )}
                    <Chip
                      label={p.position}
                      size="small"
                      sx={{
                        bgcolor: `${posColor}20`,
                        color: posColor,
                        fontWeight: 800,
                        borderRadius: 9999
                      }}
                    />
                  </Box>
                </Box>
              );
            })}
          </Stack>
        )}
      </CardContent>
    </Card>
  );
};

export default FormationViewer;
