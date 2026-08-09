import React from 'react';
import { Box, Typography, Select, MenuItem } from '@mui/material';
import { MapPin, Calendar, Circle } from 'lucide-react';

/**
 * TopBar — outlet picker, date picker, and live status indicator.
 * Positioned at the top of the center content area.
 */
export const TopBar: React.FC = () => {
  return (
    <Box
      id="top-bar"
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        py: 1.5,
        px: 0,
        mb: 2,
      }}
    >
      {/* Spacer for left alignment */}
      <Box sx={{ flex: 1 }} />

      {/* Center: Pickers */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
        {/* Outlet Picker */}
        <Select
          value="indiranagar"
          size="small"
          IconComponent={() => null}
          sx={{
            backgroundColor: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '10px',
            color: '#F4F7FB',
            fontSize: '0.8125rem',
            fontWeight: 500,
            minWidth: 180,
            '& .MuiSelect-select': {
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              py: 0.875,
              px: 1.5,
            },
            '& .MuiOutlinedInput-notchedOutline': { border: 'none' },
            '&:hover': {
              backgroundColor: 'rgba(255,255,255,0.06)',
            },
          }}
          renderValue={() => (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <MapPin size={14} color="#8B95A8" />
              <span>Indiranagar Outlet</span>
            </Box>
          )}
        >
          <MenuItem value="indiranagar">Indiranagar Outlet</MenuItem>
          <MenuItem value="koramangala">Koramangala Outlet</MenuItem>
          <MenuItem value="hsr">HSR Layout Outlet</MenuItem>
        </Select>

        {/* Date Picker */}
        <Select
          value="today"
          size="small"
          IconComponent={() => null}
          sx={{
            backgroundColor: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '10px',
            color: '#F4F7FB',
            fontSize: '0.8125rem',
            fontWeight: 500,
            minWidth: 160,
            '& .MuiSelect-select': {
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              py: 0.875,
              px: 1.5,
            },
            '& .MuiOutlinedInput-notchedOutline': { border: 'none' },
            '&:hover': {
              backgroundColor: 'rgba(255,255,255,0.06)',
            },
          }}
          renderValue={() => (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Calendar size={14} color="#8B95A8" />
              <span>Today, 12 May</span>
            </Box>
          )}
        >
          <MenuItem value="today">Today, 12 May</MenuItem>
          <MenuItem value="yesterday">Yesterday, 11 May</MenuItem>
          <MenuItem value="tomorrow">Tomorrow, 13 May</MenuItem>
        </Select>
      </Box>

      {/* Right: Live Status */}
      <Box
        sx={{
          flex: 1,
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
          gap: 1,
        }}
      >
        <Circle
          size={8}
          fill="#22C55E"
          color="#22C55E"
          style={{
            filter: 'drop-shadow(0 0 4px rgba(34,197,94,0.6))',
            animation: 'pulse 2s ease-in-out infinite',
          }}
        />
        <Box>
          <Typography
            variant="body2"
            sx={{
              fontWeight: 600,
              color: '#F4F7FB',
              fontSize: '0.8125rem',
              lineHeight: 1.2,
            }}
          >
            Live
          </Typography>
          <Typography
            variant="caption"
            sx={{
              color: '#8B95A8',
              fontSize: '0.6875rem',
              lineHeight: 1.2,
              display: 'block',
            }}
          >
            Updated 08:45 AM
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};
