import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { useDashboard } from '../../state/DashboardContext';

/**
 * Custom tooltip — consistent with DemandForecastChart tooltip style.
 */
const CustomTooltip: React.FC<{
  active?: boolean;
  payload?: Array<{ value: number; name: string; color: string }>;
  label?: string;
}> = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <Box
      sx={{
        backgroundColor: 'rgba(17, 22, 49, 0.95)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: '10px',
        px: 1.5, py: 1,
        backdropFilter: 'blur(8px)',
      }}
    >
      <Typography variant="caption" sx={{ color: '#8B95A8', mb: 0.5, display: 'block' }}>
        {label}
      </Typography>
      {payload.map((entry, idx) => (
        <Typography key={idx} variant="caption" sx={{ color: entry.color, display: 'block', fontWeight: 500 }}>
          {entry.name}: {entry.value}
        </Typography>
      ))}
    </Box>
  );
};

/**
 * SkuBreakdownChart — stacked bar chart showing hourly demand per SKU.
 */
export const SkuBreakdownChart: React.FC = () => {
  const { hourlyForecastBreakdown, hourlySkuSeries } = useDashboard();
  return (
    <Paper
      id="sku-breakdown-chart"
      sx={{
        p: 3, mb: 3,
        background: '#111631',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '16px',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2.5 }}>
        <Box>
          <Typography variant="h2" sx={{ color: '#F4F7FB', mb: 0.25 }}>
            Hourly Demand by SKU
          </Typography>
          <Typography variant="caption" sx={{ color: '#8B95A8' }}>
            Forecasted portions per hour breakdown
          </Typography>
        </Box>
      </Box>

      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={hourlyForecastBreakdown} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
          <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: '#525C6C', fontSize: 11 }} interval={2} />
          <YAxis axisLine={false} tickLine={false} tick={{ fill: '#525C6C', fontSize: 11 }} />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ paddingTop: 12, fontSize: 11, color: '#8B95A8' }}
            iconType="circle"
            iconSize={8}
          />
          {hourlySkuSeries.map((series, index) => (
            <Bar key={series.key} dataKey={series.key} name={series.name} stackId="demand"
              fill={series.color} radius={index === hourlySkuSeries.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </Paper>
  );
};
