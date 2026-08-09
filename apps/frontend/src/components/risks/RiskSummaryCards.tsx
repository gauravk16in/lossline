import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import { AlertTriangle, AlertCircle, ShieldCheck, Layers, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { RiskSummaryCard } from '../../data/viewModels';
import { useDashboard } from '../../state/DashboardContext';

const ICON_MAP: Record<RiskSummaryCard['icon'], React.ElementType> = {
  'alert-triangle': AlertTriangle,
  'alert-circle': AlertCircle,
  'shield-check': ShieldCheck,
  layers: Layers,
};

const TREND_ICONS: Record<string, React.ElementType> = {
  up: TrendingUp,
  down: TrendingDown,
  stable: Minus,
};

/**
 * RiskSummaryCards — 4 color-coded risk level cards.
 * Matches the design's top row: High Risk | Medium Risk | Low Risk | Total At Risk
 */
export const RiskSummaryCardsRow: React.FC = () => {
  const { riskSummaryCards } = useDashboard();
  return (
    <Box
      id="risk-summary-cards"
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
        gap: 2,
        mb: 3,
      }}
    >
      {riskSummaryCards.map((card) => {
        const IconComponent = ICON_MAP[card.icon];
        const TrendIcon = TREND_ICONS[card.trend];
        const trendColor = card.trend === 'up' ? '#22C55E' : card.trend === 'down' ? '#EF4444' : '#8B95A8';
        const trendArrow = card.trend === 'up' ? '↑' : card.trend === 'down' ? '↓' : '—';

        return (
          <Paper
            key={card.id}
            sx={{
              p: 2.5,
              background: '#111631',
              border: `1px solid ${card.borderColor}`,
              borderRadius: '14px',
              transition: 'border-color 200ms ease, box-shadow 200ms ease',
              '&:hover': {
                borderColor: card.color,
                boxShadow: `0 4px 20px ${card.bgColor}`,
              },
            }}
          >
            {/* Label + Icon */}
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" sx={{ color: card.color, fontWeight: 600, fontSize: '0.8125rem' }}>
                {card.label}
              </Typography>
              <Box
                sx={{
                  width: 32, height: 32, borderRadius: '8px',
                  backgroundColor: card.bgColor,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                <IconComponent size={16} color={card.color} />
              </Box>
            </Box>

            {/* Count */}
            <Typography sx={{ fontSize: '1.75rem', fontWeight: 700, color: '#F4F7FB', lineHeight: 1, letterSpacing: '-0.02em', mb: 0.75 }}>
              {card.count}
            </Typography>
            <Typography variant="caption" sx={{ color: '#8B95A8', fontSize: '0.75rem', display: 'block' }}>
              Items
            </Typography>

            {/* Trend */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.75 }}>
              <TrendIcon size={12} color={trendColor} />
              <Typography variant="caption" sx={{ color: trendColor, fontSize: '0.75rem' }}>
                {trendArrow} {card.trendValue}
              </Typography>
            </Box>
          </Paper>
        );
      })}
    </Box>
  );
};
