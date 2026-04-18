"use client";

import React from "react";
import { motion } from "motion/react";
import { X, User, Zap, Package } from "lucide-react";
import { SelectionType } from "../hooks/useMapController";
import { VolunteerPin, OperationPin, ResourcePin } from "../data/dummyData";

interface Props {
  entity: SelectionType;
  onClose: () => void;
}

const STATUS_BADGE: Record<string, string> = {
  available: "bg-emerald-100 text-emerald-700",
  busy:      "bg-amber-100 text-amber-700",
  critical:  "bg-red-100 text-red-700",
  active:    "bg-teal-100 text-teal-700",
  completed: "bg-slate-100 text-slate-500",
  medical:   "bg-red-50 text-red-600",
  food:      "bg-amber-50 text-amber-700",
  equipment: "bg-blue-50 text-blue-700",
};

function VolunteerPanel({ data }: { data: VolunteerPin }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-sm shrink-0"
          style={{ background: data.status === "available" ? "linear-gradient(135deg,#2A8256,#48A15E)" : "linear-gradient(135deg,#d97706,#fbbf24)" }}
        >
          {data.initials}
        </div>
        <div>
          <p className="text-sm font-bold text-gray-800">{data.name}</p>
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${STATUS_BADGE[data.status]}`}>
            {data.status}
          </span>
        </div>
      </div>
      {data.skills.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1.5">Skills</p>
          <div className="flex flex-wrap gap-1">
            {data.skills.map((s) => (
              <span key={s} className="text-[10px] px-2 py-0.5 rounded-full border border-[#2A8256]/20 text-[#2A8256]"
                style={{ background: "rgba(42,130,86,0.08)" }}>
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
      {data.assignedTo && (
        <p className="text-[10px] text-amber-600 flex items-center gap-1">
          <Zap size={10} /> Currently deployed to an operation
        </p>
      )}
      <button
        className="w-full text-white text-xs font-bold py-2.5 rounded-xl transition-opacity hover:opacity-90"
        style={{ background: "linear-gradient(135deg,#2A8256,#48A15E)" }}
      >
        Assign to Operation
      </button>
    </div>
  );
}

function OperationPanel({ data }: { data: OperationPin }) {
  const pct = data.needed > 0 ? Math.min((data.assigned / data.needed) * 100, 100) : 100;
  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm font-bold text-gray-800 leading-tight">{data.title}</p>
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full mt-1 inline-block ${STATUS_BADGE[data.status]}`}>
          {data.status}
        </span>
      </div>
      {data.description && (
        <p className="text-xs text-gray-500 leading-relaxed">{data.description}</p>
      )}
      <div>
        <div className="flex justify-between text-[10px] text-gray-400 mb-1.5">
          <span>Volunteers assigned</span>
          <span className="font-semibold text-gray-700">{data.assigned}/{data.needed}</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${pct}%`,
              background: data.status === "critical"
                ? "#ef4444"
                : "linear-gradient(90deg,#2A8256,#48A15E)",
            }}
          />
        </div>
      </div>
      <button
        className="w-full text-white text-xs font-bold py-2.5 rounded-xl transition-opacity hover:opacity-90"
        style={{ background: "linear-gradient(135deg,#2A8256,#48A15E)" }}
      >
        Deploy Resources
      </button>
    </div>
  );
}

function ResourcePanel({ data }: { data: ResourcePin }) {
  const icons: Record<string, string> = { medical: "💊", food: "🍱", equipment: "🔧" };
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl shrink-0 border border-[#2A8256]/20"
          style={{ background: "rgba(42,130,86,0.08)" }}
        >
          {icons[data.type] ?? "📦"}
        </div>
        <div>
          <p className="text-sm font-bold text-gray-800 leading-tight">{data.title}</p>
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full mt-0.5 inline-block ${STATUS_BADGE[data.type]}`}>
            {data.type}
          </span>
        </div>
      </div>
      <div className="bg-gray-50 rounded-xl px-4 py-3 flex items-center justify-between border border-gray-100">
        <p className="text-xs text-gray-500">Stock available</p>
        <p className="text-lg font-bold" style={{ color: data.stock > 100 ? "#2A8256" : "#d97706" }}>
          {data.stock}
        </p>
      </div>
      <button
        className="w-full text-white text-xs font-bold py-2.5 rounded-xl transition-opacity hover:opacity-90"
        style={{ background: "linear-gradient(135deg,#2A8256,#48A15E)" }}
      >
        Allocate Resource
      </button>
    </div>
  );
}

export default function EntityDetailPanel({ entity, onClose }: Props) {
  if (!entity) return null;

  return (
    <motion.div
      initial={{ x: 100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 100, opacity: 0 }}
      transition={{ type: "spring", stiffness: 340, damping: 28 }}
      className="absolute right-4 top-16 w-72 rounded-2xl p-5 z-20"
      style={{
        background: "#F5F6F1",
        boxShadow:  "0 24px 60px rgba(0,0,0,0.22)",
        border:     "1px solid rgba(0,0,0,0.06)",
      }}
    >
      <button
        onClick={onClose}
        className="absolute top-3.5 right-3.5 text-gray-400 hover:text-gray-600 transition-colors"
      >
        <X size={15} />
      </button>

      <div className="mb-4 flex items-center gap-1.5 text-[10px] text-gray-400 uppercase tracking-wide font-semibold">
        {entity.type === "volunteer" && <><User size={10} /> Volunteer</>}
        {entity.type === "operation" && <><Zap size={10} className="text-red-500" /> Operation</>}
        {entity.type === "resource"  && <><Package size={10} className="text-[#2A8256]" /> Resource</>}
      </div>

      {entity.type === "volunteer" && <VolunteerPanel data={entity.data as VolunteerPin} />}
      {entity.type === "operation" && <OperationPanel data={entity.data as OperationPin} />}
      {entity.type === "resource"  && <ResourcePanel  data={entity.data as ResourcePin}  />}
    </motion.div>
  );
}
