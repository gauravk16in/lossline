import React from 'react';
import {
  Box,
  List,
  ListItem,
  Typography,
  Divider,
} from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCircleCheck, faCircleExclamation } from '@fortawesome/free-solid-svg-icons';
import type { Signal } from '../../types/api';
import { formatSignalType, formatValue } from '../utils/format';

interface EvidenceListProps {
  signals: Signal[];
}

export const EvidenceList: React.FC<EvidenceListProps> = ({ signals }) => {
  if (!signals.length) {
    return (
      <Typography variant="body2" sx={{ color: 'text.secondary', py: 1 }}>
        No signals recorded for this incident.
      </Typography>
    );
  }

  return (
    <List disablePadding>
      {signals.map((signal, idx) => {
        const currentFormatted = formatValue(Number(signal.current_value), signal.unit);
        const baselineFormatted = signal.baseline_value != null
          ? formatValue(Number(signal.baseline_value), signal.unit)
          : null;
        const deviation = signal.deviation != null ? Number(signal.deviation) : null;

        return (
          <React.Fragment key={signal.id}>
            <ListItem
              disableGutters
              sx={{
                py: 1.5,
                alignItems: 'flex-start',
                gap: 1.5,
              }}
            >
              <Box sx={{ pt: 0.25, flexShrink: 0 }}>
                <FontAwesomeIcon
                  icon={signal.severity >= 0.7 ? faCircleExclamation : faCircleCheck}
                  style={{
                    fontSize: 14,
                    color: signal.severity >= 0.7 ? '#E03131' : '#2F9E44',
                  }}
                />
              </Box>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary', mb: 0.25 }}>
                  {formatSignalType(signal.signal_type)}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
                  <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>
                      {currentFormatted}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      current
                    </Typography>
                  </Box>
                  {baselineFormatted && (
                    <>
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        vs
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5 }}>
                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                          {baselineFormatted}
                        </Typography>
                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                          baseline
                        </Typography>
                      </Box>
                    </>
                  )}
                  {deviation != null && deviation > 0 && (
                    <Typography
                      variant="caption"
                      sx={{
                        color: 'error.main',
                        fontWeight: 600,
                        bgcolor: '#FFF5F5',
                        px: 0.75,
                        py: 0.25,
                        borderRadius: 1,
                      }}
                    >
                      +{(deviation * 100).toFixed(0)}%
                    </Typography>
                  )}
                </Box>
              </Box>
            </ListItem>
            {idx < signals.length - 1 && <Divider />}
          </React.Fragment>
        );
      })}
    </List>
  );
};
