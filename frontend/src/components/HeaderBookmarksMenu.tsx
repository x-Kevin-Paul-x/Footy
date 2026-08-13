import React, { useState, useEffect } from 'react';
import {
  Popover,
  Box,
  Typography,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Button,
  TextField,
  Chip,
  Divider,
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import PushPinIcon from '@mui/icons-material/PushPin';
import StarIcon from '@mui/icons-material/Star';
import AddIcon from '@mui/icons-material/Add';
import { useNavigate } from 'react-router-dom';

interface Bookmark {
  id: string;
  title: string;
  url: string;
  category: 'Team' | 'Player' | 'Analytics' | 'League';
}

const DEFAULT_BOOKMARKS: Bookmark[] = [
  { id: '1', title: 'Arsenal Squad & Tactics', url: '/team-details/Arsenal', category: 'Team' },
  { id: '2', title: 'Manchester City Lineup', url: '/team-details/Manchester%20City', category: 'Team' },
  { id: '3', title: 'League Standings & Form', url: '/league-overview', category: 'League' },
  { id: '4', title: 'Transfer Market Live', url: '/transfer-market', category: 'Analytics' },
  { id: '5', title: 'RL Manager Benchmarks', url: '/ai-benchmarks', category: 'Analytics' },
];

interface Props {
  anchorEl: HTMLElement | null;
  open: boolean;
  onClose: () => void;
}

export const HeaderBookmarksMenu: React.FC<Props> = ({ anchorEl, open, onClose }) => {
  const navigate = useNavigate();
  const [bookmarks, setBookmarks] = useState<Bookmark[]>(() => {
    try {
      const saved = localStorage.getItem('footy_bookmarks');
      return saved ? JSON.parse(saved) : DEFAULT_BOOKMARKS;
    } catch {
      return DEFAULT_BOOKMARKS;
    }
  });

  const [newTitle, setNewTitle] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  useEffect(() => {
    localStorage.setItem('footy_bookmarks', JSON.stringify(bookmarks));
  }, [bookmarks]);

  const handleNavigate = (url: string) => {
    navigate(url);
    onClose();
  };

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setBookmarks((prev) => prev.filter((b) => b.id !== id));
  };

  const handleAddCurrent = () => {
    const currentPath = window.location.pathname;
    const title = newTitle.trim() || `Bookmark ${bookmarks.length + 1}`;
    setBookmarks((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        title,
        url: currentPath,
        category: 'Analytics',
      },
    ]);
    setNewTitle('');
    setIsAdding(false);
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
          width: 340,
          p: 2,
          borderRadius: 3,
          boxShadow: '0 12px 36px rgba(0,0,0,0.22)',
          bgcolor: 'background.paper',
          border: '1px solid rgba(255,255,255,0.08)',
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <StarIcon sx={{ color: '#F7A400', fontSize: 20 }} />
          <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
            Saved Favorites
          </Typography>
        </Box>
        <Chip label={`${bookmarks.length} pinned`} size="small" sx={{ fontWeight: 700, fontSize: '0.75rem' }} />
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
        Quick shortcuts to your favorite clubs, tactics, and reports.
      </Typography>

      <List dense sx={{ maxHeight: 280, overflowY: 'auto', p: 0 }}>
        {bookmarks.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
            No pinned favorites yet.
          </Typography>
        ) : (
          bookmarks.map((bm) => (
            <ListItem
              key={bm.id}
              onClick={() => handleNavigate(bm.url)}
              sx={{
                borderRadius: 2,
                mb: 0.8,
                cursor: 'pointer',
                transition: 'all 0.2s',
                '&:hover': {
                  bgcolor: 'action.hover',
                  transform: 'translateX(4px)',
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 32 }}>
                <PushPinIcon fontSize="small" sx={{ color: '#028391', fontSize: 16 }} />
              </ListItemIcon>
              <ListItemText
                primary={bm.title}
                secondary={bm.category}
                primaryTypographyProps={{ fontWeight: 600, fontSize: '0.85rem', noWrap: true }}
                secondaryTypographyProps={{ fontSize: '0.7rem' }}
              />
              <ListItemSecondaryAction>
                <IconButton edge="end" size="small" onClick={(e) => handleDelete(bm.id, e)}>
                  <DeleteOutlineIcon fontSize="small" sx={{ fontSize: 16, color: 'text.secondary' }} />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))
        )}
      </List>

      <Divider sx={{ my: 1.5 }} />

      {isAdding ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <TextField
            size="small"
            placeholder="Custom Bookmark Title"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            autoFocus
          />
          <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
            <Button size="small" onClick={() => setIsAdding(false)}>
              Cancel
            </Button>
            <Button size="small" variant="contained" onClick={handleAddCurrent}>
              Save Current
            </Button>
          </Box>
        </Box>
      ) : (
        <Button
          fullWidth
          size="small"
          startIcon={<AddIcon />}
          variant="outlined"
          onClick={() => setIsAdding(true)}
          sx={{ borderRadius: 2, textTransform: 'none', fontWeight: 700 }}
        >
          Pin Current Page
        </Button>
      )}
    </Popover>
  );
};
