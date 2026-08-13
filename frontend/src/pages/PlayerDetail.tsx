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
import AssistIcon from "@mui/icons-material/Moving";
import PersonIcon from "@mui/icons-material/Person";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";
import FitnessCenterIcon from "@mui/icons-material/FitnessCenter";
import PsychologyIcon from "@mui/icons-material/Psychology";
import FlashOnIcon from "@mui/icons-material/FlashOn";

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
const getFMRatingBadge = (value: number) => {
  const val = Math.round(value);
  if (val >= 75) return { bg: "#10b981", color: "#ffffff" }; // Excellent (Green)
  if (val >= 60) return { bg: "#FAA968", color: "#01204E" }; // Good (Warm Gold)
  if (val >= 45) return { bg: "#028391", color: "#ffffff" }; // Average (Teal)
  return { bg: "rgba(1, 32, 78, 0.12)", color: "#01204E" }; // Low (Slate)
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

const PlayerDetail: React.FC = () => {
  const { playerName } = useParams<{ playerName: string }>();
  const { selectedSeason, currentReport, isLoading, error, fetchAvailableSeasons } = useSimulationStore();

  const [player, setPlayer] = useState<Player | null>(null);
  const [localLoading, setLocalLoading] = useState(true);
  const [localError, setLocalError] = useState<string | null>(null);
  const [tab, setTab] = useState(0);

  useEffect(() => {
    if (!selectedSeason) {
      fetchAvailableSeasons();
    }
  }, [selectedSeason, fetchAvailableSeasons]);

  useEffect(() => {
    if (currentReport && playerName) {
      setLocalLoading(true);
      setLocalError(null);
      let foundPlayer: Player | null = null;
      for (const teamDetail of currentReport.all_teams_details) {
        foundPlayer = teamDetail.players.find((p) => p.name === playerName) || null;
        if (foundPlayer) break;
      }

      if (foundPlayer) {
        setPlayer(foundPlayer);
      } else {
        setLocalError(`Player "${playerName}" not found for season ${selectedSeason}.`);
      }
      setLocalLoading(false);
    } else if (!currentReport && !isLoading && !error && selectedSeason) {
      setLocalLoading(true);
    }
  }, [currentReport, playerName, selectedSeason, isLoading, error]);

  if (isLoading || localLoading) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <CircularProgress size={44} sx={{ color: "#01204E" }} />
        <Typography sx={{ mt: 2, fontWeight: 600, color: "#028391" }}>
          Loading player details...
        </Typography>
      </Box>
    );
  }

  if (error || localError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ bgcolor: "rgba(244, 63, 94, 0.1)", color: "#f43f5e", border: "1px solid rgba(244, 63, 94, 0.2)" }}>
          {error || localError}
        </Alert>
      </Box>
    );
  }

  if (!player) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography variant="h6" sx={{ fontWeight: 800, color: "#01204E" }}>
          No player data available.
        </Typography>
      </Box>
    );
  }

  const getOverallRating = (attributes: Player["attributes"]) => {
    if (!attributes) return 70;
    const totalSum = Object.values(attributes).reduce(
      (sum, category: Record<string, number>) =>
        sum + Object.values(category || {}).reduce((catSum, val) => catSum + val, 0),
      0
    );
    const totalCount = Object.values(attributes).reduce(
      (count, category: Record<string, number>) => count + Object.keys(category || {}).length,
      0
    );
    return totalCount > 0 ? Math.round(totalSum / totalCount) : 70;
  };

  const overall = getOverallRating(player.attributes);
  const clubMeta = getClubMeta(player.team);

  // Flatten raw attributes
  const rawFlattenedAttrs: { [key: string]: number } = {};
  Object.values(player.attributes || {}).forEach((cat) => {
    if (cat && typeof cat === "object") {
      Object.entries(cat).forEach(([k, v]) => {
        rawFlattenedAttrs[k] = Math.round(v);
      });
    }
  });

  // FM Full 12-Item Attribute Collections
  const technicalKeys = ["finishing", "passing", "dribbling", "crossing", "tackling", "heading", "first_touch", "long_shots", "ball_control", "technique", "free_kicks", "penalties"];
  const mentalKeys = ["vision", "positioning", "work_rate", "composure", "decisions", "aggression", "anticipation", "bravery", "concentration", "determination", "flair", "leadership"];
  const physicalGkKeys = ["pace", "acceleration", "agility", "balance", "stamina", "strength", "jumping_reach", "natural_fitness", "reflexes", "diving", "handling", "kicking"];

  const buildAttrList = (keyList: string[]) => {
    return keyList.map((k) => ({
      key: k,
      name: k.replace(/_/g, " "),
      val: getFMAttrValue(player, k, rawFlattenedAttrs, overall)
    }));
  };

  const technicalAttrs = buildAttrList(technicalKeys);
  const mentalAttrs = buildAttrList(mentalKeys);
  const physicalGkAttrs = buildAttrList(physicalGkKeys);

  // Radar Chart Data (averaged categories)
  const radarData = [
    { category: "Defending", value: Math.round((getFMAttrValue(player, "tackling", rawFlattenedAttrs, overall) + getFMAttrValue(player, "marking", rawFlattenedAttrs, overall)) / 2) },
    { category: "Dribbling", value: Math.round((getFMAttrValue(player, "dribbling", rawFlattenedAttrs, overall) + getFMAttrValue(player, "ball_control", rawFlattenedAttrs, overall)) / 2) },
    { category: "Goalkeeping", value: Math.round((getFMAttrValue(player, "diving", rawFlattenedAttrs, overall) + getFMAttrValue(player, "handling", rawFlattenedAttrs, overall)) / 2) },
    { category: "Pace", value: Math.round((getFMAttrValue(player, "pace", rawFlattenedAttrs, overall) + getFMAttrValue(player, "acceleration", rawFlattenedAttrs, overall)) / 2) },
    { category: "Passing", value: Math.round((getFMAttrValue(player, "passing", rawFlattenedAttrs, overall) + getFMAttrValue(player, "vision", rawFlattenedAttrs, overall)) / 2) },
    { category: "Physical", value: Math.round((getFMAttrValue(player, "stamina", rawFlattenedAttrs, overall) + getFMAttrValue(player, "strength", rawFlattenedAttrs, overall)) / 2) },
    { category: "Shooting", value: Math.round((getFMAttrValue(player, "finishing", rawFlattenedAttrs, overall) + getFMAttrValue(player, "long_shots", rawFlattenedAttrs, overall)) / 2) },
  ];

  const statCards = [
    { label: "Goals", value: player.stats?.goals || 0, icon: <SportsSoccerIcon />, color: "#01204E" },
    { label: "Assists", value: player.stats?.assists || 0, icon: <AssistIcon />, color: "#028391" },
    { label: "Appearances", value: player.stats?.appearances || 0, icon: <PersonIcon />, color: "#01204E" },
    { label: "Fitness", value: `${player.stats?.fitness || 100}%`, icon: <FitnessCenterIcon />, color: "#FAA968" },
  ];

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3.5, pb: 6 }}>

      {/* 1. HERO TITLE HEADER & BACK BUTTON */}
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Chip
            component={Link}
            to="/player-profiles"
            label="← Back to Player Profiles"
            clickable
            sx={{
              bgcolor: "#F6DCAC",
              color: "#01204E",
              fontWeight: 800,
              borderRadius: 9999,
              border: "1px solid rgba(1, 32, 78, 0.15)",
              "&:hover": { bgcolor: "#FAA968" }
            }}
          />
        </Box>
      </Box>

      {/* 2. MAIN HERO PLAYER BANNER CARD */}
      <Card
        className="finnova-card"
        sx={{
          borderRadius: "24px",
          bgcolor: "#F6DCAC",
          border: "1.5px solid rgba(250, 169, 104, 0.45)",
          boxShadow: "0 12px 32px rgba(1, 32, 78, 0.08), 0 2px 8px rgba(250, 169, 104, 0.3)",
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
                boxShadow: "0 8px 24px rgba(1, 32, 78, 0.2)",
                border: "2.5px solid rgba(255, 255, 255, 0.6)"
              }}
            >
              {clubMeta.code}
            </Avatar>

            <Box>
              <Typography variant="h3" sx={{ fontWeight: 900, fontFamily: "Outfit, sans-serif", color: "#01204E", letterSpacing: "-0.03em" }}>
                {player.name}
              </Typography>

              <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mt: 1, mb: 2 }}>
                <Chip label={player.position} sx={{ bgcolor: "#FAA968", color: "#01204E", fontWeight: 800, borderRadius: 9999, height: 26 }} />
                <Chip component={Link} to={`/team-details/${player.team}`} label={player.team} clickable sx={{ bgcolor: "#ffffff", color: "#01204E", fontWeight: 700, borderRadius: 9999, height: 26, border: "1px solid rgba(1, 32, 78, 0.15)" }} />
                <Chip label={`${player.age} years`} sx={{ bgcolor: "#fde8c5", color: "#01204E", fontWeight: 700, borderRadius: 9999, height: 26 }} />
                <Chip label={player.squad_role} sx={{ bgcolor: "#028391", color: "#ffffff", fontWeight: 700, borderRadius: 9999, height: 26 }} />
                {player.is_injured && (
                  <Chip icon={<LocalHospitalIcon sx={{ color: "#ffffff !important", fontSize: 14 }} />} label={`Injured (${player.recovery_time}d)`} sx={{ bgcolor: "#f43f5e", color: "#ffffff", fontWeight: 800, borderRadius: 9999, height: 26 }} />
                )}
              </Box>

              {/* Value, Wage & Contract */}
              <Box sx={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                <Box>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: "#028391", textTransform: "uppercase" }}>Market Value</Typography>
                  <Typography variant="h5" sx={{ fontWeight: 900, color: "#01204E", fontFamily: "Outfit, sans-serif" }}>
                    £{((player?.market_value ?? 0) / 1e6).toFixed(1)}M
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: "#028391", textTransform: "uppercase" }}>Weekly Wage</Typography>
                  <Typography variant="h5" sx={{ fontWeight: 900, color: "#01204E", fontFamily: "Outfit, sans-serif" }}>
                    £{player.wage ? player.wage.toLocaleString() : "45,000"}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: "#028391", textTransform: "uppercase" }}>Contract</Typography>
                  <Typography variant="h5" sx={{ fontWeight: 900, color: "#01204E", fontFamily: "Outfit, sans-serif" }}>
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
              bgcolor: "#01204E",
              color: "#ffffff",
              boxShadow: "0 8px 24px rgba(1, 32, 78, 0.35)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              border: "3px solid #FAA968",
              flexShrink: 0
            }}
          >
            <Typography variant="h4" sx={{ fontWeight: 900, fontFamily: "Outfit, sans-serif", lineHeight: 1, color: "#FAA968" }}>
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
          <Card key={stat.label} className="finnova-card" sx={{ bgcolor: "#fde8c5", borderRadius: "20px", border: "1px solid rgba(250, 169, 104, 0.4)" }}>
            <CardContent sx={{ p: 2.5, display: "flex", alignItems: "center", gap: 2 }}>
              <Avatar sx={{ bgcolor: "#FAA968", color: "#01204E", width: 44, height: 44 }}>
                {stat.icon}
              </Avatar>
              <Box>
                <Typography variant="h4" sx={{ fontWeight: 900, color: "#01204E", fontFamily: "Outfit, sans-serif" }}>
                  {stat.value}
                </Typography>
                <Typography variant="caption" sx={{ fontWeight: 700, color: "#028391" }}>
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
          bgcolor: "#F6DCAC",
          borderRadius: 9999,
          p: 0.5,
          border: "1px solid rgba(1, 32, 78, 0.15)",
          width: "fit-content",
          minHeight: 0,
          "& .MuiTabs-flexContainer": { gap: 0.5 },
          "& .MuiTabs-indicator": { bgcolor: "#01204E", height: "100%", borderRadius: 9999, zIndex: 0 },
          "& .MuiTab-root": {
            zIndex: 1,
            fontWeight: 800,
            color: "#01204E",
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
            <Card className="finnova-card" sx={{ bgcolor: "#fde8c5", borderRadius: "20px", border: "1px solid rgba(250, 169, 104, 0.4)", p: 2.5, display: "flex", flexDirection: "column", justifyContent: "space-between", height: "100%" }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.8, pb: 0.8, borderBottom: "1.5px solid rgba(1, 32, 78, 0.12)" }}>
                <SportsSoccerIcon sx={{ color: "#028391", fontSize: 18 }} />
                <Typography variant="subtitle2" sx={{ fontWeight: 900, color: "#01204E", fontFamily: "Outfit, sans-serif", letterSpacing: "0.06em", textTransform: "uppercase", fontSize: "0.8rem" }}>
                  Technical
                </Typography>
              </Box>

              <Box sx={{ display: "flex", flexDirection: "column", justifyContent: "space-between", flex: 1, gap: 1.2 }}>
                {technicalAttrs.map((attr) => {
                  const badge = getFMRatingBadge(attr.val);
                  return (
                    <Box key={attr.key} sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", py: 0.5, borderBottom: "1px dashed rgba(1, 32, 78, 0.07)" }}>
                      <Typography variant="body2" sx={{ fontWeight: 700, color: "#01204E", textTransform: "capitalize", fontSize: "0.84rem" }}>
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
            <Card className="finnova-card" sx={{ bgcolor: "#fde8c5", borderRadius: "20px", border: "1px solid rgba(250, 169, 104, 0.4)", p: 2.5, display: "flex", flexDirection: "column", justifyContent: "space-between", height: "100%" }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.8, pb: 0.8, borderBottom: "1.5px solid rgba(1, 32, 78, 0.12)" }}>
                <PsychologyIcon sx={{ color: "#028391", fontSize: 18 }} />
                <Typography variant="subtitle2" sx={{ fontWeight: 900, color: "#01204E", fontFamily: "Outfit, sans-serif", letterSpacing: "0.06em", textTransform: "uppercase", fontSize: "0.8rem" }}>
                  Mental
                </Typography>
              </Box>

              <Box sx={{ display: "flex", flexDirection: "column", justifyContent: "space-between", flex: 1, gap: 1.2 }}>
                {mentalAttrs.map((attr) => {
                  const badge = getFMRatingBadge(attr.val);
                  return (
                    <Box key={attr.key} sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", py: 0.5, borderBottom: "1px dashed rgba(1, 32, 78, 0.07)" }}>
                      <Typography variant="body2" sx={{ fontWeight: 700, color: "#01204E", textTransform: "capitalize", fontSize: "0.84rem" }}>
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
            <Card className="finnova-card" sx={{ bgcolor: "#fde8c5", borderRadius: "20px", border: "1px solid rgba(250, 169, 104, 0.4)", p: 2.5, display: "flex", flexDirection: "column", justifyContent: "space-between", height: "100%" }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.8, pb: 0.8, borderBottom: "1.5px solid rgba(1, 32, 78, 0.12)" }}>
                <FlashOnIcon sx={{ color: "#028391", fontSize: 18 }} />
                <Typography variant="subtitle2" sx={{ fontWeight: 900, color: "#01204E", fontFamily: "Outfit, sans-serif", letterSpacing: "0.06em", textTransform: "uppercase", fontSize: "0.8rem" }}>
                  Physical & GK
                </Typography>
              </Box>

              <Box sx={{ display: "flex", flexDirection: "column", justifyContent: "space-between", flex: 1, gap: 1.2 }}>
                {physicalGkAttrs.map((attr) => {
                  const badge = getFMRatingBadge(attr.val);
                  return (
                    <Box key={attr.key} sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", py: 0.5, borderBottom: "1px dashed rgba(1, 32, 78, 0.07)" }}>
                      <Typography variant="body2" sx={{ fontWeight: 700, color: "#01204E", textTransform: "capitalize", fontSize: "0.84rem" }}>
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
            <Card className="finnova-card" sx={{ bgcolor: "#fde8c5", borderRadius: "20px", border: "1px solid rgba(250, 169, 104, 0.4)", p: 2.5 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 900, color: "#01204E", fontFamily: "Outfit, sans-serif", mb: 1, textTransform: "uppercase", letterSpacing: "0.05em", fontSize: "0.85rem" }}>
                Attribute Polygon Analysis
              </Typography>
              <Box sx={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="rgba(1, 32, 78, 0.18)" />
                    <PolarAngleAxis dataKey="category" tick={{ fill: "#01204E", fontSize: 11, fontWeight: 800 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#028391", fontSize: 10 }} />
                    <Radar
                      name="Attributes"
                      dataKey="value"
                      stroke="#028391"
                      fill="#FAA968"
                      fillOpacity={0.5}
                      strokeWidth={2.5}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </Box>
            </Card>

            {/* CARD 2: Foot Proficiency & Playing Traits */}
            <Card className="finnova-card" sx={{ bgcolor: "#fde8c5", borderRadius: "20px", border: "1px solid rgba(250, 169, 104, 0.4)", p: 2.5 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 900, color: "#01204E", fontFamily: "Outfit, sans-serif", mb: 1.5, textTransform: "uppercase", letterSpacing: "0.05em", fontSize: "0.85rem" }}>
                Foot Proficiency & Player Traits
              </Typography>

              <Box sx={{ display: "flex", gap: 1.5, mb: 2 }}>
                <Box sx={{ flex: 1, bgcolor: "#F6DCAC", p: 1.2, borderRadius: "14px", border: "1px solid rgba(1, 32, 78, 0.12)" }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: "#028391" }}>Left Foot</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 800, color: "#01204E" }}>Reasonable</Typography>
                </Box>
                <Box sx={{ flex: 1, bgcolor: "#F6DCAC", p: 1.2, borderRadius: "14px", border: "1px solid rgba(1, 32, 78, 0.12)" }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: "#028391" }}>Right Foot</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 800, color: "#01204E" }}>Very Strong</Typography>
                </Box>
              </Box>

              <Typography variant="caption" sx={{ fontWeight: 800, color: "#028391", textTransform: "uppercase" }}>Player Traits</Typography>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 0.8 }}>
                <Chip label="Dictates Tempo" size="small" sx={{ bgcolor: "#FAA968", color: "#01204E", fontWeight: 800, borderRadius: 9999, fontSize: "0.72rem" }} />
                <Chip label="Tries Killer Balls" size="small" sx={{ bgcolor: "#F6DCAC", color: "#01204E", fontWeight: 700, borderRadius: 9999, fontSize: "0.72rem" }} />
                <Chip label="Shoots From Distance" size="small" sx={{ bgcolor: "#F6DCAC", color: "#01204E", fontWeight: 700, borderRadius: 9999, fontSize: "0.72rem" }} />
              </Box>
            </Card>

          </Box>

        </Box>
      )}

      {/* 6. TAB 1: FORM & MATCH HISTORY */}
      {tab === 1 && (
        <Card className="finnova-card" sx={{ bgcolor: "#fde8c5", borderRadius: "20px", border: "1px solid rgba(250, 169, 104, 0.4)", p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 900, color: "#01204E", fontFamily: "Outfit, sans-serif", mb: 2 }}>
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
