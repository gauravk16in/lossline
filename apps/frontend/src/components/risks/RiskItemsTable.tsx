import React, { useState } from 'react';
import { Box, Typography, Paper, Button, IconButton } from '@mui/material';
import { Filter, MoreHorizontal, ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import { riskItems, type RiskLevel } from '../../data/risksMockData';

/** Risk badge color config — same as AtRiskTable for consistency */
const RISK_COLORS: Record<RiskLevel, { text: string; bg: string; border: string }> = {
  HIGH:   { text: '#EF4444', bg: 'rgba(239,68,68,0.1)',  border: 'rgba(239,68,68,0.2)' },
  MEDIUM: { text: '#F59E0B', bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.2)' },
  LOW:    { text: '#22C55E', bg: 'rgba(34,197,94,0.1)',   border: 'rgba(34,197,94,0.2)' },
};

type TabValue = 'risk' | 'category' | 'outlet';

/**
 * RiskItemsTable — full at-risk items table with tabs, filter, pagination.
 * Matches the risk.png design: tabs (By Risk / By Category / By Outlet),
 * columns: Item, Risk Level, Projected Issue, Expected Time, Impact (₹), Action.
 */
export const RiskItemsTable: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabValue>('risk');

  const tabs: { value: TabValue; label: string }[] = [
    { value: 'risk', label: 'By Risk' },
    { value: 'category', label: 'By Category' },
    { value: 'outlet', label: 'By Outlet' },
  ];

  return (
    <Paper
      id="risk-items-table"
      sx={{
        p: 3, mb: 3,
        background: '#111631',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '16px',
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h2" sx={{ color: '#F4F7FB' }}>
          At Risk Items
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
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
      </Box>

      {/* Tabs */}
      <Box sx={{ display: 'flex', gap: 0.5, mb: 2.5 }}>
        {tabs.map((tab) => (
          <Box
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            sx={{
              px: 1.5, py: 0.625, borderRadius: '8px',
              cursor: 'pointer',
              backgroundColor: activeTab === tab.value ? 'rgba(124,92,252,0.15)' : 'transparent',
              border: activeTab === tab.value ? '1px solid rgba(124,92,252,0.3)' : '1px solid transparent',
              transition: 'all 150ms ease',
              '&:hover': {
                backgroundColor: activeTab === tab.value ? 'rgba(124,92,252,0.2)' : 'rgba(255,255,255,0.04)',
              },
            }}
          >
            <Typography
              variant="body2"
              sx={{
                color: activeTab === tab.value ? '#A78BFA' : '#8B95A8',
                fontWeight: activeTab === tab.value ? 600 : 400,
                fontSize: '0.8125rem',
              }}
            >
              {tab.label}
            </Typography>
          </Box>
        ))}
      </Box>

      {/* Column Headers */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: '2.2fr 0.9fr 1.2fr 1fr 1fr 0.7fr',
          gap: 1, pb: 1.5,
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          mb: 0.5,
        }}
      >
        {['Item', 'Risk Level', 'Projected Issue', 'Expected Time', 'Impact (₹)', 'Action'].map((h) => (
          <Typography
            key={h} variant="caption"
            sx={{ color: '#525C6C', fontSize: '0.75rem', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.04em' }}
          >
            {h}
          </Typography>
        ))}
      </Box>

      {/* Rows */}
      {riskItems.map((item) => {
        const riskColor = RISK_COLORS[item.riskLevel];
        return (
          <Box
            key={item.id}
            sx={{
              display: 'grid',
              gridTemplateColumns: '2.2fr 0.9fr 1.2fr 1fr 1fr 0.7fr',
              gap: 1, alignItems: 'center', py: 1.5,
              borderBottom: '1px solid rgba(255,255,255,0.03)',
              mx: -1.5, px: 1.5, borderRadius: '8px',
              transition: 'background-color 150ms ease',
              /* Highlight left border for HIGH risk items */
              borderLeft: item.riskLevel === 'HIGH' ? '3px solid #EF4444' : '3px solid transparent',
              '&:hover': { backgroundColor: 'rgba(255,255,255,0.02)' },
              '&:last-child': { borderBottom: 'none' },
            }}
          >
            {/* Item */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
              <Box component="img" src={item.image} alt={item.name}
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

            {/* Risk Level Badge */}
            <Box
              sx={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                px: 1.25, py: 0.375, borderRadius: '6px',
                backgroundColor: riskColor.bg, border: `1px solid ${riskColor.border}`,
                width: 'fit-content',
              }}
            >
              <Typography variant="caption" sx={{ color: riskColor.text, fontWeight: 600, fontSize: '0.6875rem', letterSpacing: '0.04em' }}>
                {item.riskLevel}
              </Typography>
            </Box>

            {/* Projected Issue */}
            <Box>
              <Typography variant="body2" sx={{ color: item.projectedIssue === 'Stockout' ? '#EF4444' : '#F59E0B', fontWeight: 500 }}>
                {item.projectedIssue}
              </Typography>
              <Typography variant="caption" sx={{ color: '#525C6C', fontSize: '0.6875rem' }}>
                {item.shortagePortions} portions
              </Typography>
            </Box>

            {/* Expected Time */}
            <Typography variant="body2" sx={{ color: '#8B95A8' }}>
              {item.expectedTime || '—'}
            </Typography>

            {/* Impact */}
            <Typography variant="body2" sx={{ color: '#8B95A8' }}>
              ₹{item.impactRupees.toLocaleString('en-IN')}
            </Typography>

            {/* Action */}
            <Button
              size="small"
              startIcon={<Eye size={12} />}
              sx={{
                color: '#22C55E', fontSize: '0.75rem', fontWeight: 600,
                textTransform: 'none', px: 1, py: 0.375, borderRadius: '6px',
                border: '1px solid rgba(34,197,94,0.2)',
                backgroundColor: 'rgba(34,197,94,0.08)',
                minWidth: 'auto',
                '&:hover': { backgroundColor: 'rgba(34,197,94,0.15)' },
              }}
            >
              View
            </Button>
          </Box>
        );
      })}

      {/* Pagination */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 2, pt: 2, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <Typography variant="caption" sx={{ color: '#525C6C' }}>
          1–5 of 12 items
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <IconButton size="small" sx={{ color: '#525C6C' }}>
            <ChevronLeft size={16} />
          </IconButton>
          {[1, 2, 3].map((page) => (
            <Box
              key={page}
              sx={{
                width: 28, height: 28, borderRadius: '6px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                backgroundColor: page === 1 ? 'rgba(124,92,252,0.15)' : 'transparent',
                border: page === 1 ? '1px solid rgba(124,92,252,0.3)' : '1px solid transparent',
                cursor: 'pointer',
                '&:hover': { backgroundColor: page === 1 ? 'rgba(124,92,252,0.2)' : 'rgba(255,255,255,0.04)' },
              }}
            >
              <Typography variant="caption" sx={{ color: page === 1 ? '#A78BFA' : '#525C6C', fontWeight: page === 1 ? 600 : 400 }}>
                {page}
              </Typography>
            </Box>
          ))}
          <IconButton size="small" sx={{ color: '#525C6C' }}>
            <ChevronLeft size={16} style={{ transform: 'rotate(180deg)' }} />
          </IconButton>
          <IconButton size="small" sx={{ color: '#525C6C' }}>
            <ChevronRight size={16} />
          </IconButton>
        </Box>
      </Box>
    </Paper>
  );
};
