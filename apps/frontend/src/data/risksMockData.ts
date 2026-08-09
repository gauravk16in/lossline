/**
 * Static mock data for the Risks screen.
 * Matches the risk.png design exactly.
 */

import chickenBiryaniImg from '../assets/food/chicken-biryani.png';
import paneerBiryaniImg from '../assets/food/paneer-biryani.png';
import vegFriedRiceImg from '../assets/food/veg-fried-rice.png';
import masalaChaasImg from '../assets/food/masala-chaas.png';
import gulabJamunImg from '../assets/food/gulab-jamun.png';

/* ── Risk Summary Cards ── */

export type RiskLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export interface RiskSummaryCard {
  id: string;
  label: string;
  count: number;
  trend: 'up' | 'down' | 'stable';
  trendValue: string;
  color: string;
  bgColor: string;
  borderColor: string;
  icon: 'alert-triangle' | 'alert-circle' | 'shield-check' | 'layers';
}

export const riskSummaryCards: RiskSummaryCard[] = [
  {
    id: 'high-risk',
    label: 'High Risk',
    count: 3,
    trend: 'up',
    trendValue: '2 vs yesterday',
    color: '#EF4444',
    bgColor: 'rgba(239,68,68,0.08)',
    borderColor: 'rgba(239,68,68,0.15)',
    icon: 'alert-triangle',
  },
  {
    id: 'medium-risk',
    label: 'Medium Risk',
    count: 5,
    trend: 'down',
    trendValue: '1 vs yesterday',
    color: '#F59E0B',
    bgColor: 'rgba(245,158,11,0.08)',
    borderColor: 'rgba(245,158,11,0.15)',
    icon: 'alert-circle',
  },
  {
    id: 'low-risk',
    label: 'Low Risk',
    count: 4,
    trend: 'stable',
    trendValue: 'vs yesterday',
    color: '#22C55E',
    bgColor: 'rgba(34,197,94,0.08)',
    borderColor: 'rgba(34,197,94,0.15)',
    icon: 'shield-check',
  },
  {
    id: 'total-at-risk',
    label: 'Total At Risk',
    count: 12,
    trend: 'up',
    trendValue: '1 vs yesterday',
    color: '#A78BFA',
    bgColor: 'rgba(167,139,250,0.08)',
    borderColor: 'rgba(167,139,250,0.15)',
    icon: 'layers',
  },
];

/* ── At Risk Items Table (extended) ── */

export type ProjectedIssue = 'Stockout' | 'Surplus';

export interface RiskItem {
  id: string;
  name: string;
  category: string;
  image: string;
  riskLevel: RiskLevel;
  projectedIssue: ProjectedIssue;
  shortagePortions: number;
  expectedTime: string | null;
  impactRupees: number;
}

export const riskItems: RiskItem[] = [
  {
    id: 'risk-chicken-biryani',
    name: 'Chicken Biryani',
    category: 'Main Course',
    image: chickenBiryaniImg,
    riskLevel: 'HIGH',
    projectedIssue: 'Stockout',
    shortagePortions: 19,
    expectedTime: '~7:10 PM',
    impactRupees: 4750,
  },
  {
    id: 'risk-paneer-biryani',
    name: 'Paneer Biryani',
    category: 'Main Course',
    image: paneerBiryaniImg,
    riskLevel: 'MEDIUM',
    projectedIssue: 'Stockout',
    shortagePortions: 6,
    expectedTime: '~8:35 PM',
    impactRupees: 1620,
  },
  {
    id: 'risk-veg-fried-rice',
    name: 'Veg Fried Rice',
    category: 'Rice',
    image: vegFriedRiceImg,
    riskLevel: 'LOW',
    projectedIssue: 'Surplus',
    shortagePortions: 38,
    expectedTime: null,
    impactRupees: 950,
  },
  {
    id: 'risk-masala-chaas',
    name: 'Masala Chaas',
    category: 'Beverage',
    image: masalaChaasImg,
    riskLevel: 'MEDIUM',
    projectedIssue: 'Stockout',
    shortagePortions: 8,
    expectedTime: '~6:40 PM',
    impactRupees: 880,
  },
  {
    id: 'risk-gulab-jamun',
    name: 'Gulab Jamun',
    category: 'Dessert',
    image: gulabJamunImg,
    riskLevel: 'LOW',
    projectedIssue: 'Surplus',
    shortagePortions: 22,
    expectedTime: null,
    impactRupees: 320,
  },
];

/* ── Risk Detail Panel (selected item) ── */

