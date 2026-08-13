import React, { useState } from 'react';
import {
  Menu,
  MenuItem,
  Box,
  Typography,
  Avatar,
  Divider,
  ListItemIcon,
  ListItemText,
  Chip,
  CircularProgress,
} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import SaveIcon from '@mui/icons-material/Save';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import MilitaryTechIcon from '@mui/icons-material/MilitaryTech';
import { useNavigate } from 'react-router-dom';
import { createSaveState } from '../services/api';

interface Props {
  anchorEl: HTMLElement | null;
  open: boolean;
  onClose: () => void;
  onShowToast: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export const HeaderProfileMenu: React.FC<Props> = ({
  anchorEl,
  open,
  onClose,
  onShowToast,
}) => {
  const navigate = useNavigate();
  const [isSaving, setIsSaving] = useState(false);

  const handleQuickSave = async () => {
    setIsSaving(true);
    try {
      const resp = await createSaveState();
      onShowToast(`Simulation state saved successfully! (ID: ${resp.save_id})`, 'success');
    } catch (err) {
      console.error('Save failed', err);
      onShowToast('Failed to create save state snapshot.', 'error');
    } finally {
      setIsSaving(false);
      onClose();
    }
  };

  return (
    <Menu
      anchorEl={anchorEl}
      open={open}
      onClose={onClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      PaperProps={{
        sx: {
          width: 300,
          p: 1.5,
          borderRadius: 3.5,
          boxShadow: '0 16px 40px rgba(0,0,0,0.22)',
          bgcolor: 'background.paper',
          backgroundImage: 'none',
        },
      }}
    >
      {/* Profile Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, p: 1 }}>
        <Avatar
          sx={{
            width: 46,
            height: 46,
            bgcolor: '#01204E',
            color: '#ffffff',
            fontWeight: 800,
            fontSize: '1.1rem',
            border: '2px solid #028391',
            boxShadow: '0 4px 12px rgba(1, 32, 78, 0.4)',
          }}
        >
          FM
        </Avatar>
        <Box sx={{ flex: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 800, lineHeight: 1.2 }}>
            Head Coach & Director
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
            Footy Premier League
          </Typography>
          <Chip
            label="UEFA Pro License"
            size="small"
            icon={<MilitaryTechIcon sx={{ fontSize: '14px !important' }} />}
            sx={{ mt: 0.5, height: 20, fontSize: '0.65rem', fontWeight: 700 }}
          />
        </Box>
      </Box>

      <Divider sx={{ my: 1.5 }} />

      {/* Quick Actions */}
      <MenuItem onClick={() => { navigate('/manager-profiles'); onClose(); }}>
        <ListItemIcon>
          <PersonIcon fontSize="small" sx={{ color: '#028391' }} />
        </ListItemIcon>
        <ListItemText
          primary="Manager Profiles & Tactics"
          primaryTypographyProps={{ fontSize: '0.85rem', fontWeight: 600 }}
        />
      </MenuItem>

      <MenuItem onClick={handleQuickSave} disabled={isSaving}>
        <ListItemIcon>
          {isSaving ? <CircularProgress size={18} /> : <SaveIcon fontSize="small" sx={{ color: '#10b981' }} />}
        </ListItemIcon>
        <ListItemText
          primary={isSaving ? 'Creating Snapshot...' : 'Quick Save Game'}
          secondary="Create timestamped DB save"
          primaryTypographyProps={{ fontSize: '0.85rem', fontWeight: 600 }}
          secondaryTypographyProps={{ fontSize: '0.7rem' }}
        />
      </MenuItem>

      <MenuItem onClick={() => { navigate('/dashboard'); onClose(); }}>
        <ListItemIcon>
          <FolderOpenIcon fontSize="small" sx={{ color: '#F7A400' }} />
        </ListItemIcon>
        <ListItemText
          primary="Load Saved Career"
          secondary="Browse checkpoints & saves"
          primaryTypographyProps={{ fontSize: '0.85rem', fontWeight: 600 }}
          secondaryTypographyProps={{ fontSize: '0.7rem' }}
        />
      </MenuItem>

      <Divider sx={{ my: 1 }} />

      <Box sx={{ p: 1, bgcolor: 'action.hover', borderRadius: 2, textAlign: 'center' }}>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontWeight: 600 }}>
          Footy Engine v2.0 • RL Agent Active
        </Typography>
      </Box>
    </Menu>
  );
};
