/**
 * Static mock data for the Forecasts screen.
 * Reuses DemandDataPoint from overviewMockData for consistency.
 */

import chickenBiryaniImg from '../assets/food/chicken-biryani.png';
import paneerBiryaniImg from '../assets/food/paneer-biryani.png';
import vegFriedRiceImg from '../assets/food/veg-fried-rice.png';

/* ── SKU-level Forecast Cards ── */

export interface SkuForecast {
  id: string;
  name: string;
  category: string;
  image: string;
  forecastDemand: number;
  currentInventory: number;
  gap: number;
  confidence: number; // 0-100
  trend: 'up' | 'down' | 'stable';
  trendPercent: number;
  peakWindow: string;
}

export const skuForecasts: SkuForecast[] = [
  {
    id: 'sku-chicken-biryani',
    name: 'Chicken Biryani',
    category: 'Main Course',
    image: chickenBiryaniImg,
    forecastDemand: 71,
    currentInventory: 52,
    gap: -19,
    confidence: 87,
    trend: 'up',
    trendPercent: 24,
    peakWindow: '7–9 PM',
  },
  {
    id: 'sku-paneer-biryani',
    name: 'Paneer Biryani',
    category: 'Main Course',
    image: paneerBiryaniImg,
    forecastDemand: 41,
    currentInventory: 35,
    gap: -6,
    confidence: 82,
    trend: 'up',
    trendPercent: 12,
    peakWindow: '7–9 PM',
  },
  {
    id: 'sku-veg-fried-rice',
    name: 'Veg Fried Rice',
    category: 'Rice',
    image: vegFriedRiceImg,
    forecastDemand: 58,
    currentInventory: 96,
    gap: 38,
    confidence: 91,
    trend: 'stable',
    trendPercent: 3,
    peakWindow: '12–2 PM',
  },
];

/* ── Forecast Accuracy Metrics ── */

export interface ForecastAccuracyMetric {
  id: string;
  label: string;
  value: string;
  subtitle: string;
  subtitleColor?: string;
  icon: 'target' | 'trending-up' | 'bar-chart' | 'clock';
}

export const forecastAccuracyMetrics: ForecastAccuracyMetric[] = [
  {
    id: 'overall-accuracy',
    label: 'Forecast Accuracy',
    value: '89%',
    subtitle: '↗ 3% vs last week',
    subtitleColor: '#22C55E',
    icon: 'target',
  },
  {
    id: 'total-forecast',
    label: 'Total Forecast',
    value: '1,246',
    subtitle: 'portions today',
    icon: 'trending-up',
  },
  {
    id: 'skus-tracked',
    label: 'SKUs Tracked',
    value: '18',
    subtitle: 'Active items',
    icon: 'bar-chart',
  },
  {
    id: 'next-update',
    label: 'Next Update',
    value: '12:30 PM',
    subtitle: 'In 45 minutes',
    icon: 'clock',
  },
];

/* ── Hourly Forecast Breakdown (per-SKU) ── */

export interface HourlyForecastPoint {
  time: string;
  chickenBiryani: number;
  paneerBiryani: number;
  vegFriedRice: number;
}

export const hourlyForecastBreakdown: HourlyForecastPoint[] = [
  { time: '6 AM',  chickenBiryani: 1,  paneerBiryani: 0,  vegFriedRice: 2 },
  { time: '7 AM',  chickenBiryani: 2,  paneerBiryani: 1,  vegFriedRice: 3 },
  { time: '8 AM',  chickenBiryani: 3,  paneerBiryani: 2,  vegFriedRice: 4 },
  { time: '9 AM',  chickenBiryani: 3,  paneerBiryani: 2,  vegFriedRice: 5 },
  { time: '10 AM', chickenBiryani: 4,  paneerBiryani: 2,  vegFriedRice: 4 },
  { time: '11 AM', chickenBiryani: 5,  paneerBiryani: 3,  vegFriedRice: 6 },
  { time: '12 PM', chickenBiryani: 8,  paneerBiryani: 5,  vegFriedRice: 9 },
  { time: '1 PM',  chickenBiryani: 9,  paneerBiryani: 6,  vegFriedRice: 8 },
  { time: '2 PM',  chickenBiryani: 6,  paneerBiryani: 4,  vegFriedRice: 5 },
  { time: '3 PM',  chickenBiryani: 4,  paneerBiryani: 3,  vegFriedRice: 4 },
  { time: '4 PM',  chickenBiryani: 5,  paneerBiryani: 3,  vegFriedRice: 3 },
  { time: '5 PM',  chickenBiryani: 7,  paneerBiryani: 4,  vegFriedRice: 5 },
  { time: '6 PM',  chickenBiryani: 10, paneerBiryani: 6,  vegFriedRice: 7 },
  { time: '7 PM',  chickenBiryani: 12, paneerBiryani: 7,  vegFriedRice: 6 },
  { time: '8 PM',  chickenBiryani: 11, paneerBiryani: 6,  vegFriedRice: 5 },
  { time: '9 PM',  chickenBiryani: 8,  paneerBiryani: 5,  vegFriedRice: 4 },
  { time: '10 PM', chickenBiryani: 5,  paneerBiryani: 3,  vegFriedRice: 3 },
  { time: '11 PM', chickenBiryani: 3,  paneerBiryani: 2,  vegFriedRice: 2 },
  { time: '12 AM', chickenBiryani: 1,  paneerBiryani: 1,  vegFriedRice: 1 },
];

/* ── Feature Drivers (what's influencing forecast) ── */

export interface ForecastDriver {
  id: string;
  feature: string;
  contribution: number;  // percentage
  direction: 'up' | 'down';
  description: string;
}

export const forecastDrivers: ForecastDriver[] = [
  {
    id: 'fd-1',
    feature: 'Day of Week',
    contribution: 32,
    direction: 'up',
    description: 'Friday historically sees 24% higher demand',
  },
  {
    id: 'fd-2',
    feature: 'Weather',
    contribution: 18,
    direction: 'up',
    description: 'Rain forecast driving indoor dining',
  },
  {
    id: 'fd-3',
    feature: 'Promotion',
    contribution: 15,
    direction: 'up',
    description: '20% OFF promotion boosting orders',
  },
  {
    id: 'fd-4',
    feature: 'Historical Trend',
    contribution: 12,
    direction: 'up',
    description: 'Steady weekly growth pattern',
  },
  {
    id: 'fd-5',
    feature: 'Local Events',
    contribution: 8,
    direction: 'up',
    description: 'Concert venue nearby this evening',
  },
];
