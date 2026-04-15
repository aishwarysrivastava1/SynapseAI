"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Users, AlertTriangle, CheckCircle2, Clock, Search,
  Zap, MapPin, Trophy, Activity, ArrowLeft, UserCheck,
  TrendingUp, Shield
} from "lucide-react";
import { useAllVolunteers } from "../../hooks/useFirestore";
import { useNeeds } from "../../hooks/useFirestore";
import { useActivityFeed } from "../../hooks/useActivityFeed";
import { ThemeToggle } from "../../components/ui/ThemeToggle";

const STATUS_DOT: Record<string, string> = {
  ACTIVE:  "bg-[#48A15E]",
  BUSY:    "bg-amber-500",
  OFFLINE: "bg-gray-300 dark:bg-gray-600",
};

const LEVEL_THRESHOLDS = [0, 100, 300, 600, 1000, 1500, 2200, 3000, 4000, 5000];
function getLevel(xp: number) {
  let level = 1;
  for (let i = 0; i < LEVEL_THRESHOLDS.length; i++) {
    if (xp >= LEVEL_THRESHOLDS[i]) level = i + 1;
  }
  return Math.min(level, LEVEL_THRESHOLDS.length);
}

function timeAgo(ts: any): string {
  if (!ts) return "";
  const date = ts?.toDate ? ts.toDate() : new Date(ts);
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diff < 60)   return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

const ACTIVITY_ICON: Record<string, React.ReactNode> = {
  NEED_REPORTED:    <AlertTriangle size={12} className="text-red-500" />,
  TASK_ASSIGNED:    <Zap size={12} className="text-amber-500" />,
  TASK_VERIFIED:    <CheckCircle2 size={12} className="text-[#48A15E]" />,
  VOLUNTEER_JOINED: <UserCheck size={12} className="text-[#115E54]" />,
};

