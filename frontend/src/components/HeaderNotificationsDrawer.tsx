import React, { useState } from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  Chip,
  Button,
  Divider,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import SwapHorizontalCircleIcon from '@mui/icons-material/SwapHorizontalCircle';
import SportsSoccerIcon from '@mui/icons-material/SportsSoccer';
import EmojiEventsIcon from '@mui/icons-material/EmojiEvents';
import SchoolIcon from '@mui/icons-material/School';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';

export interface NotificationItem {
  id: string;
  type: 'transfer' | 'match' | 'trophy' | 'youth' | 'system';
  title: string;
  message: string;
  timestamp: string;
  unread: boolean;
}

const INITIAL_NOTIFICATIONS: NotificationItem[] = [
  {
    id: '1',
    type: 'transfer',
    title: 'Blockbuster Transfer Complete',
    message: 'Daniel Vargas transferred from Aston Villa to Arsenal for £42.5M.',
    timestamp: '5m ago',
    unread: true,
  },
  {
    id: '2',
    type: 'match',
    title: 'Matchday 38 Results In',
    message: 'Manchester City defeated Chelsea 3-1 to secure the Premier League title.',
    timestamp: '18m ago',
    unread: true,
  },
  {
    id: '3',
    type: 'trophy',
    title: 'Manager of the Season',
    message: 'Bradley Rust awarded Manager of the Season with 79% win rate.',
    timestamp: '1h ago',
    unread: true,
  },
  {
    id: '4',
    type: 'youth',
    title: 'Academy Wonderkid Emerged',
    message: 'Terry Davidson (17yo ST, Potential 90) promoted to senior training.',
    timestamp: '3h ago',
    unread: false,
  },
  {
    id: '5',
    type: 'system',
    title: 'DQN Checkpoint Updated',
    message: 'Model dqn_best.pt achieved new high evaluation reward (+14.2).',
    timestamp: '5h ago',
    unread: false,
  },
];

interface Props {
  open: boolean;
  onClose: () => void;
  unreadCount: number;
  setUnreadCount: (count: number) => void;
}

export const HeaderNotificationsDrawer: React.FC<Props> = ({
  open,
  onClose,
  unreadCount,
  setUnreadCount,
}) => {
  const [notifications, setNotifications] = useState<NotificationItem[]>(INITIAL_NOTIFICATIONS);

  const getIcon = (type: NotificationItem['type']) => {
    switch (type) {
      case 'transfer':
        return <SwapHorizontalCircleIcon sx={{ color: '#10b981' }} />;
      case 'match':
        return <SportsSoccerIcon sx={{ color: '#3b82f6' }} />;
      case 'trophy':
        return <EmojiEventsIcon sx={{ color: '#F7A400' }} />;
      case 'youth':
        return <SchoolIcon sx={{ color: '#ec4899' }} />;
      default:
        return <NotificationsActiveIcon sx={{ color: '#8b5cf6' }} />;
    }
  };

  const handleMarkAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, unread: false })));
    setUnreadCount(0);
  };

  const handleClearAll = () => {
    setNotifications([]);
    setUnreadCount(0);
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: { xs: '100%', sm: 380 },
          p: 2.5,
          bgcolor: 'background.paper',
          backgroundImage: 'none',
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <NotificationsActiveIcon sx={{ color: '#028391' }} />
          <Typography variant="h6" sx={{ fontWeight: 800 }}>
            Activity Feed
          </Typography>
          {unreadCount > 0 && (
            <Chip
              label={`${unreadCount} new`}
              size="small"
              sx={{ bgcolor: '#f43f5e', color: '#fff', fontWeight: 800, height: 20, fontSize: '0.7rem' }}
            />
          )}
        </Box>
        <IconButton size="small" onClick={onClose}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
        Live simulation events, transfer alerts, and managerial announcements
      </Typography>

      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <Button
          size="small"
          startIcon={<CheckCircleOutlineIcon />}
          onClick={handleMarkAllRead}
          disabled={unreadCount === 0}
          sx={{ textTransform: 'none', fontWeight: 700, fontSize: '0.75rem' }}
        >
          Mark all read
        </Button>
        <Button
          size="small"
          color="error"
          onClick={handleClearAll}
          disabled={notifications.length === 0}
          sx={{ textTransform: 'none', fontWeight: 700, fontSize: '0.75rem' }}
        >
          Clear all
        </Button>
      </Box>

      <Divider sx={{ mb: 1.5 }} />

      <List sx={{ p: 0, overflowY: 'auto', flex: 1 }}>
        {notifications.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <Typography variant="body2" color="text.secondary">
              No recent notifications.
            </Typography>
          </Box>
        ) : (
          notifications.map((item) => (
            <ListItem
              key={item.id}
              sx={{
                p: 1.5,
                mb: 1.2,
                borderRadius: 2.5,
                bgcolor: item.unread ? 'action.hover' : 'transparent',
                border: '1px solid',
                borderColor: item.unread ? 'primary.main' : 'divider',
                flexDirection: 'column',
                alignItems: 'flex-start',
                transition: 'all 0.2s',
              }}
            >
              <Box sx={{ display: 'flex', width: '100%', alignItems: 'center', gap: 1.2, mb: 0.5 }}>
                <ListItemIcon sx={{ minWidth: 28 }}>{getIcon(item.type)}</ListItemIcon>
                <Typography variant="subtitle2" sx={{ fontWeight: 800, flex: 1, fontSize: '0.85rem' }}>
                  {item.title}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                  {item.timestamp}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem', pl: 4.8 }}>
                {item.message}
              </Typography>
            </ListItem>
          ))
        )}
      </List>
    </Drawer>
  );
};
