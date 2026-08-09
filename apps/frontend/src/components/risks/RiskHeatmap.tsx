import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import { Info } from 'lucide-react';
import { heatmapData, heatmapDays, type RiskLevel } from '../../data/risksMockData';

/** Cell background colors by risk level */
const CELL_COLORS: Record<RiskLevel | 'NONE', string> = {
  NONE:   'rgba(255,255,255,0.03)',
  LOW:    'rgba(34,197,94,0.2)',
  MEDIUM: 'rgba(245,158,11,0.25)',
  HIGH:   'rgba(239,68,68,0.3)',
};

const CELL_BORDERS: Record<RiskLevel | 'NONE', string> = {
  NONE:   'rgba(255,255,255,0.04)',
  LOW:    'rgba(34,197,94,0.15)',
  MEDIUM: 'rgba(245,158,11,0.2)',
  HIGH:   'rgba(239,68,68,0.25)',
};

/**
 * RiskHeatmap — weekly risk heatmap grid.
 * Rows = time windows, Columns = days of week.
 * Cell color intensity by risk level; cell number = count of at-risk items.
 */
export const RiskHeatmap: React.FC = () => {
  return (
    <Paper
      id="risk-heatmap"
      sx={{
        p: 3,
        background: '#111631',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '16px',
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <Typography variant="h2" sx={{ color: '#F4F7FB' }}>
            Risk Heatmap
          </Typography>
          <Info size={14} color="#525C6C" style={{ cursor: 'help' }} />
        </Box>

        {/* Legend */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {[
            { label: 'Low', color: 'rgba(34,197,94,0.5)' },
            { label: 'Medium', color: 'rgba(245,158,11,0.5)' },
            { label: 'High', color: 'rgba(239,68,68,0.5)' },
          ].map((item) => (
            <Box key={item.label} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: '2px', backgroundColor: item.color }} />
              <Typography variant="caption" sx={{ color: '#8B95A8', fontSize: '0.75rem' }}>
                {item.label}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>

      {/* Grid */}
      <Box sx={{ overflowX: 'auto' }}>
        {/* Day headers */}
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: `140px repeat(${heatmapDays.length}, 1fr)`,
            gap: '2px',
            mb: '2px',
          }}
        >
          <Typography variant="caption" sx={{ color: '#525C6C', fontSize: '0.75rem', fontWeight: 500, py: 0.75 }}>
            Time Window
          </Typography>
          {heatmapDays.map((day) => (
            <Typography
              key={day} variant="caption"
              sx={{ color: '#8B95A8', fontSize: '0.75rem', fontWeight: 500, textAlign: 'center', py: 0.75 }}
            >
              {day}
            </Typography>
          ))}
        </Box>

        {/* Data rows */}
        {heatmapData.map((row) => (
          <Box
            key={row.timeWindow}
            sx={{
              display: 'grid',
              gridTemplateColumns: `140px repeat(${heatmapDays.length}, 1fr)`,
              gap: '2px',
              mb: '2px',
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: '#8B95A8', fontSize: '0.75rem',
                display: 'flex', alignItems: 'center',
                pr: 1,
              }}
            >
              {row.timeWindow}
            </Typography>
            {row.days.map((cell, idx) => (
              <Box
                key={idx}
                sx={{
                  backgroundColor: CELL_COLORS[cell.risk],
                  border: `1px solid ${CELL_BORDERS[cell.risk]}`,
                  borderRadius: '4px',
                  py: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'transform 150ms ease, box-shadow 150ms ease',
                  cursor: 'default',
                  '&:hover': {
                    transform: 'scale(1.05)',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                    zIndex: 1,
                  },
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    color: cell.risk === 'NONE' ? '#525C6C' : '#F4F7FB',
                    fontWeight: cell.risk !== 'NONE' ? 600 : 400,
                    fontSize: '0.8125rem',
                  }}
                >
                  {cell.value}
                </Typography>
              </Box>
            ))}
          </Box>
        ))}
      </Box>

      {/* Footer */}
      <Typography variant="caption" sx={{ color: '#525C6C', fontSize: '0.6875rem', mt: 1.5, display: 'block' }}>
        Numbers represent count of at-risk items
      </Typography>
    </Paper>
  );
};