export default function PublicTransparencyPage() {
  const { volunteers, loading: volLoading } = useAllVolunteers();
  const { needs, loading: needsLoading } = useNeeds();
  const { events: activity } = useActivityFeed(30);

  const [volSearch, setVolSearch] = useState("");
  const [needFilter, setNeedFilter] = useState<"ALL" | "PENDING" | "RESOLVED">("ALL");
  const [activeTab, setActiveTab] = useState<"volunteers" | "issues" | "activity">("volunteers");

  const filteredVols = volunteers.filter((v) =>
    v.name?.toLowerCase().includes(volSearch.toLowerCase()) ||
    (v.skills ?? []).some((s) => s.toLowerCase().includes(volSearch.toLowerCase()))
  );

  const filteredNeeds = needs.filter((n) =>
    needFilter === "ALL" || n.status === needFilter
  );

  const pendingCount  = needs.filter((n) => n.status === "PENDING").length;
  const resolvedCount = needs.filter((n) => n.status === "RESOLVED").length;
  const activeVols    = volunteers.filter((v) => v.availabilityStatus === "ACTIVE").length;

  return (
    <div className="min-h-screen bg-[#F5F6F1] dark:bg-gray-950 flex flex-col">

      {/* ── Header ───────────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 bg-white/90 dark:bg-gray-900/90 backdrop-blur border-b border-gray-200 dark:border-gray-800 flex items-center px-5 lg:px-8 h-14 gap-3 shadow-sm">
        <Link href="/" className="flex items-center gap-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors mr-1">
          <ArrowLeft size={14} />
        </Link>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo/logo-icon.png" alt="logo" className="h-7 w-7 object-contain shrink-0" />
        <div className="leading-none">
          <p className="text-sm font-bold text-[#115E54]">Sanchaalan Saathi</p>
          <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5">Public Transparency Dashboard</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-1.5 bg-[#48A15E]/10 dark:bg-[#48A15E]/20 border border-[#48A15E]/25 text-[#2A8256] dark:text-[#48A15E] text-[10px] font-semibold px-2.5 py-1 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-[#48A15E] animate-pulse" />
            Live
          </div>
          <ThemeToggle size="sm" />
        </div>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 lg:px-8 py-8">

        {/* ── Hero / Stats ─────────────────────────────────────────── */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-1">
            <Shield size={16} className="text-[#115E54]" />
            <span className="text-xs font-semibold text-[#115E54] uppercase tracking-wide">Open Data</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-bold text-gray-900 dark:text-gray-100 leading-tight">
            Community Transparency
          </h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1.5 max-w-lg">
            Real-time, public record of every registered volunteer and every field issue raised or resolved on the platform.
          </p>
        </div>

        {/* Stats cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <Users size={14} className="text-[#115E54]" />
              <span className="text-xs text-gray-500 dark:text-gray-400">Volunteers</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 tabular-nums">{volunteers.length}</p>
            <p className="text-[10px] text-[#48A15E] font-medium mt-0.5">{activeVols} active now</p>
          </div>
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle size={14} className="text-amber-500" />
              <span className="text-xs text-gray-500 dark:text-gray-400">Open Issues</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 tabular-nums">{pendingCount}</p>
            <p className="text-[10px] text-amber-600 font-medium mt-0.5">pending response</p>
          </div>
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 size={14} className="text-[#48A15E]" />
              <span className="text-xs text-gray-500 dark:text-gray-400">Resolved</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 tabular-nums">{resolvedCount}</p>
            <p className="text-[10px] text-[#48A15E] font-medium mt-0.5">issues closed</p>
          </div>
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp size={14} className="text-purple-500" />
              <span className="text-xs text-gray-500 dark:text-gray-400">Resolution Rate</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 tabular-nums">
              {needs.length > 0 ? Math.round((resolvedCount / needs.length) * 100) : 0}%
            </p>
            <p className="text-[10px] text-purple-500 font-medium mt-0.5">of all issues</p>
          </div>
        </div>

        {/* ── Tab switcher ──────────────────────────────────────────── */}
        <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-xl mb-6 w-fit">
          {([
            { key: "volunteers", icon: Users,         label: `Volunteers (${volunteers.length})` },
            { key: "issues",     icon: AlertTriangle,  label: `Issues (${needs.length})` },
            { key: "activity",   icon: Activity,       label: "Live Feed" },
          ] as const).map(({ key, icon: Icon, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === key
                  ? "bg-white dark:bg-gray-700 text-[#115E54] dark:text-[#48A15E] shadow-sm"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
              }`}
            >
              <Icon size={13} />
              {label}
            </button>
          ))}
        </div>

        {/* ── VOLUNTEERS TAB ──────────────────────────────────────────── */}
        {activeTab === "volunteers" && (
          <div>
            <div className="relative mb-4">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
              <input
                type="text"
                placeholder="Search by name or skill..."
                value={volSearch}
                onChange={(e) => setVolSearch(e.target.value)}
                className="w-full bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl pl-9 pr-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 outline-none focus:border-[#115E54]/40 placeholder-gray-400 dark:placeholder-gray-600 shadow-sm transition-colors"
              />
            </div>

            {volLoading ? (
              <div className="space-y-3">
                {[1,2,3,4,5].map(i => (
                  <div key={i} className="h-20 bg-white dark:bg-gray-900 rounded-xl animate-pulse border border-gray-200 dark:border-gray-800" />
                ))}
              </div>
            ) : filteredVols.length === 0 ? (
              <div className="text-center py-16 text-gray-400 dark:text-gray-500">
                <Users size={32} className="mx-auto mb-3 opacity-30" />
                <p className="text-sm font-medium">No volunteers found</p>
                {volSearch && <p className="text-xs mt-1">Try a different search term</p>}
              </div>
            ) : (
              <div className="space-y-2">
                {filteredVols.map((v, idx) => {
                  const level = getLevel(v.totalXP ?? 0);
                  return (
                    <div
                      key={v.uid}
                      className="flex items-center gap-4 p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl hover:border-gray-300 dark:hover:border-gray-700 transition-all shadow-sm"
                    >
                      {/* Rank */}
                      <div className="w-8 text-center shrink-0">
                        {idx === 0 ? <span className="text-xl">🥇</span> :
                         idx === 1 ? <span className="text-xl">🥈</span> :
                         idx === 2 ? <span className="text-xl">🥉</span> :
                         <span className="text-xs text-gray-400 dark:text-gray-500 font-semibold tabular-nums">#{idx + 1}</span>}
                      </div>

                      {/* Avatar initial */}
                      <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#115E54]/20 to-[#48A15E]/10 dark:from-[#115E54]/30 dark:to-[#48A15E]/20 border border-[#115E54]/20 flex items-center justify-center shrink-0">
                        <span className="text-sm font-bold text-[#115E54] dark:text-[#48A15E]">
                          {(v.name ?? "?").charAt(0).toUpperCase()}
                        </span>
                      </div>

                      {/* Name + skills */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-sm text-gray-900 dark:text-gray-100 truncate">{v.name}</span>
                          <span className="text-[9px] bg-[#115E54]/8 dark:bg-[#115E54]/20 border border-[#115E54]/20 dark:border-[#115E54]/30 text-[#115E54] px-1.5 py-0.5 rounded-full font-semibold shrink-0">
                            Lv{level}
                          </span>
                          <div className={`w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[v.availabilityStatus] ?? "bg-gray-300"}`} title={v.availabilityStatus} />
                        </div>
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {(v.skills ?? []).slice(0, 5).map((s) => (
                            <span key={s} className="text-[10px] text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-md">
                              {s}
                            </span>
                          ))}
                          {(v.skills ?? []).length > 5 && (
                            <span className="text-[10px] text-gray-400 dark:text-gray-500 px-1.5 py-0.5">+{(v.skills ?? []).length - 5} more</span>
                          )}
                        </div>
                      </div>

                      {/* Stats */}
                      <div className="flex flex-col items-end gap-1.5 shrink-0 text-right">
                        <div className="flex items-center gap-1 text-amber-600 dark:text-amber-400">
                          <Zap size={11} />
                          <span className="text-xs font-bold tabular-nums">{v.totalXP ?? 0} XP</span>
                        </div>
                        <div className="flex items-center gap-1 text-[#2A8256] dark:text-[#48A15E]">
                          <CheckCircle2 size={11} />
                          <span className="text-[10px] tabular-nums">{v.totalTasksCompleted ?? 0} tasks</span>
                        </div>
                        <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-semibold ${
                          v.availabilityStatus === "ACTIVE"  ? "bg-[#48A15E]/10 text-[#2A8256] dark:text-[#48A15E]" :
                          v.availabilityStatus === "BUSY"    ? "bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400" :
                          "bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500"
                        }`}>
                          {v.availabilityStatus ?? "OFFLINE"}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ── ISSUES TAB ──────────────────────────────────────────────── */}
        {activeTab === "issues" && (
          <div>
            <div className="flex gap-1.5 mb-4">
              {(["ALL", "PENDING", "RESOLVED"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setNeedFilter(f)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                    needFilter === f
                      ? f === "RESOLVED"
                        ? "bg-[#48A15E]/10 dark:bg-[#48A15E]/20 text-[#2A8256] dark:text-[#48A15E] border-[#48A15E]/30"
                        : f === "PENDING"
                        ? "bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border-amber-300 dark:border-amber-800"
                        : "bg-[#115E54]/10 dark:bg-[#115E54]/20 text-[#115E54] dark:text-[#48A15E] border-[#115E54]/30"
                      : "bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400 border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700"
                  }`}
                >
                  {f === "ALL" ? `All (${needs.length})` :
                   f === "PENDING" ? `Open (${pendingCount})` :
                   `Resolved (${resolvedCount})`}
                </button>
              ))}
            </div>

            {needsLoading ? (
              <div className="space-y-3">
                {[1,2,3,4,5].map(i => (
                  <div key={i} className="h-24 bg-white dark:bg-gray-900 rounded-xl animate-pulse border border-gray-200 dark:border-gray-800" />
                ))}
              </div>
            ) : filteredNeeds.length === 0 ? (
              <div className="text-center py-16 text-gray-400 dark:text-gray-500">
                <AlertTriangle size={32} className="mx-auto mb-3 opacity-30" />
                <p className="text-sm font-medium">No issues found</p>
              </div>
            ) : (
              <div className="space-y-2">
                {filteredNeeds.map((need) => (
                  <div
                    key={need.id}
                    className="p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl hover:border-gray-300 dark:hover:border-gray-700 transition-all shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                          need.urgency_score >= 0.8 ? "bg-red-500 animate-pulse" :
                          need.urgency_score >= 0.5 ? "bg-amber-500" : "bg-[#48A15E]"
                        }`} />
                        <span className="font-semibold text-sm text-gray-900 dark:text-gray-100 capitalize truncate">
                          {need.type} — {need.sub_type}
                        </span>
                      </div>
                      <span className={`shrink-0 text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                        need.status === "RESOLVED"
                          ? "bg-[#48A15E]/10 dark:bg-[#48A15E]/20 text-[#2A8256] dark:text-[#48A15E]"
                          : need.status === "CLAIMED"
                          ? "bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-400"
                          : "bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800"
                      }`}>
                        {need.status === "PENDING" ? "Open" : need.status}
                      </span>
                    </div>

                    <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed mb-3 line-clamp-2">
                      {need.description}
                    </p>

                    <div className="flex items-center gap-4 text-[10px] text-gray-400 dark:text-gray-600 flex-wrap">
                      {need.location?.name && (
                        <span className="flex items-center gap-1">
                          <MapPin size={9} />
                          {need.location.name}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <AlertTriangle size={9} />
                        Severity: <strong className="text-gray-500 dark:text-gray-400">{(need.urgency_score * 10).toFixed(1)}/10</strong>
                      </span>
                      {need.population_affected > 0 && (
                        <span className="flex items-center gap-1">
                          <Users size={9} />
                          {need.population_affected.toLocaleString()} affected
                        </span>
                      )}
                      {need.reported_at && (
                        <span className="flex items-center gap-1">
                          <Clock size={9} />
                          {timeAgo(need.reported_at)}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── ACTIVITY TAB ─────────────────────────────────────────────── */}
        {activeTab === "activity" && (
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100 dark:border-gray-800">
              <Activity size={14} className="text-[#115E54]" />
              <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">Live Activity Feed</span>
              <span className="ml-auto w-1.5 h-1.5 rounded-full bg-[#48A15E] animate-pulse" />
            </div>
            {activity.length === 0 ? (
              <div className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
                <Activity size={28} className="mx-auto mb-3 opacity-30" />
                <p>No recent activity</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-50 dark:divide-gray-800">
                {activity.map((event) => (
                  <div key={event.id} className="flex items-start gap-3 px-4 py-3.5 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                    <div className="mt-0.5 shrink-0 w-6 h-6 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                      {ACTIVITY_ICON[event.type] ?? <Activity size={11} className="text-gray-400" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-gray-800 dark:text-gray-200">{event.title}</p>
                      <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5 leading-relaxed">{event.description}</p>
                    </div>
                    <span className="text-[10px] text-gray-400 dark:text-gray-600 shrink-0 mt-0.5 tabular-nums whitespace-nowrap">
                      {timeAgo(event.timestamp)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="text-center py-5 text-xs text-gray-400 dark:text-gray-600 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        Sanchaalan Saathi — Open Data · Team CrownBreakers
        <span className="mx-2">·</span>
        <Link href="/" className="text-[#115E54] hover:underline">Back to Home</Link>
      </footer>
    </div>
  );
}
