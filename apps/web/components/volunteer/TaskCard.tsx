"use client";

import React from "react";
import { FirestoreTask } from "../../lib/types";

export default function TaskCard({ task, onClaim }: { task: FirestoreTask; onClaim?: (id: string) => void }) {
  const urgencyColor = task.xpReward > 50 ? "bg-red-500" : task.xpReward > 20 ? "bg-orange-500" : "bg-green-500";

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 mb-4 shadow-lg active:scale-[0.98] transition-transform">
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${urgencyColor} animate-pulse`}></div>
          <h3 className="font-bold text-white text-lg">{task.title}</h3>
        </div>
        <span className="bg-cyan-900/50 text-cyan-400 text-xs font-bold px-2 py-1 rounded-full border border-cyan-800">
          +{task.xpReward} XP
        </span>
      </div>
      
      <p className="text-slate-400 text-sm mb-4 line-clamp-2">{task.description}</p>
      
      <div className="flex justify-between items-center mt-4">
        <span className="bg-slate-900 text-slate-300 text-xs px-2 py-1 rounded">
          {task.requiredSkill}
        </span>
        
        {task.status === "OPEN" && onClaim && (
          <button 
            onClick={() => onClaim(task.id)}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold py-1.5 px-4 rounded-lg transition-colors shadow-[0_0_15px_rgba(79,70,229,0.3)]">
            Claim Task
          </button>
        )}
        {task.status !== "OPEN" && (
           <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">{task.status}</span>
        )}
      </div>
    </div>
  );
}
