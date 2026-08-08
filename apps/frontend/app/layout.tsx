import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { OutletProvider } from "@/context/OutletContext";
import Sidebar from "@/components/layout/Sidebar";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "LOSSLine — Operational Intelligence Dashboard",
  description:
    "Real-time operational degradation detection and AI-guided recommendations for Meghana Foods outlets. Synthetic data for demonstration.",
  keywords: ["restaurant", "operations", "intelligence", "dashboard", "LOSSLine"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={inter.variable}>
      <body>
        <OutletProvider>
          <div className="app-shell">
            <Sidebar />
            <div className="main-content">
              {children}
            </div>
          </div>
        </OutletProvider>
      </body>
    </html>
  );
}
