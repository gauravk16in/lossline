// Format snake_case incident types to human-readable titles
const INCIDENT_TYPE_MAP: Record<string, string> = {
  CANCELLATION_SPIKE: 'Cancellation spike',
  ORDER_VOLUME_SPIKE: 'Order volume surge',
  PREPARATION_TIME_DEGRADATION: 'Preparation delay',
  DELIVERY_DELAY: 'Delivery delay',
  ORDER_OVERLOAD: 'Operational overload',
  REVIEW_SENTIMENT_DROP: 'Review sentiment drop',
  REFUND_SPIKE: 'Refund spike',
};

export function formatIncidentType(type: string): string {
  return INCIDENT_TYPE_MAP[type] ?? type.replace(/_/g, ' ').toLowerCase().replace(/^\w/, c => c.toUpperCase());
}

// Format restaurant_id / outlet name
export function formatOutletName(id: string): string {
  return id.replace(/_/g, ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

// Format signal type to readable label
const SIGNAL_TYPE_MAP: Record<string, string> = {
  CANCELLATION_SPIKE: 'Cancellation rate',
  ORDER_VOLUME_SPIKE: 'Order volume',
  PREPARATION_TIME_SPIKE: 'Preparation time',
  DELIVERY_TIME_SPIKE: 'Delivery time',
  REVIEW_SENTIMENT: 'Review sentiment',
  REFUND_RATE_SPIKE: 'Refund rate',
};

export function formatSignalType(type: string): string {
  return SIGNAL_TYPE_MAP[type] ?? type.replace(/_/g, ' ').toLowerCase().replace(/^\w/, c => c.toUpperCase());
}

// Format unit string
const UNIT_MAP: Record<string, string> = {
  cancellation_rate: '%',
  order_count: 'orders',
  seconds: 's',
  minutes: 'min',
  rate: '%',
};

export function formatUnit(unit: string): string {
  return UNIT_MAP[unit] ?? unit;
}

// Format signal value with unit
export function formatValue(value: number, unit: string): string {
  const u = formatUnit(unit);
  if (u === '%') return `${(value * 100).toFixed(1)}%`;
  if (u === 'orders') return `${Math.round(value)} orders`;
  if (u === 'min') return `${Math.round(value)} min`;
  return `${value.toFixed(2)} ${u}`;
}
