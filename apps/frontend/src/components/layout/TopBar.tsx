import React from 'react';
import { Box, Typography, Select, MenuItem, IconButton, Tooltip } from '@mui/material';
import { MapPin, Calendar, Circle } from 'lucide-react';
import { RefreshCw } from 'lucide-react';
import { useDashboard } from '../../state/DashboardContext';

/**
 * TopBar — outlet picker, date picker, and live status indicator.
 * Positioned at the top of the center content area.
 */
export const TopBar: React.FC = () => {
  const { restaurants, outletId, setOutletId, serviceWindow, setServiceWindow, serviceWindows, loading, error, refreshedAt, refresh } = useDashboard();
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
          value={outletId}
          onChange={(event) => setOutletId(event.target.value)}
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
          renderValue={(value) => (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <MapPin size={14} color="#8B95A8" />
              <span>{restaurants.find((item) => item.id === value)?.name || value}</span>
            </Box>
          )}
        >
          {restaurants.map((restaurant) => <MenuItem key={restaurant.id} value={restaurant.id}>{restaurant.name}</MenuItem>)}
        </Select>

        {/* Service-window picker */}
        <Select
          value={serviceWindow}
          onChange={(event) => setServiceWindow(event.target.value)}
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
              <span>{serviceWindow}</span>
            </Box>
          )}
        >
          {serviceWindows.map((window) => <MenuItem key={window} value={window}>{window[0] + window.slice(1).toLowerCase()}</MenuItem>)}
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
          fill={error ? '#EF4444' : '#22C55E'}
          color={error ? '#EF4444' : '#22C55E'}
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
            {error ? 'Offline' : loading ? 'Updating' : 'Live'}
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
            {error || (refreshedAt ? `Updated ${refreshedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Connecting')}
          </Typography>
        </Box>
        <Tooltip title="Refresh live data"><IconButton size="small" onClick={() => void refresh()} disabled={loading} sx={{ color: '#8B95A8' }}><RefreshCw size={14} /></IconButton></Tooltip>
      </Box>
    </Box>
  );
};
