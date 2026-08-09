import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  List,
  ListItem,
  CircularProgress,
  Divider,
} from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faLightbulb,
  faCheck,
  faXmark,
  faArrowTrendUp,
  faArrowTrendDown,
} from '@fortawesome/free-solid-svg-icons';
import type { Recommendation } from '../../types/api';

interface RecommendationCardProps {
  recommendations: Recommendation[];
  incidentStatus: string;
  onDecide: (decision: 'APPROVE' | 'REJECT', note?: string) => Promise<void>;
}

export const RecommendationCard: React.FC<RecommendationCardProps> = ({
  recommendations,
  incidentStatus,
  onDecide,
}) => {
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState<'APPROVE' | 'REJECT' | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const rec = recommendations[0];
  const canDecide = incidentStatus === 'AWAITING_APPROVAL' && !!rec;

  if (!rec) return null;

  async function handleDecide(decision: 'APPROVE' | 'REJECT') {
    setLoading(decision);
    setLocalError(null);
    try {
      await onDecide(decision, note || undefined);
      setNote('');
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setLoading(null);
    }
  }

  const riskColor = {
    LOW: '#2F9E44',
    MEDIUM: '#E67700',
    HIGH: '#E03131',
    CRITICAL: '#C92A2A',
  }[rec.risk_tier?.toUpperCase()] ?? '#495057';

  return (
    <Paper
      sx={{
        p: 2.5,
        border: '1px solid rgba(0,0,0,0.06)',
        borderTop: `3px solid ${riskColor}`,
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, mb: 2 }}>
        <Box
          sx={{
            width: 32,
            height: 32,
            borderRadius: '10px',
            backgroundColor: '#FFF9DB',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            mt: 0.25,
          }}
        >
          <FontAwesomeIcon icon={faLightbulb} style={{ fontSize: 14, color: '#E67700' }} />
        </Box>
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.25 }}>
            <Typography variant="overline" sx={{ color: 'text.secondary' }}>
              Recommended action
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: riskColor,
                fontWeight: 600,
                bgcolor: `${riskColor}18`,
                px: 0.75,
                py: 0.125,
                borderRadius: 1,
                fontSize: '0.6875rem',
              }}
            >
              {rec.risk_tier} risk
            </Typography>
          </Box>
          <Typography variant="body1" sx={{ fontWeight: 600, color: 'text.primary', lineHeight: 1.5 }}>
            {rec.action_text}
          </Typography>
        </Box>
      </Box>

      {/* Expected impact */}
      {rec.expected_impact?.length > 0 && (
        <>
          <Divider sx={{ mb: 1.5 }} />
          <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', mb: 1 }}>
            Expected impact
          </Typography>
          <List disablePadding sx={{ mb: 2 }}>
            {rec.expected_impact.map((impact, i) => (
              <ListItem key={i} disableGutters sx={{ py: 0.5, gap: 1 }}>
                <FontAwesomeIcon
                  icon={impact.direction === 'DOWN' || impact.direction === 'decrease' ? faArrowTrendDown : faArrowTrendUp}
                  style={{
                    fontSize: 11,
                    color: impact.direction === 'DOWN' || impact.direction === 'decrease' ? '#2F9E44' : '#E03131',
                    flexShrink: 0,
                  }}
                />
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  <strong style={{ color: '#1C1B1F' }}>
                    {impact.metric.replace(/_/g, ' ')}
                  </strong>{' '}
                  {impact.note ? `· ${impact.note}` : impact.direction.toLowerCase()}
                </Typography>
              </ListItem>
            ))}
          </List>
        </>
      )}

      {/* Requires approval note */}
      {canDecide && (
        <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1.5 }}>
          Requires manager approval before execution.
        </Typography>
      )}

      {/* Decision UI */}
      {canDecide && (
        <Box>
          <TextField
            fullWidth
            size="small"
            multiline
            rows={2}
            placeholder="Optional manager note\u2026"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            sx={{
              mb: 2,
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
                fontSize: '0.875rem',
                '& fieldset': { borderColor: 'rgba(0,0,0,0.1)' },
              },
            }}
          />

          {localError && (
            <Typography variant="caption" sx={{ color: 'error.main', display: 'block', mb: 1 }}>
              {localError}
            </Typography>
          )}

          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <Button
              variant="outlined"
              startIcon={
                loading === 'REJECT' ? (
                  <CircularProgress size={14} />
                ) : (
                  <FontAwesomeIcon icon={faXmark} style={{ fontSize: 13 }} />
                )
              }
              disabled={loading !== null}
              onClick={() => void handleDecide('REJECT')}
              sx={{
                borderRadius: 2,
                flex: 1,
                borderColor: 'rgba(0,0,0,0.12)',
                color: 'text.secondary',
                '&:hover': { borderColor: 'error.main', color: 'error.main' },
              }}
            >
              Reject
            </Button>
            <Button
              variant="contained"
              color="primary"
              startIcon={
                loading === 'APPROVE' ? (
                  <CircularProgress size={14} sx={{ color: 'white' }} />
                ) : (
                  <FontAwesomeIcon icon={faCheck} style={{ fontSize: 13 }} />
                )
              }
              disabled={loading !== null}
              onClick={() => void handleDecide('APPROVE')}
              sx={{ borderRadius: 2, flex: 2 }}
            >
              Approve action
            </Button>
          </Box>
        </Box>
      )}

      {incidentStatus === 'ACTION_APPROVED' && (
        <Box
          sx={{
            mt: 2,
            p: 1.5,
            borderRadius: 2,
            bgcolor: '#EBFBEE',
            border: '1px solid #B2F2BB',
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <FontAwesomeIcon icon={faCheck} style={{ fontSize: 13, color: '#2F9E44' }} />
          <Typography variant="body2" sx={{ color: '#237032', fontWeight: 500 }}>
            Action approved. Monitoring for outcome.
          </Typography>
        </Box>
      )}

      {incidentStatus === 'ACTION_REJECTED' && (
        <Box
          sx={{
            mt: 2,
            p: 1.5,
            borderRadius: 2,
            bgcolor: '#FFF5F5',
            border: '1px solid #FFC9C9',
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <FontAwesomeIcon icon={faXmark} style={{ fontSize: 13, color: '#C92A2A' }} />
          <Typography variant="body2" sx={{ color: '#C92A2A', fontWeight: 500 }}>
            Action rejected by manager.
          </Typography>
        </Box>
      )}
    </Paper>
  );
};
