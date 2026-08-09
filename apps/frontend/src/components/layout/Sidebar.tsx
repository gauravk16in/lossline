import React from 'react';
import { Box, Typography, Drawer, List, ListItem, ListItemButton } from '@mui/material';
import {
  Home,
  BarChart3,
  AlertTriangle,
  FileText,
  Store,
  Settings,
  Circle,
  ChevronRight,
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';

const SIDEBAR_WIDTH = 200;

interface NavItem {
  label: string;
  path: string;
  icon: React.ElementType;
}

const mainNavItems: NavItem[] = [
  { label: 'Overview',   path: '/',           icon: Home },
  { label: 'Forecasts',  path: '/forecasts',  icon: BarChart3 },
  { label: 'Risks',      path: '/risks',      icon: AlertTriangle },
  { label: 'Decisions',  path: '/decisions',  icon: FileText },
  { label: 'Outlets',    path: '/outlets',     icon: Store },
];

function isActive(path: string, currentPath: string): boolean {
  if (path === '/') return currentPath === '/';
  return currentPath.startsWith(path);
}

export const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const renderNavItem = (item: NavItem) => {
    const active = isActive(item.path, location.pathname);
    const IconComponent = item.icon;

    return (
      <ListItem key={item.path} disablePadding sx={{ mb: 0.25 }}>
        <ListItemButton
          onClick={() => navigate(item.path)}
          sx={{
            borderRadius: '12px',
            px: 1.5,
            py: 1,
            position: 'relative',
            backgroundColor: active
              ? 'rgba(124, 92, 252, 0.12)'
              : 'transparent',
            color: active ? '#A78BFA' : '#8B95A8',
            '&:hover': {
              backgroundColor: active
                ? 'rgba(124, 92, 252, 0.16)'
                : 'rgba(255, 255, 255, 0.04)',
              color: active ? '#A78BFA' : '#F4F7FB',
            },
            transition: 'all 150ms ease',
            display: 'flex',
            alignItems: 'center',
            gap: 1.25,
            /* Active indicator bar on the left */
            '&::before': active
              ? {
                  content: '""',
                  position: 'absolute',
                  left: -12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: 3,
                  height: 24,
                  borderRadius: '0 3px 3px 0',
                  backgroundColor: '#7C5CFC',
                }
              : {},
          }}
        >
          <IconComponent
            size={18}
            strokeWidth={active ? 2.2 : 1.8}
            style={{ flexShrink: 0 }}
          />
          <Typography
            variant="body2"
            sx={{
              fontWeight: active ? 600 : 400,
              color: 'inherit',
              flex: 1,
              fontSize: '0.8125rem',
            }}
          >
            {item.label}
          </Typography>
        </ListItemButton>
      </ListItem>
    );
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: SIDEBAR_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: SIDEBAR_WIDTH,
          boxSizing: 'border-box',
          backgroundColor: '#0E1225',
          borderRight: '1px solid rgba(255,255,255,0.06)',
          boxShadow: 'none',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        },
      }}
    >
      {/* ── Logo ── */}
      <Box sx={{ px: 2.5, pt: 2.5, pb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          {/* Logo icon — stylized wave/chart */}
          <Box
            sx={{
              width: 24, height: 24, borderRadius: '6px',
              background: 'linear-gradient(135deg, #7C5CFC, #A78BFA)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <BarChart3 size={14} color="#fff" strokeWidth={2.5} />
          </Box>
          <Typography
            sx={{
              fontWeight: 700,
              fontSize: '1.125rem',
              letterSpacing: '-0.02em',
              color: '#F4F7FB',
              lineHeight: 1,
            }}
          >
            <span style={{ fontWeight: 800 }}>LOSS</span>
            <span style={{ fontWeight: 400, color: '#8B95A8' }}>Line</span>
          </Typography>
        </Box>
      </Box>

      {/* ── Main Navigation ── */}
      <List sx={{ px: 1.5, py: 0.5, flex: 1 }}>
        {mainNavItems.map(renderNavItem)}
      </List>

      {/* ── Branding Widget ── */}
      <Box
        sx={{
          mx: 1.5,
          mb: 1,
          p: 1.5,
          borderRadius: '12px',
          background: 'linear-gradient(145deg, rgba(124,92,252,0.08), rgba(124,92,252,0.02))',
          border: '1px solid rgba(124,92,252,0.1)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
          <Typography
            sx={{
              color: '#F4F7FB',
              fontWeight: 700,
              fontSize: '0.8125rem',
              lineHeight: 1,
            }}
          >
            LOSSLine AI
          </Typography>
          <Box
            sx={{
              px: 0.625, py: 0.125,
              borderRadius: '4px',
              backgroundColor: 'rgba(124,92,252,0.2)',
              border: '1px solid rgba(124,92,252,0.3)',
            }}
          >
            <Typography variant="caption" sx={{ color: '#A78BFA', fontSize: '0.5625rem', fontWeight: 700, letterSpacing: '0.06em' }}>
              BETA
            </Typography>
          </Box>
        </Box>
        <Typography variant="caption" sx={{ color: '#525C6C', display: 'block', lineHeight: 1.3, fontSize: '0.6875rem' }}>
          Operational intelligence
          <br />
          for restaurants
        </Typography>
      </Box>

      {/* ── System Status ── */}
      <Box sx={{ mx: 1.5, mb: 1, px: 1.5, py: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.25 }}>
          <Circle
            size={7}
            fill="#22C55E"
            color="#22C55E"
            style={{ filter: 'drop-shadow(0 0 3px rgba(34,197,94,0.5))', animation: 'pulse 2s ease-in-out infinite' }}
          />
          <Typography variant="body2" sx={{ color: '#F4F7FB', fontWeight: 500, fontSize: '0.8125rem' }}>
            System Live
          </Typography>
        </Box>
        <Typography variant="caption" sx={{ color: '#525C6C', fontSize: '0.6875rem', pl: 1.75 }}>
          All systems operational
        </Typography>
      </Box>

      {/* ── Settings ── */}
      <Box
        onClick={() => navigate('/settings')}
        sx={{
          mx: 1.5, mb: 1.5, px: 1.5, py: 1,
          borderRadius: '10px',
          display: 'flex', alignItems: 'center', gap: 1,
          cursor: 'pointer',
          transition: 'background-color 150ms ease',
          '&:hover': { backgroundColor: 'rgba(255,255,255,0.04)' },
        }}
      >
        <Settings size={16} color="#525C6C" />
        <Typography variant="body2" sx={{ color: '#8B95A8', flex: 1, fontSize: '0.8125rem' }}>
          Settings
        </Typography>
        <ChevronRight size={14} color="#525C6C" />
      </Box>
    </Drawer>
  );
};
