import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import { skuDisplay } from '../data/catalog';
import type { PredictiveToday, Restaurant } from '../types/api';
import type { AtRiskItem, DecisionDetail, DecisionItem, DemandDataPoint, ForecastAccuracyMetric, ForecastDriver, HeatmapRow, MetricStat, PriorityDecision, RiskDetailItem, RiskItem, RiskLevel, RiskSummaryCard, SkuForecast } from '../data/viewModels';

const EMPTY_TODAY: PredictiveToday = { outlet_id: '', service_window: 'DINNER', forecasts: [], feature_snapshots: [], inventory_projections: [], capacity_projections: [], risks: [], drivers: [], dossiers: [], decisions: [], outcomes: [], evaluations: [], synthetic: true };
const severity = (value: string): RiskLevel => value === 'CRITICAL' || value === 'HIGH' ? 'HIGH' : value === 'MEDIUM' ? 'MEDIUM' : 'LOW';
const displaySeverity = (value: string) => severity(value)[0] + severity(value).slice(1).toLowerCase() as 'High' | 'Medium' | 'Low';
const number = (value: unknown) => Number(value || 0);
const time = (value?: string) => value ? new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date(value)) : '—';

interface DashboardValue {
  restaurants: Restaurant[]; outletId: string; setOutletId: (id: string) => void;
  serviceWindow: string; setServiceWindow: (window: string) => void; serviceWindows: string[];
  loading: boolean; error: string | null; refreshedAt: Date | null; refresh: () => Promise<void>;
  demandForecastData: DemandDataPoint[]; nowIndex: number; metricStats: MetricStat[]; atRiskItems: AtRiskItem[];
  priorityDecision: PriorityDecision | null; skuForecasts: SkuForecast[]; forecastAccuracyMetrics: ForecastAccuracyMetric[];
  hourlyForecastBreakdown: Array<Record<string, string | number>>; hourlySkuSeries: { key: string; name: string; color: string }[]; forecastDrivers: ForecastDriver[];
  riskSummaryCards: RiskSummaryCard[]; riskItems: RiskItem[]; riskDetailItem: RiskDetailItem | null;
  heatmapDays: string[]; heatmapData: HeatmapRow[]; decisionItems: DecisionItem[]; decisionDetail: DecisionDetail | null;
  decisionTabs: { status: 'Pending' | 'Approved' | 'Completed'; count: number }[];
  selectedRiskId: string | null; selectRisk: (id: string) => void;
  selectedDecisionId: string | null; selectDecision: (id: string) => void;
  reviewDecision: (decision: 'APPROVE' | 'REJECT', note?: string) => Promise<void>;
}

