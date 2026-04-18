"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  Plus, X, Sparkles, Trash2, UserCheck, Loader2, AlertCircle, ChevronDown, CheckCircle2,
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { api } from "../../../lib/ngo-api";
import { useNGOAuth } from "../../../lib/ngo-auth";

type Task = {
  id: string;
  title: string;
  description: string;
  required_skills: string[];
  priority: "low" | "medium" | "high";
  status: "open" | "in_progress" | "completed";
  deadline?: string;
};

type Volunteer = { id: string; email: string };

type RankedVol = {
  volunteer_id: string;
  name: string;
  email: string;
  score: number;
  matched_skills: string[];
};

const STATUS_META: Record<string, { label: string; color: string; borderColor: string }> = {
  open:        { label: "Open",        color: "bg-teal-50 text-teal-700 border-teal-200",     borderColor: "#2dd4bf" },
  in_progress: { label: "In Progress", color: "bg-amber-50 text-amber-700 border-amber-200",  borderColor: "#fbbf24" },
  completed:   { label: "Completed",   color: "bg-emerald-50 text-emerald-700 border-emerald-200", borderColor: "#34d399" },
};

const PRIORITY_COLOR: Record<string, string> = {
  high:   "bg-red-50 text-red-600 border-red-200",
  medium: "bg-amber-50 text-amber-600 border-amber-200",
  low:    "bg-gray-50 text-gray-400 border-gray-200",
};

function SkillChipInput({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  const [input, setInput] = useState("");
  const add = () => {
    const s = input.trim();
    if (s && !value.includes(s)) onChange([...value, s]);
    setInput("");
  };
  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }}
          placeholder="Add skill + Enter"
          className="flex-1 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-[#115E54]/50"
        />
        <button type="button" onClick={add} className="bg-[#115E54] text-white px-3 py-2 rounded-lg text-sm font-semibold hover:bg-[#0d4a42] transition-colors">Add</button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {value.map((s) => (
          <span key={s} className="flex items-center gap-1 bg-teal-50 text-teal-700 border border-teal-100 rounded-full px-2.5 py-1 text-xs font-medium">
            {s}
            <button type="button" onClick={() => onChange(value.filter((x) => x !== s))} className="hover:text-red-500"><X size={10} /></button>
          </span>
        ))}
      </div>
    </div>
  );
}

