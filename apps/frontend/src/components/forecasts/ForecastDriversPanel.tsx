import React from 'react';
import { Box, Typography, Paper, LinearProgress } from '@mui/material';
import { TrendingUp, TrendingDown, ArrowRight } from 'lucide-react';
import { forecastDrivers } from '../../data/forecastsMockData';

/**
 * ForecastDriversPanel — right-side panel showing what's influencing today's forecast.
 * Consistent styling with PriorityDecisionPanel from overview.
 */
export const ForecastDriversPanel: React.FC = () => {
  return (
    <Box
      id="forecast-drivers-panel"
      sx={{
        width: 320,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        background: '#111631',
        borderRadius: '16px',
        border: '1px solid rgba(255,255,255,0.06)',
        overflow: 'hidden',
        alignSelf: 'flex-start',
        position: 'sticky',
        top: 24,
      }}
    >
      {/* Header */}
      <Box sx={{ p: 2.5, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <Typography variant="h3" sx={{ color: '#F4F7FB', fontWeight: 600 }}>
          Forecast Drivers
        </Typography>
        <Typography variant="caption" sx={{ color: '#8B95A8', mt: 0.25, display: 'block' }}>
          What's influencing today's forecast
        </Typography>
      </Box>

      {/* Drivers list */}
      <Box sx={{ p: 2.5, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {forecastDrivers.map((driver) => {
          const DirectionIcon = driver.direction === 'up' ? TrendingUp : TrendingDown;
          const dirColor = driver.direction === 'up' ? '#22C55E' : '#EF4444';

          return (
            <Box key={driver.id}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                  <DirectionIcon size={14} color={dirColor} />
                  <Typography variant="body2" sx={{ color: '#F4F7FB', fontWeight: 500, fontSize: '0.8125rem' }}>
                    {driver.feature}
                  </Typography>
                </Box>
                <Typography variant="caption" sx={{ color: '#A78BFA', fontWeight: 600, fontSize: '0.8125rem' }}>
                  {driver.contribution}%
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={driver.contribution}
                sx={{
                  height: 4, borderRadius: 2, mb: 0.5,
                  backgroundColor: 'rgba(255,255,255,0.04)',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 2,
                    background: 'linear-gradient(90deg, #7C5CFC, #A78BFA)',
                  },
                }}
              />
              <Typography variant="caption" sx={{ color: '#525C6C', fontSize: '0.6875rem' }}>
                {driver.description}
              </Typography>
            </Box>
          );
        })}
      </Box>

      {/* Bottom CTA */}
      <Box sx={{ p: 2.5, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <Box
          sx={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.75,
            py: 1, px: 2, borderRadius: '10px',
            border: '1px solid rgba(255,255,255,0.08)',
            cursor: 'pointer',
            transition: 'all 150ms ease',
            '&:hover': {
              backgroundColor: 'rgba(255,255,255,0.04)',
              borderColor: 'rgba(255,255,255,0.12)',
            },
          }}
        >
          <Typography variant="body2" sx={{ color: '#8B95A8', fontWeight: 500 }}>
            View full analysis
          </Typography>
          <ArrowRight size={14} color="#8B95A8" />
        </Box>
      </Box>
    </Box>
  );
};
