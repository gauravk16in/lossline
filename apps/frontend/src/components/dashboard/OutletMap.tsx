"use client";

import { motion } from "framer-motion";
import { UserCircle2 } from "lucide-react";
import { useOutlet } from "@/context/OutletContext";
import { OUTLETS } from "@/data/mock";

// Bengaluru outlet positions — hand-tuned to approximate geographic layout
// mapX/mapY are fractions of the card [0–1]
// The connecting lines form a rough Bengaluru road-map quadrant

const CONNECTIONS: [string, string][] = [
  ["KOR001", "IND002"],
  ["KOR001", "JAY003"],
  ["KOR001", "MAR004"],
  ["IND002", "MAR004"],
];

export default function OutletMap() {
  const { activeOutlet, setActiveOutlet } = useOutlet();

  return (
    <motion.div
      className="bento-card map-card"
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, delay: 0.15 }}
    >
      {/* Header */}
      <div className="map-header">
        <h2 className="map-title">OUTLET MAP</h2>
        <UserCircle2 size={16} className="map-header-icon" />
      </div>

      {/* Map canvas */}
      <div className="map-canvas" aria-label="Bengaluru outlets map">
        {/* Dotgrid background handled via CSS */}

        {/* Connection lines (SVG overlay) */}
        <svg className="map-svg" aria-hidden>
          {CONNECTIONS.map(([a, b]) => {
            const outA = OUTLETS.find((o) => o.outlet_id === a)!;
            const outB = OUTLETS.find((o) => o.outlet_id === b)!;
            return (
              <line
                key={`${a}-${b}`}
                x1={`${outA.mapX * 100}%`}
                y1={`${outA.mapY * 100}%`}
                x2={`${outB.mapX * 100}%`}
                y2={`${outB.mapY * 100}%`}
                stroke="rgba(255,255,255,0.15)"
                strokeWidth="1"
                strokeDasharray="4 4"
              />
            );
          })}
        </svg>

        {/* Outlet pins */}
        {OUTLETS.map((outlet) => {
          const isActive = outlet.outlet_id === activeOutlet.outlet_id;
          return (
            <button
              key={outlet.outlet_id}
              className={`map-pin ${isActive ? "map-pin--active" : ""}`}
              style={{ left: `${outlet.mapX * 100}%`, top: `${outlet.mapY * 100}%` }}
              onClick={() => setActiveOutlet(outlet)}
              aria-label={`Select ${outlet.name}`}
              aria-pressed={isActive}
            >
              {/* Pulse ring */}
              {isActive && <span className="pin-pulse" />}
              {/* Dot */}
              <span className="pin-dot" />
              {/* Label tooltip */}
              <span className="pin-label">{outlet.name}</span>
            </button>
          );
        })}
      </div>
    </motion.div>
  );
}