export default function TasksPage() {
  const { user, loading: authLoading } = useNGOAuth();
  const [tasks, setTasks]           = useState<Task[]>([]);
  const [volunteers, setVolunteers] = useState<Volunteer[]>([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [assignModal, setAssignModal] = useState<{ task: Task; ranked: RankedVol[] } | null>(null);
  const [matchLoading, setMatchLoading] = useState(false);
  const [assigning, setAssigning]   = useState<string | null>(null);
  const [deleting, setDeleting]     = useState<string | null>(null);
  const [completing, setCompleting] = useState<string | null>(null);

  const [form, setForm] = useState({ title: "", description: "", required_skills: [] as string[], priority: "medium", deadline: "" });
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(() => {
    if (!user) return;
    setLoading(true);
    Promise.all([
      api.ngoTasks(user.token, { status: statusFilter || undefined }),
      api.ngoVolunteers(user.token, { status: "active" }),
    ])
      .then(([t, v]) => { setTasks(t as Task[]); setVolunteers(v as Volunteer[]); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [user, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setSubmitting(true);
    try {
      await api.createTask(user.token, {
        title: form.title,
        description: form.description,
        required_skills: form.required_skills,
        priority: form.priority,
        deadline: form.deadline || undefined,
      } as any);
      setForm({ title: "", description: "", required_skills: [], priority: "medium", deadline: "" });
      setShowCreate(false);
      load();
    } catch (e: any) { setError(e.message); }
    finally { setSubmitting(false); }
  };

  const handleComplete = async (id: string) => {
    if (!user) return;
    setCompleting(id);
    try {
      await api.completeTask(user.token, id);
      load();
    } catch (e: any) { setError(e.message); }
    finally { setCompleting(null); }
  };

  const handleDelete = async (id: string) => {
    if (!user) return;
    setDeleting(id);
    try {
      await api.deleteTask(user.token, id);
      setTasks((prev) => prev.filter((t) => t.id !== id));
    } catch (e: any) { setError(e.message); }
    finally { setDeleting(null); }
  };

  const openAssign = async (task: Task) => {
    if (!user) return;
    setMatchLoading(true);
    try {
      const res = await api.aiMatch(user.token, task.id);
      setAssignModal({ task, ranked: res.ranked_volunteers });
    } catch (e: any) { setError(e.message); }
    finally { setMatchLoading(false); }
  };

  const handleAssign = async (taskId: string, volId: string) => {
    if (!user) return;
    setAssigning(volId);
    try {
      await api.assignTask(user.token, taskId, volId);
      setAssignModal(null);
      load();
    } catch (e: any) { setError(e.message); }
    finally { setAssigning(null); }
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
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="appearance-none bg-white border border-gray-200 rounded-xl px-3 pr-8 py-2 text-sm outline-none focus:border-[#115E54]/50 text-gray-700"
          >
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
          </select>
          <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>
        <motion.button
          onClick={() => setShowCreate(true)}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          className="ml-auto flex items-center gap-2 text-white px-4 py-2 rounded-xl text-sm font-semibold"
          style={{ background: "linear-gradient(135deg, #2A8256 0%, #48A15E 100%)" }}
        >
          <Plus size={14} /> New Task
        </motion.button>
      </div>

      {error && (
        <div className="rounded-xl px-4 py-3 flex items-center gap-3 text-sm text-red-300" style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.25)" }}>
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {/* Task list */}
      {loading ? (
        <div className="flex justify-center py-16"><Loader2 size={22} className="animate-spin text-[#48A15E]" /></div>
      ) : tasks.length === 0 ? (
        <motion.div
          whileHover={{ y: -2, borderColor: "#95C78F" }}
          className="rounded-2xl border border-gray-200 p-8 text-center text-sm text-gray-400"
          style={{ background: "linear-gradient(135deg, #F5F6F1 0%, #ffffff 100%)" }}
        >
          No tasks. Click &quot;New Task&quot; to create one.
        </motion.div>
      ) : (
        <div className="space-y-3">
          {tasks.map((task, i) => {
            const meta = STATUS_META[task.status] ?? STATUS_META.open;
            return (
              <motion.div
                key={task.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                whileHover={{ y: -3, boxShadow: "0 16px 36px rgba(42,130,86,0.15)", borderColor: "#95C78F" }}
                className="rounded-2xl border border-gray-200 overflow-hidden"
                style={{
                  background: "linear-gradient(135deg, #F5F6F1 0%, #ffffff 100%)",
                  borderLeft: `4px solid ${meta.borderColor}`,
                }}
              >
                <div className="px-5 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-semibold text-gray-800 text-sm">{task.title}</h3>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${meta.color}`}>
                          {meta.label}
                        </span>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${PRIORITY_COLOR[task.priority] ?? PRIORITY_COLOR.medium}`}>
                          {task.priority}
                        </span>
                      </div>
                      {task.description && (
                        <p className="text-xs text-gray-500 mt-1 line-clamp-2">{task.description}</p>
                      )}
                      <div className="flex flex-wrap gap-1 mt-2">
                        {task.required_skills.map((s) => (
                          <span key={s} className="text-[10px] text-[#2A8256] border border-[#2A8256]/20 rounded-full px-2 py-0.5" style={{ background: "rgba(42,130,86,0.08)" }}>{s}</span>
                        ))}
                      </div>
                      {task.deadline && (
                        <p className="text-[11px] text-gray-400 mt-1.5">Due: {new Date(task.deadline).toLocaleDateString()}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {task.status === "open" && (
                        <button
                          onClick={() => openAssign(task)}
                          disabled={matchLoading}
                          className="flex items-center gap-1.5 text-xs rounded-lg px-3 py-1.5 font-semibold transition-all disabled:opacity-50 text-[#2A8256]"
                          style={{ background: "rgba(42,130,86,0.1)", border: "1px solid rgba(42,130,86,0.2)" }}
                        >
                          {matchLoading ? <Loader2 size={11} className="animate-spin" /> : <Sparkles size={11} />}
                          Assign
                        </button>
                      )}
                      {task.status === "in_progress" && (
                        <button
                          onClick={() => handleComplete(task.id)}
                          disabled={completing === task.id}
                          className="flex items-center gap-1.5 text-xs rounded-lg px-3 py-1.5 font-semibold transition-all disabled:opacity-50 text-emerald-700"
                          style={{ background: "rgba(52,211,153,0.1)", border: "1px solid rgba(52,211,153,0.25)" }}
                        >
                          {completing === task.id ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />}
                          Complete
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(task.id)}
                        disabled={deleting === task.id}
                        className="text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg p-1.5 transition-all"
                      >
                        {deleting === task.id ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                      </button>
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Create task modal */}
      <AnimatePresence>
        {showCreate && (
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
              className="bg-white rounded-2xl shadow-2xl w-full max-w-md"
            >
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
                <p className="text-sm font-bold text-gray-800">Create Task</p>
                <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600 p-1"><X size={16} /></button>
              </div>
              <form onSubmit={handleCreate} className="p-5 space-y-4">
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Title</label>
                  <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
                    className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#115E54]/50" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Description</label>
                  <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                    rows={2} className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-[#115E54]/50 resize-none" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Required Skills</label>
                  <SkillChipInput value={form.required_skills} onChange={(v) => setForm({ ...form, required_skills: v })} />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Priority</label>
                  <div className="relative">
                    <select
                      value={form.priority}
                      onChange={(e) => setForm({ ...form, priority: e.target.value })}
                      className="appearance-none w-full bg-gray-50 border border-gray-200 rounded-lg px-3 pr-8 py-2.5 text-sm outline-none focus:border-[#115E54]/50"
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                    <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">Deadline <span className="text-gray-300">(optional)</span></label>
                  <input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })}
                    className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#115E54]/50" />
                </div>
                <motion.button
                  type="submit"
                  disabled={submitting}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full text-white py-2.5 rounded-xl text-sm font-bold disabled:opacity-60 flex items-center justify-center gap-2"
                  style={{ background: "linear-gradient(135deg, #2A8256 0%, #48A15E 100%)" }}
                >
                  {submitting && <Loader2 size={14} className="animate-spin" />}
                  Create Task
                </motion.button>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Assign modal */}
      <AnimatePresence>
        {assignModal && (
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
                  <p className="text-xs text-gray-400 mt-0.5">{assignModal.task.title}</p>
                </div>
                <button onClick={() => setAssignModal(null)} className="text-gray-400 hover:text-gray-600 p-1"><X size={16} /></button>
              </div>
              <div className="p-5 max-h-[400px] overflow-y-auto space-y-2">
                {assignModal.ranked.length === 0 ? (
                  <p className="text-center text-sm text-gray-400 py-6">No matching volunteers available.</p>
                ) : assignModal.ranked.map((r, i) => (
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
                      <div className="flex gap-1 mt-0.5 flex-wrap">
                        {r.matched_skills.map((s) => (
                          <span key={s} className="text-[10px] bg-teal-50 text-teal-700 border border-teal-100 rounded-full px-1.5 py-0.5">{s}</span>
                        ))}
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-sm font-bold text-[#2A8256]">{Math.round(r.score * 100)}%</div>
                    </div>
                    <button
                      onClick={() => handleAssign(assignModal.task.id, r.volunteer_id)}
                      disabled={assigning === r.volunteer_id}
                      className="flex items-center gap-1.5 text-xs text-white rounded-lg px-3 py-1.5 font-semibold transition-all disabled:opacity-50 shrink-0"
                      style={{ background: "linear-gradient(135deg, #2A8256 0%, #48A15E 100%)" }}
                    >
                      {assigning === r.volunteer_id ? <Loader2 size={11} className="animate-spin" /> : <UserCheck size={11} />}
                      Assign
                    </button>
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
