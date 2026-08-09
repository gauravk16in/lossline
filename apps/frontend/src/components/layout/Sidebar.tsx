import React from 'react';
import {
  Box,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  Divider,
  Badge,
} from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faGaugeHigh,
  faTriangleExclamation,
  faStore,
  faCheck,
  faChartLine,
} from '@fortawesome/free-solid-svg-icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { ConnectionBadge } from '../common/ConnectionBadge';

const SIDEBAR_WIDTH = 220;

interface SidebarProps {
  activeIncidentCount: number;
  connectionStatus: 'connecting' | 'live' | 'reconnecting';
}

interface NavItem {
  label: string;
  path: string;
  icon: typeof faGaugeHigh;
  badgeCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeIncidentCount,
  connectionStatus,
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  const navItems: NavItem[] = [
    { label: 'Overview', path: '/', icon: faGaugeHigh },
    { label: 'Predictive Today', path: '/predictive', icon: faChartLine },
    {
      label: 'Incidents',
      path: '/incidents',
      icon: faTriangleExclamation,
      badgeCount: activeIncidentCount || undefined,
    },
    { label: 'Outlets', path: '/outlets', icon: faStore },
    { label: 'Actions', path: '/actions', icon: faCheck },
  ];

  function isActive(path: string) {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  }

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: SIDEBAR_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: SIDEBAR_WIDTH,
          boxSizing: 'border-box',
          backgroundColor: '#FFFFFF',
          borderRight: '1px solid rgba(0,0,0,0.06)',
          boxShadow: 'none',
          display: 'flex',
          flexDirection: 'column',
        },
      }}
    >
      {/* Logo */}
      <Box sx={{ px: 2.5, py: 2.5 }}>
        <Typography
          sx={{
            fontWeight: 700,
            fontSize: '1.0625rem',
            letterSpacing: '-0.02em',
            color: 'text.primary',
            lineHeight: 1,
          }}
        >
          LOSSLine
        </Typography>
        <Typography
          variant="caption"
          sx={{ color: 'text.secondary', mt: 0.25, display: 'block' }}
        >
          Operational Intelligence
        </Typography>
      </Box>

      <Divider />

      {/* Nav */}
      <List sx={{ px: 1.5, py: 1.5, flex: 1 }}>
        {navItems.map(item => {
          const active = isActive(item.path);
          return (
            <ListItem key={item.path} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                onClick={() => navigate(item.path)}
                sx={{
                  borderRadius: 2,
                  px: 1.5,
                  py: 1,
                  backgroundColor: active ? 'rgba(59,91,219,0.08)' : 'transparent',
                  color: active ? 'primary.main' : 'text.secondary',
                  '&:hover': {
                    backgroundColor: active ? 'rgba(59,91,219,0.10)' : 'rgba(0,0,0,0.04)',
                    color: active ? 'primary.main' : 'text.primary',
                  },
                  transition: 'all 150ms ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                }}
              >
                <FontAwesomeIcon
                  icon={item.icon}
                  style={{
                    fontSize: 14,
                    width: 16,
                    color: active ? '#3B5BDB' : '#868E96',
                    flexShrink: 0,
                  }}
                />
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: active ? 600 : 400,
                    color: 'inherit',
                    flex: 1,
                  }}
                >
                  {item.label}
                </Typography>
                {item.badgeCount != null && item.badgeCount > 0 && (
                  <Badge
                    badgeContent={item.badgeCount}
                    sx={{
                      '& .MuiBadge-badge': {
                        backgroundColor: '#E03131',
                        color: '#fff',
                        fontSize: '0.625rem',
                        fontWeight: 700,
                        minWidth: 18,
                        height: 18,
                        borderRadius: 9,
                        position: 'static',
                        transform: 'none',
                      },
                    }}
                  />
                )}
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>

      <Divider />

      {/* Bottom section */}
      <Box sx={{ px: 2.5, py: 2 }}>
        <ConnectionBadge status={connectionStatus} />
        <Typography
          variant="caption"
          sx={{ color: 'text.secondary', display: 'block', mt: 0.75 }}
        >
          Demo Scenario
        </Typography>
      </Box>
    </Drawer>
  );
};
