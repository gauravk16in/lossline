import React from 'react';
import { Box, Paper, Typography } from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faIndianRupeeSign } from '@fortawesome/free-solid-svg-icons';

interface RevenueRiskCardProps {
  revenueAtRisk: number | null;
  currency?: string;
}

export const RevenueRiskCard: React.FC<RevenueRiskCardProps> = ({
  revenueAtRisk,
  currency = 'INR',
}) => {
  const hasValue = revenueAtRisk != null && revenueAtRisk > 0;

  return (
    <Paper
      sx={{
        p: 2.5,
        border: '1px solid rgba(0,0,0,0.06)',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
        <Box
          sx={{
            width: 28,
            height: 28,
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: hasValue ? '#FFF5F5' : '#F8F9FA',
          }}
        >
          <FontAwesomeIcon
            icon={faIndianRupeeSign}
            style={{
              fontSize: 12,
              color: hasValue ? '#C92A2A' : '#868E96',
            }}
          />
        </Box>
        <Typography variant="body2" sx={{ color: 'text.secondary', fontWeight: 500 }}>
          Estimated revenue at risk
        </Typography>
      </Box>

      <Typography
        sx={{
          fontSize: '1.75rem',
          fontWeight: 700,
          lineHeight: 1,
          color: hasValue ? 'error.main' : 'text.secondary',
          letterSpacing: '-0.02em',
          mb: 1,
        }}
      >
        {hasValue
          ? `\u20B9${Math.round(revenueAtRisk!).toLocaleString('en-IN')}`
          : 'Insufficient data'}
      </Typography>

      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
        {hasValue
          ? `${currency} · Model estimate based on current operational evidence.`
          : 'Revenue risk model requires more signal data.'}
      </Typography>
    </Paper>
  );
};
