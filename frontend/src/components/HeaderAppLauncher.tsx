import React from 'react';
import {
  Popover,
  Box,
  Typography,
  Paper,
  Divider,
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import EmojiEventsIcon from '@mui/icons-material/EmojiEvents';
import PeopleIcon from '@mui/icons-material/People';
import PersonPinIcon from '@mui/icons-material/PersonPin';
import SwapHorizontalCircleIcon from '@mui/icons-material/SwapHorizontalCircle';
import SportsSoccerIcon from '@mui/icons-material/SportsSoccer';
import SchoolIcon from '@mui/icons-material/School';
import AssessmentIcon from '@mui/icons-material/Assessment';
import InsightsIcon from '@mui/icons-material/Insights';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { useNavigate } from 'react-router-dom';

interface AppItem {
  name: string;
  desc: string;
  path: string;
  icon: React.ReactNode;
  color: string;
}

const APPS: AppItem[] = [
  { name: 'Dashboard', desc: 'League overview & feed', path: '/', icon: <DashboardIcon />, color: '#028391' },
  { name: 'League Standings', desc: 'Table, form & stats', path: '/league-overview', icon: <EmojiEventsIcon />, color: '#F7A400' },
  { name: 'Player Database', desc: 'Squad attributes & scout', path: '/player-profiles', icon: <PeopleIcon />, color: '#3b82f6' },
  { name: 'Manager Room', desc: 'Tactics & philosophies', path: '/manager-profiles', icon: <PersonPinIcon />, color: '#8b5cf6' },
  { name: 'Transfer Market', desc: 'Deals & bidding war', path: '/transfer-market', icon: <SwapHorizontalCircleIcon />, color: '#10b981' },
  { name: 'Match Center', desc: 'Live scores & reports', path: '/match-reports', icon: <SportsSoccerIcon />, color: '#f43f5e' },
  { name: 'Youth Academy', desc: 'Wonderkids & training', path: '/youth-academy', icon: <SchoolIcon />, color: '#ec4899' },
  { name: 'Season Reports', desc: 'Yearly archives & awards', path: '/season-reports', icon: <AssessmentIcon />, color: '#06b6d4' },
  { name: 'AI Benchmarks', desc: 'RL DQN model evaluation', path: '/ai-benchmarks', icon: <SmartToyIcon />, color: '#6366f1' },
  { name: 'Advanced Analytics', desc: 'Charts & team telemetry', path: '/statistics-analytics', icon: <InsightsIcon />, color: '#14b8a6' },
];

interface Props {
  anchorEl: HTMLElement | null;
  open: boolean;
  onClose: () => void;
}

export const HeaderAppLauncher: React.FC<Props> = ({ anchorEl, open, onClose }) => {
  const navigate = useNavigate();

  const handleNavigate = (path: string) => {
    navigate(path);
    onClose();
  };

  return (
    <Popover
      open={open}
      anchorEl={anchorEl}
      onClose={onClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      PaperProps={{
        sx: {
          width: { xs: 320, sm: 440 },
          p: 2.5,
          borderRadius: 3.5,
          boxShadow: '0 16px 48px rgba(0,0,0,0.25)',
          bgcolor: 'background.paper',
          border: '1px solid rgba(255,255,255,0.08)',
        },
      }}
    >
      <Box sx={{ mb: 2 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
          Footy Module Launcher
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Jump directly to any simulation suite or tactical center
        </Typography>
      </Box>

      <Divider sx={{ mb: 2 }} />

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(3, 1fr)' },
          gap: 1.5,
        }}
      >
        {APPS.map((app) => (
          <Paper
            key={app.path}
            elevation={0}
            onClick={() => handleNavigate(app.path)}
            sx={{
              p: 1.5,
              borderRadius: 2.5,
              border: '1px solid',
              borderColor: 'divider',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              textAlign: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
              '&:hover': {
                bgcolor: 'action.hover',
                borderColor: app.color,
                transform: 'translateY(-3px)',
                boxShadow: `0 8px 20px ${app.color}25`,
              },
            }}
          >
            <Box
              sx={{
                width: 42,
                height: 42,
                borderRadius: 2,
                bgcolor: `${app.color}15`,
                color: app.color,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                mb: 1,
              }}
            >
              {app.icon}
            </Box>
            <Typography variant="body2" sx={{ fontWeight: 700, fontSize: '0.8rem', lineHeight: 1.2 }}>
              {app.name}
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ fontSize: '0.65rem', mt: 0.5, display: { xs: 'none', sm: 'block' } }}
            >
              {app.desc}
            </Typography>
          </Paper>
        ))}
      </Box>
    </Popover>
  );
};
