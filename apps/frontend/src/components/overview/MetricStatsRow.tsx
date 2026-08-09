import React from 'react';
import { Box } from '@mui/material';
import { MetricStatCard } from './MetricStatCard';
import { metricStats } from '../../data/overviewMockData';

/**
 * MetricStatsRow — horizontal row of 4 MetricStatCards.
 * Responsive: stacks 2×2 on smaller viewports.
 */
export const MetricStatsRow: React.FC = () => {
  return (
    <Box
      id="metric-stats-row"
      sx={{
        display: 'grid',
        gridTemplateColumns: {
          xs: '1fr',
          sm: 'repeat(2, 1fr)',
          md: 'repeat(4, 1fr)',
        },
        gap: 2,
        mb: 3,
      }}
    >
      {metricStats.map((stat) => (
        <MetricStatCard key={stat.id} stat={stat} />
      ))}
    </Box>
  );
};
