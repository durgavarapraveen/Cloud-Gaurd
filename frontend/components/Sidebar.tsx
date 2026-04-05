"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const nav = [
  {
    href: "/",
    label: "Dashboard",
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <rect
          x="1"
          y="1"
          width="5.5"
          height="5.5"
          rx="1"
          stroke="currentColor"
          strokeWidth="1.2"
        />
        <rect
          x="8.5"
          y="1"
          width="5.5"
          height="5.5"
          rx="1"
          stroke="currentColor"
          strokeWidth="1.2"
        />
        <rect
          x="1"
          y="8.5"
          width="5.5"
          height="5.5"
          rx="1"
          stroke="currentColor"
          strokeWidth="1.2"
        />
        <rect
          x="8.5"
          y="8.5"
          width="5.5"
          height="5.5"
          rx="1"
          stroke="currentColor"
          strokeWidth="1.2"
        />
      </svg>
    ),
  },
  {
    href: "/findings",
    label: "Findings",
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <circle
          cx="7.5"
          cy="7.5"
          r="6"
          stroke="currentColor"
          strokeWidth="1.2"
        />
        <line
          x1="7.5"
          y1="4.5"
          x2="7.5"
          y2="8"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        <circle cx="7.5" cy="10.5" r="0.75" fill="currentColor" />
      </svg>
    ),
  },
  {
    href: "/policies",
    label: "Policies",
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <rect
          x="2"
          y="1"
          width="11"
          height="13"
          rx="1.5"
          stroke="currentColor"
          strokeWidth="1.2"
        />
        <line
          x1="4.5"
          y1="5"
          x2="10.5"
          y2="5"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeLinecap="round"
        />
        <line
          x1="4.5"
          y1="7.5"
          x2="10.5"
          y2="7.5"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeLinecap="round"
        />
        <line
          x1="4.5"
          y1="10"
          x2="8"
          y2="10"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
  {
    href: "/resources",
    label: "Resources",
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <rect
          x="1"
          y="4"
          width="13"
          height="3"
          rx="1"
          stroke="currentColor"
          strokeWidth="1.2"
        />
        <rect
          x="1"
          y="9"
          width="13"
          height="3"
          rx="1"
          stroke="currentColor"
          strokeWidth="1.2"
        />
        <circle cx="3.5" cy="5.5" r="0.75" fill="currentColor" />
        <circle cx="3.5" cy="10.5" r="0.75" fill="currentColor" />
      </svg>
    ),
  },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="fixed top-0 left-0 h-screen w-56 bg-[#0d0d14] border-r border-white/[0.06] flex flex-col z-40">
      {/* Logo */}
      <div className="px-5 pt-6 pb-5 border-b border-white/[0.06]">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path
                d="M7 1L12 4V10L7 13L2 10V4L7 1Z"
                stroke="#10b981"
                strokeWidth="1.2"
                strokeLinejoin="round"
              />
              <path
                d="M7 5L9 6.5V9.5L7 11L5 9.5V6.5L7 5Z"
                fill="#10b981"
                fillOpacity="0.4"
              />
            </svg>
          </div>
          <div>
            <div className="text-[13px] font-semibold text-white tracking-tight">
              CloudGuard
            </div>
            <div className="text-[10px] text-slate-500 tracking-wide uppercase">
              CSPM
            </div>
          </div>
        </div>
      </div>

      {/* Provider badge */}
      <div className="px-4 pt-4 pb-2">
        <div className="text-[10px] text-slate-600 uppercase tracking-widest mb-2 px-1">
          Provider
        </div>
        <div className="flex items-center gap-2 px-2 py-1.5 rounded bg-orange-500/10 border border-orange-500/20">
          <div className="w-2 h-2 rounded-full bg-orange-400 pulse-dot" />
          <span className="text-[11px] text-orange-300 font-medium">AWS</span>
          <span className="ml-auto text-[10px] text-slate-500">ap-south-1</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 pt-3 space-y-0.5">
        <div className="text-[10px] text-slate-600 uppercase tracking-widest mb-2 px-2">
          Navigation
        </div>
        {nav.map((item) => {
          const active = path === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-2.5 py-2 rounded-md text-[13px] transition-all duration-150 group
                ${
                  active
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]"
                }`}
            >
              <span
                className={
                  active
                    ? "text-emerald-400"
                    : "text-slate-500 group-hover:text-slate-300"
                }
              >
                {item.icon}
              </span>
              {item.label}
              {active && (
                <span className="ml-auto w-1 h-1 rounded-full bg-emerald-400" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-white/[0.06]">
        <div className="text-[10px] text-slate-600">
          CloudGuard v0.1 · Sprint 2
        </div>
      </div>
    </aside>
  );
}
