import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Skeleton,
} from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faStore, faTriangleExclamation, faCircleCheck } from '@fortawesome/free-solid-svg-icons';
import type { Restaurant, Incident } from '../../types/api';
import { formatOutletName } from '../utils/format';
import { useNavigate } from 'react-router-dom';

interface OutletHealthListProps {
  restaurants: Restaurant[];
  incidents: Incident[];
  loading?: boolean;
}

export const OutletHealthList: React.FC<OutletHealthListProps> = ({
  restaurants,
  incidents,
  loading = false,
}) => {
  const navigate = useNavigate();

  if (loading) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {[1, 2].map(i => (
          <Skeleton key={i} variant="rectangular" height={72} sx={{ borderRadius: 2 }} />
        ))}
      </Box>
    );
  }

  if (!restaurants.length) {
    return (
      <Typography variant="body2" sx={{ color: 'text.secondary', py: 2 }}>
        No outlets registered.
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {restaurants.map(restaurant => {
        const activeIncidents = incidents.filter(
          inc =>
            inc.restaurant_id === restaurant.id &&
            !['RESOLVED', 'ACTION_REJECTED'].includes(inc.status)
        );
        const hasIncident = activeIncidents.length > 0;
        const highestSeverity = hasIncident
          ? Math.max(...activeIncidents.map(i => i.severity))
          : 0;

        const statusColor = hasIncident
          ? highestSeverity >= 0.7
            ? '#E03131'
            : '#E67700'
          : '#2F9E44';

        return (
          <Paper
            key={restaurant.id}
            sx={{
              px: 2,
              py: 1.5,
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              cursor: 'pointer',
              transition: 'box-shadow 150ms ease',
              '&:hover': { boxShadow: '0px 2px 8px rgba(0,0,0,0.08)' },
            }}
            onClick={() => hasIncident && navigate(`/incidents/${activeIncidents[0].id}`)}
          >
            <Box
              sx={{
                width: 36,
                height: 36,
                borderRadius: '10px',
                backgroundColor: hasIncident ? `${statusColor}14` : '#EBFBEE',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <FontAwesomeIcon
                icon={faStore}
                style={{ fontSize: 14, color: hasIncident ? statusColor : '#2F9E44' }}
              />
            </Box>

            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary', mb: 0.25 }}>
                {formatOutletName(restaurant.id)}
              </Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                {hasIncident ? `${activeIncidents.length} active incident${activeIncidents.length > 1 ? 's' : ''}` : 'Operating normally'}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
              <FontAwesomeIcon
                icon={hasIncident ? faTriangleExclamation : faCircleCheck}
                style={{ fontSize: 12, color: statusColor }}
              />
              <Typography
                variant="caption"
                sx={{ color: statusColor, fontWeight: 600 }}
              >
                {hasIncident ? (highestSeverity >= 0.7 ? 'At risk' : 'Warning') : 'Healthy'}
              </Typography>
            </Box>
          </Paper>
        );
      })}
    </Box>
  );
};
