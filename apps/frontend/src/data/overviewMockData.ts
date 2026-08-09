/**
 * Static mock data for the Overview screen.
 * Will be replaced by real API calls when backend endpoints are ready.
 */

import chickenBiryaniImg from '../assets/food/chicken-biryani.png';
import paneerBiryaniImg from '../assets/food/paneer-biryani.png';
import vegFriedRiceImg from '../assets/food/veg-fried-rice.png';

/* ── Demand Forecast Timeseries ── */

export interface DemandDataPoint {
  time: string;       // e.g. "6 AM"
  actual: number | null;
  forecast: number | null;
  forecastLower: number | null;
  forecastUpper: number | null;
}

export const demandForecastData: DemandDataPoint[] = [
  { time: '6 AM',  actual: 120,  forecast: 140,  forecastLower: 100,  forecastUpper: 180 },
  { time: '7 AM',  actual: 280,  forecast: 300,  forecastLower: 230,  forecastUpper: 370 },
  { time: '8 AM',  actual: 420,  forecast: 390,  forecastLower: 310,  forecastUpper: 470 },
  { time: '9 AM',  actual: 510,  forecast: 520,  forecastLower: 430,  forecastUpper: 610 },
  { time: '10 AM', actual: 680,  forecast: 640,  forecastLower: 530,  forecastUpper: 750 },
  { time: '11 AM', actual: 920,  forecast: 880,  forecastLower: 740,  forecastUpper: 1020 },
  { time: '12 PM', actual: null,  forecast: 1050, forecastLower: 880,  forecastUpper: 1220 },
  { time: '1 PM',  actual: null, forecast: 1180, forecastLower: 990,  forecastUpper: 1370 },
  { time: '2 PM',  actual: null, forecast: 1100, forecastLower: 920,  forecastUpper: 1280 },
  { time: '3 PM',  actual: null, forecast: 1020, forecastLower: 860,  forecastUpper: 1180 },
  { time: '4 PM',  actual: null, forecast: 1080, forecastLower: 900,  forecastUpper: 1260 },
  { time: '5 PM',  actual: null, forecast: 1250, forecastLower: 1050, forecastUpper: 1450 },
  { time: '6 PM',  actual: null, forecast: 1520, forecastLower: 1280, forecastUpper: 1760 },
  { time: '7 PM',  actual: null, forecast: 1780, forecastLower: 1500, forecastUpper: 2060 },
  { time: '8 PM',  actual: null, forecast: 1650, forecastLower: 1390, forecastUpper: 1910 },
  { time: '9 PM',  actual: null, forecast: 1380, forecastLower: 1160, forecastUpper: 1600 },
  { time: '10 PM', actual: null, forecast: 1050, forecastLower: 880,  forecastUpper: 1220 },
  { time: '11 PM', actual: null, forecast: 680,  forecastLower: 570,  forecastUpper: 790 },
  { time: '12 AM', actual: null, forecast: 320,  forecastLower: 270,  forecastUpper: 370 },
];

/** Index of the "Now" marker in the data (11 AM → 12 PM boundary) */
export const NOW_INDEX = 5;

/* ── Metric Stats ── */

export interface MetricStat {
  id: string;
  label: string;
  value: string;
  subtitle: string;
  subtitleColor?: string;
  icon: 'trending-up' | 'shield-alert' | 'clock' | 'indian-rupee';
}

export const metricStats: MetricStat[] = [
  {
    id: 'expected-orders',
    label: 'Expected Orders',
    value: '1,246',
    subtitle: 'vs yesterday',
    subtitleColor: '#22c55e',
    icon: 'trending-up',
  },
  {
    id: 'at-risk-skus',
    label: 'At-Risk SKUs',
    value: '7',
    subtitle: 'High risk: 2',
    icon: 'shield-alert',
  },
  {
    id: 'capacity-risk',
    label: 'Capacity Risk',
    value: 'High',
    subtitle: 'Dinner Peak 6–9 PM',
    icon: 'clock',
  },
  {
    id: 'revenue-at-risk',
    label: 'Revenue at Risk',
    value: '₹18,430',
    subtitle: 'Potential loss',
    icon: 'indian-rupee',
  },
];

/* ── At-Risk Items ── */

export type RiskLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export interface AtRiskItem {
  id: string;
  name: string;
  image: string;
  forecast: number;
  available: number;
  gap: number;
  risk: RiskLevel;
}

export const atRiskItems: AtRiskItem[] = [
  {
    id: 'sku-chicken-biryani',
    name: 'Chicken Biryani',
    image: chickenBiryaniImg,
    forecast: 71,
    available: 52,
    gap: -19,
    risk: 'HIGH',
  },
  {
    id: 'sku-paneer-biryani',
    name: 'Paneer Biryani',
    image: paneerBiryaniImg,
    forecast: 41,
    available: 35,
    gap: -6,
    risk: 'MEDIUM',
  },
  {
    id: 'sku-veg-fried-rice',
    name: 'Veg Fried Rice',
    image: vegFriedRiceImg,
    forecast: 58,
    available: 96,
    gap: 38,
    risk: 'LOW',
  },
];

/* ── Priority Decision ── */

export interface KeyDriver {
  id: string;
  icon: 'calendar' | 'cloud-rain' | 'tag' | 'map-pin';
  label: string;
  impact: 'High' | 'Medium' | 'Low';
}

export interface PriorityDecision {
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  itemName: string;
  itemImage: string;
  outletName: string;
  forecastDemand: number;
  availableInventory: number;
  projectedShortage: number;
  expectedStockout: string;
  keyDrivers: KeyDriver[];
  recommendedAction: string;
  recommendedDeadline: string;
}

export const priorityDecision: PriorityDecision = {
  priority: 'HIGH',
  itemName: 'Chicken Biryani',
  itemImage: chickenBiryaniImg,
  outletName: 'Indiranagar Outlet',
  forecastDemand: 71,
  availableInventory: 52,
  projectedShortage: 19,
  expectedStockout: '~7:10 PM',
  keyDrivers: [
    { id: 'drv-1', icon: 'calendar',   label: 'Friday Dinner Pattern', impact: 'High' },
    { id: 'drv-2', icon: 'cloud-rain', label: 'Rain Forecast',         impact: 'High' },
    { id: 'drv-3', icon: 'tag',        label: 'Promotion (20% OFF)',   impact: 'Medium' },
    { id: 'drv-4', icon: 'map-pin',    label: 'Local Event',           impact: 'Medium' },
  ],
  recommendedAction: 'Prepare ~20 additional portions',
  recommendedDeadline: '5:30 PM',
};
