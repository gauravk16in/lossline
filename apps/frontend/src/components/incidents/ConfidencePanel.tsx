import React from 'react';
import { Box, Typography, LinearProgress } from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faShieldHalved } from '@fortawesome/free-solid-svg-icons';

interface ConfidencePanelProps {
  confidence: number; // 0–1 from backend
  components?: Record<string, unknown>;
}

export const ConfidencePanel: React.FC<ConfidencePanelProps> = ({ confidence }) => {
  const pct = Math.round(confidence * 100);

  const color = confidence >= 0.8
    ? '#2F9E44'
    : confidence >= 0.6
    ? '#E67700'
    : '#E03131';

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
        <FontAwesomeIcon icon={faShieldHalved} style={{ fontSize: 13, color: '#868E96' }} />
        <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Confidence
        </Typography>
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mb: 1.5 }}>
        <Typography
          sx={{
            fontSize: '2rem',
            fontWeight: 700,
            lineHeight: 1,
            color,
            letterSpacing: '-0.02em',
          }}
        >
          {pct}%
        </Typography>
      </Box>

      <LinearProgress
        variant="determinate"
        value={pct}
        sx={{
          mb: 1.5,
          height: 6,
          borderRadius: 3,
          backgroundColor: 'rgba(0,0,0,0.06)',
          '& .MuiLinearProgress-bar': {
            borderRadius: 3,
            backgroundColor: color,
            transition: 'width 600ms ease',
          },
        }}
      />

      <Typography variant="caption" sx={{ color: 'text.secondary', lineHeight: 1.5 }}>
        Determined by the correlation engine from signal count, temporal alignment, and evidence coverage.
        Not a probabilistic estimate.
      </Typography>
    </Box>
  );
};
