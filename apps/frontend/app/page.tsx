import type { Metadata } from "next";
import Header from "@/components/layout/Header";
import AlertBanner from "@/components/dashboard/AlertBanner";
import RevenueBento from "@/components/dashboard/RevenueBento";
import VenueCapacity from "@/components/dashboard/VenueCapacity";
import OperationalTiming from "@/components/dashboard/OperationalTiming";
import OutletMap from "@/components/dashboard/OutletMap";
import AIOperationsLead from "@/components/dashboard/AIOperationsLead";

export const metadata: Metadata = {
  title: "Dashboard — LOSSLine",
  description: "Live operational overview for Meghana Foods outlets: revenue, capacity, timing, and AI-guided incident management.",
};

export default function DashboardPage() {
  return (
    <>
      <Header breadcrumb="Overview" />

      <main className="page-scroll" id="dashboard-main">
        {/* Full-width alert strip */}
        <div className="alert-span">
          <AlertBanner />
        </div>

        {/* Primary bento grid */}
        <div className="dashboard-grid">
          {/* Row 1: Revenue (tall, left) + Venue Capacity (right) */}
          <div className="revenue-span">
            <RevenueBento />
          </div>
          <div className="venue-span">
            <VenueCapacity />
          </div>

          {/* Row 2: Map + Timing + AI */}
          <div className="bottom-row">
            <OutletMap />
            <OperationalTiming />
            <AIOperationsLead />
          </div>
        </div>

        {/* Synthetic data disclaimer */}
        <p style={{ fontSize: "10px", color: "rgba(255,255,255,0.2)", textAlign: "center", paddingBottom: "8px" }}>
          Synthetic data for demonstration — LOSSLine Intelligence v0.1
        </p>
      </main>
    </>
  );
}
