import React, { useState } from 'react';
import { Box, Typography, Button, Divider, TextField } from '@mui/material';
import {
  MoreHorizontal,
  CheckSquare,
  AlertCircle,
  Calendar,
  CloudRain,
  Tag,
  Zap,
  X,
  Check,
} from 'lucide-react';
import type { DisplayRiskLevel } from '../../data/viewModels';
import { useDashboard } from '../../state/DashboardContext';

const RISK_BADGE: Record<DisplayRiskLevel, { text: string; bg: string; border: string }> = {
  High:   { text: '#EF4444', bg: 'rgba(239,68,68,0.1)',  border: 'rgba(239,68,68,0.2)' },
  Medium: { text: '#F59E0B', bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.2)' },
  Low:    { text: '#22C55E', bg: 'rgba(34,197,94,0.1)',   border: 'rgba(34,197,94,0.2)' },
};

const DRIVER_ICONS: Record<string, React.ElementType> = {
  calendar: Calendar,
  'cloud-rain': CloudRain,
  tag: Tag,
};

/**
 * DecisionDetailPanel — right-side panel for reviewing a specific decision.
 * Matches decision.png: Priority Decision header, item info, "What we expect",
 * "Why this matters", "Top Drivers", "Recommended Action", Reject/Approve buttons.
 */
