import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Typography,
  Box,
  Card,
  CardContent,
  Avatar,
  CircularProgress,
  Alert,
  Chip,
  Tabs,
  Tab,
  useTheme,
} from "@mui/material";
import { useSimulationStore } from "../store/simulationStore";
import type { Player } from "../services/api";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from "recharts";

// Icons
import SportsSoccerIcon from "@mui/icons-material/SportsSoccer";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import PersonIcon from "@mui/icons-material/Person";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";
import PsychologyIcon from "@mui/icons-material/Psychology";
import FlashOnIcon from "@mui/icons-material/FlashOn";
import ShieldIcon from "@mui/icons-material/Shield";
import WorkspacePremiumIcon from "@mui/icons-material/WorkspacePremium";

// Club Palette Map for realistic team avatars
const CLUB_PALETTES: { [key: string]: { code: string; bg: string } } = {
  "arsenal": { code: "ARS", bg: "linear-gradient(135deg, #ef4444 0%, #991b1b 100%)" },
  "chelsea": { code: "CHE", bg: "linear-gradient(135deg, #2563eb 0%, #1e40af 100%)" },
  "manchester city": { code: "MCI", bg: "linear-gradient(135deg, #38bdf8 0%, #0284c7 100%)" },
  "man city": { code: "MCI", bg: "linear-gradient(135deg, #38bdf8 0%, #0284c7 100%)" },
  "manchester united": { code: "MUN", bg: "linear-gradient(135deg, #dc2626 0%, #7f1d1d 100%)" },
  "man united": { code: "MUN", bg: "linear-gradient(135deg, #dc2626 0%, #7f1d1d 100%)" },
  "liverpool": { code: "LIV", bg: "linear-gradient(135deg, #e11d48 0%, #9f1239 100%)" },
  "tottenham": { code: "TOT", bg: "linear-gradient(135deg, #475569 0%, #0f172a 100%)" },
  "spurs": { code: "TOT", bg: "linear-gradient(135deg, #475569 0%, #0f172a 100%)" },
  "brighton": { code: "BHA", bg: "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)" },
  "aston villa": { code: "AVL", bg: "linear-gradient(135deg, #7c3aed 0%, #4c1d95 100%)" },
  "newcastle": { code: "NEW", bg: "linear-gradient(135deg, #334155 0%, #0f172a 100%)" },
  "wolves": { code: "WOL", bg: "linear-gradient(135deg, #f59e0b 0%, #b45309 100%)" },
  "west ham": { code: "WHU", bg: "linear-gradient(135deg, #9333ea 0%, #581c87 100%)" },
  "everton": { code: "EVE", bg: "linear-gradient(135deg, #1d4ed8 0%, #1e3a8a 100%)" },
  "fulham": { code: "FUL", bg: "linear-gradient(135deg, #64748b 0%, #1e293b 100%)" },
  "brentford": { code: "BRE", bg: "linear-gradient(135deg, #ea580c 0%, #9a3412 100%)" },
  "crystal palace": { code: "CRY", bg: "linear-gradient(135deg, #2563eb 0%, #dc2626 100%)" },
  "nottingham forest": { code: "NFO", bg: "linear-gradient(135deg, #f43f5e 0%, #881337 100%)" },
  "burnley": { code: "BUR", bg: "linear-gradient(135deg, #881337 0%, #4c0519 100%)" },
  "sheffield united": { code: "SHU", bg: "linear-gradient(135deg, #ef4444 0%, #450a0a 100%)" },
  "luton": { code: "LUT", bg: "linear-gradient(135deg, #f97316 0%, #7c2d12 100%)" },
};

function getClubMeta(teamName: string) {
  const clean = (teamName || "").toLowerCase().trim();
  if (CLUB_PALETTES[clean]) return CLUB_PALETTES[clean];
  const code = teamName ? teamName.substring(0, 3).toUpperCase() : "FC";
  const bg = "linear-gradient(135deg, #028391 0%, #01204E 100%)";
  return { code, bg };
}

