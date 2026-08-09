import React from 'react';
import { Box, Typography } from '@mui/material';
import {
  Calendar,
  CloudRain,
  Tag,
  MapPin,
} from 'lucide-react';
import type { KeyDriver } from '../../data/viewModels';

/** Maps driver icon names to lucide-react components */
const ICON_MAP: Record<KeyDriver['icon'], React.ElementType> = {
  calendar: Calendar,
  'cloud-rain': CloudRain,
  tag: Tag,
  'map-pin': MapPin,
};

/** Impact level colors */
const IMPACT_COLORS: Record<string, string> = {
  High: '#EF4444',
  Medium: '#F59E0B',
  Low: '#22C55E',
};

interface KeyDriversListProps {
  drivers: KeyDriver[];
}

/**
 * KeyDriversList — list of demand drivers with icon, label, and impact badge.
 * Used inside the PriorityDecisionPanel.
 */
export const KeyDriversList: React.FC<KeyDriversListProps> = ({ drivers }) => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {drivers.map((driver) => {
        const IconComponent = ICON_MAP[driver.icon];
        const impactColor = IMPACT_COLORS[driver.impact];

        return (
          <Box
            key={driver.id}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              py: 0.375,
            }}
          >
            <IconComponent
              size={14}
              color="#525C6C"
              style={{ flexShrink: 0 }}
            />
            <Typography
              variant="body2"
              sx={{
                color: '#8B95A8',
                flex: 1,
                fontSize: '0.8125rem',
              }}
            >
              {driver.label}
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: impactColor,
                fontWeight: 600,
                fontSize: '0.75rem',
              }}
            >
              {driver.impact}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
};
