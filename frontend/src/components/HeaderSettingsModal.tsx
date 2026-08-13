import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Typography,
  Switch,
  FormControlLabel,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Divider,
  Slider,
  TextField,
  Chip,
} from '@mui/material';
import TuneIcon from '@mui/icons-material/Tune';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import SpeedIcon from '@mui/icons-material/Speed';
import StorageIcon from '@mui/icons-material/Storage';
import { getMlModels, type MlModelItem } from '../services/api';

interface Props {
  open: boolean;
  onClose: () => void;
  onShowToast: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export const HeaderSettingsModal: React.FC<Props> = ({ open, onClose, onShowToast }) => {
  const [models, setModels] = useState<MlModelItem[]>([]);
  const [activeModel, setActiveModel] = useState<string>(() => {
    return localStorage.getItem('footy_active_model') || 'dqn_best.pt';
  });
  const [fastMode, setFastMode] = useState<boolean>(() => {
    return localStorage.getItem('footy_fast_mode') !== 'false';
  });
  const [matchSpeed, setMatchSpeed] = useState<number>(() => {
    return Number(localStorage.getItem('footy_match_speed') || '50');
  });
  const [enableSound, setEnableSound] = useState<boolean>(() => {
    return localStorage.getItem('footy_enable_sound') !== 'false';
  });
  const [enableToasts, setEnableToasts] = useState<boolean>(() => {
    return localStorage.getItem('footy_enable_toasts') !== 'false';
  });
  const [apiUrl, setApiUrl] = useState<string>(() => {
    return localStorage.getItem('footy_api_url') || 'http://localhost:5001';
  });

  useEffect(() => {
    if (open) {
      getMlModels()
        .then((mList) => setModels(mList))
        .catch(() => {
          // Fallback defaults
          setModels([
            { name: 'dqn_best.pt', path: 'backend/src/ml/models/dqn_best.pt', size_bytes: 176377, modified_at: '' },
            { name: 'dqn_final.pt', path: 'backend/src/ml/models/dqn_final.pt', size_bytes: 176407, modified_at: '' },
          ]);
        });
    }
  }, [open]);

  const handleSave = () => {
    localStorage.setItem('footy_active_model', activeModel);
    localStorage.setItem('footy_fast_mode', String(fastMode));
    localStorage.setItem('footy_match_speed', String(matchSpeed));
    localStorage.setItem('footy_enable_sound', String(enableSound));
    localStorage.setItem('footy_enable_toasts', String(enableToasts));
    localStorage.setItem('footy_api_url', apiUrl);

    onShowToast('Settings saved successfully!', 'success');
    onClose();
  };

  const handleResetDefaults = () => {
    setActiveModel('dqn_best.pt');
    setFastMode(true);
    setMatchSpeed(50);
    setEnableSound(true);
    setEnableToasts(true);
    setApiUrl('http://localhost:5001');
    onShowToast('Settings reset to defaults.', 'info');
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3.5,
          p: 1.5,
          bgcolor: 'background.paper',
          backgroundImage: 'none',
        },
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1.2, pb: 1 }}>
        <TuneIcon sx={{ color: '#028391' }} />
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 800, lineHeight: 1.2 }}>
            Footy Simulation Settings
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Configure reinforcement learning agents, engine speed, and telemetry
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 2 }}>
        {/* Section 1: AI & ML Engine */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <SmartToyIcon sx={{ color: '#6366f1', fontSize: 20 }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
              AI Manager & Checkpoint
            </Typography>
          </Box>
          <FormControl fullWidth size="small">
            <InputLabel id="active-model-label">Active DQN Checkpoint</InputLabel>
            <Select
              labelId="active-model-label"
              value={activeModel}
              label="Active DQN Checkpoint"
              onChange={(e) => setActiveModel(e.target.value)}
            >
              {models.length > 0 ? (
                models.map((m) => (
                  <MenuItem key={m.name} value={m.name}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        {m.name}
                      </Typography>
                      <Chip label="Action-Masked Dueling DQN" size="small" sx={{ fontSize: '0.65rem', height: 20 }} />
                    </Box>
                  </MenuItem>
                ))
              ) : (
                <MenuItem value="dqn_best.pt">dqn_best.pt (Default)</MenuItem>
              )}
            </Select>
          </FormControl>
        </Box>

        <Divider />

        {/* Section 2: Engine Speed & Simulation */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <SpeedIcon sx={{ color: '#F7A400', fontSize: 20 }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
              Simulation Engine Speed
            </Typography>
          </Box>
          <FormControlLabel
            control={<Switch checked={fastMode} onChange={(e) => setFastMode(e.target.checked)} color="primary" />}
            label={
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                  Turbo Simulation Mode
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Bypasses frame delays for 100x match generation speed
                </Typography>
              </Box>
            }
          />
          {!fastMode && (
            <Box sx={{ mt: 1.5, px: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Match Tick Delay ({matchSpeed}ms)
              </Typography>
              <Slider
                value={matchSpeed}
                min={10}
                max={200}
                step={10}
                onChange={(_, val) => setMatchSpeed(val as number)}
                valueLabelDisplay="auto"
              />
            </Box>
          )}
        </Box>

        <Divider />

        {/* Section 3: Audio & Telemetry */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <StorageIcon sx={{ color: '#10b981', fontSize: 20 }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
              Telemetry & Backend API
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <FormControlLabel
              control={<Switch checked={enableToasts} onChange={(e) => setEnableToasts(e.target.checked)} />}
              label={<Typography variant="body2" sx={{ fontWeight: 600 }}>Enable Live Toast Notifications</Typography>}
            />
            <FormControlLabel
              control={<Switch checked={enableSound} onChange={(e) => setEnableSound(e.target.checked)} />}
              label={<Typography variant="body2" sx={{ fontWeight: 600 }}>Enable Whistle & Goal Sound FX</Typography>}
            />
            <TextField
              size="small"
              label="Backend API Base URL"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              sx={{ mt: 1 }}
            />
          </Box>
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2, display: 'flex', justifyContent: 'space-between' }}>
        <Button size="small" color="inherit" onClick={handleResetDefaults}>
          Reset Defaults
        </Button>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button size="small" onClick={onClose}>
            Cancel
          </Button>
          <Button size="small" variant="contained" onClick={handleSave} sx={{ fontWeight: 800 }}>
            Save Changes
          </Button>
        </Box>
      </DialogActions>
    </Dialog>
  );
};
