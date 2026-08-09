import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Skeleton,
  Alert,
  IconButton,
  Divider,
  Button,
  Tooltip,
} from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faArrowLeft,
  faStore,
  faMagnifyingGlass,
  faTriangleExclamation,
  faRotateRight,
} from '@fortawesome/free-solid-svg-icons';
import { useParams, useNavigate } from 'react-router-dom';
import { PageContainer } from '../components/layout/PageContainer';
import { SeverityChip } from '../components/common/SeverityChip';
import { StatusChip } from '../components/common/StatusChip';
import { EvidenceList } from '../components/incidents/EvidenceList';
import { ConfidencePanel } from '../components/incidents/ConfidencePanel';
import { RevenueRiskCard } from '../components/incidents/RevenueRiskCard';
import { RecommendationCard } from '../components/incidents/RecommendationCard';
import { OutcomeComparison } from '../components/incidents/OutcomeComparison';
import { api } from '../api/client';
import type { Incident, Outcome, DecisionPayload } from '../types/api';
import { formatIncidentType, formatOutletName } from '../components/utils/format';
import { formatTime, formatDistanceToNow } from '../components/utils/time';

export const IncidentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const incidentId = Number(id);

  const [incident, setIncident] = useState<Incident | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);

  const loadIncident = useCallback(async () => {
    if (!incidentId) return;
    try {
      const inc = await api.getIncident(incidentId);
      setIncident(inc);
      setError(null);
      // Try to load outcome if applicable
      if (['ACTION_APPROVED', 'VERIFYING', 'RESOLVED', 'NOT_IMPROVED'].includes(inc.status)) {
        try {
          const out = await api.getOutcome(incidentId);
          setOutcome(out);
        } catch {
          // Outcome not yet available
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load incident.');
    } finally {
      setLoading(false);
    }
  }, [incidentId]);

  useEffect(() => {
    void loadIncident();
  }, [loadIncident]);

  async function handleDecide(decision: 'APPROVE' | 'REJECT', note?: string) {
    if (!incident) return;
    const payload: DecisionPayload = {
      decision,
      manager_note: note,
      idempotency_key: crypto.randomUUID(),
    };
    await api.submitDecision(incident.id, payload);
    await loadIncident();
  }

  async function handleVerify() {
    if (!incident) return;
    setVerifying(true);
    try {
      const out = await api.verifyOutcome(incident.id);
      setOutcome(out);
      await loadIncident();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed.');
    } finally {
      setVerifying(false);
    }
  }

  if (loading) {
    return (
      <PageContainer>
        <Skeleton variant="rectangular" height={80} sx={{ borderRadius: 2, mb: 2 }} />
        <Skeleton variant="rectangular" height={200} sx={{ borderRadius: 2, mb: 2 }} />
        <Skeleton variant="rectangular" height={150} sx={{ borderRadius: 2 }} />
      </PageContainer>
    );
  }

  if (error || !incident) {
    return (
      <PageContainer>
        <Alert severity="error">{error ?? 'Incident not found.'}</Alert>
      </PageContainer>
    );
  }

  const signals = incident.signals ?? [];
  const recommendations = incident.recommendations ?? [];
  const showVerifyButton =
    incident.status === 'ACTION_APPROVED' && !outcome && !verifying;

  return (
    <PageContainer>
      {/* Back button */}
      <Box sx={{ mb: 2 }}>
        <IconButton
          size="small"
          onClick={() => navigate(-1)}
          sx={{
            color: 'text.secondary',
            borderRadius: 2,
            border: '1px solid rgba(0,0,0,0.1)',
            '&:hover': { borderColor: 'primary.main', color: 'primary.main' },
          }}
        >
          <FontAwesomeIcon icon={faArrowLeft} style={{ fontSize: 13 }} />
        </IconButton>
      </Box>

      {/* Incident header */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 2, mb: 2 }}>
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Typography variant="overline" sx={{ color: 'text.secondary' }}>
                Incident #{incident.id}
              </Typography>
            </Box>
            <Typography variant="h1" sx={{ mb: 1 }}>
              {formatIncidentType(incident.incident_type)}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                <FontAwesomeIcon icon={faStore} style={{ fontSize: 11, color: '#868E96' }} />
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  {formatOutletName(incident.restaurant_id)}
                </Typography>
              </Box>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                Started {formatTime(incident.window_start)} · {formatDistanceToNow(incident.created_at)}
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
            <SeverityChip severity={incident.severity} size="medium" />
            <StatusChip status={incident.status} size="medium" />
          </Box>
        </Box>
      </Paper>

      <Grid container spacing={3}>
        {/* Left column: narrative */}
        <Grid size={{ xs: 12, md: 8 }}>

          {/* What happened */}
          {signals.length > 0 && (
            <Paper sx={{ p: 3, mb: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <FontAwesomeIcon icon={faTriangleExclamation} style={{ fontSize: 14, color: '#E67700' }} />
                <Typography variant="h2">What happened</Typography>
              </Box>
              {/* Signal comparison cards */}
              <Grid container spacing={1.5} sx={{ mb: 0.5 }}>
                {signals.slice(0, 3).map(signal => {
                  const curr = Number(signal.current_value);
                  const base = signal.baseline_value != null ? Number(signal.baseline_value) : null;
                  const unit = signal.unit;

                  function fmtV(v: number) {
                    if (unit === 'cancellation_rate' || unit === 'rate') return `${(v * 100).toFixed(1)}%`;
                    if (unit === 'seconds') return `${Math.round(v / 60)} min`;
                    return String(Math.round(v));
                  }

                  const change = base && base > 0 ? ((curr - base) / base * 100) : null;

                  return (
                    <Grid size={{ xs: 12, sm: 4 }} key={signal.id}>
                      <Box
                        sx={{
                          p: 2,
                          borderRadius: 2,
                          bgcolor: '#F8F9FA',
                          border: '1px solid rgba(0,0,0,0.06)',
                        }}
                      >
                        <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1 }}>
                          {signal.signal_type.replace(/_/g, ' ').toLowerCase().replace(/^\w/, c => c.toUpperCase())}
                        </Typography>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                          <Box>
                            <Typography sx={{ fontSize: '1.25rem', fontWeight: 700, color: 'text.primary', lineHeight: 1 }}>
                              {fmtV(curr)}
                            </Typography>
                            <Typography variant="caption" sx={{ color: 'text.secondary' }}>Current</Typography>
                          </Box>
                          {base != null && (
                            <Box sx={{ textAlign: 'right' }}>
                              <Typography sx={{ fontSize: '1rem', fontWeight: 500, color: 'text.secondary', lineHeight: 1 }}>
                                {fmtV(base)}
                              </Typography>
                              <Typography variant="caption" sx={{ color: 'text.secondary' }}>Baseline</Typography>
                            </Box>
                          )}
                        </Box>
                        {change != null && (
                          <Typography
                            variant="caption"
                            sx={{
                              mt: 1,
                              display: 'block',
                              color: Math.abs(change) > 20 ? 'error.main' : 'warning.main',
                              fontWeight: 600,
                            }}
                          >
                            {change > 0 ? '+' : ''}{change.toFixed(0)}%
                          </Typography>
                        )}
                      </Box>
                    </Grid>
                  );
                })}
              </Grid>
            </Paper>
          )}

          {/* Likely contributing cause */}
          {incident.explanation && (
            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h2" sx={{ mb: 1.5 }}>
                Likely contributing cause
              </Typography>
              <Typography
                variant="body1"
                sx={{
                  color: 'text.secondary',
                  lineHeight: 1.7,
                  fontStyle: 'italic',
                  borderLeft: '3px solid rgba(0,0,0,0.08)',
                  pl: 2,
                  mb: 2.5,
                }}
              >
                &ldquo;{incident.explanation}&rdquo;
              </Typography>
              {incident.probable_cause && (
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Classification:{' '}
                  <strong style={{ color: '#1C1B1F' }}>
                    {incident.probable_cause.replace(/_/g, ' ')}
                  </strong>
                </Typography>
              )}
            </Paper>
          )}

          {/* Evidence */}
          {signals.length > 0 && (
            <Paper sx={{ p: 3, mb: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <FontAwesomeIcon icon={faMagnifyingGlass} style={{ fontSize: 14, color: '#868E96' }} />
                <Typography variant="h2">Evidence</Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary', ml: 'auto' }}>
                  {signals.length} signal{signals.length > 1 ? 's' : ''}
                </Typography>
              </Box>
              <EvidenceList signals={signals} />
            </Paper>
          )}

          {/* Outcome section (post-approval) */}
          {outcome && (
            <Box sx={{ mb: 3 }}>
              <OutcomeComparison outcome={outcome} />
            </Box>
          )}

          {/* Verify outcome button */}
          {showVerifyButton && (
            <Box sx={{ mb: 3 }}>
              <Tooltip title="Trigger outcome verification to see whether metrics improved after the approved action">
                <Button
                  variant="outlined"
                  startIcon={<FontAwesomeIcon icon={faRotateRight} style={{ fontSize: 13 }} />}
                  onClick={() => void handleVerify()}
                  disabled={verifying}
                  sx={{ borderRadius: 2 }}
                >
                  {verifying ? 'Verifying\u2026' : 'Verify outcome'}
                </Button>
              </Tooltip>
              <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 1 }}>
                Check whether operational metrics improved after the approved action.
              </Typography>
            </Box>
          )}

          {incident.status === 'ACTION_APPROVED' && !outcome && !showVerifyButton && (
            <Paper sx={{ p: 2.5, mb: 3, bgcolor: '#F8F9FA' }}>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                Waiting for post-action evidence.
              </Typography>
            </Paper>
          )}
        </Grid>

        {/* Right column: confidence + revenue + recommendation */}
        <Grid size={{ xs: 12, md: 4 }}>
          {/* Confidence */}
          <Paper sx={{ p: 2.5, mb: 2 }}>
            <ConfidencePanel
              confidence={incident.confidence}
              components={incident.confidence_components}
            />
          </Paper>

          {/* Revenue risk */}
          <Box sx={{ mb: 2 }}>
            <RevenueRiskCard
              revenueAtRisk={incident.revenue_at_risk != null ? Number(incident.revenue_at_risk) : null}
              currency={incident.currency}
            />
          </Box>

          {/* Recommendation */}
          {recommendations.length > 0 && (
            <RecommendationCard
              recommendations={recommendations}
              incidentStatus={incident.status}
              onDecide={handleDecide}
            />
          )}

          {recommendations.length === 0 && incident.status === 'AWAITING_APPROVAL' && (
            <Paper sx={{ p: 2.5 }}>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                Recommendation generation in progress.
              </Typography>
            </Paper>
          )}
        </Grid>
      </Grid>
    </PageContainer>
  );
};
