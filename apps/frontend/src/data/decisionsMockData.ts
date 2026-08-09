/**
 * Static mock data for the Decisions screen.
 * Matches the decision.png design exactly.
 */

import chickenBiryaniImg from '../assets/food/chicken-biryani.png';
import paneerBiryaniImg from '../assets/food/paneer-biryani.png';
import vegFriedRiceImg from '../assets/food/veg-fried-rice.png';
import masalaChaasImg from '../assets/food/masala-chaas.png';
import gulabJamunImg from '../assets/food/gulab-jamun.png';
import dalMakhaniImg from '../assets/food/dal-makhani.png';
import hakkaNoodlesImg from '../assets/food/hakka-noodles.png';
import coldCoffeeImg from '../assets/food/cold-coffee.png';

/* ── Decision Status Tabs ── */

export type DecisionStatus = 'Pending' | 'Approved' | 'Completed';

export interface DecisionTabCount {
  status: DecisionStatus;
  count: number;
}

export const decisionTabs: DecisionTabCount[] = [
  { status: 'Pending',   count: 8 },
  { status: 'Approved',  count: 24 },
  { status: 'Completed', count: 56 },
];

/* ── Decision Items ── */

export type RiskType = 'Stockout Risk' | 'Surplus Risk';
export type RiskLevel = 'High' | 'Medium' | 'Low';

export interface DecisionItem {
  id: string;
  name: string;
  category: string;
  image: string;
  riskType: RiskType;
  riskLevel: RiskLevel;
  forecastDemand: number;
  availableInventory: number;
  projectedGap: number;
  deadline: string | null;
  status: DecisionStatus;
}

export const decisionItems: DecisionItem[] = [
  {
    id: 'dec-chicken-biryani',
    name: 'Chicken Biryani',
    category: 'Main Course',
    image: chickenBiryaniImg,
    riskType: 'Stockout Risk',
    riskLevel: 'High',
    forecastDemand: 71,
    availableInventory: 52,
    projectedGap: -19,
    deadline: 'Before 5:30 PM',
    status: 'Pending',
  },
  {
    id: 'dec-paneer-biryani',
    name: 'Paneer Biryani',
    category: 'Main Course',
    image: paneerBiryaniImg,
    riskType: 'Stockout Risk',
    riskLevel: 'Medium',
    forecastDemand: 46,
    availableInventory: 28,
    projectedGap: -18,
    deadline: 'Before 6:00 PM',
    status: 'Pending',
  },
  {
    id: 'dec-veg-fried-rice',
    name: 'Veg Fried Rice',
    category: 'Rice',
    image: vegFriedRiceImg,
    riskType: 'Surplus Risk',
    riskLevel: 'Low',
    forecastDemand: 38,
    availableInventory: 72,
    projectedGap: 34,
    deadline: null,
    status: 'Pending',
  },
  {
    id: 'dec-masala-chaas',
    name: 'Masala Chaas',
    category: 'Beverage',
    image: masalaChaasImg,
    riskType: 'Stockout Risk',
    riskLevel: 'Medium',
    forecastDemand: 25,
    availableInventory: 12,
    projectedGap: -13,
    deadline: 'Before 4:30 PM',
    status: 'Pending',
  },
  {
    id: 'dec-gulab-jamun',
    name: 'Gulab Jamun',
    category: 'Dessert',
    image: gulabJamunImg,
    riskType: 'Surplus Risk',
    riskLevel: 'Low',
    forecastDemand: 60,
    availableInventory: 110,
    projectedGap: 50,
    deadline: null,
    status: 'Pending',
  },
  {
    id: 'dec-dal-makhani',
    name: 'Dal Makhani',
    category: 'Main Course',
    image: dalMakhaniImg,
    riskType: 'Stockout Risk',
    riskLevel: 'Medium',
    forecastDemand: 33,
    availableInventory: 18,
    projectedGap: -15,
    deadline: 'Before 6:30 PM',
    status: 'Pending',
  },
  {
    id: 'dec-hakka-noodles',
    name: 'Hakka Noodles',
    category: 'Sides',
    image: hakkaNoodlesImg,
    riskType: 'Surplus Risk',
    riskLevel: 'Low',
    forecastDemand: 29,
    availableInventory: 60,
    projectedGap: 31,
    deadline: null,
    status: 'Pending',
  },
  {
    id: 'dec-cold-coffee',
    name: 'Cold Coffee',
    category: 'Beverage',
    image: coldCoffeeImg,
    riskType: 'Stockout Risk',
    riskLevel: 'Medium',
    forecastDemand: 41,
    availableInventory: 20,
    projectedGap: -21,
    deadline: 'Before 4:00 PM',
    status: 'Pending',
  },
];

/* ── Priority Decision Detail (right panel) ── */

export interface DecisionDetail {
  name: string;
  category: string;
  outletName: string;
  image: string;
  riskLevel: RiskLevel;
  /* What we expect */
  forecastDemand: number;
  forecastRange: string;
  availableInventory: number;
  projectedShortage: number;
  expectedStockout: string;
  /* Why this matters */
  whyItMatters: string[];
  /* Top Drivers */
  topDrivers: {
    id: string;
    label: string;
    impact: string;
    icon: 'calendar' | 'cloud-rain' | 'tag';
  }[];
  /* Recommended Action */
  recommendedAction: string;
  recommendedDeadline: string;
}

export const decisionDetail: DecisionDetail = {
  name: 'Chicken Biryani',
  category: 'Main Course',
  outletName: 'Indiranagar Outlet',
  image: chickenBiryaniImg,
  riskLevel: 'High',
  forecastDemand: 71,
  forecastRange: '61 – 82 portions',
  availableInventory: 52,
  projectedShortage: 19,
  expectedStockout: '~7:10 PM',
  whyItMatters: [
    'High demand expected during dinner peak',
    'Low inventory compared to forecast',
    'Past trends show similar spike on Fridays',
  ],
  topDrivers: [
    { id: 'td-1', label: 'Friday Dinner Pattern', impact: '+18%', icon: 'calendar' },
    { id: 'td-2', label: 'Rain Forecast',         impact: '+11%', icon: 'cloud-rain' },
    { id: 'td-3', label: '20% OFF Promotion',     impact: '+7%',  icon: 'tag' },
  ],
  recommendedAction: 'Prepare ~20 additional portions',
  recommendedDeadline: '5:30 PM',
};
