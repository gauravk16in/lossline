import React from 'react';
import { Box, Typography } from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCircle, faWifi } from '@fortawesome/free-solid-svg-icons';

interface ConnectionBadgeProps {
  status: 'connecting' | 'live' | 'reconnecting';
}

export const ConnectionBadge: React.FC<ConnectionBadgeProps> = ({ status }) => {
  const config = {
    live: { label: 'Live', color: '#2F9E44', icon: faCircle, animate: true },
    reconnecting: { label: 'Reconnecting\u2026', color: '#E67700', icon: faWifi, animate: false },
    connecting: { label: 'Connecting\u2026', color: '#868E96', icon: faCircle, animate: false },
  }[status];

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
      <Box
        sx={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
        }}
      >
        <FontAwesomeIcon
          icon={config.icon}
          style={{
            fontSize: 7,
            color: config.color,
          }}
        />
        {config.animate && (
          <Box
            sx={{
              position: 'absolute',
              inset: -3,
              borderRadius: '50%',
              border: `1px solid ${config.color}`,
              opacity: 0,
              animation: 'ping 2s cubic-bezier(0,0,0.2,1) infinite',
              '@keyframes ping': {
                '0%': { transform: 'scale(0.8)', opacity: 0.8 },
                '100%': { transform: 'scale(2)', opacity: 0 },
              },
            }}
          />
        )}
      </Box>
      <Typography
        variant="caption"
        sx={{ color: config.color, fontWeight: 500, fontSize: '0.75rem' }}
      >
        {config.label}
      </Typography>
    </Box>
  );
};
