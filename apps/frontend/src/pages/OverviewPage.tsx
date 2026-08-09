import React from 'react';
import { Box } from '@mui/material';
import { TopBar } from '../components/layout/TopBar';
import { DemandForecastChart } from '../components/overview/DemandForecastChart';
import { MetricStatsRow } from '../components/overview/MetricStatsRow';
import { AtRiskTable } from '../components/overview/AtRiskTable';
import { PriorityDecisionPanel } from '../components/overview/PriorityDecisionPanel';

/**
 * OverviewPage — main dashboard screen.
 *
 * Layout:
 *   ┌──────────────────────────────────┬─────────────────┐
 *   │  TopBar                          │                 │
 *   │  DemandForecastChart             │  Priority       │
 *   │  MetricStatsRow                  │  Decision       │
 *   │  AtRiskTable                     │  Panel          │
 *   └──────────────────────────────────┴─────────────────┘
 */
export const OverviewPage: React.FC = () => {
  return (
    <Box
      id="overview-page"
      sx={{
        display: 'flex',
        gap: 3,
        p: 3,
        minHeight: '100vh',
        alignItems: 'flex-start',
      }}
    >
      {/* ── Main Content (left) ── */}
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <TopBar />
        <DemandForecastChart />
        <MetricStatsRow />
        <AtRiskTable />
      </Box>

      {/* ── Priority Decision (right) ── */}
      <PriorityDecisionPanel />
    </Box>
  );
};
