"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../lib/ngo-api";
import { useNGOAuth } from "../../lib/ngo-auth";
import { Building2, Users, Eye, EyeOff, Loader2 } from "lucide-react";
import { motion } from "motion/react";

type Tab = "ngo" | "volunteer";

export default function RegisterPage() {
  const router  = useRouter();
  const { setUser } = useNGOAuth();
  const [tab, setTab]   = useState<Tab>("ngo");
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const [showPwd, setShowPwd] = useState(false);

  // Shared fields
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  // NGO fields
  const [ngoName, setNgoName]   = useState("");
  const [ngoDesc, setNgoDesc]   = useState("");
  // Volunteer fields
  const [inviteCode, setInviteCode] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (tab === "ngo") {
        const signup = await api.signup({ email, password, role: "ngo_admin" });
        const ngoRes = await api.createNGO(signup.token, { name: ngoName, description: ngoDesc });
        localStorage.setItem("ngo_token", ngoRes.token);
        document.cookie = `ngo_token=${ngoRes.token}; path=/; max-age=${60 * 60 * 24}`;
        const p = JSON.parse(atob(ngoRes.token.split(".")[1]));
        setUser({ user_id: p.sub, role: "ngo_admin", ngo_id: p.ngo_id, email, token: ngoRes.token });
        router.push("/ngo/dashboard");
      } else {
        const signup = await api.signup({ email, password, role: "volunteer", invite_code: inviteCode });
        localStorage.setItem("ngo_token", signup.token);
        document.cookie = `ngo_token=${signup.token}; path=/; max-age=${60 * 60 * 24}`;
        const p = JSON.parse(atob(signup.token.split(".")[1]));
        setUser({ user_id: p.sub, role: "volunteer", ngo_id: p.ngo_id, email, token: signup.token });
        router.push("/vol/dashboard");
      }
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = { background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.12)" };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ background: "radial-gradient(ellipse at 50% 0%, #115E54 0%, #0B3D36 50%, #072921 100%)" }}
    >
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-[#2A8256]/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-[#48A15E]/8 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ y: 30, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="w-full max-w-md relative"
      >
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8 justify-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo/logo-icon.png" alt="logo" className="h-10 w-10 object-contain" />
          <div>
            <h1 className="text-lg font-bold text-white leading-tight">Sanchaalan Saathi</h1>
            <p className="text-xs text-white/40">Smart Resource Allocation Platform</p>
          </div>
        </div>

        <div
          className="rounded-2xl overflow-hidden"
          style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)", backdropFilter: "blur(20px)" }}
        >
          {/* Tab toggle */}
          <div className="flex border-b" style={{ borderColor: "rgba(255,255,255,0.08)" }}>
            {(["ngo", "volunteer"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => { setTab(t); setError(""); }}
                className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-sm font-semibold transition-all ${
                  tab === t
                    ? "text-white"
                    : "text-white/35 hover:text-white/60"
                }`}
                style={tab === t ? { background: "linear-gradient(135deg, #2A8256 0%, #48A15E 100%)" } : {}}
              >
                {t === "ngo" ? <Building2 size={15} /> : <Users size={15} />}
                {t === "ngo" ? "Create NGO" : "Join as Volunteer"}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            <p className="text-xs text-white/35 -mt-1 mb-2">
              {tab === "ngo"
                ? "Register your NGO and become an admin coordinator."
                : "Join an NGO using your invite code."}
            </p>

            <div>
              <label className="text-xs font-medium text-white/60 block mb-1">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/30 outline-none"
                style={inputStyle}
              />
            </div>

            <div>
              <label className="text-xs font-medium text-white/60 block mb-1">Password</label>
              <div className="relative">
                <input
                  type={showPwd ? "text" : "password"}
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min 8 characters"
                  className="w-full rounded-lg px-3 py-2.5 pr-10 text-sm text-white placeholder-white/30 outline-none"
                  style={inputStyle}
                />
                <button
                  type="button"
                  onClick={() => setShowPwd((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60"
                >
                  {showPwd ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            {tab === "ngo" && (
              <>
                <div>
                  <label className="text-xs font-medium text-white/60 block mb-1">NGO Name</label>
                  <input
                    type="text"
                    required
                    minLength={2}
                    value={ngoName}
                    onChange={(e) => setNgoName(e.target.value)}
                    placeholder="e.g. Green Earth Foundation"
                    className="w-full rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/30 outline-none"
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-white/60 block mb-1">
                    Description <span className="text-white/20">(optional)</span>
                  </label>
                  <textarea
                    value={ngoDesc}
                    onChange={(e) => setNgoDesc(e.target.value)}
                    placeholder="What does your NGO do?"
                    rows={2}
                    className="w-full rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 outline-none resize-none"
                    style={inputStyle}
                  />
                </div>
              </>
            )}

            {tab === "volunteer" && (
              <div>
                <label className="text-xs font-medium text-white/60 block mb-1">NGO Invite Code</label>
                <input
                  type="text"
                  required
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                  placeholder="e.g. AB3K7XPQ"
                  maxLength={16}
                  className="w-full rounded-lg px-3 py-2.5 text-sm text-white font-mono placeholder-white/30 outline-none tracking-widest"
                  style={inputStyle}
                />
                <p className="text-[10px] text-white/25 mt-1">Ask your NGO coordinator for the invite code.</p>
              </div>
            )}

            {error && (
              <p className="text-xs text-red-300 rounded-lg px-3 py-2" style={{ background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.25)" }}>
                {error}
              </p>
            )}

            <motion.button
              type="submit"
              disabled={loading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
              className="w-full py-2.5 rounded-xl text-sm font-bold text-white disabled:opacity-60 flex items-center justify-center gap-2 mt-2"
              style={{ background: "linear-gradient(135deg, #2A8256 0%, #48A15E 100%)" }}
            >
              {loading && <Loader2 size={14} className="animate-spin" />}
              {tab === "ngo" ? "Create NGO Account" : "Join NGO"}
            </motion.button>

            <p className="text-center text-xs text-white/30 pt-1">
              Already have an account?{" "}
              <a href="/login-ngo" className="text-[#95C78F] font-semibold hover:underline">
                Sign in
              </a>
            </p>
          </form>
        </div>
      </motion.div>
    </div>
  );
}
