// FormationViewer.tsx
import React from "react";
import { Box, Typography } from "@mui/material";

interface PlayerPosition {
  name: string;
  position: string;
  x: number;
  y: number;
  number?: number;
  isInjured?: boolean;
  hasCard?: "yellow" | "red";
}

interface FormationViewerProps {
  teamName: string;
  formation: string;
  players: PlayerPosition[];
}

const pitchWidth = 600;
const pitchHeight = 400;

const FormationViewer: React.FC<FormationViewerProps> = ({
  teamName,
  formation,
  players,
}) => {
  return (
    <Box sx={{ p: 2, bgcolor: "#eaf6ff", borderRadius: 2, mb: 2 }}>
      <Typography variant="h6" gutterBottom>
        {teamName} Formation: {formation}
      </Typography>
      <Box
        sx={{
          position: "relative",
          width: pitchWidth,
          height: pitchHeight,
          bgcolor: "#4caf50",
          borderRadius: 3,
          mx: "auto",
          boxShadow: 2,
        }}
      >
        {/* Pitch lines */}
        <Box
          sx={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            border: "2px solid #fff",
            borderRadius: 3,
          }}
        />
        {/* Players */}
        {players.map((p, idx) => (
          <Box
            key={idx}
            sx={{
              position: "absolute",
              left: `${p.x * pitchWidth}px`,
              top: `${p.y * pitchHeight}px`,
              width: 40,
              height: 40,
              bgcolor: p.isInjured ? "#f44336" : "#2196f3",
              color: "#fff",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: "bold",
              boxShadow: 3,
              border: p.hasCard === "yellow" ? "3px solid yellow" : p.hasCard === "red" ? "3px solid red" : "none",
            }}
            title={`${p.name} (${p.position})`}
          >
            {p.number ?? idx + 1}
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default FormationViewer;
