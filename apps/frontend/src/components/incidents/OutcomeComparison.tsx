import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Chip,
} from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowTrendUp, faArrowRight } from '@fortawesome/free-solid-svg-icons';
import type { Outcome } from '../../types/api';

interface OutcomeComparisonProps {
  outcome: Outcome;
}

const STATUS_CONFIG = {
  IMPROVED: { label: 'Improved', color: '#2F9E44', bg: '#EBFBEE', border: '#69DB7C' },
  NO_CHANGE: { label: 'No change', color: '#E67700', bg: '#FFF9DB', border: '#FFE066' },
  WORSENED: { label: 'Worsened', color: '#C92A2A', bg: '#FFF5F5', border: '#FFC9C9' },
  INSUFFICIENT_DATA: { label: 'Insufficient data', color: '#868E96', bg: '#F8F9FA', border: '#DEE2E6' },
};

function MetricRow({
  label,
  before,
  after,
  unit,
}: {
  label: string;
  before: number;
  after: number;
  unit?: string;
}) {
  const improved = after <= before; // lower is usually better for rate/time metrics
  const pctChange = before !== 0 ? ((after - before) / before * 100).toFixed(1) : null;

  function fmt(v: number) {
    if (unit === 'rate' || label.toLowerCase().includes('rate') || label.toLowerCase().includes('cancellation')) {
      return `${(v * 100).toFixed(1)}%`;
    }
    return `${v.toFixed(2)}`;
  }

  return (
    <Grid container spacing={2} sx={{ mb: 2, alignItems: 'center' }}>
      <Grid size={3}>
        <Typography variant="body2" sx={{ color: 'text.secondary', fontWeight: 500 }}>
          {label.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase())}
        </Typography>
      </Grid>
      <Grid size={3} sx={{ textAlign: 'center' }}>
        <Typography sx={{ fontWeight: 700, fontSize: '1.25rem', color: 'text.primary' }}>
          {fmt(before)}
        </Typography>
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>Before</Typography>
      </Grid>
      <Grid size={1} sx={{ textAlign: 'center' }}>
        <FontAwesomeIcon icon={faArrowRight} style={{ fontSize: 12, color: '#868E96' }} />
      </Grid>
      <Grid size={3} sx={{ textAlign: 'center' }}>
        <Typography sx={{ fontWeight: 700, fontSize: '1.25rem', color: improved ? '#2F9E44' : '#E03131' }}>
          {fmt(after)}
        </Typography>
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>After</Typography>
      </Grid>
      <Grid size={2} sx={{ textAlign: 'right' }}>
        {pctChange && (
          <Chip
            label={`${Number(pctChange) > 0 ? '+' : ''}${pctChange}%`}
            size="small"
            sx={{
              fontWeight: 600,
              fontSize: '0.6875rem',
              bgcolor: improved ? '#EBFBEE' : '#FFF5F5',
              color: improved ? '#2F9E44' : '#E03131',
              border: 'none',
              height: 22,
            }}
          />
        )}
      </Grid>
    </Grid>
  );
}

export const OutcomeComparison: React.FC<OutcomeComparisonProps> = ({ outcome }) => {
  const statusConfig = STATUS_CONFIG[outcome.status] ?? STATUS_CONFIG.INSUFFICIENT_DATA;
  const baseline = outcome.baseline_metrics ?? {};
  const post = outcome.post_metrics ?? {};
  const sharedKeys = Object.keys(baseline).filter(k => k in post);

  return (
    <Paper
      sx={{
        p: 2.5,
        border: '1px solid rgba(0,0,0,0.06)',
        borderTop: `3px solid ${statusConfig.color}`,
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.5 }}>
        <Box
          sx={{
            width: 32,
            height: 32,
            borderRadius: '10px',
            backgroundColor: statusConfig.bg,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <FontAwesomeIcon icon={faArrowTrendUp} style={{ fontSize: 14, color: statusConfig.color }} />
        </Box>
        <Box>
          <Typography variant="overline" sx={{ color: 'text.secondary' }}>
            Outcome
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h3" sx={{ color: statusConfig.color }}>
              {statusConfig.label}
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Metric comparisons */}
      {sharedKeys.length > 0 ? (
        sharedKeys.map(key => (
          <MetricRow
            key={key}
            label={key}
            before={Number(baseline[key])}
            after={Number(post[key])}
          />
        ))
      ) : (
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          Metric comparison data not available.
        </Typography>
      )}

      {/* Disclaimer */}
      <Box
        sx={{
          mt: 2,
          p: 1.5,
          borderRadius: 2,
          bgcolor: '#F8F9FA',
          border: '1px solid rgba(0,0,0,0.06)',
        }}
      >
        <Typography variant="caption" sx={{ color: 'text.secondary', lineHeight: 1.5 }}>
          Metrics measured after the simulated intervention. This does not establish causality between
          the action and the improvement.
        </Typography>
      </Box>
    </Paper>
  );
};
