"use client";

import React, { useEffect, useState } from "react";
import { X, Loader2, AlertCircle, CheckCircle2, Award } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { api } from "../../../lib/ngo-api";
import { useNGOAuth } from "../../../lib/ngo-auth";

const BADGES = [
  { id: "starter",     label: "Starter",     desc: "First task completed",    threshold: 1,  emoji: "🌱" },
  { id: "contributor", label: "Contributor",  desc: "5 tasks completed",       threshold: 5,  emoji: "⭐" },
  { id: "champion",    label: "Champion",     desc: "15 tasks completed",      threshold: 15, emoji: "🏆" },
  { id: "legend",      label: "Legend",       desc: "30 tasks completed",      threshold: 30, emoji: "🔥" },
];

const DAYS = ["mon","tue","wed","thu","fri","sat","sun"] as const;
const DAY_LABELS: Record<string, string> = {
  mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun",
};

export default function VolProfilePage() {
  const { user, loading: authLoading } = useNGOAuth();
  const [skills, setSkills]             = useState<string[]>([]);
  const [availability, setAvail]        = useState<Record<string, boolean>>({});
  const [performance, setPerformance]   = useState<{ completed_tasks: number; total_assigned: number; performance_score: number } | null>(null);
  const [loading, setLoading]       = useState(true);
  const [saving, setSaving]         = useState(false);
  const [error, setError]           = useState("");
  const [saved, setSaved]           = useState(false);
  const [skillInput, setSkillInput] = useState("");

  useEffect(() => {
    if (!user) return;
    api.volProfile(user.token)
      .then((p: any) => {
        setSkills(p.skills ?? []);
        setAvail(p.availability ?? {});
        if (p.performance_score !== undefined) {
          setPerformance({ completed_tasks: p.completed_tasks ?? 0, total_assigned: p.total_assigned ?? 0, performance_score: p.performance_score ?? 0 });
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [user]);

  const addSkill = () => {
    const s = skillInput.trim();
    if (s && !skills.includes(s)) setSkills([...skills, s]);
    setSkillInput("");
  };

  const toggleDay = (day: string) => {
    setAvail((prev) => ({ ...prev, [day]: !prev[day] }));
  };

  const handleSave = async () => {
    if (!user) return;
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      await api.updateVolProfile(user.token, { skills, availability });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  };

  if (authLoading || loading) return (
    <div className="flex items-center justify-center h-64">
      <Loader2 size={22} className="animate-spin text-[#48A15E]" />
    </div>
  );
  if (!user) return null;

  const activeDayCount = DAYS.filter((d) => availability[d]).length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="p-6 space-y-6 max-w-xl"
    >
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="rounded-xl px-4 py-3 flex items-center gap-3 text-sm text-red-300"
            style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.25)" }}
          >
            <AlertCircle size={14} /> {error}
          </motion.div>
        )}
        {saved && (
          <motion.div
            initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="rounded-xl px-4 py-3 flex items-center gap-3 text-sm text-emerald-300"
            style={{ background: "rgba(52,211,153,0.1)", border: "1px solid rgba(52,211,153,0.25)" }}
          >
            <CheckCircle2 size={14} /> Profile saved successfully.
          </motion.div>
        )}
      </AnimatePresence>

      {/* Skills section */}
      <motion.div
        whileHover={{ y: -2, boxShadow: "0 12px 32px rgba(42,130,86,0.12)", borderColor: "#95C78F" }}
        className="rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4"
        style={{ background: "linear-gradient(135deg, #F5F6F1 0%, #ffffff 100%)" }}
      >
        <h2 className="text-sm font-semibold text-gray-700">Skills</h2>
        <div className="flex gap-2">
          <input
            value={skillInput}
            onChange={(e) => setSkillInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addSkill(); } }}
            placeholder="Add skill + Enter"
            className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-[#115E54]/50"
          />
          <motion.button
            type="button"
            onClick={addSkill}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.96 }}
            className="text-white px-4 py-2.5 rounded-xl text-sm font-semibold"
            style={{ background: "linear-gradient(135deg, #2A8256 0%, #48A15E 100%)" }}
          >
            Add
          </motion.button>
        </div>
        <div className="flex flex-wrap gap-2 min-h-[28px]">
          {skills.length === 0 && <p className="text-xs text-gray-300">No skills added yet.</p>}
          {skills.map((s) => (
            <motion.span
              key={s}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="flex items-center gap-1.5 text-[#2A8256] border border-[#2A8256]/20 rounded-full px-3 py-1.5 text-xs font-medium"
              style={{ background: "rgba(42,130,86,0.08)" }}
            >
              {s}
              <button
                type="button"
                onClick={() => setSkills(skills.filter((x) => x !== s))}
                className="hover:text-red-500 transition-colors"
              >
                <X size={11} />
              </button>
            </motion.span>
          ))}
        </div>
      </motion.div>

      {/* Availability section */}
      <motion.div
        whileHover={{ y: -2, boxShadow: "0 12px 32px rgba(42,130,86,0.12)", borderColor: "#95C78F" }}
        className="rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4"
        style={{ background: "linear-gradient(135deg, #F5F6F1 0%, #ffffff 100%)" }}
      >
        <h2 className="text-sm font-semibold text-gray-700">Weekly Availability</h2>
        <div className="grid grid-cols-7 gap-1.5">
          {DAYS.map((d) => (
            <motion.button
              key={d}
              type="button"
              onClick={() => toggleDay(d)}
              whileTap={{ scale: 0.88 }}
              transition={{ type: "spring", stiffness: 500, damping: 20 }}
              className={`flex flex-col items-center gap-1 py-2.5 rounded-xl border text-xs font-semibold transition-colors ${
                availability[d]
                  ? "text-white border-transparent"
                  : "bg-gray-50 border-gray-200 text-gray-400 hover:border-[#2A8256]/40 hover:text-[#2A8256]"
              }`}
              style={availability[d] ? { background: "linear-gradient(135deg, #2A8256 0%, #48A15E 100%)" } : {}}
            >
              <span>{DAY_LABELS[d]}</span>
              <div className={`w-1.5 h-1.5 rounded-full ${availability[d] ? "bg-white/60" : "bg-gray-200"}`} />
            </motion.button>
          ))}
        </div>
        <p className="text-[10px] text-gray-400">
          {activeDayCount} day{activeDayCount !== 1 ? "s" : ""} available per week
        </p>
      </motion.div>

      {/* Performance stats */}
      {performance && (
        <motion.div
          whileHover={{ y: -2, boxShadow: "0 12px 32px rgba(42,130,86,0.12)", borderColor: "#95C78F" }}
          className="rounded-2xl border border-gray-200 shadow-sm p-5"
          style={{ background: "linear-gradient(135deg, #F5F6F1 0%, #ffffff 100%)" }}
        >
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Performance</h2>
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center">
              <div className="text-xl font-bold" style={{ color: "#2A8256" }}>{performance.performance_score.toFixed(0)}%</div>
              <div className="text-[10px] text-gray-400 mt-0.5">Score</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-gray-800">{performance.completed_tasks}</div>
              <div className="text-[10px] text-gray-400 mt-0.5">Completed</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-gray-800">{performance.total_assigned}</div>
              <div className="text-[10px] text-gray-400 mt-0.5">Total Assigned</div>
            </div>
          </div>
          <div className="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${performance.performance_score}%` }}
              transition={{ duration: 0.8, ease: "easeOut", delay: 0.2 }}
              className="h-full rounded-full"
              style={{ background: "linear-gradient(90deg, #2A8256 0%, #48A15E 100%)" }}
            />
          </div>
        </motion.div>
      )}

      {/* Badges */}
      <motion.div
        whileHover={{ y: -2, boxShadow: "0 12px 32px rgba(42,130,86,0.12)", borderColor: "#95C78F" }}
        className="rounded-2xl border border-gray-200 shadow-sm p-5"
        style={{ background: "linear-gradient(135deg, #F5F6F1 0%, #ffffff 100%)" }}
      >
        <div className="flex items-center gap-2 mb-4">
          <Award size={14} className="text-[#2A8256]" />
          <h2 className="text-sm font-semibold text-gray-700">Achievements</h2>
          {performance && (
            <span className="ml-auto text-[10px] text-gray-400">{performance.completed_tasks} task{performance.completed_tasks !== 1 ? "s" : ""} done</span>
          )}
        </div>
        <div className="grid grid-cols-4 gap-2">
          {BADGES.map((b) => {
            const unlocked = (performance?.completed_tasks ?? 0) >= b.threshold;
            return (
              <motion.div
                key={b.id}
                whileHover={{ scale: unlocked ? 1.06 : 1 }}
                className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border text-center transition-all ${
                  unlocked
                    ? "border-[#2A8256]/30 bg-gradient-to-b from-emerald-50 to-white"
                    : "border-gray-100 bg-gray-50 opacity-40 grayscale"
                }`}
              >
                <span className="text-xl">{b.emoji}</span>
                <p className="text-[10px] font-bold text-gray-700">{b.label}</p>
                <p className="text-[9px] text-gray-400 leading-tight">{b.desc}</p>
                {unlocked && <div className="w-1.5 h-1.5 rounded-full bg-[#48A15E]" />}
              </motion.div>
            );
          })}
        </div>
      </motion.div>

      <motion.button
        onClick={handleSave}
        disabled={saving}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.98 }}
        className="w-full text-white py-3 rounded-xl text-sm font-bold disabled:opacity-60 flex items-center justify-center gap-2"
        style={{ background: "linear-gradient(135deg, #2A8256 0%, #48A15E 100%)" }}
      >
        {saving && <Loader2 size={14} className="animate-spin" />}
        Save Profile
      </motion.button>
    </motion.div>
  );
}
