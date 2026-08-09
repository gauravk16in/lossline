import React from 'react';
import { Box, Typography, Button, Divider } from '@mui/material';
import { Sparkles, ArrowRight, Zap } from 'lucide-react';
import { KeyDriversList } from './KeyDriversList';
import { priorityDecision } from '../../data/overviewMockData';

/**
 * PriorityDecisionPanel — right-side panel showing the highest-priority decision.
 * Contains item details, key drivers, recommended action, and CTA button.
 */
export const PriorityDecisionPanel: React.FC = () => {
  const d = priorityDecision;

  return (
    <Box
      id="priority-decision-panel"
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
          p: 2.5,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <Sparkles size={18} color="#A78BFA" />
        <Typography
          variant="h3"
          sx={{ color: '#F4F7FB', fontWeight: 600, flex: 1 }}
        >
          Priority Decision
        </Typography>
      </Box>

      {/* ── Content ── */}
      <Box sx={{ p: 2.5, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {/* Priority Badge */}
        <Box
          sx={{
            display: 'inline-flex',
            alignItems: 'center',
            px: 1,
            py: 0.25,
            borderRadius: '6px',
            backgroundColor: 'rgba(239,68,68,0.1)',
            border: '1px solid rgba(239,68,68,0.2)',
            width: 'fit-content',
          }}
        >
          <Typography
            variant="caption"
            sx={{
              color: '#EF4444',
              fontWeight: 600,
              fontSize: '0.6875rem',
              letterSpacing: '0.04em',
            }}
          >
            HIGH PRIORITY
          </Typography>
        </Box>

        {/* Item Info */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
          <Box
            component="img"
            src={d.itemImage}
            alt={d.itemName}
            sx={{
              width: 48,
              height: 48,
              borderRadius: '10px',
              objectFit: 'cover',
              flexShrink: 0,
            }}
          />
          <Box>
            <Typography
              variant="body1"
              sx={{ color: '#F4F7FB', fontWeight: 600, lineHeight: 1.3 }}
            >
              {d.itemName}
            </Typography>
            <Typography
              variant="caption"
              sx={{ color: '#8B95A8', lineHeight: 1.3 }}
            >
              {d.outletName}
            </Typography>
          </Box>
        </Box>

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.06)' }} />

        {/* Stats Rows */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <StatRow label="Forecast Demand" value={`${d.forecastDemand} portions`} />
          <StatRow label="Available Inventory" value={`${d.availableInventory} portions`} />
          <StatRow
            label="Projected Shortage"
            value={`${d.projectedShortage} portions`}
            valueColor="#EF4444"
          />
        </Box>

        {/* Expected Stockout */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: 1.5,
            py: 1,
            borderRadius: '10px',
            backgroundColor: 'rgba(239,68,68,0.06)',
            border: '1px solid rgba(239,68,68,0.1)',
          }}
        >
          <Typography variant="body2" sx={{ color: '#8B95A8', fontSize: '0.8125rem' }}>
            Expected Stockout
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: '#EF4444',
              fontWeight: 700,
              fontSize: '0.9375rem',
            }}
          >
            {d.expectedStockout}
          </Typography>
        </Box>

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.06)' }} />

        {/* Key Drivers */}
        <Box>
          <Typography
            variant="h4"
            sx={{ color: '#F4F7FB', mb: 1, fontWeight: 600 }}
          >
            Key Drivers
          </Typography>
          <KeyDriversList drivers={d.keyDrivers} />
        </Box>

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.06)' }} />

        {/* Recommended Action */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.75 }}>
            <Zap size={14} color="#A78BFA" />
            <Typography
              variant="h4"
              sx={{ color: '#F4F7FB', fontWeight: 600 }}
            >
              Recommended Action
            </Typography>
          </Box>
          <Typography variant="body2" sx={{ color: '#8B95A8', lineHeight: 1.5 }}>
            {d.recommendedAction} before{' '}
            <Typography
              component="span"
              sx={{ color: '#F4F7FB', fontWeight: 600, fontSize: 'inherit' }}
            >
              {d.recommendedDeadline}
            </Typography>{' '}
            to avoid stockout.
          </Typography>
        </Box>

        {/* CTA Button */}
        <Button
          variant="contained"
          fullWidth
          endIcon={<ArrowRight size={16} />}
          sx={{
            mt: 0.5,
            py: 1.25,
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #7C5CFC, #6C4FE0)',
            color: '#fff',
            fontWeight: 600,
            fontSize: '0.875rem',
            textTransform: 'none',
            boxShadow: '0 4px 16px rgba(124,92,252,0.25)',
            '&:hover': {
              background: 'linear-gradient(135deg, #8B6FFD, #7C5CFC)',
              boxShadow: '0 6px 24px rgba(124,92,252,0.35)',
              transform: 'translateY(-1px)',
            },
          }}
        >
          Review decision
        </Button>
      </Box>
    </Box>
  );
};

/* ── Helper: Stat Row ── */

interface StatRowProps {
  label: string;
  value: string;
  valueColor?: string;
}

const StatRow: React.FC<StatRowProps> = ({
  label,
  value,
  valueColor = '#F4F7FB',
}) => (
  <Box
    sx={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    }}
  >
    <Typography variant="body2" sx={{ color: '#8B95A8', fontSize: '0.8125rem' }}>
      {label}
    </Typography>
    <Typography
      variant="body2"
      sx={{
        color: valueColor,
        fontWeight: 600,
        fontSize: '0.8125rem',
      }}
    >
      {value}
    </Typography>
  </Box>
);