// FM Rating Badge Style Helper
const getFMRatingBadge = (value: number, isDark = false) => {
  const val = Math.round(value);
  if (val >= 75) return { bg: "#10b981", color: "#ffffff" }; // Excellent (Green)
  if (val >= 60) return { bg: isDark ? "#F85525" : "#FAA968", color: isDark ? "#ffffff" : "#01204E" }; // Good
  if (val >= 45) return { bg: "#028391", color: "#ffffff" }; // Average (Teal)
  return { bg: isDark ? "rgba(143, 227, 236, 0.15)" : "rgba(1, 32, 78, 0.12)", color: isDark ? "#8FE3EC" : "#01204E" }; // Low
};

// Deterministic generator for full FM attribute profiles
function getFMAttrValue(player: Player, attrKey: string, rawAttrs: { [key: string]: number }, overall: number): number {
  if (rawAttrs[attrKey] !== undefined && rawAttrs[attrKey] !== null) {
    return Math.round(rawAttrs[attrKey]);
  }

  const pos = (player.position || "").toUpperCase();
  let base = overall || 70;

  // Position bias adjustment
  if (pos.includes("CB") || pos.includes("RB") || pos.includes("LB") || pos.includes("D")) {
    if (["tackling", "marking", "heading", "positioning", "strength", "bravery", "jumping_reach", "sliding_tackle", "standing_tackle"].includes(attrKey)) base += 8;
    if (["finishing", "flair", "dribbling", "penalties"].includes(attrKey)) base -= 15;
  } else if (pos.includes("FW") || pos.includes("ST") || pos.includes("RW") || pos.includes("LW") || pos.includes("F")) {
    if (["finishing", "dribbling", "acceleration", "pace", "off_the_ball", "composure", "first_touch"].includes(attrKey)) base += 10;
    if (["tackling", "marking", "sliding_tackle", "diving"].includes(attrKey)) base -= 20;
  } else if (pos.includes("CM") || pos.includes("CDM") || pos.includes("CAM") || pos.includes("M")) {
    if (["passing", "vision", "stamina", "work_rate", "technique", "decisions", "ball_control"].includes(attrKey)) base += 8;
  } else if (pos.includes("GK")) {
    if (["diving", "handling", "kicking", "reflexes", "positioning"].includes(attrKey)) base += 14;
    if (["dribbling", "finishing", "crossing", "tackling"].includes(attrKey)) base -= 35;
  }

  // Deterministic seed hash (-5 to +5)
  let hash = 0;
  const seedStr = `${player.name}-${attrKey}`;
  for (let i = 0; i < seedStr.length; i++) {
    hash = (hash << 5) - hash + seedStr.charCodeAt(i);
    hash |= 0;
  }
  const variance = (Math.abs(hash) % 11) - 5;

  return Math.min(99, Math.max(18, Math.round(base + variance)));
}

const getOverallRating = (attributes: Player["attributes"]): number => {
  if (!attributes) return 0;
  let total = 0;
  let count = 0;
  for (const attrType in attributes) {
    if (attributes[attrType]) {
      for (const subAttr in attributes[attrType]) {
        total += attributes[attrType][subAttr] || 0;
        count += 1;
      }
    }
  }
  return count > 0 ? Math.round(total / count) : 0;
};

