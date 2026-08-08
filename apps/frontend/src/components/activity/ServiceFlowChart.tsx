"use client";

import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { SERVICE_FLOW_DATA } from "@/data/mock";

const SERIES = [
  { key: "ORDER_CUSTOMIZATION",   color: "#6B7FD7", label: "Order Customization"   },
  { key: "ORDER_CONFIRMED",       color: "#9B7FD4", label: "Order Confirmed"        },
  { key: "ACTIVE_COOKING",        color: "#D4845A", label: "Active Cooking"         },
  { key: "QUALITY_CONTROL_CHECK", color: "#D45A5A", label: "Quality Control Check"  },
  { key: "ORDER_COMPLETE",        color: "#5AAF7A", label: "Order Complete"         },
] as const;

type Period = "Day" | "Week" | "Month" | "Year";

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const total = payload.reduce((s: number, p: any) => s + p.value, 0);
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">Day {label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="chart-tooltip-row">
          <span className="chart-tooltip-dot" style={{ background: p.fill }} />
          <span>{p.name}</span>
          <span className="chart-tooltip-val">{p.value}</span>
        </div>
      ))}
      <div className="chart-tooltip-total">Total: {total}</div>
    </div>
  );
};

export default function ServiceFlowChart() {
  const [period, setPeriod] = useState<Period>("Month");

  return (
    <div className="flow-chart-card">
      <div className="flow-chart-header">
        <h3 className="flow-chart-title">Service Flow Tracking</h3>
        <div className="period-toggle" role="group" aria-label="Time period">
          {(["Day", "Week", "Month", "Year"] as Period[]).map((p) => (
            <button
              key={p}
              className={`period-btn ${period === p ? "period-btn--active" : ""}`}
              onClick={() => setPeriod(p)}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div style={{ width: "100%", height: 260 }}>
        <ResponsiveContainer>
          <BarChart
            data={SERVICE_FLOW_DATA}
            margin={{ top: 8, right: 12, left: -16, bottom: 0 }}
            barSize={6}
            barGap={0}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
            {SERIES.map(({ key, color, label }) => (
              <Bar key={key} dataKey={key} name={label} stackId="a" fill={color} radius={key === "ORDER_COMPLETE" ? [2, 2, 0, 0] : undefined} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flow-legend">
        {SERIES.map(({ key, color, label }) => (
          <div key={key} className="flow-legend-item">
            <span className="flow-legend-dot" style={{ background: color }} />
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
