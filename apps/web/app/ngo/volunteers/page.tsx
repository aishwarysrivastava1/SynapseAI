"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Search, UserX, Sparkles, X, Loader2, AlertCircle, ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { api } from "../../../lib/ngo-api";
import { useNGOAuth } from "../../../lib/ngo-auth";

type Volunteer = {
  id: string;
  email: string;
  skills: string[];
  availability: Record<string, boolean>;
  status: "active" | "inactive";
};

type RankedVol = {
  volunteer_id: string;
  name: string;
  email: string;
  score: number;
  matched_skills: string[];
  workload: number;
};

type Task = { id: string; title: string };

function AvailDots({ avail }: { avail: Record<string, boolean> }) {
  const days = ["mon","tue","wed","thu","fri","sat","sun"];
  return (
    <div className="flex gap-0.5">
      {days.map((d) => (
        <div
          key={d}
          title={d}
          className={`w-2.5 h-2.5 rounded-full ${avail?.[d] ? "bg-emerald-400" : "bg-gray-200"}`}
        />
      ))}
    </div>
  );
}

export default function VolunteersPage() {
  const { user, loading: authLoading } = useNGOAuth();
  const [volunteers, setVolunteers] = useState<Volunteer[]>([]);
  const [tasks, setTasks]           = useState<Task[]>([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState("");
  const [skillFilter, setSkillFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [matchModal, setMatchModal] = useState<{ taskId: string; taskTitle: string } | null>(null);
  const [ranked, setRanked]         = useState<RankedVol[]>([]);
  const [matchLoading, setMatchLoading] = useState(false);
  const [deactivating, setDeactivating] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!user) return;
    setLoading(true);
    Promise.all([
      api.ngoVolunteers(user.token, {
        skill: skillFilter || undefined,
        status: statusFilter || undefined,
      }),
      api.ngoTasks(user.token, { status: "open" }),
    ])
      .then(([vols, tsks]) => {
        setVolunteers(vols as Volunteer[]);
        setTasks(tsks as Task[]);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [user, skillFilter, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleDeactivate = async (id: string) => {
    if (!user) return;
    setDeactivating(id);
    try {
      await api.deactivateVolunteer(user.token, id);
      setVolunteers((prev) => prev.map((v) => v.id === id ? { ...v, status: "inactive" } : v));
    } catch (e: any) { setError(e.message); }
    finally { setDeactivating(null); }
  };

  const openMatch = async (taskId: string, taskTitle: string) => {
    if (!user) return;
    setMatchModal({ taskId, taskTitle });
    setMatchLoading(true);
    try {
      const res = await api.aiMatch(user.token, taskId);
      setRanked(res.ranked_volunteers);
    } catch (e: any) { setError(e.message); }
    finally { setMatchLoading(false); }
  };

  if (authLoading) return <div className="flex justify-center py-16"><Loader2 size={22} className="animate-spin text-[#48A15E]" /></div>;
  if (!user) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="p-6 space-y-5"
    >
      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[160px]">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            placeholder="Filter by skill…"
            value={skillFilter}
            onChange={(e) => setSkillFilter(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load()}
            className="w-full pl-8 pr-3 py-2 text-sm bg-white border border-gray-200 rounded-xl outline-none focus:border-[#115E54]/50"
          />
        </div>
        <div className="relative">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="appearance-none bg-white border border-gray-200 rounded-xl px-3 pr-8 py-2 text-sm outline-none text-gray-700"
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>
        {tasks.length > 0 && (
          <div className="relative">
            <select
              onChange={(e) => e.target.value && openMatch(e.target.value, tasks.find(t => t.id === e.target.value)?.title ?? "")}
              defaultValue=""
              className="appearance-none rounded-xl px-3 pr-8 py-2 text-xs font-semibold outline-none cursor-pointer text-white"
              style={{ background: "linear-gradient(135deg, #2A8256 0%, #48A15E 100%)" }}
            >
              <option value="" disabled>AI Match for task…</option>
              {tasks.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
            </select>
            <Sparkles size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-white/60 pointer-events-none" />
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-xl px-4 py-3 flex items-center gap-3 text-sm text-red-300" style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.25)" }}>
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-16"><Loader2 size={22} className="animate-spin text-[#48A15E]" /></div>
      ) : volunteers.length === 0 ? (
        <motion.div
          whileHover={{ y: -2, borderColor: "#95C78F" }}
          className="rounded-2xl border border-gray-200 p-8 text-center text-sm text-gray-400"
          style={{ background: "linear-gradient(135deg, #F5F6F1 0%, #ffffff 100%)" }}
        >
          No volunteers found. Share your invite code to onboard volunteers.
        </motion.div>
      ) : (
        <motion.div
          whileHover={{ y: -2, boxShadow: "0 12px 32px rgba(42,130,86,0.12)", borderColor: "#95C78F" }}
          className="rounded-2xl border border-gray-200 shadow-sm overflow-hidden"
          style={{ background: "linear-gradient(135deg, #F5F6F1 0%, #ffffff 100%)" }}
        >
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200/60">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">Volunteer</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">Skills</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">Availability</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {volunteers.map((v, i) => (
                <motion.tr
                  key={v.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.04 }}
                  className="border-b border-gray-100/60 last:border-0 hover:bg-[#2A8256]/5 transition-colors"
                >
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-800">{v.email.split("@")[0]}</p>
                    <p className="text-[11px] text-gray-400">{v.email}</p>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(v.skills ?? []).slice(0, 3).map((s) => (
                        <span key={s} className="text-[10px] text-[#2A8256] border border-[#2A8256]/20 rounded-full px-2 py-0.5" style={{ background: "rgba(42,130,86,0.08)" }}>{s}</span>
                      ))}
                      {(v.skills ?? []).length > 3 && (
                        <span className="text-[10px] text-gray-400">+{v.skills.length - 3}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3"><AvailDots avail={v.availability} /></td>
                  <td className="px-4 py-3">
                    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
                      v.status === "active"
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                        : "bg-gray-100 text-gray-500 border-gray-200"
                    }`}>
                      {v.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {v.status === "active" && (
                      <button
                        onClick={() => handleDeactivate(v.id)}
                        disabled={deactivating === v.id}
                        className="flex items-center gap-1 text-[11px] text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg px-2 py-1 transition-all disabled:opacity-50 ml-auto"
                      >
                        {deactivating === v.id ? <Loader2 size={11} className="animate-spin" /> : <UserX size={11} />}
                        Deactivate
                      </button>
                    )}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      )}

      {/* AI Match modal */}
      <AnimatePresence>
        {matchModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.92, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.92, opacity: 0 }}
              transition={{ type: "spring", stiffness: 400, damping: 28 }}
              className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden"
            >
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
                <div>
                  <div className="flex items-center gap-2">
                    <Sparkles size={14} className="text-[#2A8256]" />
                    <p className="text-sm font-bold text-gray-800">AI Volunteer Match</p>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">{matchModal.taskTitle}</p>
                </div>
                <button onClick={() => { setMatchModal(null); setRanked([]); }} className="text-gray-400 hover:text-gray-600 p-1">
                  <X size={16} />
                </button>
              </div>
              <div className="p-5 max-h-[420px] overflow-y-auto space-y-2">
                {matchLoading ? (
                  <div className="flex justify-center py-10"><Loader2 size={20} className="animate-spin text-[#2A8256]" /></div>
                ) : ranked.length === 0 ? (
                  <p className="text-center text-sm text-gray-400 py-8">No active volunteers with matching skills.</p>
                ) : ranked.map((r, i) => (
                  <motion.div
                    key={r.volunteer_id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center gap-3 rounded-xl px-4 py-3 border border-gray-100"
                    style={{ background: "linear-gradient(135deg, #F5F6F1 0%, #ffffff 100%)" }}
                  >
                    <div
                      className="w-7 h-7 rounded-full text-white text-xs font-bold flex items-center justify-center shrink-0"
                      style={{ background: "linear-gradient(135deg, #2A8256 0%, #48A15E 100%)" }}
                    >
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-800 truncate">{r.name}</p>
                      <p className="text-[11px] text-gray-400 truncate">{r.email}</p>
                      <div className="flex gap-1 mt-1 flex-wrap">
                        {r.matched_skills.map((s) => (
                          <span key={s} className="text-[10px] text-[#2A8256] border border-[#2A8256]/20 rounded-full px-1.5 py-0.5" style={{ background: "rgba(42,130,86,0.08)" }}>{s}</span>
                        ))}
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-base font-bold text-[#2A8256]">{Math.round(r.score * 100)}%</div>
                      <div className="text-[10px] text-gray-400">{r.workload} task{r.workload !== 1 ? "s" : ""}</div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
