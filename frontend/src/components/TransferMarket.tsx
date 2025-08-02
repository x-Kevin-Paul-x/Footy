import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Modal,
  Stepper,
  Step,
  StepLabel,
  CircularProgress,
  Alert,
} from "@mui/material";
import { getSeasonReportData } from "../services/api";
import type { SeasonReport } from "../services/api"; // Type-only import

const steps = ["Window Open", "Negotiations", "Window Close"];

const TransferMarket: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const [activeStep] = useState(1); // Removed setActiveStep as it's unused
  const [transfers, setTransfers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch latest season (demo: 2025)
    getSeasonReportData(2025)
      .then((data: SeasonReport) => {
        setTransfers(data.transfers?.all_completed_transfers || []);
        setLoading(false);
      })
      .catch(() => {
        setError("Failed to fetch transfer market data.");
        setLoading(false);
      });
  }, []);

  const handleOpen = (index: number) => { // Renamed idx to index
    setSelected(index);
    setOpen(true);
  };
  const handleClose = () => setOpen(false);

  return (
    <Box sx={{ p: 3, maxWidth: 700, mx: "auto" }}>
      <Typography variant="h4" gutterBottom>Transfer Market</Typography>
      <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
        {steps.map((label, idx) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      {loading && <CircularProgress />}
      {error && <Alert severity="error">{error}</Alert>}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Player</TableCell>
              <TableCell>From</TableCell>
              <TableCell>To</TableCell>
              <TableCell>Fee</TableCell>
              <TableCell>Bid</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {transfers.map((t, idx) => (
              <TableRow key={idx}>
                <TableCell>{t.player || t.name}</TableCell>
                <TableCell>{t.from || t.seller || t.old_team}</TableCell>
                <TableCell>{t.to || t.buyer || t.new_team}</TableCell>
                <TableCell>{t.fee || t.price || t.amount || "-"}</TableCell>
                <TableCell>
                  <Button variant="contained" size="small" onClick={() => handleOpen(idx)}>
                    Bid
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Modal open={open} onClose={handleClose}>
        <Box sx={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          bgcolor: "background.paper",
          boxShadow: 24,
          p: 4,
          minWidth: 300,
        }}>
          <Typography variant="h6" gutterBottom>Place Bid</Typography>
          {selected !== null && transfers[selected] && (
            <>
              <Typography variant="body1">
                Player: {transfers[selected].player || transfers[selected].name}
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                From: {transfers[selected].from || transfers[selected].seller || transfers[selected].old_team} → To: {transfers[selected].to || transfers[selected].buyer || transfers[selected].new_team}
              </Typography>
              <Button variant="contained" color="primary" onClick={handleClose}>
                Submit Bid (placeholder)
              </Button>
            </>
          )}
        </Box>
      </Modal>
    </Box>
  );
};

export default TransferMarket;
