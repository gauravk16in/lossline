"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useOutlet } from "@/context/OutletContext";
import { TIMING_BY_OUTLET } from "@/data/mock";

function GaugeArc({
  value,
  max,
  target,
  color,
  label,
}: {
  value: number;
  max: number;
  target: number;
  color: string;
  label: string;
}) {
  const R = 60;
  const cx = 80, cy = 80;
  const startAngle = -135;
  const endAngle = 135;
  const totalDeg = endAngle - startAngle;
  const pct = Math.min(value / max, 1);
  const targetPct = Math.min(target / max, 1);
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const arc = (pct: number) => {
    const angle = startAngle + pct * totalDeg;
    return {
      x: cx + R * Math.cos(toRad(angle)),
      y: cy + R * Math.sin(toRad(angle)),
    };
  };
  const largeArc = pct * totalDeg > 180 ? 1 : 0;
  const { x: sx, y: sy } = arc(0);
  const { x: ex, y: ey } = arc(pct);
  const { x: tx, y: ty } = arc(targetPct);
  const bgLargeArc = totalDeg > 180 ? 1 : 0;
  const { x: bex, y: bey } = arc(1);

  return (
    <div className="gauge-wrap">
      <svg width="160" height="160" viewBox="0 0 160 160" aria-label={`${label}: ${value} minutes`}>
        {/* Track */}
        <path
          d={`M ${sx} ${sy} A ${R} ${R} 0 ${bgLargeArc} 1 ${bex} ${bey}`}
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* Value arc */}
        <motion.path
          d={`M ${sx} ${sy} A ${R} ${R} 0 ${largeArc} 1 ${ex} ${ey}`}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1, delay: 0.2 }}
        />
        {/* Target marker */}
        <circle cx={tx} cy={ty} r="5" fill="white" />
        {/* Center text */}
        <text x={cx} y={cy - 6} textAnchor="middle" fill="white" fontSize="22" fontWeight="700">{value}</text>
        <text x={cx} y={cy + 14} textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize="10">min</text>
        <text x={cx} y={cy + 28} textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="9">{label}</text>
      </svg>
    </div>
  );
}

export default function OperationalTiming() {
  const { activeOutlet } = useOutlet();
  const timing = TIMING_BY_OUTLET[activeOutlet.outlet_id];

  const isOverPrep = timing.prepMins > timing.targetPrepMins;
  const isOverHandoff = timing.handoffMins > timing.targetHandoffMins;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeOutlet.outlet_id}
        className="bento-card timing-card"
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        <div className="timing-header">
          <h2 className="timing-title">OPERATIONAL<br />TIMING</h2>
          <span className="timing-tz">UTC+5:30</span>
        </div>

        <div className="timing-gauges">
          <GaugeArc
            value={timing.prepMins}
            max={30}
            target={timing.targetPrepMins}
            color={isOverPrep ? "#FF6B5A" : "#7EC8A0"}
            label="Prep"
          />
          <GaugeArc
            value={timing.handoffMins}
            max={15}
            target={timing.targetHandoffMins}
            color={isOverHandoff ? "#FF6B5A" : "#7EC8A0"}
            label="Handoff"
          />
        </div>

        <div className="timing-legend">
          <div className="timing-legend-item">
            <span className="legend-indicator legend-indicator--peak" />
            <span>Target</span>
          </div>
          <div className="timing-legend-item">
            <span className="legend-indicator legend-indicator--value" style={{ background: isOverPrep ? "#FF6B5A" : "#7EC8A0" }} />
            <span>Current</span>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
