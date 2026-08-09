import React from 'react';
import { Box, Typography } from '@mui/material';
import { TopBar } from '../components/layout/TopBar';
import { RiskSummaryCardsRow } from '../components/risks/RiskSummaryCards';
import { RiskItemsTable } from '../components/risks/RiskItemsTable';
import { RiskHeatmap } from '../components/risks/RiskHeatmap';
import { RiskDetailPanel } from '../components/risks/RiskDetailPanel';

/**
 * RisksPage — risk analysis dashboard.
 *
 * Layout:
 *   ┌──────────────────────────────────┬─────────────────┐
 *   │  Page Header + TopBar + Refresh  │                 │
 *   │  RiskSummaryCards (4)            │  Risk Detail    │
 *   │  RiskItemsTable                  │  Panel          │
 *   │  RiskHeatmap                     │                 │
 *   └──────────────────────────────────┴─────────────────┘
 */
export const RisksPage: React.FC = () => {
  return (
    <Box
      id="risks-page"
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
              Risks
            </Typography>
            <Typography variant="body2" sx={{ color: '#8B95A8', mt: 0.25 }}>
              Identify potential issues before they impact operations
            </Typography>
          </Box>
        </Box>

        <TopBar />
        <RiskSummaryCardsRow />
        <RiskItemsTable />
        <RiskHeatmap />
      </Box>

      {/* ── Right Panel ── */}
      <RiskDetailPanel />
    </Box>
  );
};
