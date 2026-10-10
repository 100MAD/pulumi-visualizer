import { useState } from 'react';
import {
  Box, Drawer, AppBar, Toolbar, Typography, List, ListItem,
  ListItemButton, ListItemIcon, ListItemText, IconButton,
  Avatar, Divider, useMediaQuery, useTheme, Tooltip,
} from '@mui/material';
import LayersIcon from '@mui/icons-material/Layers';
import MenuIcon from '@mui/icons-material/Menu';
import LogoutIcon from '@mui/icons-material/Logout';
import { useAuth } from './App.jsx';

const DRAWER_W = 220;

export default function Layout({ children }) {
  const { username, signOut } = useAuth();
  const muiTheme = useTheme();
  const isLg = useMediaQuery(muiTheme.breakpoints.up('md'));
  const [mobileOpen, setMobileOpen] = useState(false);

  const drawer = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ px: 3, py: 2.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Box sx={{
          width: 36, height: 36,
          background: 'linear-gradient(135deg,#6366f1,#06b6d4)',
          borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 4px 16px rgba(99,102,241,0.4)',
        }}>
          <LayersIcon sx={{ color: '#fff', fontSize: 20 }} />
        </Box>
        <Typography variant="h6" sx={{ fontWeight: 800, letterSpacing: '-0.02em', background: 'linear-gradient(90deg,#818cf8,#06b6d4)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Pulumi
        </Typography>
      </Box>

      <Divider sx={{ borderColor: 'rgba(148,163,184,0.08)', mx: 2 }} />

      <List sx={{ px: 1.5, pt: 1.5, flex: 1 }}>
        <ListItem disablePadding sx={{ mb: 0.5 }}>
          <ListItemButton
            selected
            sx={{
              borderRadius: 2, py: 1.1,
              '&.Mui-selected': {
                background: 'rgba(99,102,241,0.14)',
                '& .MuiListItemIcon-root': { color: '#818cf8' },
                '& .MuiListItemText-primary': { color: '#c7d2fe', fontWeight: 700 },
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: 36, color: '#64748b' }}>
              <LayersIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText
              primary="Stacks"
              primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: 500 }}
            />
          </ListItemButton>
        </ListItem>
      </List>

      <Divider sx={{ borderColor: 'rgba(148,163,184,0.08)', mx: 2 }} />
      <Box sx={{ px: 2, py: 2, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Avatar sx={{ width: 32, height: 32, fontSize: '0.75rem', fontWeight: 700, background: 'linear-gradient(135deg,#6366f1,#06b6d4)' }}>
          {(username || '').slice(0, 2).toUpperCase()}
        </Avatar>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.8rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {username}
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem' }}>
            Operator
          </Typography>
        </Box>
        <Tooltip title="Sign out">
          <IconButton size="small" onClick={signOut} sx={{ color: 'text.secondary', '&:hover': { color: 'error.main' } }}>
            <LogoutIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }} className="gradient-bg">
      {isLg && (
        <Drawer variant="permanent" sx={{ width: DRAWER_W, flexShrink: 0, '& .MuiDrawer-paper': { width: DRAWER_W, boxSizing: 'border-box' } }}>
          {drawer}
        </Drawer>
      )}

      {!isLg && (
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          sx={{ '& .MuiDrawer-paper': { width: DRAWER_W } }}
        >
          {drawer}
        </Drawer>
      )}

      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {!isLg && (
          <AppBar position="sticky" sx={{ zIndex: 100 }}>
            <Toolbar sx={{ minHeight: '56px !important' }}>
              <IconButton edge="start" onClick={() => setMobileOpen(true)} sx={{ mr: 1, color: 'text.primary' }}>
                <MenuIcon />
              </IconButton>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <LayersIcon sx={{ color: '#6366f1', fontSize: 20 }} />
                <Typography variant="h6" sx={{ fontWeight: 800, fontSize: '1rem' }}>Pulumi</Typography>
              </Box>
            </Toolbar>
          </AppBar>
        )}
        <Box sx={{ flex: 1, p: { xs: 2, md: 3 }, maxWidth: 1200, mx: 'auto', width: '100%' }}>
          {children}
        </Box>
      </Box>
    </Box>
  );
}
