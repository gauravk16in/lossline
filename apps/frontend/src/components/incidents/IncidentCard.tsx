import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Divider,
  Button,
} from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTriangleExclamation, faStore, faArrowRight } from '@fortawesome/free-solid-svg-icons';
import { useNavigate } from 'react-router-dom';
import { SeverityChip } from '../common/SeverityChip';
import { StatusChip } from '../common/StatusChip';
import type { Incident } from '../../types/api';
import { formatDistanceToNow } from '../utils/time';
import { formatIncidentType, formatOutletName } from '../utils/format';

interface IncidentCardProps {
  incident: Incident;
}

export const IncidentCard: React.FC<IncidentCardProps> = ({ incident }) => {
  const navigate = useNavigate();
  const confidencePct = Math.round(incident.confidence * 100);

  return (
    <Paper
      sx={{
        p: 2.5,
        mb: 1.5,
        cursor: 'pointer',
        transition: 'box-shadow 150ms ease, transform 150ms ease',
        '&:hover': {
          boxShadow: '0px 4px 16px rgba(0,0,0,0.08)',
          transform: 'translateY(-1px)',
        },
        borderLeft: `3px solid ${incident.severity >= 0.7 ? '#E03131' : incident.severity >= 0.4 ? '#F59F00' : '#2F9E44'}`,
      }}
      onClick={() => navigate(`/incidents/${incident.id}`)}
    >
      {/* Header row */}
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SeverityChip severity={incident.severity} />
          <StatusChip status={incident.status} />
        </Box>
        <Typography variant="caption" sx={{ color: 'text.secondary', mt: 0.25 }}>
          {formatDistanceToNow(incident.created_at)}
        </Typography>
      </Box>

      {/* Title */}
      <Typography variant="h3" sx={{ mb: 0.5, color: 'text.primary', fontWeight: 600 }}>
        {formatIncidentType(incident.incident_type)}
      </Typography>

      {/* Outlet */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 1.5 }}>
        <FontAwesomeIcon icon={faStore} style={{ fontSize: 11, color: '#868E96' }} />
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          {formatOutletName(incident.restaurant_id)}
        </Typography>
      </Box>

      {/* Explanation */}
      {incident.explanation && (
        <Typography
          variant="body2"
          sx={{
            color: 'text.secondary',
            lineHeight: 1.6,
            mb: 2,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {incident.explanation}
        </Typography>
      )}

      <Divider sx={{ mb: 1.5 }} />

      {/* Footer metrics + CTA */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', gap: 3 }}>
          <Box>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
              Confidence
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>
              {confidencePct}%
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
              Revenue at risk
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 600, color: incident.revenue_at_risk ? 'error.main' : 'text.secondary' }}>
              {incident.revenue_at_risk != null
                ? `\u20B9${Math.round(incident.revenue_at_risk).toLocaleString('en-IN')}`
                : 'Estimating\u2026'}
            </Typography>
          </Box>
        </Box>
        <Button
          size="small"
          variant="outlined"
          endIcon={<FontAwesomeIcon icon={faArrowRight} style={{ fontSize: 11 }} />}
          sx={{
            borderRadius: 2,
            fontSize: '0.75rem',
            borderColor: 'rgba(0,0,0,0.12)',
            color: 'text.secondary',
            '&:hover': { borderColor: 'primary.main', color: 'primary.main' },
          }}
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/incidents/${incident.id}`);
          }}
        >
          View incident
        </Button>
      </Box>
    </Paper>
  );
};
