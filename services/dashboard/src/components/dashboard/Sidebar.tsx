import { Link, useLocation } from "react-router-dom";
import {
  Radio,
  Bell,
  Search,
  Shield,
  Send,
  ChevronLeft,
  LogOut,
} from "lucide-react";
import { useAuth } from "@/lib/AuthContext";

const navItems = [
  { icon: Radio, label: "Streams", path: "/dashboard" },
  { icon: Shield, label: "Rules", path: "/dashboard/rules" },
  { icon: Bell, label: "Alerts", path: "/dashboard/alerts" },
  { icon: Send, label: "Channels", path: "/dashboard/channels" },
  { icon: Search, label: "Search", path: "/dashboard/search" },
];

export default function Sidebar() {
  const location = useLocation();
  const { logout } = useAuth();

  return (
    <aside className="w-14 md:w-52 border-r border-white/[0.06] flex flex-col shrink-0 transition-all">
      {/* Logo */}
      <div className="h-14 flex items-center justify-between px-3 md:px-4 border-b border-white/[0.06]">
        <Link
          to="/"
          className="flex items-center gap-2 text-sm font-bold tracking-tight"
        >
          <div className="w-6 h-6 rounded bg-white/10 flex items-center justify-center text-[10px] font-bold">
            VS
          </div>
          <span className="hidden md:inline">VoxSentinel</span>
        </Link>
        <Link
          to="/"
          className="hidden md:flex items-center justify-center w-6 h-6 rounded hover:bg-white/5 text-white/20 hover:text-white/50 transition-colors"
          title="Back to landing"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3">
        {navItems.map(({ icon: Icon, label, path }) => {
          const isActive =
            path === "/dashboard"
              ? location.pathname === "/dashboard" ||
                location.pathname === "/dashboard/streams"
              : location.pathname.startsWith(path);
          return (
            <Link
              key={path}
              to={path}
              className={`flex items-center gap-3 px-3 md:px-4 py-2.5 text-xs transition-colors duration-200 ${
                isActive
                  ? "text-white bg-white/[0.04] border-r border-r-white/30"
                  : "text-white/30 hover:text-white/60 hover:bg-white/[0.02]"
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" strokeWidth={1.5} />
              <span className="hidden md:inline tracking-wide">{label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Logout + System status */}
      <div className="p-3 md:p-4 border-t border-white/[0.06] space-y-3">
        <button
          onClick={logout}
          className="flex items-center gap-2 text-xs text-white/30 hover:text-white/60 transition-colors w-full"
        >
          <LogOut className="w-4 h-4 shrink-0" strokeWidth={1.5} />
          <span className="hidden md:inline tracking-wide">Logout</span>
        </button>
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse-slow" />
          <span className="text-[9px] text-white/25 tracking-[0.15em] uppercase hidden md:inline">
            System Healthy
          </span>
        </div>
      </div>
    </aside>
  );
}
