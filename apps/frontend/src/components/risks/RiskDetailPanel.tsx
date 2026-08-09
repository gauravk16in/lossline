import React from 'react';
import { Box, Typography, Button, Divider } from '@mui/material';
import { ArrowLeft, ArrowRight, Calendar, CloudRain, Tag, Zap } from 'lucide-react';
import type { RiskLevel } from '../../data/viewModels';
import { useDashboard } from '../../state/DashboardContext';
import { useNavigate } from 'react-router-dom';

const RISK_BADGE: Record<RiskLevel, { text: string; bg: string; border: string }> = {
  HIGH:   { text: '#EF4444', bg: 'rgba(239,68,68,0.1)',  border: 'rgba(239,68,68,0.2)' },
  MEDIUM: { text: '#F59E0B', bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.2)' },
  LOW:    { text: '#22C55E', bg: 'rgba(34,197,94,0.1)',   border: 'rgba(34,197,94,0.2)' },
};

const DRIVER_ICONS: Record<string, React.ElementType> = {
  calendar: Calendar,
  'cloud-rain': CloudRain,
  tag: Tag,
};

/**
 * RiskDetailPanel — right-side panel showing selected risk item details.
 * Matches the risk.png design's right panel exactly.
 * Consistent styling with PriorityDecisionPanel from overview.
 */
export const RiskDetailPanel: React.FC = () => {
  const { riskDetailItem: d } = useDashboard();
  const navigate = useNavigate();
  if (!d) return null;
  const badge = RISK_BADGE[d.riskLevel];

  return (
    <Box
      id="risk-detail-panel"
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
      {/* ── Back header ── */}
      <Box
        sx={{
          px: 2.5, py: 1.5,
          display: 'flex', alignItems: 'center', gap: 0.75,
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          cursor: 'pointer',
          transition: 'background-color 150ms ease',
          '&:hover': { backgroundColor: 'rgba(255,255,255,0.02)' },
        }}
      >
        <ArrowLeft size={16} color="#8B95A8" />
        <Typography variant="body2" sx={{ color: '#8B95A8', fontWeight: 500, fontSize: '0.8125rem' }}>
          Back
        </Typography>
      </Box>

      {/* ── Content ── */}
      <Box sx={{ p: 2.5, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {/* Item Info */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
          <Box component="img" src={d.image} alt={d.name}
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
            {d.riskLevel} RISK
          </Typography>
        </Box>

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.06)' }} />

        {/* Risk Summary */}
        <Box>
          <Typography variant="h4" sx={{ color: '#F4F7FB', mb: 1.25, fontWeight: 600 }}>
            Risk Summary
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
            <StatRow label="Forecast Demand" value={`${d.forecastDemand} portions`} />
            <StatRow label="Available Inventory" value={`${d.availableInventory} portions`} />
            <StatRow label="Projected Gap" value={`${d.projectedGap} portions`} valueColor="#EF4444" />
            <StatRow label="Safety Buffer" value={`${d.safetyBuffer} portions`} />
          </Box>
        </Box>

        {/* Expected Stockout */}
        <Box
          sx={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            px: 1.5, py: 1, borderRadius: '10px',
            backgroundColor: 'rgba(239,68,68,0.06)',
            border: '1px solid rgba(239,68,68,0.1)',
          }}
        >
          <Box>
            <Typography variant="body2" sx={{ color: '#8B95A8', fontSize: '0.8125rem' }}>
              Expected Stockout
            </Typography>
            <Typography variant="caption" sx={{ color: '#525C6C', fontSize: '0.6875rem' }}>
              {d.stockoutCountdown}
            </Typography>
          </Box>
          <Typography variant="body2" sx={{ color: '#EF4444', fontWeight: 700, fontSize: '1rem' }}>
            {d.expectedStockout}
          </Typography>
        </Box>

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.06)' }} />

        {/* Top Drivers */}
        <Box>
          <Typography variant="h4" sx={{ color: '#F4F7FB', mb: 1, fontWeight: 600 }}>
            Top Drivers
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
            {d.topDrivers.map((driver) => {
              const IconComp = DRIVER_ICONS[driver.icon];
              return (
                <Box key={driver.id} sx={{ display: 'flex', alignItems: 'center', gap: 0.75, py: 0.25 }}>
                  <Box sx={{ width: 24, height: 24, borderRadius: '6px', backgroundColor: 'rgba(167,139,250,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <IconComp size={12} color="#A78BFA" />
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
          <Typography
            variant="caption"
            sx={{
              color: '#A78BFA', fontSize: '0.75rem', fontWeight: 500,
              mt: 1, display: 'flex', alignItems: 'center', gap: 0.5,
              cursor: 'pointer',
              '&:hover': { textDecoration: 'underline' },
            }}
          >
            View all drivers <ArrowRight size={12} />
          </Typography>
        </Box>

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.06)' }} />

        {/* Recommended Action */}
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

        {/* CTA Button */}
        <Button
          onClick={() => navigate('/decisions')}
          variant="contained"
          fullWidth
          endIcon={<ArrowRight size={16} />}
          sx={{
            mt: 0.5, py: 1.25, borderRadius: '12px',
            background: 'linear-gradient(135deg, #7C5CFC, #6C4FE0)',
            color: '#fff', fontWeight: 600, fontSize: '0.875rem',
            textTransform: 'none',
            boxShadow: '0 4px 16px rgba(124,92,252,0.25)',
            '&:hover': {
              background: 'linear-gradient(135deg, #8B6FFD, #7C5CFC)',
              boxShadow: '0 6px 24px rgba(124,92,252,0.35)',
              transform: 'translateY(-1px)',
            },
          }}
        >
          Review Decision
        </Button>
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
