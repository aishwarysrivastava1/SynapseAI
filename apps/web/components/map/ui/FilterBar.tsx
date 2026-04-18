"use client";

import React from "react";
import { FilterType } from "../hooks/useMapController";

const PILLS: { key: FilterType; label: string }[] = [
  { key: "all",        label: "All"        },
  { key: "volunteers", label: "Volunteers" },
  { key: "resources",  label: "Resources"  },
  { key: "operations", label: "Operations" },
];

interface Props {
  filter: FilterType;
  setFilter: (f: FilterType) => void;
}

export default function FilterBar({ filter, setFilter }: Props) {
  return (
    <div
      className="absolute top-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1 px-2 py-1.5 rounded-full"
      style={{
        background:     "rgba(11,61,54,0.92)",
        backdropFilter: "blur(10px)",
        border:         "1px solid rgba(255,255,255,0.12)",
        boxShadow:      "0 8px 32px rgba(0,0,0,0.25)",
      }}
    >
      {PILLS.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => setFilter(key)}
          className="px-3 py-1 rounded-full text-[11px] font-semibold transition-all duration-150 whitespace-nowrap"
          style={
            filter === key
              ? { background: "#2A8256", color: "#ffffff" }
              : { background: "transparent", color: "rgba(255,255,255,0.5)" }
          }
          onMouseEnter={(e) => {
            if (filter !== key) (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.8)";
          }}
          onMouseLeave={(e) => {
            if (filter !== key) (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.5)";
          }}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
