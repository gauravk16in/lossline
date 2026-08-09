import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import { Target, TrendingUp, BarChart3, Clock } from 'lucide-react';
import type { ForecastAccuracyMetric } from '../../data/viewModels';

/** Maps metric icon names to lucide-react components + accent colors */
const ICON_CONFIG: Record<
  ForecastAccuracyMetric['icon'],
  { Component: React.ElementType; color: string; bg: string }
> = {
  target:       { Component: Target,     color: '#22C55E', bg: 'rgba(34,197,94,0.1)' },
  'trending-up': { Component: TrendingUp, color: '#A78BFA', bg: 'rgba(167,139,250,0.1)' },
  'bar-chart':   { Component: BarChart3,  color: '#3B82F6', bg: 'rgba(59,130,246,0.1)' },
  clock:        { Component: Clock,      color: '#F59E0B', bg: 'rgba(245,158,11,0.1)' },
};

interface ForecastMetricCardProps {
  metric: ForecastAccuracyMetric;
}

/**
 * ForecastMetricCard — consistent style with MetricStatCard from overview.
 */
export const ForecastMetricCard: React.FC<ForecastMetricCardProps> = ({ metric }) => {
  const { Component: IconComponent, color, bg } = ICON_CONFIG[metric.icon];

  return (
    <Paper
      id={`forecast-metric-${metric.id}`}
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
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="body2" sx={{ color: '#8B95A8', fontSize: '0.8125rem' }}>
          {metric.label}
        </Typography>
        <Box
          sx={{
            width: 32, height: 32, borderRadius: '8px',
            backgroundColor: bg,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <IconComponent size={16} color={color} />
        </Box>
      </Box>
      <Typography sx={{ fontSize: '1.75rem', fontWeight: 700, color: '#F4F7FB', lineHeight: 1, letterSpacing: '-0.02em' }}>
        {metric.value}
      </Typography>
      <Typography variant="caption" sx={{ color: metric.subtitleColor || '#8B95A8', fontSize: '0.75rem' }}>
        {metric.subtitle}
      </Typography>
    </Paper>
  );
};
