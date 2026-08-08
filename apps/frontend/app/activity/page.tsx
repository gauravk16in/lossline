import type { Metadata } from "next";
import Header from "@/components/layout/Header";
import ServiceFlowChart from "@/components/activity/ServiceFlowChart";
import ShiftsTable from "@/components/activity/ShiftsTable";
import ChainMetrics from "@/components/activity/ChainMetrics";
import { Calendar } from "lucide-react";

export const metadata: Metadata = {
  title: "Activity — LOSSLine",
  description: "Daily service shifts, order flow tracking, and chain-wide performance metrics for Meghana Foods outlets.",
};

export default function ActivityPage() {
  return (
    <>
      <Header breadcrumb="Activity" />

      <main className="page-scroll" id="activity-main">
        <div className="activity-layout">
          {/* Activity header */}
          <div className="activity-header">
            <h1 className="activity-title">Activity</h1>
            <div className="activity-date-range">
              <Calendar size={14} />
              <span>10/01/2024 – 10/30/2024</span>
            </div>
          </div>

          {/* Two-column body */}
          <div className="activity-body">
            {/* Left: chart + table */}
            <div className="activity-main">
              <ServiceFlowChart />
              <ShiftsTable />

              {/* Synthetic disclaimer */}
              <p style={{ fontSize: "10px", color: "rgba(255,255,255,0.2)", textAlign: "center", paddingBottom: "8px" }}>
                Synthetic data for demonstration — LOSSLine Intelligence v0.1
              </p>
            </div>

            {/* Right: chain metrics sidebar */}
            <ChainMetrics />
          </div>
        </div>
      </main>
    </>
  );
}
