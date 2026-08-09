import React from 'react';
import { Box, Typography } from '@mui/material';
import { TopBar } from '../components/layout/TopBar';
import { DecisionsTable } from '../components/decisions/DecisionsTable';
import { DecisionDetailPanel } from '../components/decisions/DecisionDetailPanel';

/**
 * DecisionsPage — review and approve recommended actions.
 *
 * Layout:
 *   ┌──────────────────────────────────┬─────────────────┐
 *   │  Page Header + TopBar            │                 │
 *   │  DecisionsTable (tabs + rows)    │  Decision       │
 *   │                                  │  Detail Panel   │
 *   └──────────────────────────────────┴─────────────────┘
 */
export const DecisionsPage: React.FC = () => {
  return (
    <Box
      id="decisions-page"
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
              Decisions
            </Typography>
            <Typography variant="body2" sx={{ color: '#8B95A8', mt: 0.25 }}>
              Review and approve recommended actions
            </Typography>
          </Box>
        </Box>

        <TopBar />
        <DecisionsTable />
      </Box>

      {/* ── Right Panel ── */}
      <DecisionDetailPanel />
    </Box>
  );
};
