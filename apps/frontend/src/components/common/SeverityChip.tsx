import React from 'react';
import { Chip } from '@mui/material';

// severity is 0–1 from backend
function getSeverityLabel(severity: number): string {
  if (severity >= 0.9) return 'CRITICAL';
  if (severity >= 0.7) return 'HIGH';
  if (severity >= 0.4) return 'MEDIUM';
  return 'LOW';
}

function getSeverityColors(severity: number): { bg: string; color: string; border: string } {
  if (severity >= 0.9) return { bg: '#FFF5F5', color: '#C92A2A', border: '#FFC9C9' };
  if (severity >= 0.7) return { bg: '#FFF9DB', color: '#E67700', border: '#FFE066' };
  if (severity >= 0.4) return { bg: '#E7F5FF', color: '#1864AB', border: '#BAD4F5' };
  return { bg: '#EBFBEE', color: '#237032', border: '#B2F2BB' };
}

interface SeverityChipProps {
  severity: number;
  size?: 'small' | 'medium';
}

export const SeverityChip: React.FC<SeverityChipProps> = ({ severity, size = 'small' }) => {
  const label = getSeverityLabel(severity);
  const colors = getSeverityColors(severity);

  return (
    <Chip
      label={label}
      size={size}
      sx={{
        backgroundColor: colors.bg,
        color: colors.color,
        border: `1px solid ${colors.border}`,
        fontWeight: 600,
        fontSize: '0.6875rem',
        letterSpacing: '0.06em',
        height: size === 'small' ? 22 : 28,
        borderRadius: '6px',
        '& .MuiChip-label': { px: 1 },
      }}
    />
  );
};