export interface RiskDetailItem {
  name: string;
  category: string;
  outletName: string;
  image: string;
  riskLevel: RiskLevel;
  forecastDemand: number;
  availableInventory: number;
  projectedGap: number;
  safetyBuffer: number;
  expectedStockout: string;
  stockoutCountdown: string;
  topDrivers: {
    id: string;
    label: string;
    impact: string;
    icon: 'calendar' | 'cloud-rain' | 'tag';
  }[];
  recommendedAction: string;
  recommendedDeadline: string;
}

export const riskDetailItem: RiskDetailItem = {
  name: 'Chicken Biryani',
  category: 'Main Course',
  outletName: 'Indiranagar Outlet',
  image: chickenBiryaniImg,
  riskLevel: 'HIGH',
  forecastDemand: 71,
  availableInventory: 52,
  projectedGap: -19,
  safetyBuffer: 5,
  expectedStockout: '~7:10 PM',
  stockoutCountdown: 'Within 2h 25m',
  topDrivers: [
    { id: 'td-1', label: 'Friday Dinner Pattern', impact: '+18%', icon: 'calendar' },
    { id: 'td-2', label: 'Rain Forecast',         impact: '+11%', icon: 'cloud-rain' },
    { id: 'td-3', label: '20% OFF Promotion',     impact: '+7%',  icon: 'tag' },
  ],
  recommendedAction: 'Prepare ~20 additional portions',
  recommendedDeadline: '5:30 PM',
};

/* ── Risk Heatmap Data ── */

export interface HeatmapCell {
  value: number;
  risk: RiskLevel | 'NONE';
}

export interface HeatmapRow {
  timeWindow: string;
  days: HeatmapCell[];
}

export const heatmapDays = ['Mon 12', 'Tue 13', 'Wed 14', 'Thu 15', 'Fri 16', 'Sat 17', 'Sun 18'];

export const heatmapData: HeatmapRow[] = [
  {
    timeWindow: '6 AM – 9 AM',
    days: [
      { value: 0, risk: 'NONE' },
      { value: 0, risk: 'NONE' },
      { value: 0, risk: 'NONE' },
      { value: 1, risk: 'LOW' },
      { value: 1, risk: 'LOW' },
      { value: 0, risk: 'NONE' },
      { value: 0, risk: 'NONE' },
    ],
  },
  {
    timeWindow: '9 AM – 12 PM',
    days: [
      { value: 1, risk: 'LOW' },
      { value: 0, risk: 'NONE' },
      { value: 1, risk: 'LOW' },
      { value: 1, risk: 'LOW' },
      { value: 1, risk: 'LOW' },
      { value: 0, risk: 'NONE' },
      { value: 0, risk: 'NONE' },
    ],
  },
  {
    timeWindow: '12 PM – 3 PM',
    days: [
      { value: 2, risk: 'MEDIUM' },
      { value: 1, risk: 'LOW' },
      { value: 1, risk: 'LOW' },
      { value: 1, risk: 'LOW' },
      { value: 1, risk: 'LOW' },
      { value: 2, risk: 'MEDIUM' },
      { value: 1, risk: 'LOW' },
    ],
  },
  {
    timeWindow: '3 PM – 6 PM',
    days: [
      { value: 2, risk: 'MEDIUM' },
      { value: 2, risk: 'MEDIUM' },
      { value: 2, risk: 'MEDIUM' },
      { value: 1, risk: 'LOW' },
      { value: 2, risk: 'MEDIUM' },
      { value: 3, risk: 'HIGH' },
      { value: 2, risk: 'MEDIUM' },
    ],
  },
  {
    timeWindow: '6 PM – 9 PM',
    days: [
      { value: 3, risk: 'HIGH' },
      { value: 2, risk: 'MEDIUM' },
      { value: 3, risk: 'HIGH' },
      { value: 2, risk: 'MEDIUM' },
      { value: 4, risk: 'HIGH' },
      { value: 4, risk: 'HIGH' },
      { value: 3, risk: 'HIGH' },
    ],
  },
  {
    timeWindow: '9 PM – 12 AM',
    days: [
      { value: 2, risk: 'MEDIUM' },
      { value: 1, risk: 'LOW' },
      { value: 2, risk: 'MEDIUM' },
      { value: 1, risk: 'LOW' },
      { value: 3, risk: 'HIGH' },
      { value: 3, risk: 'HIGH' },
      { value: 2, risk: 'MEDIUM' },
    ],
  },
];
