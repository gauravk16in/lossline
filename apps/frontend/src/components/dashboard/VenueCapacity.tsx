"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useOutlet } from "@/context/OutletContext";
import { CAPACITY_BY_OUTLET } from "@/data/mock";

function CapacityCircle({ pct, day }: { pct: number; day: string }) {
  const r = 20;
  const circ = 2 * Math.PI * r;
  const stroke = (pct / 100) * circ;
  const isHigh = pct >= 90;
  const isMid = pct >= 75;

  return (
    <div className="capacity-day">
      <div className="capacity-ring-wrap">
        <svg width="52" height="52" viewBox="0 0 52 52">
          <circle cx="26" cy="26" r={r} fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="4" />
          <motion.circle
            cx="26" cy="26" r={r}
            fill="none"
            stroke={isHigh ? "#FF6B5A" : isMid ? "#FFFFFF" : "#A8B4FF"}
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={`${stroke} ${circ}`}
            strokeDashoffset={circ / 4}
            initial={{ strokeDasharray: `0 ${circ}` }}
            animate={{ strokeDasharray: `${stroke} ${circ}` }}
            transition={{ duration: 0.8, delay: 0.2 }}
          />
        </svg>
        <span className="capacity-pct">{pct}%</span>
      </div>
      <span className="capacity-day-label">{day}</span>
    </div>
  );
}

export default function VenueCapacity() {
  const { activeOutlet } = useOutlet();
  const data = CAPACITY_BY_OUTLET[activeOutlet.outlet_id];

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeOutlet.outlet_id}
        className="bento-card venue-card"
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, delay: 0.05 }}
      >
        <div className="venue-header">
          <h2 className="venue-title">VENUE CAPACITY</h2>
          <span className="pill pill--ghost">This week</span>
        </div>

        <div className="venue-rings">
          {data.map((d) => (
            <CapacityCircle key={d.day} pct={d.pct} day={d.day} />
          ))}
        </div>

        {/* Sparkline area chart (decorative SVG) */}
        <div className="venue-sparkline">
          <svg viewBox="0 0 260 40" preserveAspectRatio="none" aria-hidden>
            <defs>
              <linearGradient id="spark-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#FF6B5A" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#FF6B5A" stopOpacity="0" />
              </linearGradient>
            </defs>
            {(() => {
              const pts = data.map((d, i) => {
                const x = (i / (data.length - 1)) * 260;
                const y = 40 - (d.pct / 100) * 38;
                return `${x},${y}`;
              });
              const path = `M${pts.join(" L")}`;
              const fill = `${path} L260,40 L0,40 Z`;
              return (
                <>
                  <path d={fill} fill="url(#spark-grad)" />
                  <path d={path} fill="none" stroke="#FF6B5A" strokeWidth="1.5" />
                </>
              );
            })()}
          </svg>
        </div>

        <div className="venue-legend">
          <span className="legend-dot" style={{ background: "#FF6B5A" }} /> High
          <span className="legend-dot" style={{ background: "#fff" }} /> Mid
          <span className="legend-dot" style={{ background: "#A8B4FF" }} /> Low
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
