"use client";

import { useState } from "react";
import { ArrowDownUp } from "lucide-react";
import { motion } from "framer-motion";
import { SHIFTS_DATA } from "@/data/mock";
import type { ServiceStatus } from "@/types";

const STATUS_CONFIG: Record<ServiceStatus, { label: string; color: string; bg: string }> = {
  PREP:                  { label: "Prep",                color: "#F4C26A", bg: "rgba(244,194,106,0.15)" },
  RUSH_HOUR:             { label: "Rush Hour",           color: "#FF8A65", bg: "rgba(255,138,101,0.15)" },
  CLOSING:               { label: "Closing",             color: "#EF5350", bg: "rgba(239,83,80,0.15)"  },
  STAFF_MEETING:         { label: "Staff Meeting",       color: "#7E57C2", bg: "rgba(126,87,194,0.15)" },
  CLEAN_UP:              { label: "Clean-up",            color: "#78909C", bg: "rgba(120,144,156,0.15)"},
  ORDER_CUSTOMIZATION:   { label: "Order Customization", color: "#6B7FD7", bg: "rgba(107,127,215,0.15)"},
  ORDER_CONFIRMED:       { label: "Order Confirmed",     color: "#9B7FD4", bg: "rgba(155,127,212,0.15)"},
  ACTIVE_COOKING:        { label: "Active Cooking",      color: "#D4845A", bg: "rgba(212,132,90,0.15)" },
  QUALITY_CONTROL_CHECK: { label: "QC Check",            color: "#D45A5A", bg: "rgba(212,90,90,0.15)"  },
  ORDER_COMPLETE:        { label: "Order Complete",      color: "#5AAF7A", bg: "rgba(90,175,122,0.15)" },
};

function HeatBar({ hours, max = 7 }: { hours: number; max?: number }) {
  const pct = Math.min((hours / max) * 100, 100);
  const urgency = hours <= 2 ? "#EF5350" : hours <= 4 ? "#FF8A65" : "#4A9EFF";
  return (
    <div className="heatbar-wrap">
      <div className="heatbar-track">
        <motion.div
          className="heatbar-fill"
          style={{ background: urgency }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, delay: 0.1 }}
        />
      </div>
      <span className="heatbar-label" style={{ color: urgency }}>{hours.toFixed(1)}</span>
    </div>
  );
}

function StatusBadge({ status }: { status: ServiceStatus }) {
  const cfg = STATUS_CONFIG[status];
  return (
    <span
      className="status-badge"
      style={{ color: cfg.color, background: cfg.bg, borderColor: `${cfg.color}30` }}
    >
      {cfg.label}
    </span>
  );
}

export default function ShiftsTable() {
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const sorted = [...SHIFTS_DATA].sort((a, b) =>
    sortDir === "desc" ? b.hoursUntilClose - a.hoursUntilClose : a.hoursUntilClose - b.hoursUntilClose
  );

  return (
    <div className="shifts-card">
      <div className="shifts-header">
        <h3 className="shifts-title">Daily Service Shifts</h3>
        <div className="shifts-actions">
          <button className="shifts-filter-btn">Stalled</button>
          <button className="shifts-filter-btn shifts-filter-btn--active">Top</button>
        </div>
      </div>

      <div className="shifts-table-wrap">
        <table className="shifts-table" aria-label="Daily service shifts">
          <thead>
            <tr>
              <th>Shift Manager</th>
              <th>Location</th>
              <th>Service Date</th>
              <th>Operational Status</th>
              <th>
                <button
                  className="th-sort-btn"
                  onClick={() => setSortDir((d) => (d === "desc" ? "asc" : "desc"))}
                  aria-label="Sort by hours until close"
                >
                  Hours Until Close <ArrowDownUp size={12} />
                </button>
              </th>
              <th>Exp. Daily Revenue</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <motion.tr
                key={row.id}
                className="shifts-row"
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
              >
                <td className="shifts-cell shifts-cell--manager">{row.manager}</td>
                <td className="shifts-cell">{row.location}</td>
                <td className="shifts-cell shifts-cell--muted">{row.date}</td>
                <td className="shifts-cell">
                  <StatusBadge status={row.status} />
                </td>
                <td className="shifts-cell">
                  <HeatBar hours={row.hoursUntilClose} />
                </td>
                <td className="shifts-cell shifts-cell--revenue">
                  ₹{row.expectedRevenue.toLocaleString("en-IN")}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
