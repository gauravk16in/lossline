"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronDown, Wifi, Search } from "lucide-react";
import { useOutlet } from "@/context/OutletContext";
import { motion, AnimatePresence } from "framer-motion";

export default function Header({ breadcrumb }: { breadcrumb: string }) {
  const { activeOutlet, setActiveOutlet, outlets } = useOutlet();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <header className="header">
      {/* Breadcrumb */}
      <div className="header-breadcrumb">
        <span className="breadcrumb-parent">Dashboard /</span>
        <span className="breadcrumb-current">{breadcrumb}</span>
      </div>

      <div className="header-right">
        {/* Search */}
        <button className="header-search" aria-label="Search">
          <Search size={16} />
        </button>

        {/* Outlet selector */}
        <div className="outlet-selector" ref={ref}>
          <button
            className="outlet-trigger"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
          >
            <span className="outlet-dot" />
            <span>{activeOutlet.name}</span>
            <ChevronDown size={14} className={`outlet-chevron ${open ? "open" : ""}`} />
          </button>

          <AnimatePresence>
            {open && (
              <motion.ul
                className="outlet-dropdown"
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.15 }}
                role="listbox"
              >
                {outlets.map((o) => (
                  <li
                    key={o.outlet_id}
                    role="option"
                    aria-selected={o.outlet_id === activeOutlet.outlet_id}
                    className={`outlet-option ${o.outlet_id === activeOutlet.outlet_id ? "active" : ""}`}
                    onClick={() => { setActiveOutlet(o); setOpen(false); }}
                  >
                    <span className="outlet-dot" />
                    {o.name}
                  </li>
                ))}
              </motion.ul>
            )}
          </AnimatePresence>
        </div>

        {/* Live status */}
        <div className="live-badge">
          <Wifi size={13} />
          <span>Live</span>
          <span className="live-pulse" />
        </div>
      </div>
    </header>
  );
}
