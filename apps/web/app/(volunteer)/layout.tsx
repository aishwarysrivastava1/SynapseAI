"use client";

import React from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { Home, User, Trophy } from "lucide-react";
import RoleGuard from "../../components/auth/RoleGuard";
import { ThemeToggle } from "../../components/ui/ThemeToggle";

const NAV_ITEMS = [
  { href: "/feed",        icon: Home,   label: "Task Feed"    },
  { href: "/leaderboard", icon: Trophy, label: "Leaderboard"  },
  { href: "/profile",     icon: User,   label: "Profile"      },
];

function VolunteerShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[#F5F6F1] dark:bg-gray-950 flex flex-col">

      {/* ── Header ─────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 bg-[#115E54] h-14 flex items-center px-5 gap-3 shrink-0 shadow-md">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo/logo-icon.png" alt="logo" className="h-7 w-7 object-contain shrink-0" />
        <div className="leading-none">
          <p className="text-sm font-bold text-white tracking-tight">Sanchaalan Saathi</p>
          <p className="text-[10px] text-white/50">Field Portal</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="hidden lg:inline-flex items-center gap-1.5 bg-white/10 border border-white/15 text-white/70 text-xs px-2.5 py-1 rounded-lg font-medium">
            Volunteer
          </span>
          <ThemeToggle size="sm" className="border-white/20 bg-white/10 text-white hover:bg-white/20 hover:border-white/30" />
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Desktop Sidebar */}
        <aside className="hidden lg:flex flex-col w-56 xl:w-60 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 shrink-0">
          <nav className="flex-1 p-3 space-y-0.5">
            {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
              const isActive = pathname === href || (href !== "/" && pathname?.startsWith(href));
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? "bg-[#115E54]/10 dark:bg-[#115E54]/20 text-[#115E54] dark:text-[#48A15E]"
                      : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100"
                  }`}
                >
                  <Icon size={17} strokeWidth={isActive ? 2.5 : 1.8} />
                  <span className="flex-1">{label}</span>
                  {isActive && <span className="w-1.5 h-1.5 rounded-full bg-[#115E54] dark:bg-[#48A15E]" />}
                </Link>
              );
            })}
          </nav>
          <div className="p-4 border-t border-gray-100 dark:border-gray-800">
            <p className="text-[10px] text-gray-400 dark:text-gray-600 text-center">
              Sanchaalan Saathi · Team CrownBreakers
            </p>
          </div>
        </aside>

        {/* Main scrollable content */}
        <main className="flex-1 overflow-y-auto custom-scrollbar pb-16 lg:pb-0">
          <div className="max-w-2xl xl:max-w-3xl mx-auto lg:mx-0 lg:max-w-none">
            {children}
          </div>
        </main>
      </div>

      {/* ── Mobile Bottom Nav ──────────────────────────────── */}
      <nav className="lg:hidden fixed bottom-0 inset-x-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 flex justify-around py-1.5 z-50 shadow-[0_-1px_12px_rgba(0,0,0,0.06)] dark:shadow-[0_-1px_12px_rgba(0,0,0,0.3)]">
        {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
          const isActive = pathname === href || (href !== "/" && pathname?.startsWith(href));
          return (
            <a
              key={href}
              href={href}
              className={`flex flex-col items-center gap-0.5 px-6 py-1.5 rounded-lg transition-all ${
                isActive
                  ? "text-[#115E54] dark:text-[#48A15E]"
                  : "text-gray-400 dark:text-gray-600 hover:text-gray-600 dark:hover:text-gray-400"
              }`}
            >
              <Icon size={18} strokeWidth={isActive ? 2.5 : 1.8} />
              <span className={`text-[10px] ${isActive ? "font-bold" : "font-medium"}`}>{label}</span>
              {isActive && <span className="w-1 h-1 rounded-full bg-[#115E54] dark:bg-[#48A15E] mt-0.5" />}
            </a>
          );
        })}
      </nav>
    </div>
  );
}

export default function VolunteerLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard requiredRole="Volunteer">
      <VolunteerShell>{children}</VolunteerShell>
    </RoleGuard>
  );
}
