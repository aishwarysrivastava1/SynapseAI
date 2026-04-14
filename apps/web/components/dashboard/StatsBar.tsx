"use client";

import React from "react";
import { NeedNode } from "../../lib/types";

export default function StatsBar({ needs, vols }: { needs: NeedNode[], vols: any[] }) {
  const total = needs.length;
  const pending = needs.filter(n => n.status === "PENDING").length;
  const resolved = needs.filter(n => n.status === "RESOLVED").length;
  const activeVols = vols.filter(v => v.availabilityStatus === "ACTIVE").length || 0;
  
  const coverage = total ? Math.round((resolved / total) * 100) : 0;

  const cards = [
    { label: "Total Needs", value: total, color: "text-blue-400 drop-shadow-[0_0_5px_rgba(96,165,250,0.8)]", border: "border-blue-500/20", glow: "hover:shadow-[0_0_20px_rgba(96,165,250,0.3)]" },
    { label: "Pending", value: pending, color: "text-neon-orange drop-shadow-[0_0_5px_rgba(255,77,0,0.8)]", border: "border-[#ff4d00]/20", glow: "hover:shadow-[0_0_20px_rgba(255,77,0,0.3)]" },
    { label: "Resolved", value: resolved, color: "text-neon-green drop-shadow-[0_0_5px_rgba(0,255,102,0.8)]", border: "border-[#00ff66]/20", glow: "hover:shadow-[0_0_20px_rgba(0,255,102,0.3)]" },
    { label: "Active Vols", value: activeVols, color: "text-neon-purple drop-shadow-[0_0_5px_rgba(217,0,255,0.8)]", border: "border-[#d900ff]/20", glow: "hover:shadow-[0_0_20px_rgba(217,0,255,0.3)]" },
    { label: "Coverage", value: `${coverage}%`, color: "text-neon-cyan drop-shadow-[0_0_5px_rgba(0,243,255,0.8)]", border: "border-[#00f3ff]/20", glow: "hover:shadow-[0_0_20px_rgba(0,243,255,0.3)]" },
  ];

  return (
    <div className="flex w-full gap-4 mb-4 z-10 relative">
      {cards.map((c, i) => (
        <div key={i} className={`flex-1 hud-panel ${c.border} rounded-xl p-4 shadow-md flex flex-col items-center justify-center transition-all duration-300 ${c.glow} hover:-translate-y-1`}>
          <span className="text-xs text-slate-400 uppercase tracking-widest font-mono font-semibold">{c.label}</span>
          <span className={`text-3xl font-black mt-2 font-mono ${c.color}`}>{c.value}</span>
        </div>
      ))}
    </div>
  );
}
