import React from 'react';
import { Box, Typography } from '@mui/material';
import { TopBar } from '../components/layout/TopBar';
import { ForecastMetricsRow } from '../components/forecasts/ForecastMetricsRow';
import { SkuBreakdownChart } from '../components/forecasts/SkuBreakdownChart';
import { SkuForecastTable } from '../components/forecasts/SkuForecastTable';
import { ForecastDriversPanel } from '../components/forecasts/ForecastDriversPanel';

/**
 * ForecastsPage — similar layout to OverviewPage.
 *
 * Layout:
 *   ┌──────────────────────────────────┬─────────────────┐
 *   │  Page Header + TopBar            │                 │
 *   │  ForecastMetricsRow              │  Forecast       │
 *   │  SkuBreakdownChart              │  Drivers        │
 *   │  SkuForecastTable               │  Panel          │
 *   └──────────────────────────────────┴─────────────────┘
 */
export const ForecastsPage: React.FC = () => {
  return (
    <Box
      id="forecasts-page"
      sx={{
        display: 'flex',
        gap: 3,
        p: 3,
        minHeight: '100vh',
        alignItems: 'flex-start',
      }}
    >
      {/* ── Main Content ── */}
      <Box sx={{ flex: 1, minWidth: 0 }}>
        {/* Page Header */}
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1 }}>
          <Box>
            <Typography variant="h1" sx={{ color: '#F4F7FB' }}>
              Forecasts
            </Typography>
            <Typography variant="body2" sx={{ color: '#8B95A8', mt: 0.25 }}>
              Demand predictions and inventory planning
            </Typography>
          </Box>
        </Box>

        <TopBar />
        <ForecastMetricsRow />
        <SkuBreakdownChart />
        <SkuForecastTable />
      </Box>

      {/* ── Right Panel ── */}
      <ForecastDriversPanel />
    </Box>
  );
};
