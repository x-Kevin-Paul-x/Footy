import React from "react";
import { Box, Avatar, Typography } from "@mui/material";
import { Link } from "react-router-dom";

interface TeamCellProps {
  id: string | number;
  name: string;
  crestUrl?: string | null;
  alt?: string;
}

/**
 * TeamCell - show team crest (if available) and name as a link.
 * No initials avatar fallback to keep table layout clean.
 */
const TeamCell: React.FC<TeamCellProps> = ({ id, name, crestUrl, alt }) => {
  return (
    <Box sx={{ display: "flex", alignItems: "center" }}>
      <Link
        to={`/team-details/${id}`}
        style={{
          display: "inline-flex",
          alignItems: "center",
          textDecoration: "none",
          color: "inherit",
        }}
        aria-label={`View details for ${name}`}
      >
        {crestUrl ? (
          <Avatar src={crestUrl} alt={alt ?? name} sx={{ width: 36, height: 36, mr: 1 }} />
        ) : null}
        <Typography variant="body2" component="span">
          {name}
        </Typography>
      </Link>
    </Box>
  );
};

export default TeamCell;
