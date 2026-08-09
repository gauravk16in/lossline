import React from 'react';
import { Box, Typography, Paper, LinearProgress } from '@mui/material';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { useDashboard } from '../../state/DashboardContext';

const TREND_ICONS: Record<string, React.ElementType> = {
  up: TrendingUp,
  down: TrendingDown,
  stable: Minus,
};
const TREND_COLORS: Record<string, string> = {
  up: '#22C55E',
  down: '#EF4444',
  stable: '#8B95A8',
};

/**
 * SkuForecastTable — table of SKU forecasts with progress bars.
 * Consistent card styling with AtRiskTable.
 */
export const SkuForecastTable: React.FC = () => {
  const { skuForecasts } = useDashboard();
  return (
    <Paper
      id="sku-forecast-table"
      sx={{
        p: 3,
        background: '#111631',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '16px',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2.5 }}>
        <Typography variant="h2" sx={{ color: '#F4F7FB' }}>
          SKU Forecast Detail
        </Typography>
        <Typography variant="caption" sx={{ color: '#8B95A8' }}>
          {skuForecasts.length} items tracked
        </Typography>
      </Box>

      {/* Column Headers */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr 1fr 1fr 1.2fr 0.8fr',
          gap: 1, pb: 1.5,
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          mb: 0.5,
        }}
      >
        {['Item', 'Forecast', 'Inventory', 'Gap', 'Confidence', 'Peak'].map((h) => (
          <Typography
            key={h} variant="caption"
            sx={{ color: '#525C6C', fontSize: '0.75rem', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.04em' }}
          >
            {h}
          </Typography>
        ))}
      </Box>

      {/* Rows */}
      {skuForecasts.map((sku) => {
        const TrendIcon = TREND_ICONS[sku.trend];
        const trendColor = TREND_COLORS[sku.trend];

        return (
          <Box
            key={sku.id}
            sx={{
              display: 'grid',
              gridTemplateColumns: '2fr 1fr 1fr 1fr 1.2fr 0.8fr',
              gap: 1, alignItems: 'center', py: 1.5,
              borderBottom: '1px solid rgba(255,255,255,0.03)',
              mx: -1.5, px: 1.5, borderRadius: '8px',
              transition: 'background-color 150ms ease',
              '&:hover': { backgroundColor: 'rgba(255,255,255,0.02)' },
              '&:last-child': { borderBottom: 'none' },
            }}
          >
            {/* Item */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
              <Box component="img" src={sku.image} alt={sku.name}
                sx={{ width: 36, height: 36, borderRadius: '8px', objectFit: 'cover', flexShrink: 0 }}
              />
              <Box>
                <Typography variant="body2" sx={{ color: '#F4F7FB', fontWeight: 500 }}>
                  {sku.name}
                </Typography>
                <Typography variant="caption" sx={{ color: '#525C6C', fontSize: '0.6875rem' }}>
                  {sku.category}
                </Typography>
              </Box>
            </Box>

            {/* Forecast */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Typography variant="body2" sx={{ color: '#8B95A8' }}>
                {sku.forecastDemand}
              </Typography>
              <TrendIcon size={12} color={trendColor} />
              <Typography variant="caption" sx={{ color: trendColor, fontSize: '0.6875rem' }}>
                {sku.trendPercent}%
              </Typography>
            </Box>

            {/* Inventory */}
            <Typography variant="body2" sx={{ color: '#8B95A8' }}>
              {sku.currentInventory}
            </Typography>

            {/* Gap */}
            <Typography variant="body2" sx={{ color: sku.gap < 0 ? '#EF4444' : '#22C55E', fontWeight: 500 }}>
              {sku.gap > 0 ? '+' : ''}{sku.gap}
            </Typography>

            {/* Confidence */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <LinearProgress
                variant="determinate"
                value={sku.confidence}
                sx={{
                  flex: 1, height: 6, borderRadius: 3,
                  backgroundColor: 'rgba(255,255,255,0.06)',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 3,
                    background: sku.confidence >= 85
                      ? 'linear-gradient(90deg, #22C55E, #4ADE80)'
                      : sku.confidence >= 70
                      ? 'linear-gradient(90deg, #F59E0B, #FBBF24)'
                      : 'linear-gradient(90deg, #EF4444, #F87171)',
                  },
                }}
              />
              <Typography variant="caption" sx={{ color: '#8B95A8', fontSize: '0.75rem', minWidth: 28 }}>
                {sku.confidence}%
              </Typography>
            </Box>

            {/* Peak */}
            <Typography variant="body2" sx={{ color: '#8B95A8', fontSize: '0.8125rem' }}>
              {sku.peakWindow}
            </Typography>
          </Box>
        );
      })}
    </Paper>
  );
};
