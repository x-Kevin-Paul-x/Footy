import React, { useRef, useState, useEffect } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Button,
  IconButton,
  ButtonGroup,
  useTheme,
  alpha,
  LinearProgress,
  CircularProgress,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PauseIcon from "@mui/icons-material/Pause";
import ReplayIcon from "@mui/icons-material/Replay";
import SportsSoccerIcon from "@mui/icons-material/SportsSoccer";
import VideocamIcon from "@mui/icons-material/Videocam";
import SpeedIcon from "@mui/icons-material/Speed";
import MemoryIcon from "@mui/icons-material/Memory";
import HourglassTopIcon from "@mui/icons-material/HourglassTop";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import { getMatchRenderStatus } from "../services/api";

interface MatchVideoReplayProps {
  videoUrl?: string | null;
  matchId: string | number;
  homeTeam: string;
  awayTeam: string;
  score?: [number, number];
  events?: Array<{ minute: number; type: string; player?: string; team?: string; details?: string }>;
  onGenerateReplay?: () => void;
  isGenerating?: boolean;
}

export const MatchVideoReplay: React.FC<MatchVideoReplayProps> = ({
  videoUrl,
  matchId,
  homeTeam,
  awayTeam,
  score = [0, 0],
  events = [],
  onGenerateReplay,
  isGenerating = false,
}) => {
  const theme = useTheme();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackRate, setPlaybackRate] = useState<number>(1);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);

  // Active Video URL & Live Rendering State
  const [activeVideoUrl, setActiveVideoUrl] = useState<string | null>(videoUrl || null);
  const [isActivelyRendering, setIsActivelyRendering] = useState<boolean>(isGenerating);
  const [renderProgress, setRenderProgress] = useState<number>(0);
  const [renderStage, setRenderStage] = useState<string>("Initializing TiKick MARL Policy...");
  const [matchMinute, setMatchMinute] = useState<number>(0);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [liveScore, setLiveScore] = useState<[number, number]>(score);

  // Synchronize when videoUrl prop changes
  useEffect(() => {
    if (videoUrl) {
      setActiveVideoUrl(videoUrl);
      setIsActivelyRendering(false);
    }
  }, [videoUrl]);

  // Synchronize when isGenerating prop changes
  useEffect(() => {
    if (isGenerating) {
      setIsActivelyRendering(true);
      setRenderProgress((prev) => (prev > 0 ? prev : 5));
    }
  }, [isGenerating]);

  // Status Polling and Mount Check
  useEffect(() => {
    let timerInterval: any = null;
    let pollInterval: any = null;

    const checkStatus = async () => {
      try {
        const statusData = await getMatchRenderStatus(String(matchId));
        if (statusData) {
          if (statusData.completed && statusData.video_url) {
            setActiveVideoUrl(statusData.video_url);
            setIsActivelyRendering(false);
            return;
          }
          if (
            statusData.status === "rendering" ||
            statusData.status === "initializing" ||
            (statusData.progress !== undefined && statusData.progress > 0 && !statusData.completed)
          ) {
            setIsActivelyRendering(true);
            if (statusData.progress !== undefined) setRenderProgress(statusData.progress);
            if (statusData.stage) setRenderStage(statusData.stage);
            if (statusData.match_minute !== undefined) setMatchMinute(statusData.match_minute);
            if (statusData.score) setLiveScore(statusData.score);
          }
        }
      } catch {
        // Ignore poll error
      }
    };

    // Check status on mount if no video
    if (!activeVideoUrl) {
      checkStatus();
    }

    if (isGenerating || isActivelyRendering) {
      timerInterval = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);

      pollInterval = setInterval(async () => {
        try {
          const statusData = await getMatchRenderStatus(String(matchId));
          if (statusData) {
            if (statusData.completed && statusData.video_url) {
              setActiveVideoUrl(statusData.video_url);
              setIsActivelyRendering(false);
              return;
            }
            if (statusData.progress !== undefined && statusData.progress > 0) {
              setRenderProgress(statusData.progress);
              setIsActivelyRendering(true);
            }
            if (statusData.stage) setRenderStage(statusData.stage);
            if (statusData.match_minute !== undefined) setMatchMinute(statusData.match_minute);
            if (statusData.score) setLiveScore(statusData.score);
          }
        } catch {
          // Ignore transient poll error
        }
      }, 800);
    }

    return () => {
      if (timerInterval) clearInterval(timerInterval);
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [isGenerating, isActivelyRendering, matchId, activeVideoUrl]);

  const handlePlayPause = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleSpeedChange = (speed: number) => {
    if (!videoRef.current) return;
    videoRef.current.playbackRate = speed;
    setPlaybackRate(speed);
  };

  const handleSeekToMinute = (minute: number) => {
    if (!videoRef.current || duration === 0) return;
    const targetTime = (minute / 90) * duration;
    videoRef.current.currentTime = Math.max(0, Math.min(duration, targetTime - 2));
    videoRef.current.play();
    setIsPlaying(true);
  };

  const isDisplayingHUD = (isGenerating || isActivelyRendering) && !activeVideoUrl;

  const goalEvents = events.filter(
    (e) => (e.type || "").toLowerCase() === "goal" || (e.details || "").toLowerCase().includes("goal")
  );

  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: 4,
        border: `1px solid ${theme.palette.divider}`,
        overflow: "hidden",
        backgroundColor: theme.palette.background.paper,
      }}
    >
      {/* Header Banner */}
      <Box
        sx={{
          px: 3,
          py: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: `1px solid ${theme.palette.divider}`,
          background: alpha(theme.palette.primary.main, 0.04),
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <VideocamIcon sx={{ color: theme.palette.primary.main }} />
          <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
            3D Broadcast Replay • Google Research Football AI
          </Typography>
          <Chip
            label={`${homeTeam} ${score[0]} - ${score[1]} ${awayTeam} (#${matchId})`}
            size="small"
            variant="outlined"
            sx={{ fontWeight: 700, fontSize: "0.75rem" }}
          />
        </Box>
        <Chip
          label="TiKick 11v11 MARL"
          size="small"
          sx={{
            fontWeight: 700,
            bgcolor: alpha(theme.palette.secondary.main, 0.1),
            color: theme.palette.secondary.main,
          }}
        />
      </Box>

      <CardContent sx={{ p: 3 }}>
        {activeVideoUrl ? (
          <Box>
            {/* HTML5 Video Player */}
            <Box
              sx={{
                position: "relative",
                width: "100%",
                borderRadius: 3,
                overflow: "hidden",
                bgcolor: "#000",
                boxShadow: "0 10px 30px rgba(0,0,0,0.25)",
              }}
            >
              <video
                ref={videoRef}
                src={activeVideoUrl}
                controls
                style={{ width: "100%", maxHeight: "520px", display: "block" }}
                onTimeUpdate={() => {
                  if (videoRef.current) setCurrentTime(videoRef.current.currentTime);
                }}
                onLoadedMetadata={() => {
                  if (videoRef.current) setDuration(videoRef.current.duration);
                }}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
              />
            </Box>

            {/* Custom Playback Speed Controls */}
            <Box
              sx={{
                mt: 2,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: 1.5,
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <IconButton onClick={handlePlayPause} color="primary" sx={{ bgcolor: alpha(theme.palette.primary.main, 0.1) }}>
                  {isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
                </IconButton>
                <IconButton onClick={() => { if (videoRef.current) videoRef.current.currentTime = 0; }} size="small">
                  <ReplayIcon />
                </IconButton>
                <Typography variant="body2" sx={{ fontWeight: 700, color: "text.secondary", ml: 1 }}>
                  {Math.floor(currentTime)}s / {Math.floor(duration)}s
                </Typography>
              </Box>

              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <SpeedIcon sx={{ fontSize: 18, color: "text.secondary" }} />
                <ButtonGroup size="small" variant="outlined">
                  {[1, 1.5, 2, 4].map((speed) => (
                    <Button
                      key={speed}
                      onClick={() => handleSpeedChange(speed)}
                      variant={playbackRate === speed ? "contained" : "outlined"}
                      sx={{ fontWeight: 700, minWidth: 38 }}
                    >
                      {speed}x
                    </Button>
                  ))}
                </ButtonGroup>
              </Box>
            </Box>

            {/* Key Moments / Goal Jumpers */}
            {goalEvents.length > 0 && (
              <Box sx={{ mt: 2.5 }}>
                <Typography variant="caption" sx={{ fontWeight: 800, textTransform: "uppercase", color: "text.secondary", mb: 1, display: "block" }}>
                  ⚡ Jump to Match Highlights
                </Typography>
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                  {goalEvents.map((evt, idx) => (
                    <Chip
                      key={idx}
                      icon={<SportsSoccerIcon sx={{ fontSize: 16 }} />}
                      label={`${evt.minute}' ${evt.team === "home" ? homeTeam : awayTeam}: ${evt.player || "Goal"}`}
                      onClick={() => handleSeekToMinute(evt.minute)}
                      clickable
                      color="primary"
                      variant="outlined"
                      sx={{ fontWeight: 700, borderRadius: 2 }}
                    />
                  ))}
                </Box>
              </Box>
            )}
          </Box>
        ) : isDisplayingHUD ? (
          /* Rich Live Rendering Progress Dashboard */
          <Box
            sx={{
              py: 5,
              px: 4,
              borderRadius: 3,
              border: `2px solid ${alpha(theme.palette.primary.main, 0.3)}`,
              bgcolor: alpha(theme.palette.primary.main, 0.03),
              boxShadow: "0 8px 32px rgba(99,102,241,0.12)",
              textAlign: "center",
              position: "relative",
              overflow: "hidden",
            }}
          >
            {/* Top Live Badge */}
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 1, mb: 2 }}>
              <Chip
                icon={<AutoAwesomeIcon sx={{ fontSize: 16 }} />}
                label="LIVE 3D REPLAY GENERATION IN PROGRESS"
                size="small"
                color="primary"
                sx={{ fontWeight: 800, letterSpacing: 0.5, px: 1 }}
              />
            </Box>

            {/* Progress Percentage Display */}
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 2, my: 2 }}>
              <Box sx={{ position: "relative", display: "inline-flex" }}>
                <CircularProgress
                  variant="determinate"
                  value={renderProgress}
                  size={80}
                  thickness={5}
                  sx={{ color: theme.palette.primary.main }}
                />
                <Box
                  sx={{
                    top: 0,
                    left: 0,
                    bottom: 0,
                    right: 0,
                    position: "absolute",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Typography variant="h6" component="div" sx={{ fontWeight: 900, color: theme.palette.primary.main }}>
                    {`${Math.round(renderProgress)}%`}
                  </Typography>
                </Box>
              </Box>
            </Box>

            {/* Stage Title */}
            <Typography variant="h6" sx={{ fontWeight: 800, color: "text.primary", mb: 0.5 }}>
              {renderStage}
            </Typography>

            {/* Live Match Minute Counter & Stats */}
            <Typography variant="body2" sx={{ color: "text.secondary", fontWeight: 600, mb: 3 }}>
              ⚽ Match Clock: <strong style={{ color: theme.palette.primary.main }}>{matchMinute}' / 90'</strong> • Score: <strong>{homeTeam} {liveScore[0]} - {liveScore[1]} {awayTeam}</strong>
            </Typography>

            {/* Linear Progress Bar */}
            <Box sx={{ maxWidth: 500, mx: "auto", mb: 2.5 }}>
              <LinearProgress
                variant="determinate"
                value={renderProgress}
                sx={{
                  borderRadius: 3,
                  height: 10,
                  bgcolor: alpha(theme.palette.primary.main, 0.12),
                  "& .MuiLinearProgress-bar": {
                    borderRadius: 3,
                    background: `linear-gradient(90deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                  },
                }}
              />
            </Box>

            {/* Sub-stages / Elapsed Time Info */}
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 3, flexWrap: "wrap" }}>
              <Chip
                icon={<HourglassTopIcon sx={{ fontSize: 16 }} />}
                label={`Elapsed: ${elapsedSeconds}s`}
                size="small"
                variant="outlined"
                sx={{ fontWeight: 700 }}
              />
              <Chip
                icon={<MemoryIcon sx={{ fontSize: 16 }} />}
                label="TiKick MARL • CUDA GPU Accelerated"
                size="small"
                variant="outlined"
                sx={{ fontWeight: 700 }}
              />
              <Chip
                icon={<VideocamIcon sx={{ fontSize: 16 }} />}
                label="H.264 720p HD Stream"
                size="small"
                variant="outlined"
                sx={{ fontWeight: 700 }}
              />
            </Box>
          </Box>
        ) : (
          /* Empty / Generate Replay State */
          <Box
            sx={{
              py: 6,
              px: 3,
              textAlign: "center",
              borderRadius: 3,
              border: `2px dashed ${alpha(theme.palette.primary.main, 0.2)}`,
              bgcolor: alpha(theme.palette.primary.main, 0.02),
            }}
          >
            <VideocamIcon sx={{ fontSize: 56, color: "text.secondary", mb: 1.5 }} />
            <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>
              No 3D Replay Rendered Yet
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary", maxWidth: 480, mx: "auto", mb: 3 }}>
              Generate a physics-accurate 720p HD broadcast replay powered by the Google Research Football 3D engine and TiKick 11v11 AI.
            </Typography>
            {onGenerateReplay && (
              <Button
                variant="contained"
                size="large"
                startIcon={<VideocamIcon />}
                onClick={onGenerateReplay}
                sx={{
                  borderRadius: 3,
                  fontWeight: 800,
                  px: 4,
                  py: 1.2,
                  boxShadow: "0 8px 20px rgba(99,102,241,0.25)",
                }}
              >
                Generate 3D Broadcast Replay
              </Button>
            )}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default MatchVideoReplay;
