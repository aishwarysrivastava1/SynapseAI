"use client";

import React, { useState } from "react";
import { ingestDocument, ingestText } from "../../lib/api";
import { UploadCloud, Type } from "lucide-react"; // Corrected icon imports

export default function FileUpload({ onUploadSuccess }: { onUploadSuccess: () => void }) {
  const [loading, setLoading] = useState(false);
  const [text, setText] = useState("");
  const [mode, setMode] = useState<"file" | "text">("text");

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    setLoading(true);
    try {
      await ingestDocument(e.target.files[0]);
      onUploadSuccess();
    } catch (err) {
      alert("Upload failed.");
    } finally {
      setLoading(false);
    }
  };

  const submitText = async () => {
    if (!text) return;
    setLoading(true);
    try {
      await ingestText(text);
      setText("");
      onUploadSuccess();
    } catch (err) {
      alert("Submission failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg w-full">
      <div className="flex gap-2 mb-3 bg-slate-950 p-1 rounded-lg w-max">
        <button 
          onClick={() => setMode("text")} 
          className={`px-3 py-1 text-xs rounded font-medium transition-colors ${mode === 'text' ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-white'}`}
        >
          Text Report
        </button>
        <button 
          onClick={() => setMode("file")} 
          className={`px-3 py-1 text-xs rounded font-medium transition-colors ${mode === 'file' ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-white'}`}
        >
          Photo/PDF
        </button>
      </div>

      {mode === "text" ? (
        <div className="flex flex-col gap-2">
          <textarea 
            className="bg-slate-800 border bg-transparent border-slate-700 rounded-lg p-2 text-sm text-slate-200 outline-none focus:border-cyan-500 h-20 resize-none"
            placeholder="Type field report here..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button 
            disabled={loading || !text}
            onClick={submitText}
            className="bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 text-white text-xs font-bold py-2 rounded-lg transition-colors"
          >
            {loading ? "Processing..." : "Submit Report"}
          </button>
        </div>
      ) : (
        <div className="border-2 border-dashed border-slate-700 rounded-lg p-4 text-center hover:border-cyan-500 transition-colors cursor-pointer relative h-28 flex flex-col justify-center items-center">
          <input 
            type="file" 
            className="absolute inset-0 opacity-0 cursor-pointer" 
            onChange={handleFileChange}
            disabled={loading}
          />
          <div className="text-slate-400 flex flex-col items-center">
             {loading ? <span className="animate-pulse">Analyzing...</span> : "Drag & Drop or Click to Upload"}
          </div>
        </div>
      )}
    </div>
  );
}
