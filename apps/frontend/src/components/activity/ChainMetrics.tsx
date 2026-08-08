"use client";

import { motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { CHAIN_METRICS } from "@/data/mock";

function ProgressBar({ achieved, total }: { achieved: number; total: number }) {
  const pct = (achieved / total) * 100;
  return (
    <div className="progress-track" aria-label={`${achieved} of ${total}`}>
      <motion.div
        className="progress-fill"
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.8, delay: 0.2 }}
      />
    </div>
  );
}

export default function ChainMetrics() {
  return (
    <aside className="chain-sidebar">
      {/* Chain metrics card */}
      <div className="chain-card">
        <div className="chain-header">
          <h3 className="chain-title">Chain-Wide Metrics</h3>
        </div>

        <div className="chain-kpis">
          <div className="chain-kpi">
            <span className="chain-kpi-label">Successful services</span>
            <div className="chain-kpi-val-row">
              <span className="chain-kpi-val">120</span>
              <span className="chain-kpi-badge">+5</span>
            </div>
          </div>
          <div className="chain-kpi">
            <span className="chain-kpi-label">Target</span>
            <span className="chain-kpi-val">480</span>
          </div>
        </div>

        <div className="chain-metrics-list">
          {CHAIN_METRICS.map((m, i) => (
            <div key={m.label} className="chain-metric-item">
              <p className="chain-metric-period">{m.label}</p>
              <p className="chain-metric-desc">{m.description}</p>
              <ProgressBar achieved={m.achieved} total={m.total} />
            </div>
          ))}
        </div>
      </div>

      {/* Industry Feed collapsible */}
      <details className="industry-feed" open>
        <summary className="industry-feed-header">
          <span className="industry-feed-icon">📡</span>
          <span>Industry Feed</span>
          <ChevronDown size={14} className="industry-feed-chevron" />
        </summary>
        <div className="industry-feed-body">
          <div className="feed-item">
            <span className="feed-dot feed-dot--green" />
            <p>Delivery platforms reporting +12% surge in Bengaluru South tonight</p>
          </div>
          <div className="feed-item">
            <span className="feed-dot feed-dot--amber" />
            <p>FSSAI inspection scheduled — Koramangala cluster — next week</p>
          </div>
          <div className="feed-item">
            <span className="feed-dot feed-dot--blue" />
            <p>Competitor new outlet opens Indiranagar — monitor AOV impact</p>
          </div>
        </div>
      </details>
    </aside>
  );
}
