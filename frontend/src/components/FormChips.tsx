import React from "react";
import { Box, Chip, Tooltip } from "@mui/material";

interface FormChipsProps {
  form: string | string[]; // e.g. "WWLDW" or ["W","W","L","D","W"]
  size?: "small" | "medium";
}

/**
 * Renders last-n match form as colored chips.
 * W = win (green), D = draw (grey), L = loss (red)
 */
const FormChips: React.FC<FormChipsProps> = ({ form, size = "small" }) => {
  const results = Array.isArray(form) ? form : form.split("");
  return (
    <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
      {results.map((r, i) => {
        const key = `${r}-${i}`;
        const label = r.toUpperCase();
        let color: "success" | "default" | "error" = "default";
        if (label === "W") color = "success";
        if (label === "L") color = "error";
        // D stays default (grey)
        return (
          <Tooltip key={key} title={label}>
            <Chip
              label={label}
              size={size}
              color={color}
              aria-label={`Match ${i + 1}: ${label}`}
              sx={{
                width: 28,
                height: 28,
                minWidth: 28,
                padding: 0,
                borderRadius: "50%",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: size === "small" ? "0.7rem" : "0.8rem",
                lineHeight: 1,
              }}
            />
          </Tooltip>
        );
      })}
    </Box>
  );
};

export default FormChips;
