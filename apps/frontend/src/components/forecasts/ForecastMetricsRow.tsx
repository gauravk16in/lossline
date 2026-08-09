import React from 'react';
import { Box } from '@mui/material';
import { ForecastMetricCard } from './ForecastMetricCard';
import { forecastAccuracyMetrics } from '../../data/forecastsMockData';

/**
 * ForecastMetricsRow — 4-card grid row, same layout as MetricStatsRow.
 */
export const ForecastMetricsRow: React.FC = () => {
  return (
    <Box
      id="forecast-metrics-row"
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
        gap: 2,
        mb: 3,
      }}
    >
      {forecastAccuracyMetrics.map((m) => (
        <ForecastMetricCard key={m.id} metric={m} />
      ))}
    </Box>
  );
};
