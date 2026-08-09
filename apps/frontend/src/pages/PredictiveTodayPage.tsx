import { useEffect, useMemo, useState } from 'react';
import { Alert, Box, Chip, FormControl, Grid, InputLabel, MenuItem, Paper, Select, Skeleton, Typography } from '@mui/material';
import { PageContainer } from '../components/layout/PageContainer';
import { usePredictiveToday } from '../hooks/usePredictiveToday';
import type { Restaurant } from '../types/api';

interface Props { restaurants: Restaurant[]; restaurantsLoading: boolean; }
const WINDOWS = ['BREAKFAST', 'LUNCH', 'DINNER'];

export function PredictiveTodayPage({ restaurants, restaurantsLoading }: Props) {
  const [outletId, setOutletId] = useState<string | null>(null);
  const [serviceWindow, setServiceWindow] = useState('DINNER');
  useEffect(() => { if (!outletId && restaurants.length) setOutletId(restaurants[0].id); }, [outletId, restaurants]);
  const { data, loading, error } = usePredictiveToday(outletId, serviceWindow);
  const inventory = useMemo(() => new Map(data?.inventory_projections.map(item => [item.forecast_id, item]) ?? []), [data]);
  const drivers = useMemo(() => new Map(data?.drivers.map(item => [item.forecast_id, item]) ?? []), [data]);
  const capacity = data?.capacity_projections[0];
  const outcomes = useMemo(() => new Map(data?.outcomes.map(item => [item.forecast_id, item]) ?? []), [data]);

  return <PageContainer>
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, gap: 2 }}>
      <Box><Typography variant="overline" color="text.secondary">Predictive Today</Typography>
        <Typography variant="h1">Upcoming service risk</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: .5 }}>Forecast facts, projections and guarded decisions from the backend.</Typography></Box>
      <Chip label="Synthetic demo data" size="small" color="info" variant="outlined" />
    </Box>
    <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
      <FormControl size="small" sx={{ minWidth: 220 }}><InputLabel>Outlet</InputLabel>
        <Select value={outletId ?? ''} label="Outlet" disabled={restaurantsLoading} onChange={event => setOutletId(event.target.value)}>
          {restaurants.map(item => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
        </Select></FormControl>
      <FormControl size="small" sx={{ minWidth: 160 }}><InputLabel>Window</InputLabel>
        <Select value={serviceWindow} label="Window" onChange={event => setServiceWindow(event.target.value)}>
          {WINDOWS.map(item => <MenuItem key={item} value={item}>{item}</MenuItem>)}
        </Select></FormControl>
    </Box>
    {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
    {loading ? <Skeleton variant="rectangular" height={240} sx={{ borderRadius: 2 }} /> : !data?.forecasts.length ?
      <Paper sx={{ p: 5, textAlign: 'center' }}><Typography variant="h2">No forecast available</Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>The scheduler has not produced this outlet/window yet.</Typography></Paper> : <>
      {capacity && <Paper sx={{ p: 2.5, mb: 3 }}><Typography variant="h2">Shared outlet capacity</Typography>
        <Typography sx={{ mt: 1 }}>Point utilization {(Number(capacity.utilization_point) * 100).toFixed(1)}% · {capacity.risk_tier}</Typography>
        <Typography variant="caption" color="text.secondary">Range {(Number(capacity.utilization_lower) * 100).toFixed(1)}%–{(Number(capacity.utilization_upper) * 100).toFixed(1)}%; computed by {capacity.projection_id}</Typography></Paper>}
      <Grid container spacing={2}>{data.forecasts.map(forecast => { const stock = inventory.get(forecast.forecast_id); const driver = drivers.get(forecast.forecast_id); const outcome = outcomes.get(forecast.forecast_id); return <Grid key={forecast.forecast_id} size={{ xs: 12, md: 6 }}>
        <Paper sx={{ p: 2.5, height: '100%' }}><Box sx={{ display: 'flex', justifyContent: 'space-between' }}><Typography variant="h2">{forecast.sku_id}</Typography>
          <Chip size="small" color={stock?.stockout_risk ? 'error' : 'success'} label={stock?.stockout_risk ? `${stock.shortage_severity} stockout risk` : 'Supply sufficient'} /></Box>
          <Typography sx={{ fontSize: '2rem', fontWeight: 700, mt: 2 }}>{Number(forecast.point_demand).toFixed(0)} <Typography component="span" color="text.secondary">portions</Typography></Typography>
          <Typography variant="body2" color="text.secondary">Forecast range {Number(forecast.lower_demand).toFixed(0)}–{Number(forecast.upper_demand).toFixed(0)}</Typography>
          {stock && <Typography sx={{ mt: 2 }}>Projected ending inventory: {stock.ending_inventory_point}; shortage: {stock.shortage_point}</Typography>}
          {outcome && <Alert severity={outcome.status === 'AVAILABLE' ? 'info' : 'warning'} sx={{ mt: 2 }}>
            {outcome.status === 'AVAILABLE' ? `Matured actual demand: ${Number(outcome.actual_demand).toFixed(0)}; unfulfilled: ${Number(outcome.unfulfilled_quantity).toFixed(0)}` : `Outcome ${outcome.status.toLowerCase()} and excluded from accuracy scoring.`}
          </Alert>}
          {driver && <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}><Typography variant="caption" color="text.secondary">Top associated driver</Typography>
            <Typography>{driver.feature_id} · {driver.direction.toLowerCase()}</Typography><Typography variant="caption" color="text.secondary">{driver.wording_limit}</Typography></Box>}
        </Paper></Grid>; })}</Grid>
      {data.decisions.length > 0 && <Paper sx={{ p: 2.5, mt: 3 }}><Typography variant="h2">Guarded decisions</Typography>{data.decisions.map(item =>
        <Box key={item.decision.decision_id} sx={{ mt: 1.5 }}><Typography>{item.decision.action.replaceAll('_', ' ')}</Typography><Typography variant="caption" color="text.secondary">{item.status} · approval {item.decision.approval_required ? 'required' : 'not required'}</Typography></Box>)}</Paper>}
    </>}
  </PageContainer>;
}
