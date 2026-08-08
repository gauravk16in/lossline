"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TrendingUp } from "lucide-react";
import { useOutlet } from "@/context/OutletContext";
import { REVENUE_BY_OUTLET, GROSS_REVENUE_BY_OUTLET, AOV_BY_OUTLET } from "@/data/mock";

function useRollingNumber(target: number, duration = 1200) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    let start: number | null = null;
    const initial = 0;
    function step(ts: number) {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(initial + (target - initial) * eased));
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }, [target, duration]);
  return display;
}

export default function RevenueBento() {
  const { activeOutlet } = useOutlet();
  const data = REVENUE_BY_OUTLET[activeOutlet.outlet_id];
  const gross = GROSS_REVENUE_BY_OUTLET[activeOutlet.outlet_id];
  const aov = AOV_BY_OUTLET[activeOutlet.outlet_id];

  const rollingGross = useRollingNumber(gross);
  const rollingAov = useRollingNumber(aov);

  const maxVal = Math.max(...data.map((d) => d.value));

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeOutlet.outlet_id}
        className="bento-card revenue-card"
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
      >
        {/* Title */}
        <div className="revenue-header">
          <div className="revenue-title-row">
            <div className="revenue-icon-box">
              <TrendingUp size={18} />
            </div>
            <h2 className="revenue-title">REVENUE</h2>
          </div>
          <div className="revenue-pills">
            <span className="pill pill--active">This week</span>
            <span className="pill">INR ₹</span>
          </div>
        </div>

        <div className="revenue-body">
          {/* Bar chart */}
          <div className="revenue-chart" aria-label="Weekly revenue bar chart">
            {data.map((d) => {
              const heightPct = (d.value / maxVal) * 100;
              return (
                <div key={d.day} className="bar-col">
                  {d.isToday && (
                    <div className="bar-tooltip">
                      ₹{d.value.toLocaleString("en-IN")}
                    </div>
                  )}
                  <motion.div
                    className={`bar ${d.isToday ? "bar--active" : ""}`}
                    initial={{ height: 0 }}
                    animate={{ height: `${heightPct}%` }}
                    transition={{ duration: 0.6, delay: 0.1 }}
                  />
                  <span className="bar-label">{d.day}</span>
                </div>
              );
            })}
          </div>

          {/* Metrics */}
          <div className="revenue-metrics">
            <div className="metric-block">
              <div className="metric-header">
                <span className="metric-label">GROSS REVENUE</span>
                <span className="metric-badge badge--green">+7.5%</span>
              </div>
              <p className="metric-value">₹{rollingGross.toLocaleString("en-IN")}</p>
            </div>
            <div className="metric-divider" />
            <div className="metric-block">
              <div className="metric-header">
                <span className="metric-label">AVG. ORDER VALUE</span>
                <span className="metric-badge badge--green">+2.4%</span>
              </div>
              <p className="metric-value">₹{rollingAov.toLocaleString("en-IN")}</p>
              <p className="metric-sub">Growth vs. last week</p>
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
