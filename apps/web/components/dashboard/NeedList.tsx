"use client";

import React, { useState } from "react";
import { NeedNode } from "../../lib/types";

export default function NeedList({ needs, onNeedClick }: { needs: NeedNode[], onNeedClick: (need: NeedNode) => void }) {
  const [filter, setFilter] = useState("ALL");

  const filtered = needs.filter(n => filter === "ALL" || n.status === filter)
                        .sort((a, b) => b.urgency_score - a.urgency_score);

  return (
    <div className="flex flex-col h-full hud-panel rounded-xl overflow-hidden shadow-[0_0_15px_rgba(0,0,0,0.8)] mt-4 flex-1">
      <div className="p-4 border-b border-neon-cyan/20 flex justify-between items-center bg-black/40">
        <h2 className="font-semibold text-white tracking-widest text-sm uppercase">Live Intel</h2>
        <select 
          className="bg-slate-900 text-xs px-2 py-1 rounded text-neon-cyan border border-neon-cyan/30 outline-none focus:ring-1 ring-neon-cyan font-mono"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="ALL">All Status</option>
          <option value="PENDING">Pending</option>
          <option value="RESOLVED">Resolved</option>
        </select>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2">
        {filtered.map(need => (
          <div 
            key={need.id} 
            onClick={() => onNeedClick(need)}
            className="group cursor-pointer p-3 mb-2 rounded-lg bg-black/40 hover:bg-neon-cyan/10 transition-all duration-300 border border-transparent hover:border-neon-cyan/50 hover:shadow-[inset_0_0_10px_rgba(0,243,255,0.2)] hover:translate-x-1"
          >
            <div className="flex justify-between items-start mb-1">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full shadow-[0_0_5px_currentColor] ${need.urgency_score >= 0.8 ? 'bg-neon-red text-neon-red animate-pulse' : need.urgency_score >= 0.5 ? 'bg-neon-orange text-neon-orange' : 'bg-neon-green text-neon-green'}`}></div>
                <span className="font-bold text-slate-200 text-sm tracking-wide">{need.type}</span>
              </div>
              <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${need.status === 'RESOLVED' ? 'bg-neon-green/20 text-neon-green' : 'bg-slate-800 text-neon-cyan'}`}>{need.status}</span>
            </div>
            <p className="text-xs text-slate-400 line-clamp-2 mt-2 leading-relaxed">{need.description}</p>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="p-4 text-center text-sm text-slate-500">No reports found.</div>
        )}
      </div>
    </div>
  );
}
