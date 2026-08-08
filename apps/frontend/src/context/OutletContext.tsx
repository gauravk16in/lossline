"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { OUTLETS } from "@/data/mock";
import type { Outlet } from "@/types";

interface OutletContextValue {
  activeOutlet: Outlet;
  setActiveOutlet: (outlet: Outlet) => void;
  outlets: Outlet[];
}

const OutletContext = createContext<OutletContextValue | null>(null);

export function OutletProvider({ children }: { children: React.ReactNode }) {
  const [activeOutlet, setActiveOutletState] = useState<Outlet>(OUTLETS[0]);

  const setActiveOutlet = useCallback((outlet: Outlet) => {
    setActiveOutletState(outlet);
  }, []);

  return (
    <OutletContext.Provider value={{ activeOutlet, setActiveOutlet, outlets: OUTLETS }}>
      {children}
    </OutletContext.Provider>
  );
}

export function useOutlet(): OutletContextValue {
  const ctx = useContext(OutletContext);
  if (!ctx) throw new Error("useOutlet must be used inside <OutletProvider>");
  return ctx;
}
