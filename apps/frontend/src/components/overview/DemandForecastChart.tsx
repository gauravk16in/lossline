import React from 'react';
import { Box, Typography, Paper, Select, MenuItem } from '@mui/material';
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { useDashboard } from '../../state/DashboardContext';

/**
 * Custom tooltip for the demand forecast chart.
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
        px: 1.5,
        py: 1,
        backdropFilter: 'blur(8px)',
      }}
    >
      <Typography variant="caption" sx={{ color: '#8B95A8', mb: 0.5, display: 'block' }}>
        {label}
      </Typography>
      {payload.map((entry, idx) => (
        <Typography
          key={idx}
          variant="caption"
          sx={{ color: entry.color, display: 'block', fontWeight: 500 }}
        >
          {entry.name}: {entry.value?.toLocaleString() ?? '—'}
        </Typography>
      ))}
    </Box>
  );
};

/**
 * Custom label for the "Now" marker on the chart.
 */
const NowLabel: React.FC<{ viewBox?: { x: number; y: number } }> = ({
  viewBox,
}) => {
  if (!viewBox) return null;
  return (
    <g>
      <rect
        x={viewBox.x - 20}
        y={8}
        width={40}
        height={22}
        rx={6}
        fill="#22C55E"
      />
      <text
        x={viewBox.x}
        y={23}
        textAnchor="middle"
        fill="#fff"
        fontSize={11}
        fontWeight={600}
        fontFamily="Inter"
      >
        Now
      </text>
    </g>
  );
};

/**
 * DemandForecastChart — Today's Demand Forecast line chart with forecast range shading.
 * Uses recharts ComposedChart with Area (range) + Line (actual + forecast).
 */
export const DemandForecastChart: React.FC = () => {
  const { demandForecastData, nowIndex: NOW_INDEX } = useDashboard();
  if (!demandForecastData.length) return null;
  return (
    <Paper
      id="demand-forecast-chart"
      sx={{
        p: 3,
        mb: 3,
        background: '#111631',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '16px',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          mb: 2.5,
        }}
      >
        <Box>
          <Typography variant="h2" sx={{ color: '#F4F7FB', mb: 0.25 }}>
            Today's Demand Forecast
          </Typography>
          <Typography variant="caption" sx={{ color: '#8B95A8' }}>
            Orders throughout the day with forecast range
          </Typography>
        </Box>

        {/* SKU Filter Dropdown */}
        <Select
          value="all"
          size="small"
          sx={{
            backgroundColor: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '8px',
            color: '#F4F7FB',
            fontSize: '0.8125rem',
            minWidth: 120,
            '& .MuiSelect-select': { py: 0.625, px: 1.25 },
            '& .MuiOutlinedInput-notchedOutline': { border: 'none' },
          }}
        >
          <MenuItem value="all">All SKUs</MenuItem>
          <MenuItem value="chicken-biryani">Chicken Biryani</MenuItem>
          <MenuItem value="paneer-biryani">Paneer Biryani</MenuItem>
        </Select>
      </Box>

      {/* Legend */}
      <Box sx={{ display: 'flex', gap: 3, mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <Box
            sx={{
              width: 20,
              height: 2,
              backgroundColor: '#A78BFA',
              borderRadius: 1,
            }}
          />
          <Typography variant="caption" sx={{ color: '#8B95A8' }}>
            Actual Orders
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <Box
            sx={{
              width: 20,
              height: 2,
              background: 'repeating-linear-gradient(to right, #8B95A8 0, #8B95A8 4px, transparent 4px, transparent 8px)',
            }}
          />
          <Typography variant="caption" sx={{ color: '#8B95A8' }}>
            Forecast
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <Box
            sx={{
              width: 20,
              height: 10,
              backgroundColor: 'rgba(167, 139, 250, 0.15)',
              borderRadius: '2px',
            }}
          />
          <Typography variant="caption" sx={{ color: '#8B95A8' }}>
            Forecast Range
          </Typography>
        </Box>
      </Box>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart
          data={demandForecastData}
          margin={{ top: 30, right: 12, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="forecastRangeGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#A78BFA" stopOpacity={0.15} />
              <stop offset="100%" stopColor="#A78BFA" stopOpacity={0.02} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.04)"
            vertical={false}
          />

          <XAxis
            dataKey="time"
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#525C6C', fontSize: 11 }}
            interval={2}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#525C6C', fontSize: 11 }}
            tickFormatter={(v: number) =>
              v >= 1000 ? `${(v / 1000).toFixed(v % 1000 === 0 ? 0 : 1)}K` : String(v)
            }
            domain={[0, 'auto']}
          />

          <Tooltip content={<CustomTooltip />} />

          {/* "Now" vertical reference line */}
          <ReferenceLine
            x={demandForecastData[NOW_INDEX].time}
            stroke="rgba(255,255,255,0.15)"
            strokeDasharray="4 4"
            label={<NowLabel />}
          />

          {/* Forecast range (shaded area) */}
          <Area
            type="monotone"
            dataKey="forecastUpper"
            stroke="none"
            fill="url(#forecastRangeGrad)"
            fillOpacity={1}
            name="Upper Range"
            isAnimationActive={true}
            animationDuration={1200}
          />
          <Area
            type="monotone"
            dataKey="forecastLower"
            stroke="none"
            fill="#111631"
            fillOpacity={1}
            name="Lower Range"
            isAnimationActive={true}
            animationDuration={1200}
          />

          {/* Forecast line (dashed) */}
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="#8B95A8"
            strokeWidth={2}
            strokeDasharray="6 4"
            dot={false}
            name="Forecast"
            isAnimationActive={true}
            animationDuration={1500}
          />

          {/* Actual orders line (solid) */}
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#A78BFA"
            strokeWidth={2.5}
            dot={(props: Record<string, unknown>) => {
              const cx = (props.cx as number) ?? 0;
              const cy = (props.cy as number) ?? 0;
              const index = (props.index as number) ?? 0;
              const value = props.value as number | null;
              // Show dot only at the last actual data point
              const isLastActual =
                value !== null &&
                (index === NOW_INDEX ||
                  demandForecastData[index + 1]?.actual === null);
              if (!isLastActual) return <circle key={index} r={0} />;
              return (
                <circle
                  key={index}
                  cx={cx}
                  cy={cy}
                  r={5}
                  fill="#A78BFA"
                  stroke="#111631"
                  strokeWidth={2}
                />
              );
            }}
            name="Actual Orders"
            isAnimationActive={true}
            animationDuration={1500}
            connectNulls={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </Paper>
  );
};
