"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Activity, Map, Settings } from "lucide-react";

const NAV = [
  { href: "/",         icon: LayoutDashboard, label: "Dashboard" },
  { href: "/activity", icon: Activity,         label: "Activity"  },
  { href: "/map",      icon: Map,              label: "Map"       },
  { href: "/settings", icon: Settings,         label: "Settings"  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      {/* Brand mark */}
      <div className="sidebar-brand">
        <div className="brand-icon">
          <span>LL</span>
        </div>
      </div>

      {/* Nav links */}
      <nav className="sidebar-nav">
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              title={label}
              className={`sidebar-item ${active ? "sidebar-item--active" : ""}`}
            >
              <Icon size={20} />
            </Link>
          );
        })}
      </nav>

      {/* Bottom user avatar */}
      <div className="sidebar-footer">
        <div className="avatar">
          <span>PM</span>
        </div>
      </div>
    </aside>
  );
}
