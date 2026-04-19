"use client";

import React from "react";
import { type User } from "firebase/auth";

type Props = {
  user: User | null;
  onLogout: () => void;
};

export default function UserProfile({ user, onLogout }: Props) {
  if (!user) return null;

  const letter = (user.displayName || user.email || "?")[0].toUpperCase();

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      {user.photoURL ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={user.photoURL}
          alt={user.displayName || ""}
          referrerPolicy="no-referrer"
          style={{ width: 36, height: 36, borderRadius: "50%", objectFit: "cover" }}
        />
      ) : (
        <div style={{
          width: 36, height: 36, borderRadius: "50%",
          background: "linear-gradient(135deg, #2A8256, #48A15E)",
          display: "flex", alignItems: "center", justifyContent: "center",
          color: "#fff", fontSize: 15, fontWeight: 700,
        }}>
          {letter}
        </div>
      )}
      <div style={{ flex: 1, minWidth: 0 }}>
        {user.displayName && (
          <p style={{ color: "#fff", fontSize: 14, fontWeight: 600, margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {user.displayName}
          </p>
        )}
        <p style={{ color: "rgba(255,255,255,0.45)", fontSize: 12, margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {user.email}
        </p>
      </div>
      <button
        onClick={onLogout}
        style={{
          padding: "6px 14px", borderRadius: 8,
          border: "1px solid rgba(255,255,255,0.15)",
          background: "rgba(255,255,255,0.07)",
          color: "rgba(255,255,255,0.7)", fontSize: 12, fontWeight: 600,
          cursor: "pointer", transition: "all 0.2s", fontFamily: "inherit",
        }}
        onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.12)"; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.07)"; }}
      >
        Log out
      </button>
    </div>
  );
}