const PlayerDetail: React.FC = () => {
  const { playerName } = useParams<{ playerName: string }>();
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const { currentReport, isLoading, error, selectedSeason, fetchAvailableSeasons } = useSimulationStore();
  const [player, setPlayer] = useState<Player | null>(null);
  const [tab, setTab] = useState(0);

  useEffect(() => {
    if (!selectedSeason) {
      fetchAvailableSeasons();
    }
  }, [selectedSeason, fetchAvailableSeasons]);

  useEffect(() => {
    if (currentReport && playerName) {
      const decodedName = decodeURIComponent(playerName).toLowerCase();
      let found: Player | null = null;
      for (const team of currentReport.all_teams_details) {
        const p = team.players.find((pl) => pl.name.toLowerCase() === decodedName);
        if (p) {
          found = p;
          break;
        }
      }
      setPlayer(found);
    }
  }, [currentReport, playerName]);

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh" }}>
        <CircularProgress size={44} color="primary" />
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

  if (!player) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography variant="h6" sx={{ fontWeight: 800, color: "text.primary" }}>
          Player Not Found
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 3 }}>
          Could not find player details for "{playerName}".
        </Typography>
        <Chip
          component={Link}
          to="/player-profiles"
          icon={<ArrowBackIcon sx={{ color: "inherit !important", fontSize: 14 }} />}
          label="Back to Player Database"
          clickable
          sx={{ bgcolor: "var(--btn-main)", color: "#ffffff", fontWeight: 800 }}
        />
      </Box>
    );
  }

  const overall = getOverallRating(player.attributes);
  const clubMeta = getClubMeta(player.team);

  // Flatten raw attributes
  const rawAttrs: { [key: string]: number } = {};
  if (player.attributes) {
    for (const cat in player.attributes) {
      if (player.attributes[cat]) {
        for (const k in player.attributes[cat]) {
          rawAttrs[k.toLowerCase()] = player.attributes[cat][k];
        }
      }
    }
  }

  // Define FM Attributes
  const technicalAttrs = [
    { key: "corners", name: "Corners", val: getFMAttrValue(player, "corners", rawAttrs, overall) },
    { key: "crossing", name: "Crossing", val: getFMAttrValue(player, "crossing", rawAttrs, overall) },
    { key: "dribbling", name: "Dribbling", val: getFMAttrValue(player, "dribbling", rawAttrs, overall) },
    { key: "finishing", name: "Finishing", val: getFMAttrValue(player, "finishing", rawAttrs, overall) },
    { key: "first_touch", name: "First Touch", val: getFMAttrValue(player, "first_touch", rawAttrs, overall) },
    { key: "free_kicks", name: "Free Kicks", val: getFMAttrValue(player, "free_kicks", rawAttrs, overall) },
    { key: "heading", name: "Heading", val: getFMAttrValue(player, "heading", rawAttrs, overall) },
    { key: "long_shots", name: "Long Shots", val: getFMAttrValue(player, "long_shots", rawAttrs, overall) },
    { key: "marking", name: "Marking", val: getFMAttrValue(player, "marking", rawAttrs, overall) },
    { key: "passing", name: "Passing", val: getFMAttrValue(player, "passing", rawAttrs, overall) },
    { key: "penalties", name: "Penalties", val: getFMAttrValue(player, "penalties", rawAttrs, overall) },
    { key: "tackling", name: "Tackling", val: getFMAttrValue(player, "tackling", rawAttrs, overall) },
    { key: "technique", name: "Technique", val: getFMAttrValue(player, "technique", rawAttrs, overall) },
  ];

  const mentalAttrs = [
    { key: "aggression", name: "Aggression", val: getFMAttrValue(player, "aggression", rawAttrs, overall) },
    { key: "anticipation", name: "Anticipation", val: getFMAttrValue(player, "anticipation", rawAttrs, overall) },
    { key: "bravery", name: "Bravery", val: getFMAttrValue(player, "bravery", rawAttrs, overall) },
    { key: "composure", name: "Composure", val: getFMAttrValue(player, "composure", rawAttrs, overall) },
    { key: "concentration", name: "Concentration", val: getFMAttrValue(player, "concentration", rawAttrs, overall) },
    { key: "decisions", name: "Decisions", val: getFMAttrValue(player, "decisions", rawAttrs, overall) },
    { key: "determination", name: "Determination", val: getFMAttrValue(player, "determination", rawAttrs, overall) },
    { key: "flair", name: "Flair", val: getFMAttrValue(player, "flair", rawAttrs, overall) },
    { key: "leadership", name: "Leadership", val: getFMAttrValue(player, "leadership", rawAttrs, overall) },
    { key: "off_the_ball", name: "Off The Ball", val: getFMAttrValue(player, "off_the_ball", rawAttrs, overall) },
    { key: "positioning", name: "Positioning", val: getFMAttrValue(player, "positioning", rawAttrs, overall) },
    { key: "teamwork", name: "Teamwork", val: getFMAttrValue(player, "teamwork", rawAttrs, overall) },
    { key: "vision", name: "Vision", val: getFMAttrValue(player, "vision", rawAttrs, overall) },
    { key: "work_rate", name: "Work Rate", val: getFMAttrValue(player, "work_rate", rawAttrs, overall) },
  ];

  const physicalGkAttrs = [
    { key: "acceleration", name: "Acceleration", val: getFMAttrValue(player, "acceleration", rawAttrs, overall) },
    { key: "agility", name: "Agility", val: getFMAttrValue(player, "agility", rawAttrs, overall) },
    { key: "balance", name: "Balance", val: getFMAttrValue(player, "balance", rawAttrs, overall) },
    { key: "jumping_reach", name: "Jumping Reach", val: getFMAttrValue(player, "jumping_reach", rawAttrs, overall) },
    { key: "natural_fitness", name: "Natural Fitness", val: getFMAttrValue(player, "natural_fitness", rawAttrs, overall) },
    { key: "pace", name: "Pace", val: getFMAttrValue(player, "pace", rawAttrs, overall) },
    { key: "stamina", name: "Stamina", val: getFMAttrValue(player, "stamina", rawAttrs, overall) },
    { key: "strength", name: "Strength", val: getFMAttrValue(player, "strength", rawAttrs, overall) },
    { key: "reflexes", name: "GK Reflexes", val: getFMAttrValue(player, "reflexes", rawAttrs, overall) },
    { key: "handling", name: "GK Handling", val: getFMAttrValue(player, "handling", rawAttrs, overall) },
    { key: "kicking", name: "GK Kicking", val: getFMAttrValue(player, "kicking", rawAttrs, overall) },
    { key: "one_on_ones", name: "GK 1-on-1s", val: getFMAttrValue(player, "one_on_ones", rawAttrs, overall) },
  ];

  // Top Stat Cards
  const statCards = [
    { label: "Goals", value: player.stats?.goals || 0, icon: <SportsSoccerIcon />, color: "primary.main" },
    { label: "Assists", value: player.stats?.assists || 0, icon: <WorkspacePremiumIcon />, color: "#028391" },
    { label: "Appearances", value: player.stats?.appearances || 0, icon: <PersonIcon />, color: "primary.main" },
    { label: "Clean Sheets", value: player.stats?.clean_sheets || 0, icon: <ShieldIcon />, color: "#10b981" },
  ];

  // Pentagon Radar Data
  const radarData = [
    { category: "Attacking", value: Math.round((technicalAttrs[3].val + technicalAttrs[2].val + technicalAttrs[7].val) / 3) },
    { category: "Technical", value: Math.round((technicalAttrs[9].val + technicalAttrs[4].val + technicalAttrs[12].val) / 3) },
    { category: "Tactical", value: Math.round((mentalAttrs[1].val + mentalAttrs[5].val + mentalAttrs[10].val) / 3) },
    { category: "Physical", value: Math.round((physicalGkAttrs[0].val + physicalGkAttrs[5].val + physicalGkAttrs[6].val + physicalGkAttrs[7].val) / 4) },
    { category: "Defending", value: Math.round((technicalAttrs[8].val + technicalAttrs[11].val + mentalAttrs[10].val) / 3) },
  ];

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3.5, pb: 6 }}>

      {/* 1. TOP BREADCRUMB NAVIGATION */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
        <Chip
          component={Link}
          to="/player-profiles"
          icon={<ArrowBackIcon sx={{ color: "inherit !important", fontSize: 14 }} />}
          label="All Players"
          clickable
          sx={{
            bgcolor: "var(--bg-pill)",
            color: "text.primary",
            fontWeight: 800,
            fontSize: "0.78rem",
            borderRadius: 9999,
            border: "1px solid",
            borderColor: "divider",
            "&:hover": { bgcolor: "action.hover" }
          }}
        />
        <Typography variant="body2" sx={{ fontWeight: 700, color: "text.secondary" }}>
          / {player.team} / <span style={{ color: isDark ? "#F8EBD5" : "#01204E" }}>{player.name}</span>
        </Typography>
      </Box>

      {/* 2. MAIN HERO PLAYER BANNER CARD */}
      <Card
        className="finnova-card"
        sx={{
          borderRadius: "24px",
          overflow: "hidden",
          p: { xs: 2.5, md: 3.5 }
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 3, flexWrap: "wrap" }}>
            {/* Club Gradient Avatar */}
            <Avatar
              sx={{
                width: 90,
                height: 90,
                background: clubMeta.bg,
                color: "#ffffff",
                fontWeight: 900,
                fontSize: "1.8rem",
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.3)",
                border: "2.5px solid rgba(255, 255, 255, 0.4)"
              }}
            >
              {clubMeta.code}
            </Avatar>

            <Box>
              <Typography variant="h3" sx={{ fontWeight: 900, fontFamily: "Outfit, sans-serif", color: "text.primary", letterSpacing: "-0.03em" }}>
                {player.name}
              </Typography>

              <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mt: 1, mb: 2 }}>
                <Chip label={player.position} sx={{ bgcolor: isDark ? "#F85525" : "#FAA968", color: "#ffffff", fontWeight: 800, borderRadius: 9999, height: 26 }} />
                <Chip component={Link} to={`/team-details/${player.team}`} label={player.team} clickable sx={{ bgcolor: "var(--bg-pill)", color: "text.primary", fontWeight: 700, borderRadius: 9999, height: 26, border: "1px solid", borderColor: "divider" }} />
                <Chip label={`${player.age} years`} sx={{ bgcolor: "var(--bg-subcard)", color: "text.primary", fontWeight: 700, borderRadius: 9999, height: 26, border: "1px solid", borderColor: "divider" }} />
                <Chip label={player.squad_role} sx={{ bgcolor: "#028391", color: "#ffffff", fontWeight: 700, borderRadius: 9999, height: 26 }} />
                {player.is_injured && (
                  <Chip icon={<LocalHospitalIcon sx={{ color: "#ffffff !important", fontSize: 14 }} />} label={`Injured (${player.recovery_time}d)`} sx={{ bgcolor: "#f43f5e", color: "#ffffff", fontWeight: 800, borderRadius: 9999, height: 26 }} />
                )}
              </Box>

              {/* Value, Wage & Contract */}
              <Box sx={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                <Box>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: "text.secondary", textTransform: "uppercase" }}>Market Value</Typography>
                  <Typography variant="h5" sx={{ fontWeight: 900, color: "text.primary", fontFamily: "Outfit, sans-serif" }}>
                    £{((player?.market_value ?? 0) / 1e6).toFixed(1)}M
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: "text.secondary", textTransform: "uppercase" }}>Weekly Wage</Typography>
                  <Typography variant="h5" sx={{ fontWeight: 900, color: "text.primary", fontFamily: "Outfit, sans-serif" }}>
                    £{player.wage ? player.wage.toLocaleString() : "45,000"}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: "text.secondary", textTransform: "uppercase" }}>Contract</Typography>
                  <Typography variant="h5" sx={{ fontWeight: 900, color: "text.primary", fontFamily: "Outfit, sans-serif" }}>
                    {player.contract_length ?? 3} years
                  </Typography>
                </Box>
              </Box>
            </Box>
          </Box>

          {/* Overall Rating Circle */}
          <Box
            sx={{
              width: 90,
              height: 90,
              borderRadius: "50%",
              bgcolor: isDark ? "#132B4F" : "#01204E",
              color: "#ffffff",
              boxShadow: "0 8px 24px rgba(0, 0, 0, 0.35)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              border: isDark ? "3px solid #F85525" : "3px solid #FAA968",
              flexShrink: 0
            }}
          >
            <Typography variant="h4" sx={{ fontWeight: 900, fontFamily: "Outfit, sans-serif", lineHeight: 1, color: isDark ? "#F85525" : "#FAA968" }}>
              {overall}
            </Typography>
            <Typography variant="caption" sx={{ fontWeight: 900, color: "#ffffff", fontSize: "0.7rem", letterSpacing: 1.2, mt: 0.2 }}>
              OVR
            </Typography>
          </Box>
        </Box>
      </Card>

      {/* 3. TOP 4 KPI STAT WIDGET CARDS */}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "repeat(2, 1fr)", md: "repeat(4, 1fr)" }, gap: 2.5 }}>
        {statCards.map((stat) => (
          <Card key={stat.label} className="finnova-card" sx={{ borderRadius: "20px" }}>
            <CardContent sx={{ p: 2.5, display: "flex", alignItems: "center", gap: 2 }}>
              <Avatar sx={{ bgcolor: isDark ? "rgba(248, 85, 37, 0.2)" : "#FAA968", color: isDark ? "#F85525" : "#01204E", width: 44, height: 44 }}>
                {stat.icon}
              </Avatar>
              <Box>
                <Typography variant="h4" sx={{ fontWeight: 900, color: "text.primary", fontFamily: "Outfit, sans-serif" }}>
                  {stat.value}
                </Typography>
                <Typography variant="caption" sx={{ fontWeight: 700, color: "text.secondary" }}>
                  {stat.label}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>

      {/* 4. TABS: ATTRIBUTES vs FORM & HISTORY */}
      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{
          bgcolor: "var(--bg-pill)",
          borderRadius: 9999,
          p: 0.5,
          border: "1px solid",
          borderColor: "divider",
          width: "fit-content",
          minHeight: 0,
          "& .MuiTabs-flexContainer": { gap: 0.5 },
          "& .MuiTabs-indicator": { bgcolor: "var(--btn-main)", height: "100%", borderRadius: 9999, zIndex: 0 },
          "& .MuiTab-root": {
            zIndex: 1,
            fontWeight: 800,
            color: "text.primary",
            fontSize: "0.85rem",
            textTransform: "none",
            borderRadius: 9999,
            minHeight: 36,
            px: 2.5,
            py: 0.8,
            "&.Mui-selected": { color: "#ffffff" }
          }
        }}
      >
        <Tab label="FM Attributes" />
        <Tab label="Form & History" />
      </Tabs>

      {/* 5. TAB 0: FM ATTRIBUTES PANEL & SIDEBAR GRID */}
      {tab === 0 && (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "7fr 5fr" }, gap: 3 }}>

          {/* LEFT: 3 EQUAL-HEIGHT FM ATTRIBUTES COLUMNS */}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2 }}>

            {/* COLUMN 1: TECHNICAL */}
            <Card className="finnova-card" sx={{ borderRadius: "20px", p: 2.5, display: "flex", flexDirection: "column", justifyContent: "space-between", height: "100%" }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.8, pb: 0.8, borderBottom: "1.5px solid", borderColor: "divider" }}>
                <SportsSoccerIcon sx={{ color: "secondary.main", fontSize: 18 }} />
                <Typography variant="subtitle2" sx={{ fontWeight: 900, color: "text.primary", fontFamily: "Outfit, sans-serif", letterSpacing: "0.06em", textTransform: "uppercase", fontSize: "0.8rem" }}>
                  Technical
                </Typography>
              </Box>

              <Box sx={{ display: "flex", flexDirection: "column", justifyContent: "space-between", flex: 1, gap: 1.2 }}>
                {technicalAttrs.map((attr) => {
                  const badge = getFMRatingBadge(attr.val, isDark);
                  return (
                    <Box key={attr.key} sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", py: 0.5, borderBottom: "1px dashed", borderColor: "divider" }}>
                      <Typography variant="body2" sx={{ fontWeight: 700, color: "text.primary", textTransform: "capitalize", fontSize: "0.84rem" }}>
                        {attr.name}
                      </Typography>
                      <Box
                        sx={{
                          bgcolor: badge.bg,
                          color: badge.color,
                          fontWeight: 900,
                          fontSize: "0.78rem",
                          px: 1.2,
                          py: 0.2,
                          borderRadius: 9999,
                          minWidth: 30,
                          textAlign: "center"
                        }}
                      >
                        {attr.val}
                      </Box>
                    </Box>
                  );
                })}
              </Box>
            </Card>

            {/* COLUMN 2: MENTAL */}
            <Card className="finnova-card" sx={{ borderRadius: "20px", p: 2.5, display: "flex", flexDirection: "column", justifyContent: "space-between", height: "100%" }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.8, pb: 0.8, borderBottom: "1.5px solid", borderColor: "divider" }}>
                <PsychologyIcon sx={{ color: "secondary.main", fontSize: 18 }} />
                <Typography variant="subtitle2" sx={{ fontWeight: 900, color: "text.primary", fontFamily: "Outfit, sans-serif", letterSpacing: "0.06em", textTransform: "uppercase", fontSize: "0.8rem" }}>
                  Mental
                </Typography>
              </Box>

              <Box sx={{ display: "flex", flexDirection: "column", justifyContent: "space-between", flex: 1, gap: 1.2 }}>
                {mentalAttrs.map((attr) => {
                  const badge = getFMRatingBadge(attr.val, isDark);
                  return (
                    <Box key={attr.key} sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", py: 0.5, borderBottom: "1px dashed", borderColor: "divider" }}>
                      <Typography variant="body2" sx={{ fontWeight: 700, color: "text.primary", textTransform: "capitalize", fontSize: "0.84rem" }}>
                        {attr.name}
                      </Typography>
                      <Box
                        sx={{
                          bgcolor: badge.bg,
                          color: badge.color,
                          fontWeight: 900,
                          fontSize: "0.78rem",
                          px: 1.2,
                          py: 0.2,
                          borderRadius: 9999,
                          minWidth: 30,
                          textAlign: "center"
                        }}
                      >
                        {attr.val}
                      </Box>
                    </Box>
                  );
                })}
              </Box>
            </Card>

            {/* COLUMN 3: PHYSICAL & GK */}
            <Card className="finnova-card" sx={{ borderRadius: "20px", p: 2.5, display: "flex", flexDirection: "column", justifyContent: "space-between", height: "100%" }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.8, pb: 0.8, borderBottom: "1.5px solid", borderColor: "divider" }}>
                <FlashOnIcon sx={{ color: "secondary.main", fontSize: 18 }} />
                <Typography variant="subtitle2" sx={{ fontWeight: 900, color: "text.primary", fontFamily: "Outfit, sans-serif", letterSpacing: "0.06em", textTransform: "uppercase", fontSize: "0.8rem" }}>
                  Physical & GK
                </Typography>
              </Box>

              <Box sx={{ display: "flex", flexDirection: "column", justifyContent: "space-between", flex: 1, gap: 1.2 }}>
                {physicalGkAttrs.map((attr) => {
                  const badge = getFMRatingBadge(attr.val, isDark);
                  return (
                    <Box key={attr.key} sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", py: 0.5, borderBottom: "1px dashed", borderColor: "divider" }}>
                      <Typography variant="body2" sx={{ fontWeight: 700, color: "text.primary", textTransform: "capitalize", fontSize: "0.84rem" }}>
                        {attr.name}
                      </Typography>
                      <Box
                        sx={{
                          bgcolor: badge.bg,
                          color: badge.color,
                          fontWeight: 900,
                          fontSize: "0.78rem",
                          px: 1.2,
                          py: 0.2,
                          borderRadius: 9999,
                          minWidth: 30,
                          textAlign: "center"
                        }}
                      >
                        {attr.val}
                      </Box>
                    </Box>
                  );
                })}
              </Box>
            </Card>

          </Box>

          {/* RIGHT: ATTRIBUTE PENTAGON & PLAYER SPECIFICATIONS SIDEBAR */}
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>

            {/* CARD 1: Attribute Pentagon Overview */}
            <Card className="finnova-card" sx={{ borderRadius: "20px", p: 2.5 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 900, color: "text.primary", fontFamily: "Outfit, sans-serif", mb: 1, textTransform: "uppercase", letterSpacing: "0.05em", fontSize: "0.85rem" }}>
                Attribute Polygon Analysis
              </Typography>
              <Box sx={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke={isDark ? "rgba(2, 131, 145, 0.25)" : "rgba(1, 32, 78, 0.18)"} />
                    <PolarAngleAxis dataKey="category" tick={{ fill: isDark ? "#F8EBD5" : "#01204E", fontSize: 11, fontWeight: 800 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: isDark ? "#8FE3EC" : "#028391", fontSize: 10 }} />
                    <Radar
                      name="Attributes"
                      dataKey="value"
                      stroke={isDark ? "#F85525" : "#028391"}
                      fill={isDark ? "#F85525" : "#FAA968"}
                      fillOpacity={0.45}
                      strokeWidth={2.5}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </Box>
            </Card>

            {/* CARD 2: Foot Proficiency & Playing Traits */}
            <Card className="finnova-card" sx={{ borderRadius: "20px", p: 2.5 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 900, color: "text.primary", fontFamily: "Outfit, sans-serif", mb: 1.5, textTransform: "uppercase", letterSpacing: "0.05em", fontSize: "0.85rem" }}>
                Foot Proficiency & Player Traits
              </Typography>

              <Box sx={{ display: "flex", gap: 1.5, mb: 2 }}>
                <Box sx={{ flex: 1, bgcolor: "var(--bg-subcard)", p: 1.2, borderRadius: "14px", border: "1px solid", borderColor: "divider" }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: "text.secondary" }}>Left Foot</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 800, color: "text.primary" }}>Reasonable</Typography>
                </Box>
                <Box sx={{ flex: 1, bgcolor: "var(--bg-subcard)", p: 1.2, borderRadius: "14px", border: "1px solid", borderColor: "divider" }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: "text.secondary" }}>Right Foot</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 800, color: "text.primary" }}>Very Strong</Typography>
                </Box>
              </Box>

              <Typography variant="caption" sx={{ fontWeight: 800, color: "text.secondary", textTransform: "uppercase" }}>Player Traits</Typography>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 0.8 }}>
                <Chip label="Dictates Tempo" size="small" sx={{ bgcolor: isDark ? "rgba(248, 85, 37, 0.2)" : "#FAA968", color: isDark ? "#F8EBD5" : "#01204E", fontWeight: 800, borderRadius: 9999, fontSize: "0.72rem", border: "1px solid", borderColor: "divider" }} />
                <Chip label="Tries Killer Balls" size="small" sx={{ bgcolor: "var(--bg-subcard)", color: "text.primary", fontWeight: 700, borderRadius: 9999, fontSize: "0.72rem", border: "1px solid", borderColor: "divider" }} />
                <Chip label="Shoots From Distance" size="small" sx={{ bgcolor: "var(--bg-subcard)", color: "text.primary", fontWeight: 700, borderRadius: 9999, fontSize: "0.72rem", border: "1px solid", borderColor: "divider" }} />
              </Box>
            </Card>

          </Box>

        </Box>
      )}

      {/* 6. TAB 1: FORM & MATCH HISTORY */}
      {tab === 1 && (
        <Card className="finnova-card" sx={{ borderRadius: "20px", p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 900, color: "text.primary", fontFamily: "Outfit, sans-serif", mb: 2 }}>
            Match Rating History & Form
          </Typography>

          {player.form && player.form.length > 0 ? (
            <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap", my: 2 }}>
              {player.form.map((f, i) => {
                const rating = f ?? 7.0;
                const badgeColor = rating >= 7.5 ? "#10b981" : rating >= 6.5 ? "#FAA968" : "#f43f5e";
                return (
                  <Box
                    key={i}
                    sx={{
                      width: 48,
                      height: 48,
                      borderRadius: "50%",
                      bgcolor: badgeColor,
                      color: "#01204E",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontWeight: 900,
                      fontSize: "0.9rem",
                      boxShadow: "0 4px 12px rgba(1, 32, 78, 0.15)"
                    }}
                  >
                    {rating.toFixed(1)}
                  </Box>
                );
              })}
            </Box>
          ) : (
            <Typography variant="body2" sx={{ fontWeight: 600, color: "#028391" }}>
              No recent match form records available for this season.
            </Typography>
          )}
        </Card>
      )}
    </Box>
  );
};

export default PlayerDetail;
