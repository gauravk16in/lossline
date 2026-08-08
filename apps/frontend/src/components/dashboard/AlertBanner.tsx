"use client";

import { useState, useEffect } from "react";
import { AlertTriangle, ArrowUpRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useOutlet } from "@/context/OutletContext";
import { INCIDENT_BY_OUTLET } from "@/data/mock";

function useCountdown(initialSeconds: number) {
  const [secs, setSecs] = useState(initialSeconds);
  useEffect(() => {
    const id = setInterval(() => setSecs((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, []);
  const h = String(Math.floor(secs / 3600)).padStart(2, "0");
  const m = String(Math.floor((secs % 3600) / 60)).padStart(2, "0");
  const s = String(secs % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

export default function AlertBanner() {
  const { activeOutlet } = useOutlet();
  const incident = INCIDENT_BY_OUTLET[activeOutlet.outlet_id];
  const countdown = useCountdown(9492);

  return (
    <AnimatePresence mode="wait">
      {incident ? (
        <motion.div
          key={activeOutlet.outlet_id + "-alert"}
          className="alert-card"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.3 }}
        >
          <div className="alert-icon">
            <AlertTriangle size={20} />
          </div>
          <div className="alert-body">
            <p className="alert-title">OPERATIONAL OVERLOAD — {incident.severity}</p>
            <p className="alert-subtitle">
              {incident.recommendation_text.split(".")[0]}. Shift ends in{" "}
              <span className="alert-time">{countdown}</span>
            </p>
          </div>
          <button className="alert-action" aria-label="View incident">
            <ArrowUpRight size={14} />
          </button>
        </motion.div>
      ) : (
        <motion.div
          key={activeOutlet.outlet_id + "-ok"}
          className="alert-card alert-card--ok"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.3 }}
        >
          <div className="alert-icon alert-icon--ok">
            <span>✓</span>
          </div>
          <div className="alert-body">
            <p className="alert-title">ALL SYSTEMS NOMINAL</p>
            <p className="alert-subtitle">No active incidents at {activeOutlet.name}</p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
