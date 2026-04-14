"use client";

import React, { useRef, useState } from "react";
import { Camera, Upload, X } from "lucide-react";

export default function CameraCapture({ onCapture }: { onCapture: (file: File) => void }) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const handleCapture = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const f = e.target.files[0];
      setFile(f);
      setPreviewUrl(URL.createObjectURL(f));
    }
  };

  const handleConfirm = () => {
    if (file) {
      onCapture(file);
    }
  };

  const clear = () => {
    setPreviewUrl(null);
    setFile(null);
  };

  if (previewUrl) {
    return (
      <div className="flex flex-col items-center gap-4 bg-slate-900 border border-slate-700 p-4 rounded-xl shadow-2xl">
        <div className="relative w-full aspect-[3/4] rounded overflow-hidden">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={previewUrl} alt="Captured preview" className="object-cover w-full h-full" />
          <button onClick={clear} className="absolute top-2 right-2 bg-slate-900/50 p-2 rounded-full text-white backdrop-blur hover:bg-red-500/80 transition-colors">
            <X size={20} />
          </button>
        </div>
        <button onClick={handleConfirm} className="w-full bg-cyan-600 hover:bg-cyan-500 py-3 rounded-xl font-bold text-white shadow-lg transition-transform active:scale-[0.98]">
          Confirm Verification Photo
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="relative p-6 border-2 border-dashed border-slate-700 bg-slate-800 rounded-xl hover:border-cyan-500 hover:bg-slate-800/80 transition-all flex flex-col items-center justify-center cursor-pointer min-h-[200px]">
        <input 
          type="file" 
          accept="image/*" 
          capture="environment"
          onChange={handleCapture}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        <div className="bg-slate-700 p-4 rounded-full mb-3 shadow-[0_0_20px_rgba(0,0,0,0.3)]">
          <Camera size={32} className="text-cyan-400" />
        </div>
        <h3 className="font-semibold text-slate-200">Open Camera</h3>
        <p className="text-xs text-slate-500 mt-1">Take a live photo for verification</p>
      </div>
      
      <div className="relative p-4 border border-slate-700 bg-slate-900 rounded-xl flex items-center justify-center gap-2">
         <input 
          type="file" 
          accept="image/*" 
          onChange={handleCapture}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
         <Upload size={18} className="text-slate-400" />
         <span className="text-sm font-medium text-slate-300">Upload existing photo</span>
      </div>
    </div>
  );
}