const DashboardContext = createContext<DashboardValue | null>(null);

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [outletId, setOutletId] = useState('meghana_indiranagar');
  const [serviceWindow, setServiceWindow] = useState('DINNER');
  const [serviceWindows, setServiceWindows] = useState<string[]>(['BREAKFAST', 'DINNER']);
  const [selectedRiskId, setSelectedRiskId] = useState<string | null>(null);
  const [selectedDecisionId, setSelectedDecisionId] = useState<string | null>(null);
  const [today, setToday] = useState<PredictiveToday>(EMPTY_TODAY);
  const [hourlyToday, setHourlyToday] = useState<PredictiveToday>({ ...EMPTY_TODAY, service_window: 'HOURLY' });
  const [summary, setSummary] = useState({ forecast_count: 0, risk_count: 0, pending_review_count: 0 });
  const [exposure, setExposure] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null);
  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const outlets = await api.restaurants();
      const effectiveOutlet = outlets.some((item) => item.id === outletId) ? outletId : outlets[0]?.id;
      setRestaurants(outlets);
      if (!effectiveOutlet) throw new Error('No outlets have been provisioned for this organization');
      if (effectiveOutlet !== outletId) setOutletId(effectiveOutlet);
      const [dashboard, hourly, predictive, reactive] = await Promise.all([
        api.predictiveToday(effectiveOutlet, serviceWindow), api.predictiveToday(effectiveOutlet, `${serviceWindow}_HOURLY`), api.predictiveSummary(), api.analytics(),
      ]);
      setToday(dashboard); setHourlyToday(hourly); setSummary(predictive); setExposure(reactive.estimated_exposure);
      setRefreshedAt(new Date()); setError(null);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to load dashboard'); }
    finally { setLoading(false); }
  }, [outletId, serviceWindow]);

  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    const poll = window.setInterval(() => { if (document.visibilityState === 'visible') void refresh(); }, 5_000);
    const onVisibility = () => { if (document.visibilityState === 'visible') void refresh(); };
    const onFocus = () => { void refresh(); };
    document.addEventListener('visibilitychange', onVisibility); window.addEventListener('focus', onFocus);
    return () => { window.clearInterval(poll); document.removeEventListener('visibilitychange', onVisibility); window.removeEventListener('focus', onFocus); };
  }, [refresh]);
  useEffect(() => {
    void api.serviceWindows(outletId).then(({ service_windows }) => {
      if (service_windows.length) {
        setServiceWindows(service_windows);
        if (!service_windows.includes(serviceWindow)) setServiceWindow(service_windows[0]);
      }
    }).catch(() => setServiceWindows(['BREAKFAST', 'DINNER']));
  }, [outletId, serviceWindow]);
  useEffect(() => { setSelectedRiskId(null); setSelectedDecisionId(null); }, [outletId, serviceWindow]);

  const value = useMemo<DashboardValue>(() => {
    const inventories = new Map(today.inventory_projections.map((item) => [item.forecast_id, item]));
    const outcomes = new Map(today.outcomes.map((item) => [item.forecast_id, item]));
    const outlet = restaurants.find((item) => item.id === outletId);
    const latestWindowStart = today.forecasts.reduce((latest, item) => item.window_start > latest ? item.window_start : latest, '');
    const currentForecasts = today.forecasts.filter((item) => item.window_start === latestWindowStart);
    const skuForecasts: SkuForecast[] = currentForecasts.map((forecast) => {
      const inventory = inventories.get(forecast.forecast_id); const item = skuDisplay(forecast.sku_id);
      const forecastDemand = number(forecast.point_demand); const available = number(inventory?.available_for_demand ?? inventory?.opening_inventory);
      const midpoint = (number(forecast.upper_demand) + number(forecast.lower_demand)) / 2;
      const confidence = forecastDemand ? Math.max(0, Math.round(100 - ((number(forecast.upper_demand) - number(forecast.lower_demand)) / forecastDemand) * 50)) : 0;
      return { id: forecast.forecast_id, ...item, forecastDemand, currentInventory: available, gap: available - forecastDemand, confidence,
        trend: forecastDemand > midpoint ? 'up' : forecastDemand < midpoint ? 'down' : 'stable', trendPercent: midpoint ? Math.round(Math.abs(forecastDemand - midpoint) / midpoint * 100) : 0,
        peakWindow: `${time(forecast.window_start)}–${time(forecast.window_end)}` };
    });
    const atRiskItems: AtRiskItem[] = skuForecasts.map((item) => ({ id: item.id, name: item.name, image: item.image, forecast: item.forecastDemand, available: item.currentInventory, gap: item.gap, risk: item.gap < 0 ? (Math.abs(item.gap) >= 10 ? 'HIGH' : 'MEDIUM') : 'LOW' }));
    const currentForecastIds = new Set(currentForecasts.map((item) => item.forecast_id));
    const drivers: ForecastDriver[] = today.drivers.filter((driver) => currentForecastIds.has(driver.forecast_id)).map((driver) => ({ id: driver.driver_id, feature: driver.feature_id.replaceAll('.', ' ').replaceAll('_', ' '), contribution: Math.min(100, Math.round(Math.abs(number(driver.score)) * 100)), direction: driver.direction === 'DECREASE' ? 'down' : 'up', description: driver.wording_limit }));
    const decisionItems: DecisionItem[] = today.decisions.map((view) => {
      const forecast = skuForecasts.find((item) => item.id === view.decision.forecast_id); const item = skuDisplay(view.decision.sku_id || 'capacity');
      const status = view.status === 'AWAITING_MANAGER_REVIEW' ? 'Pending' : view.status === 'MANAGER_APPROVED' ? 'Approved' : 'Completed';
      return { id: view.decision.decision_id, name: item.name, category: item.category, image: item.image,
        riskType: view.decision.risk_type === 'INVENTORY_SHORTAGE' ? 'Stockout Risk' : 'Capacity Risk', riskLevel: displaySeverity(view.decision.urgency),
        forecastDemand: forecast?.forecastDemand || 0, availableInventory: forecast?.currentInventory || 0, projectedGap: forecast?.gap || 0,
        deadline: view.decision.execute_by ? `Before ${time(view.decision.execute_by)}` : null, status };
    });
    const firstDecision = today.decisions.find((item) => item.decision.decision_id === selectedDecisionId)
      || today.decisions.find((item) => item.decision.forecast_id === selectedRiskId)
      || today.decisions.find((item) => item.status === 'AWAITING_MANAGER_REVIEW') || today.decisions[0];
    const firstItem = firstDecision ? decisionItems.find((item) => item.id === firstDecision.decision.decision_id) : undefined;
    const firstForecast = firstDecision ? today.forecasts.find((item) => item.forecast_id === firstDecision.decision.forecast_id) : undefined;
    const topDrivers = drivers.slice(0, 3).map((driver, index) => ({ id: driver.id, label: driver.feature, impact: `${driver.direction === 'up' ? '+' : '-'}${driver.contribution}%`, icon: (index === 0 ? 'calendar' : index === 1 ? 'cloud-rain' : 'tag') as 'calendar' | 'cloud-rain' | 'tag' }));
    const decisionDetail: DecisionDetail | null = firstDecision && firstItem ? { decisionId: firstItem.id, name: firstItem.name, category: firstItem.category, outletName: outlet?.name || outletId, image: firstItem.image, riskLevel: firstItem.riskLevel,
      forecastDemand: firstItem.forecastDemand, forecastRange: `${number(firstForecast?.lower_demand)} – ${number(firstForecast?.upper_demand)} portions`, availableInventory: firstItem.availableInventory,
      projectedShortage: Math.max(0, -firstItem.projectedGap), expectedStockout: firstItem.deadline || 'Within service window',
      whyItMatters: [firstDecision.decision.reason_code.replaceAll('_', ' '), `Evidence: ${firstDecision.decision.evidence_ids.join(', ')}`, `Guarded action risk: ${firstDecision.decision.action_risk}`], topDrivers,
      recommendedAction: firstDecision.decision.action === 'ADJUST_PREP_QUANTITY' ? `Prepare ${number(firstDecision.decision.quantity)} additional ${firstDecision.decision.unit || 'portions'}` : firstDecision.decision.action.replaceAll('_', ' ').toLowerCase(),
      recommendedDeadline: time(firstDecision.decision.execute_by), status: firstDecision.status } : null;
    const priorityDecision: PriorityDecision | null = decisionDetail ? { priority: severity(decisionDetail.riskLevel), itemName: decisionDetail.name, itemImage: decisionDetail.image, outletName: decisionDetail.outletName,
      forecastDemand: decisionDetail.forecastDemand, availableInventory: decisionDetail.availableInventory, projectedShortage: decisionDetail.projectedShortage, expectedStockout: decisionDetail.expectedStockout,
      keyDrivers: topDrivers.map((driver) => ({ ...driver, icon: driver.icon, impact: driver.impact.startsWith('+') && number(driver.impact.slice(1, -1)) > 15 ? 'High' : 'Medium' })), recommendedAction: decisionDetail.recommendedAction, recommendedDeadline: decisionDetail.recommendedDeadline } : null;
    const riskItems: RiskItem[] = atRiskItems.map((item) => ({ id: item.id, name: item.name, category: skuForecasts.find((sku) => sku.id === item.id)?.category || 'Menu Item', image: item.image, riskLevel: item.risk,
      projectedIssue: item.gap < 0 ? 'Stockout' : 'Surplus', shortagePortions: Math.abs(item.gap), expectedTime: item.gap < 0 ? `~${time(firstForecast?.window_end)}` : null, impactRupees: Math.round(Math.abs(item.gap) * (exposure > 0 ? exposure / Math.max(1, summary.risk_count) : 250)) }));
    const riskDetailItem: RiskDetailItem | null = decisionDetail ? { name: decisionDetail.name, category: decisionDetail.category, outletName: decisionDetail.outletName, image: decisionDetail.image, riskLevel: severity(decisionDetail.riskLevel), forecastDemand: decisionDetail.forecastDemand,
      availableInventory: decisionDetail.availableInventory, projectedGap: -decisionDetail.projectedShortage, safetyBuffer: number(inventories.get(firstDecision?.decision.forecast_id || '')?.safety_buffer), expectedStockout: decisionDetail.expectedStockout,
      stockoutCountdown: `By ${decisionDetail.recommendedDeadline}`, topDrivers, recommendedAction: decisionDetail.recommendedAction, recommendedDeadline: decisionDetail.recommendedDeadline } : null;
    const counts = (level: RiskLevel) => riskItems.filter((item) => item.riskLevel === level).length;
    const card = (id: string, label: string, count: number, color: string, icon: RiskSummaryCard['icon']): RiskSummaryCard => ({ id, label, count, trend: 'stable', trendValue: 'current forecast', color, bgColor: `${color}14`, borderColor: `${color}26`, icon });
    const observedTotal = currentForecasts.reduce((sum, item) => sum + number(outcomes.get(item.forecast_id)?.actual_demand), 0);
    const forecastTotal = skuForecasts.reduce((sum, item) => sum + item.forecastDemand, 0);
    const evaluated = today.evaluations.filter((item) => item.evaluation_type === 'FORECAST');
    const accuracy = evaluated.length ? Math.max(0, Math.round(100 - evaluated.reduce((sum, item) => sum + number((item.evaluation as Record<string, unknown>).absolute_percentage_error) * 100, 0) / evaluated.length)) : null;
    const windowGroups = new Map<string, typeof today.forecasts>();
    today.forecasts.forEach((forecast) => windowGroups.set(forecast.window_start, [...(windowGroups.get(forecast.window_start) || []), forecast]));
    const demandForecastData: DemandDataPoint[] = [...windowGroups.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([windowStart, forecasts]) => ({
      time: new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric' }).format(new Date(windowStart)),
      actual: forecasts.some((item) => outcomes.has(item.forecast_id)) ? forecasts.reduce((sum, item) => sum + number(outcomes.get(item.forecast_id)?.actual_demand), 0) : null,
      forecast: forecasts.reduce((sum, item) => sum + number(item.point_demand), 0),
      forecastLower: forecasts.reduce((sum, item) => sum + number(item.lower_demand), 0),
      forecastUpper: forecasts.reduce((sum, item) => sum + number(item.upper_demand), 0),
    }));
    const heatmapWindows = [...windowGroups.entries()].sort(([left], [right]) => left.localeCompare(right));
    const heatmapDays = heatmapWindows.map(([windowStart]) => new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric' }).format(new Date(windowStart)));
    const heatmapCells = heatmapWindows.map(([, forecasts]) => {
      const levels = forecasts.map((forecast) => {
        const inventory = inventories.get(forecast.forecast_id); const gap = number(inventory?.available_for_demand) - number(forecast.point_demand);
        return gap < -10 ? 'HIGH' : gap < 0 ? 'MEDIUM' : 'LOW';
      });
      const count = levels.filter((level) => level !== 'LOW').length;
      return { value: count, risk: (levels.includes('HIGH') ? 'HIGH' : levels.includes('MEDIUM') ? 'MEDIUM' : count ? 'LOW' : 'NONE') as RiskLevel | 'NONE' };
    });
    const hourlySkuIds = ['CHICKEN_BIRYANI', 'PANEER_BIRYANI', 'VEG_FRIED_RICE'];
    const hourlySkuSeries = hourlySkuIds.map((skuId, index) => ({ key: skuId, name: skuDisplay(skuId).name, color: ['#A78BFA', '#F59E0B', '#22C55E'][index] }));
    const hourlyGroups = new Map<string, typeof hourlyToday.forecasts>();
    hourlyToday.forecasts.forEach((forecast) => hourlyGroups.set(forecast.window_start, [...(hourlyGroups.get(forecast.window_start) || []), forecast]));
    const hourlyForecastBreakdown = [...hourlyGroups.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([windowStart, forecasts]) => {
      const point: Record<string, string | number> = { time: new Intl.DateTimeFormat(undefined, { hour: 'numeric' }).format(new Date(windowStart)) };
      hourlySkuIds.forEach((skuId) => { point[skuId] = number(forecasts.find((item) => item.sku_id === skuId)?.point_demand); });
      return point;
    });
    const hourlyOutcomes = new Map(hourlyToday.outcomes.map((item) => [item.forecast_id, item]));
    const overviewHourlyData: DemandDataPoint[] = [...hourlyGroups.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([windowStart, forecasts]) => ({
      time: new Intl.DateTimeFormat(undefined, { hour: 'numeric' }).format(new Date(windowStart)),
      actual: forecasts.some((item) => hourlyOutcomes.has(item.forecast_id)) ? forecasts.reduce((sum, item) => sum + number(hourlyOutcomes.get(item.forecast_id)?.actual_demand), 0) : null,
      forecast: forecasts.reduce((sum, item) => sum + number(item.point_demand), 0),
      forecastLower: forecasts.reduce((sum, item) => sum + number(item.lower_demand), 0),
      forecastUpper: forecasts.reduce((sum, item) => sum + number(item.upper_demand), 0),
    }));
    const activeRiskId = selectedRiskId || firstDecision?.decision.forecast_id || riskItems[0]?.id || null;
    const activeDecisionId = selectedDecisionId || firstDecision?.decision.decision_id || null;
    return { restaurants, outletId, setOutletId, serviceWindow, setServiceWindow, serviceWindows, loading, error, refreshedAt, refresh,
      demandForecastData: overviewHourlyData.length ? overviewHourlyData : demandForecastData,
      nowIndex: Math.max(0, (overviewHourlyData.length ? overviewHourlyData : demandForecastData).findLastIndex((item) => item.actual !== null)),
      metricStats: [{ id: 'expected-orders', label: 'Expected Orders', value: forecastTotal.toLocaleString(), subtitle: observedTotal ? `${observedTotal} observed` : 'Current forecast window', icon: 'trending-up' }, { id: 'at-risk-skus', label: 'At-Risk SKUs', value: String(riskItems.filter((item) => item.riskLevel !== 'LOW').length), subtitle: `High risk: ${counts('HIGH')}`, icon: 'shield-alert' }, { id: 'capacity-risk', label: 'Capacity Risk', value: today.capacity_projections.find((item) => currentForecastIds.has(item.forecast_id))?.risk_tier || today.capacity_projections.at(-1)?.risk_tier || '—', subtitle: serviceWindow, icon: 'clock' }, { id: 'revenue-at-risk', label: 'Revenue at Risk', value: `₹${Math.round(riskItems.reduce((sum, item) => sum + item.impactRupees, 0)).toLocaleString('en-IN')}`, subtitle: 'Estimated exposure', icon: 'indian-rupee' }],
      atRiskItems, priorityDecision, skuForecasts,
      forecastAccuracyMetrics: [{ id: 'overall-accuracy', label: 'Forecast Accuracy', value: accuracy === null ? 'Pending' : `${accuracy}%`, subtitle: `${evaluated.length} evaluated forecasts`, icon: 'target' }, { id: 'total-forecast', label: 'Total Forecast', value: forecastTotal.toLocaleString(), subtitle: 'portions in window', icon: 'trending-up' }, { id: 'skus-tracked', label: 'SKUs Tracked', value: String(skuForecasts.length), subtitle: 'Active items', icon: 'bar-chart' }, { id: 'next-update', label: 'Prediction As Of', value: time(today.forecasts[0]?.prediction_as_of), subtitle: serviceWindow, icon: 'clock' }],
      hourlyForecastBreakdown, hourlySkuSeries, forecastDrivers: drivers,
      riskSummaryCards: [card('high-risk', 'High Risk', counts('HIGH'), '#EF4444', 'alert-triangle'), card('medium-risk', 'Medium Risk', counts('MEDIUM'), '#F59E0B', 'alert-circle'), card('low-risk', 'Low Risk', counts('LOW'), '#22C55E', 'shield-check'), card('total-at-risk', 'Total At Risk', riskItems.length, '#A78BFA', 'layers')], riskItems, riskDetailItem,
      heatmapDays, heatmapData: [{ timeWindow: serviceWindow, days: heatmapCells }],
      decisionItems, decisionDetail, selectedRiskId: activeRiskId, selectRisk: setSelectedRiskId,
      selectedDecisionId: activeDecisionId, selectDecision: setSelectedDecisionId,
      decisionTabs: (['Pending', 'Approved', 'Completed'] as const).map((status) => ({ status, count: decisionItems.filter((item) => item.status === status).length })),
      reviewDecision: async (decision, note) => {
        if (!decisionDetail) return;
        setLoading(true); setError(null);
        try {
          await api.reviewDecision(decisionDetail.decisionId, decision, note);
          await refresh();
        } catch (reason) {
          setError(reason instanceof Error ? reason.message : 'Decision review failed');
          setLoading(false);
        }
      },
    };
  }, [restaurants, outletId, serviceWindow, serviceWindows, selectedRiskId, selectedDecisionId, today, hourlyToday, summary, exposure, loading, error, refreshedAt, refresh]);
  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

// This hook intentionally lives beside its provider so consumers share one contract.
// eslint-disable-next-line react-refresh/only-export-components
export function useDashboard() {
  const value = useContext(DashboardContext);
  if (!value) throw new Error('useDashboard must be used inside DashboardProvider');
  return value;
}