export const DecisionDetailPanel: React.FC = () => {
  const { decisionDetail: d, reviewDecision, loading, error } = useDashboard();
  const [note, setNote] = useState('');
  if (!d) return null;
  const badge = RISK_BADGE[d.riskLevel];

  return (
    <Box
      id="decision-detail-panel"
      sx={{
        width: 320,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        background: '#111631',
        borderRadius: '16px',
        border: '1px solid rgba(255,255,255,0.06)',
        overflow: 'hidden',
        alignSelf: 'flex-start',
        position: 'sticky',
        top: 24,
      }}
    >
      {/* ── Header ── */}
      <Box
        sx={{
          px: 2.5, py: 1.75,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <Typography variant="h3" sx={{ color: '#F4F7FB', fontWeight: 600 }}>
          Priority Decision
        </Typography>
        <MoreHorizontal size={16} color="#525C6C" style={{ cursor: 'pointer' }} />
      </Box>

      {/* ── Content ── */}
      <Box sx={{ p: 2.5, display: 'flex', flexDirection: 'column', gap: 2, overflowY: 'auto' }}>
        {/* Item Info */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
          <Box
            component="img"
            src={d.image}
            alt={d.name}
            sx={{ width: 52, height: 52, borderRadius: '10px', objectFit: 'cover', flexShrink: 0 }}
          />
          <Box>
            <Typography variant="body1" sx={{ color: '#F4F7FB', fontWeight: 600, lineHeight: 1.3 }}>
              {d.name}
            </Typography>
            <Typography variant="caption" sx={{ color: '#8B95A8', lineHeight: 1.3 }}>
              {d.category} · {d.outletName}
            </Typography>
          </Box>
        </Box>

        {/* Risk Badge */}
        <Box
          sx={{
            display: 'inline-flex', alignItems: 'center',
            px: 1, py: 0.25, borderRadius: '6px',
            backgroundColor: badge.bg, border: `1px solid ${badge.border}`,
            width: 'fit-content',
          }}
        >
          <Typography variant="caption" sx={{ color: badge.text, fontWeight: 600, fontSize: '0.6875rem', letterSpacing: '0.04em' }}>
            {d.riskLevel} Risk
          </Typography>
        </Box>

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.06)' }} />

        {/* ── What we expect ── */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 1.25 }}>
            <CheckSquare size={14} color="#A78BFA" />
            <Typography variant="h4" sx={{ color: '#F4F7FB', fontWeight: 600 }}>
              What we expect
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
            <StatRow label="Forecast Demand" value={`${d.forecastDemand} portions`} />
            <StatRow label="Forecast Range" value={d.forecastRange} />
            <StatRow label="Available Inventory" value={`${d.availableInventory} portions`} />
            <StatRow label="Projected Shortage" value={`${d.projectedShortage} portions`} valueColor="#EF4444" />
            <StatRow label="Expected Stockout" value={d.expectedStockout} valueColor="#EF4444" />
          </Box>
        </Box>

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.06)' }} />

        {/* ── Why this matters ── */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 1 }}>
            <AlertCircle size={14} color="#F59E0B" />
            <Typography variant="h4" sx={{ color: '#F4F7FB', fontWeight: 600 }}>
              Why this matters
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.625 }}>
            {d.whyItMatters.map((reason, idx) => (
              <Box key={idx} sx={{ display: 'flex', gap: 0.75, alignItems: 'flex-start' }}>
                <Box sx={{ width: 4, height: 4, borderRadius: '50%', backgroundColor: '#525C6C', mt: 0.75, flexShrink: 0 }} />
                <Typography variant="body2" sx={{ color: '#8B95A8', fontSize: '0.8125rem', lineHeight: 1.4 }}>
                  {reason}
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.06)' }} />

        {/* ── Top Drivers ── */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 1 }}>
            <Calendar size={14} color="#A78BFA" />
            <Typography variant="h4" sx={{ color: '#F4F7FB', fontWeight: 600 }}>
              Top Drivers
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.625 }}>
            {d.topDrivers.map((driver) => {
              const IconComp = DRIVER_ICONS[driver.icon];
              return (
                <Box key={driver.id} sx={{ display: 'flex', alignItems: 'center', gap: 0.75, py: 0.25 }}>
                  <Box
                    sx={{
                      width: 22, height: 22, borderRadius: '5px',
                      backgroundColor: 'rgba(167,139,250,0.1)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    }}
                  >
                    <IconComp size={11} color="#A78BFA" />
                  </Box>
                  <Typography variant="body2" sx={{ color: '#8B95A8', flex: 1, fontSize: '0.8125rem' }}>
                    {driver.label}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#22C55E', fontWeight: 600, fontSize: '0.8125rem' }}>
                    {driver.impact}
                  </Typography>
                </Box>
              );
            })}
          </Box>
        </Box>

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.06)' }} />

        {/* ── Recommended Action ── */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.75 }}>
            <Zap size={14} color="#A78BFA" />
            <Typography variant="h4" sx={{ color: '#F4F7FB', fontWeight: 600 }}>
              Recommended Action
            </Typography>
          </Box>
          <Typography variant="body2" sx={{ color: '#8B95A8', lineHeight: 1.5 }}>
            {d.recommendedAction} before{' '}
            <Typography component="span" sx={{ color: '#F4F7FB', fontWeight: 600, fontSize: 'inherit' }}>
              {d.recommendedDeadline}
            </Typography>{' '}
            to avoid stockout.
          </Typography>
        </Box>

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.06)' }} />

        {/* ── Your Decision ── */}
        <Box>
          <Typography variant="h4" sx={{ color: '#F4F7FB', fontWeight: 600, mb: 1.25 }}>
            Your Decision
          </Typography>

          {/* Reject / Approve buttons */}
          <Box sx={{ display: 'flex', gap: 1, mb: 1.5 }}>
            <Button
              disabled={loading || d.status !== 'AWAITING_MANAGER_REVIEW'}
              onClick={() => void reviewDecision('REJECT', note)}
              variant="outlined"
              startIcon={<X size={14} />}
              sx={{
                flex: 1,
                color: '#EF4444',
                borderColor: 'rgba(239,68,68,0.3)',
                borderRadius: '10px',
                textTransform: 'none',
                fontWeight: 600,
                fontSize: '0.8125rem',
                py: 0.875,
                '&:hover': {
                  borderColor: '#EF4444',
                  backgroundColor: 'rgba(239,68,68,0.08)',
                },
              }}
            >
              Reject
            </Button>
            <Button
              disabled={loading || d.status !== 'AWAITING_MANAGER_REVIEW'}
              onClick={() => void reviewDecision('APPROVE', note)}
              variant="contained"
              startIcon={<Check size={14} />}
              sx={{
                flex: 1,
                background: 'linear-gradient(135deg, #22C55E, #16A34A)',
                color: '#fff',
                borderRadius: '10px',
                textTransform: 'none',
                fontWeight: 600,
                fontSize: '0.8125rem',
                py: 0.875,
                boxShadow: '0 4px 12px rgba(34,197,94,0.25)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #4ADE80, #22C55E)',
                  boxShadow: '0 6px 20px rgba(34,197,94,0.35)',
                  transform: 'translateY(-1px)',
                },
              }}
            >
              {loading ? 'Saving…' : 'Approve'}
            </Button>
          </Box>

          {/* Note input */}
          <TextField
            placeholder="Add a note (optional)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            size="small"
            fullWidth
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: '10px',
                backgroundColor: 'rgba(255,255,255,0.03)',
                fontSize: '0.8125rem',
                color: '#F4F7FB',
                '& fieldset': {
                  borderColor: 'rgba(255,255,255,0.08)',
                },
                '&:hover fieldset': {
                  borderColor: 'rgba(255,255,255,0.12)',
                },
                '&.Mui-focused fieldset': {
                  borderColor: 'rgba(124,92,252,0.4)',
                },
              },
              '& .MuiInputBase-input::placeholder': {
                color: '#525C6C',
                opacity: 1,
              },
            }}
          />
          {error && <Typography role="alert" variant="caption" sx={{ color: '#EF4444', display: 'block', mt: 1 }}>{error}</Typography>}
        </Box>
      </Box>
    </Box>
  );
};

/* ── Helper ── */
interface StatRowProps { label: string; value: string; valueColor?: string }
const StatRow: React.FC<StatRowProps> = ({ label, value, valueColor = '#F4F7FB' }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
    <Typography variant="body2" sx={{ color: '#8B95A8', fontSize: '0.8125rem' }}>{label}</Typography>
    <Typography variant="body2" sx={{ color: valueColor, fontWeight: 600, fontSize: '0.8125rem' }}>{value}</Typography>
  </Box>
);
