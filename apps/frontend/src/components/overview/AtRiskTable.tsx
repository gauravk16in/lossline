import React from 'react';
import { Box, Typography, Paper, Button } from '@mui/material';
import type { RiskLevel } from '../../data/viewModels';
import { useDashboard } from '../../state/DashboardContext';
import { useNavigate } from 'react-router-dom';

/** Risk badge color config */
const RISK_COLORS: Record<RiskLevel, { text: string; bg: string; border: string }> = {
  HIGH:   { text: '#EF4444', bg: 'rgba(239,68,68,0.1)',  border: 'rgba(239,68,68,0.2)' },
  MEDIUM: { text: '#F59E0B', bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.2)' },
  LOW:    { text: '#22C55E', bg: 'rgba(34,197,94,0.1)',   border: 'rgba(34,197,94,0.2)' },
};

/**
 * AtRiskTable — table of SKUs with shortage risk.
 * Shows item thumbnail, forecast, available, gap, and risk badge.
 */
export const AtRiskTable: React.FC = () => {
  const { atRiskItems } = useDashboard();
  const navigate = useNavigate();
  return (
    <Paper
      id="at-risk-table"
      sx={{
        p: 3,
        background: '#111631',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '16px',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 2.5,
        }}
      >
        <Typography variant="h2" sx={{ color: '#F4F7FB' }}>
          At-Risk Items
        </Typography>
        <Button
          onClick={() => navigate('/risks')}
          variant="text"
          size="small"
          sx={{
            color: '#8B95A8',
            fontSize: '0.8125rem',
            fontWeight: 500,
            textTransform: 'none',
            px: 1.5,
            py: 0.5,
            borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.08)',
            '&:hover': {
              backgroundColor: 'rgba(255,255,255,0.04)',
              color: '#F4F7FB',
            },
          }}
        >
          View all
        </Button>
      </Box>

      {/* Column Headers */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr 1fr 1fr 0.8fr',
          gap: 1,
          pb: 1.5,
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          mb: 0.5,
        }}
      >
        {['SKU', 'Forecast', 'Available', 'Gap', 'Risk'].map((header) => (
          <Typography
            key={header}
            variant="caption"
            sx={{
              color: '#525C6C',
              fontSize: '0.75rem',
              fontWeight: 500,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            {header}
          </Typography>
        ))}
      </Box>

      {/* Rows */}
      {atRiskItems.map((item) => {
        const riskColor = RISK_COLORS[item.risk];
        return (
          <Box
            key={item.id}
            sx={{
              display: 'grid',
              gridTemplateColumns: '2fr 1fr 1fr 1fr 0.8fr',
              gap: 1,
              alignItems: 'center',
              py: 1.5,
              borderBottom: '1px solid rgba(255,255,255,0.03)',
              transition: 'background-color 150ms ease',
              mx: -1.5,
              px: 1.5,
              borderRadius: '8px',
              '&:hover': {
                backgroundColor: 'rgba(255,255,255,0.02)',
              },
              '&:last-child': {
                borderBottom: 'none',
              },
            }}
          >
            {/* SKU */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
              <Box
                component="img"
                src={item.image}
                alt={item.name}
                sx={{
                  width: 36,
                  height: 36,
                  borderRadius: '8px',
                  objectFit: 'cover',
                  flexShrink: 0,
                }}
              />
              <Typography
                variant="body2"
                sx={{ color: '#F4F7FB', fontWeight: 500 }}
              >
                {item.name}
              </Typography>
            </Box>

            {/* Forecast */}
            <Typography variant="body2" sx={{ color: '#8B95A8' }}>
              {item.forecast} portions
            </Typography>

            {/* Available */}
            <Typography variant="body2" sx={{ color: '#8B95A8' }}>
              {item.available} portions
            </Typography>

            {/* Gap */}
            <Typography
              variant="body2"
              sx={{
                color: item.gap < 0 ? '#EF4444' : '#22C55E',
                fontWeight: 500,
              }}
            >
              {item.gap > 0 ? '+' : ''}
              {item.gap}
            </Typography>

            {/* Risk Badge */}
            <Box
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                px: 1.25,
                py: 0.375,
                borderRadius: '6px',
                backgroundColor: riskColor.bg,
                border: `1px solid ${riskColor.border}`,
                width: 'fit-content',
              }}
            >
              <Typography
                variant="caption"
                sx={{
                  color: riskColor.text,
                  fontWeight: 600,
                  fontSize: '0.6875rem',
                  letterSpacing: '0.04em',
                }}
              >
                {item.risk}
              </Typography>
            </Box>
          </Box>
        );
      })}
    </Paper>
  );
};
