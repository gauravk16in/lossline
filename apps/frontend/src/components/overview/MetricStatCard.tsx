import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import { TrendingUp, ShieldAlert, Clock, IndianRupee } from 'lucide-react';
import type { MetricStat } from '../../data/overviewMockData';

/** Maps stat icon names to lucide-react components + accent colors */
const ICON_CONFIG: Record<
  MetricStat['icon'],
  { Component: React.ElementType; color: string; bg: string }
> = {
  'trending-up':  { Component: TrendingUp,  color: '#22C55E', bg: 'rgba(34,197,94,0.1)' },
  'shield-alert': { Component: ShieldAlert, color: '#F59E0B', bg: 'rgba(245,158,11,0.1)' },
  'clock':        { Component: Clock,       color: '#8B95A8', bg: 'rgba(139,149,168,0.1)' },
  'indian-rupee': { Component: IndianRupee, color: '#8B95A8', bg: 'rgba(139,149,168,0.1)' },
};

interface MetricStatCardProps {
  stat: MetricStat;
}

/**
 * MetricStatCard — displays a single KPI metric with icon, value, and subtitle.
 * Matches the "Expected Orders", "At-Risk SKUs", etc. cards in the design.
 */
export const MetricStatCard: React.FC<MetricStatCardProps> = ({ stat }) => {
  const { Component: IconComponent, color, bg } = ICON_CONFIG[stat.icon];

  return (
    <Paper
      id={`metric-${stat.id}`}
      sx={{
        p: 2.5,
        flex: 1,
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        background: '#111631',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '14px',
        transition: 'border-color 200ms ease, box-shadow 200ms ease',
        '&:hover': {
          borderColor: 'rgba(255,255,255,0.1)',
          boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
        },
      }}
    >
      {/* Top row: label + icon */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Typography
          variant="body2"
          sx={{ color: '#8B95A8', fontSize: '0.8125rem' }}
        >
          {stat.label}
        </Typography>
        <Box
          sx={{
            width: 32,
            height: 32,
            borderRadius: '8px',
            backgroundColor: bg,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <IconComponent size={16} color={color} />
        </Box>
      </Box>

      {/* Value */}
      <Typography
        sx={{
          fontSize: '1.75rem',
          fontWeight: 700,
          color: '#F4F7FB',
          lineHeight: 1,
          letterSpacing: '-0.02em',
        }}
      >
        {stat.value}
      </Typography>

      {/* Subtitle */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        {stat.subtitleColor && stat.id === 'expected-orders' && (
          <Typography
            component="span"
            sx={{
              color: stat.subtitleColor,
              fontSize: '0.75rem',
              fontWeight: 500,
            }}
          >
            ↗ 18%
          </Typography>
        )}
        <Typography
          variant="caption"
          sx={{
            color: stat.subtitleColor || '#8B95A8',
            fontSize: '0.75rem',
          }}
        >
          {stat.subtitle}
        </Typography>
      </Box>
    </Paper>
  );
};
