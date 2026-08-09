import React from 'react';
import { Chip } from '@mui/material';
import type { IncidentStatus } from '../../types/api';

interface StatusConfig {
  label: string;
  bg: string;
  color: string;
  border: string;
}

function getStatusConfig(status: IncidentStatus): StatusConfig {
  switch (status) {
    case 'DETECTED':
      return { label: 'Detected', bg: '#F3F0FF', color: '#6741D9', border: '#D0BFFF' };
    case 'INVESTIGATING':
      return { label: 'Investigating', bg: '#E7F5FF', color: '#1971C2', border: '#A5D8FF' };
    case 'AWAITING_APPROVAL':
      return { label: 'Awaiting approval', bg: '#FFF9DB', color: '#E67700', border: '#FFE066' };
    case 'ACTION_APPROVED':
      return { label: 'Approved', bg: '#EBFBEE', color: '#2F9E44', border: '#8CE99A' };
    case 'ACTION_REJECTED':
      return { label: 'Rejected', bg: '#FFF5F5', color: '#C92A2A', border: '#FFC9C9' };
    case 'VERIFYING':
      return { label: 'Verifying', bg: '#E7F5FF', color: '#1971C2', border: '#A5D8FF' };
    case 'RESOLVED':
      return { label: 'Resolved', bg: '#EBFBEE', color: '#237032', border: '#69DB7C' };
    case 'NOT_IMPROVED':
      return { label: 'Not improved', bg: '#FFF5F5', color: '#C92A2A', border: '#FFC9C9' };
    default:
      return { label: String(status).replace(/_/g, ' '), bg: '#F8F9FA', color: '#495057', border: '#DEE2E6' };
  }
}

interface StatusChipProps {
  status: IncidentStatus;
  size?: 'small' | 'medium';
}

export const StatusChip: React.FC<StatusChipProps> = ({ status, size = 'small' }) => {
  const config = getStatusConfig(status);
  return (
    <Chip
      label={config.label}
      size={size}
      sx={{
        backgroundColor: config.bg,
        color: config.color,
        border: `1px solid ${config.border}`,
        fontWeight: 500,
        fontSize: '0.75rem',
        height: size === 'small' ? 24 : 28,
        borderRadius: '8px',
        '& .MuiChip-label': { px: 1.25 },
        transition: 'all 200ms ease',
      }}
    />
  );
};
