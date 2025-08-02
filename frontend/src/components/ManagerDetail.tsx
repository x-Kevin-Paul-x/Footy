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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Paper,
} from "@mui/material";
import { getManagerDetails } from "../services/api";
import type { Manager } from "../services/api";

const ManagerDetail: React.FC = () => {
  const { managerName } = useParams<{ managerName: string }>();
  const [manager, setManager] = useState<Manager | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchManager = async () => {
      if (managerName) {
        setLoading(true);
        setError(null);
        try {
          const data = await getManagerDetails(managerName);
          setManager(data);
        } catch (err: any) {
          setError(`Failed to fetch manager details for ${managerName}.`);
          console.error("Error fetching manager details:", err);
        } finally {
          setLoading(false);
        }
      }
    };
    fetchManager();
  }, [managerName]);

  if (loading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Loading manager details for {managerName || "selected manager"}...</Typography>
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

  if (!manager) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <Typography variant="h6">No manager data available.</Typography>
        <Typography variant="body2">Please ensure the manager name is correct.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>Manager Profile: {manager.name}</Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
            <Avatar sx={{ mr: 2, width: 60, height: 60 }}>{manager.name[0]}</Avatar>
            <Box>
              <Typography variant="h5">{manager.name}</Typography>
              {manager.team && (
                <Typography variant="subtitle1" color="text.secondary">
                  Team: <Link to={`/team-details/${manager.team}`} style={{ textDecoration: 'none', color: 'inherit' }}>{manager.team}</Link>
                </Typography>
              )}
              <Typography variant="subtitle1" color="text.secondary">Experience: {manager.experience} years</Typography>
              <Typography variant="body2">Formation: {manager.formation}</Typography>
              <Typography variant="body2">Transfer Success Rate: {(manager.transfer_success_rate * 100).toFixed(1)}%</Typography>
            </Box>
          </Box>

          <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>Market Trends</Typography>
          <TableContainer component={Paper} sx={{ mb: 2 }}>
            <Table size="small">
              <TableBody>
                {manager.market_trends && Object.keys(manager.market_trends).length > 0 ? (
                  Object.entries(manager.market_trends).map(([key, value]) => (
                    <TableRow key={key}>
                      <TableCell>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</TableCell>
                      <TableCell align="right">{typeof value === 'number' ? value.toFixed(2) : String(value)}</TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={2}>No market trends data available.</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          {/* Add more manager-specific details here as available from backend */}
          {/* For example:
          <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>Achievements</Typography>
          <List>
            <ListItem><ListItemText primary="League Titles: 3" /></ListItem>
            <ListItem><ListItemText primary="Cup Wins: 2" /></ListItem>
          </List>
          */}
        </CardContent>
      </Card>
    </Box>
  );
};

export default ManagerDetail;
