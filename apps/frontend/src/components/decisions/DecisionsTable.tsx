import React, { useState } from 'react';
import { Box, Typography, Paper, Button, IconButton } from '@mui/material';
import { Filter, MoreHorizontal, ChevronLeft, ChevronRight } from 'lucide-react';
import {
  decisionItems,
  decisionTabs,
  type DecisionStatus,
  type RiskLevel,
} from '../../data/decisionsMockData';

/** Risk dot colors */
const RISK_DOT: Record<RiskLevel, string> = {
  High: '#EF4444',
  Medium: '#F59E0B',
  Low: '#22C55E',
};

/** Risk badge background */
const RISK_BG: Record<RiskLevel, string> = {
  High: 'rgba(239,68,68,0.15)',
  Medium: 'rgba(245,158,11,0.15)',
  Low: 'rgba(34,197,94,0.15)',
};

/**
 * DecisionsTable — main decisions table with status tabs.
 * Matches decision.png: Pending|Approved|Completed tabs,
 * columns: Decision, Risk, Forecast Demand, Available Inventory, Projected Gap, Deadline, Status, Action
 */
export const DecisionsTable: React.FC = () => {
  const [activeTab, setActiveTab] = useState<DecisionStatus>('Pending');

  return (
    <Paper
      id="decisions-table"
      sx={{
        p: 3,
        background: '#111631',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '16px',
      }}
    >
      {/* ── Status Tabs ── */}
      <Box sx={{ display: 'flex', gap: 0, mb: 3 }}>
        {decisionTabs.map((tab) => (
          <Box
            key={tab.status}
            onClick={() => setActiveTab(tab.status)}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.75,
              px: 2,
              py: 1,
              cursor: 'pointer',
              borderBottom: activeTab === tab.status
                ? '2px solid #7C5CFC'
                : '2px solid transparent',
              transition: 'all 150ms ease',
              '&:hover': {
                borderBottom: activeTab === tab.status
                  ? '2px solid #7C5CFC'
                  : '2px solid rgba(255,255,255,0.1)',
              },
            }}
          >
            <Typography
              variant="body2"
              sx={{
                color: activeTab === tab.status ? '#F4F7FB' : '#8B95A8',
                fontWeight: activeTab === tab.status ? 600 : 400,
                fontSize: '0.875rem',
              }}
            >
              {tab.status}
            </Typography>
            <Box
              sx={{
                px: 0.75,
                py: 0.125,
                borderRadius: '6px',
                backgroundColor: activeTab === tab.status
                  ? 'rgba(124,92,252,0.2)'
                  : 'rgba(255,255,255,0.06)',
                minWidth: 24,
                textAlign: 'center',
              }}
            >
              <Typography
                variant="caption"
                sx={{
                  color: activeTab === tab.status ? '#A78BFA' : '#525C6C',
                  fontWeight: 600,
                  fontSize: '0.75rem',
                }}
              >
                {tab.count}
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>

      {/* ── Filter Bar ── */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2 }}>
        <Button
          startIcon={<Filter size={14} />}
          size="small"
          sx={{
            color: '#8B95A8', fontSize: '0.8125rem', fontWeight: 500,
            textTransform: 'none', px: 1.5, py: 0.5, borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.08)',
            '&:hover': { backgroundColor: 'rgba(255,255,255,0.04)', color: '#F4F7FB' },
          }}
        >
          Filter
        </Button>
        <IconButton size="small" sx={{ color: '#8B95A8', '&:hover': { color: '#F4F7FB' } }}>
          <MoreHorizontal size={16} />
        </IconButton>
      </Box>

      {/* ── Column Headers ── */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: '2fr 1.3fr 0.9fr 0.9fr 0.9fr 1fr 0.8fr 0.7fr',
          gap: 1,
          pb: 1.5,
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          mb: 0.5,
        }}
      >
        {['Decision', 'Risk', 'Forecast Demand', 'Available Inventory', 'Projected Gap', 'Deadline', 'Status', 'Action'].map((h) => (
          <Typography
            key={h}
            variant="caption"
            sx={{
              color: '#525C6C',
              fontSize: '0.7rem',
              fontWeight: 500,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            {h}
          </Typography>
        ))}
      </Box>

      {/* ── Rows ── */}
      {decisionItems.map((item) => {
        const dotColor = RISK_DOT[item.riskLevel];
        const riskBg = RISK_BG[item.riskLevel];

        return (
          <Box
            key={item.id}
            sx={{
              display: 'grid',
              gridTemplateColumns: '2fr 1.3fr 0.9fr 0.9fr 0.9fr 1fr 0.8fr 0.7fr',
              gap: 1,
              alignItems: 'center',
              py: 1.5,
              borderBottom: '1px solid rgba(255,255,255,0.03)',
              mx: -1.5,
              px: 1.5,
              borderRadius: '8px',
              borderLeft: item.riskLevel === 'High' ? '3px solid #EF4444' : '3px solid transparent',
              transition: 'background-color 150ms ease',
              '&:hover': { backgroundColor: 'rgba(255,255,255,0.02)' },
              '&:last-child': { borderBottom: 'none' },
            }}
          >
            {/* Decision (Item) */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
              <Box
                component="img"
                src={item.image}
                alt={item.name}
                sx={{ width: 36, height: 36, borderRadius: '8px', objectFit: 'cover', flexShrink: 0 }}
              />
              <Box>
                <Typography variant="body2" sx={{ color: '#F4F7FB', fontWeight: 500 }}>
                  {item.name}
                </Typography>
                <Typography variant="caption" sx={{ color: '#525C6C', fontSize: '0.6875rem' }}>
                  {item.category}
                </Typography>
              </Box>
            </Box>

            {/* Risk */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.25 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Box sx={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: dotColor }} />
                <Typography variant="body2" sx={{ color: '#8B95A8', fontSize: '0.8125rem' }}>
                  {item.riskType}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, pl: 1.375 }}>
                <Box
                  sx={{
                    width: 8, height: 8, borderRadius: '2px',
                    backgroundColor: riskBg,
                    border: `1px solid ${dotColor}`,
                  }}
                />
                <Typography variant="caption" sx={{ color: dotColor, fontSize: '0.6875rem', fontWeight: 500 }}>
                  {item.riskLevel}
                </Typography>
              </Box>
            </Box>

            {/* Forecast Demand */}
            <Box>
              <Typography variant="body2" sx={{ color: '#F4F7FB', fontWeight: 500 }}>
                {item.forecastDemand}
              </Typography>
              <Typography variant="caption" sx={{ color: '#525C6C', fontSize: '0.6875rem' }}>
                portions
              </Typography>
            </Box>

            {/* Available Inventory */}
            <Box>
              <Typography variant="body2" sx={{ color: '#F4F7FB', fontWeight: 500 }}>
                {item.availableInventory}
              </Typography>
              <Typography variant="caption" sx={{ color: '#525C6C', fontSize: '0.6875rem' }}>
                portions
              </Typography>
            </Box>

            {/* Projected Gap */}
            <Box>
              <Typography
                variant="body2"
                sx={{
                  color: item.projectedGap < 0 ? '#EF4444' : '#22C55E',
                  fontWeight: 600,
                }}
              >
                {item.projectedGap > 0 ? '+' : ''}{item.projectedGap}
              </Typography>
              <Typography variant="caption" sx={{ color: '#525C6C', fontSize: '0.6875rem' }}>
                portions
              </Typography>
            </Box>

            {/* Deadline */}
            <Typography variant="body2" sx={{ color: '#8B95A8', fontSize: '0.8125rem' }}>
              {item.deadline || '—'}
            </Typography>

            {/* Status Badge */}
            <Box
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                px: 1,
                py: 0.375,
                borderRadius: '6px',
                backgroundColor: 'rgba(245,158,11,0.1)',
                border: '1px solid rgba(245,158,11,0.2)',
                width: 'fit-content',
              }}
            >
              <Typography
                variant="caption"
                sx={{ color: '#F59E0B', fontWeight: 600, fontSize: '0.6875rem' }}
              >
                Pending
              </Typography>
            </Box>

            {/* Action */}
            <Button
              size="small"
              sx={{
                color: '#A78BFA',
                fontSize: '0.75rem',
                fontWeight: 600,
                textTransform: 'none',
                px: 1,
                py: 0.375,
                borderRadius: '6px',
                border: '1px solid rgba(124,92,252,0.2)',
                backgroundColor: 'rgba(124,92,252,0.08)',
                minWidth: 'auto',
                '&:hover': { backgroundColor: 'rgba(124,92,252,0.15)' },
              }}
            >
              Review
            </Button>
          </Box>
        );
      })}

      {/* ── Pagination ── */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mt: 2,
          pt: 2,
          borderTop: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <Typography variant="caption" sx={{ color: '#525C6C' }}>
          Showing 1 to 8 of 8 decisions
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <IconButton size="small" sx={{ color: '#525C6C' }}>
            <ChevronLeft size={16} />
          </IconButton>
          <Box
            sx={{
              width: 28, height: 28, borderRadius: '6px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              backgroundColor: 'rgba(124,92,252,0.15)',
              border: '1px solid rgba(124,92,252,0.3)',
            }}
          >
            <Typography variant="caption" sx={{ color: '#A78BFA', fontWeight: 600 }}>1</Typography>
          </Box>
          <IconButton size="small" sx={{ color: '#525C6C' }}>
            <ChevronRight size={16} />
          </IconButton>
        </Box>
      </Box>
    </Paper>
  );
};
