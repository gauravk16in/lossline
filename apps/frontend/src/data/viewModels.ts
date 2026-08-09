export type RiskLevel = 'HIGH' | 'MEDIUM' | 'LOW';
export type DisplayRiskLevel = 'High' | 'Medium' | 'Low';
export type DecisionStatus = 'Pending' | 'Approved' | 'Completed';

export interface DemandDataPoint { time: string; actual: number | null; forecast: number | null; forecastLower: number | null; forecastUpper: number | null }
export interface MetricStat { id: string; label: string; value: string; subtitle: string; subtitleColor?: string; icon: 'trending-up' | 'shield-alert' | 'clock' | 'indian-rupee' }
export interface AtRiskItem { id: string; name: string; image: string; forecast: number; available: number; gap: number; risk: RiskLevel }
export interface KeyDriver { id: string; icon: 'calendar' | 'cloud-rain' | 'tag' | 'map-pin'; label: string; impact: 'High' | 'Medium' | 'Low' }
export interface PriorityDecision { priority: RiskLevel; itemName: string; itemImage: string; outletName: string; forecastDemand: number; availableInventory: number; projectedShortage: number; expectedStockout: string; keyDrivers: KeyDriver[]; recommendedAction: string; recommendedDeadline: string }
export interface ForecastAccuracyMetric { id: string; label: string; value: string; subtitle: string; subtitleColor?: string; icon: 'target' | 'trending-up' | 'bar-chart' | 'clock' }
export interface SkuForecast { id: string; name: string; category: string; image: string; forecastDemand: number; currentInventory: number; gap: number; confidence: number; trend: 'up' | 'down' | 'stable'; trendPercent: number; peakWindow: string }
export interface ForecastDriver { id: string; feature: string; contribution: number; direction: 'up' | 'down'; description: string }
export interface RiskSummaryCard { id: string; label: string; count: number; trend: 'up' | 'down' | 'stable'; trendValue: string; color: string; bgColor: string; borderColor: string; icon: 'alert-triangle' | 'alert-circle' | 'shield-check' | 'layers' }
export interface RiskItem { id: string; name: string; category: string; image: string; riskLevel: RiskLevel; projectedIssue: 'Stockout' | 'Surplus'; shortagePortions: number; expectedTime: string | null; impactRupees: number }
export interface HeatmapCell { value: number; risk: RiskLevel | 'NONE' }
export interface HeatmapRow { timeWindow: string; days: HeatmapCell[] }
export interface RiskDetailItem { name: string; category: string; outletName: string; image: string; riskLevel: RiskLevel; forecastDemand: number; availableInventory: number; projectedGap: number; safetyBuffer: number; expectedStockout: string; stockoutCountdown: string; topDrivers: { id: string; label: string; impact: string; icon: 'calendar' | 'cloud-rain' | 'tag' }[]; recommendedAction: string; recommendedDeadline: string }
export interface DecisionItem { id: string; name: string; category: string; image: string; riskType: 'Stockout Risk' | 'Surplus Risk' | 'Capacity Risk'; riskLevel: DisplayRiskLevel; forecastDemand: number; availableInventory: number; projectedGap: number; deadline: string | null; status: DecisionStatus }
export interface DecisionDetail { decisionId: string; name: string; category: string; outletName: string; image: string; riskLevel: DisplayRiskLevel; forecastDemand: number; forecastRange: string; availableInventory: number; projectedShortage: number; expectedStockout: string; whyItMatters: string[]; topDrivers: { id: string; label: string; impact: string; icon: 'calendar' | 'cloud-rain' | 'tag' }[]; recommendedAction: string; recommendedDeadline: string; status: string }
