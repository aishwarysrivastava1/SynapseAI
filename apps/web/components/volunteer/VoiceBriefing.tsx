"use client";

interface VoiceBriefingProps {
  taskTitle: string;
  taskDescription: string;
  taskLocation: string;
  language?: string; // BCP 47 language tag: "hi-IN", "en-US", "ta-IN"
}

export function VoiceBriefing({ taskTitle, taskDescription, taskLocation, language = "en-US" }: VoiceBriefingProps) {
  const speak = () => {
    if (!("speechSynthesis" in window)) {
      alert("Voice not supported in this browser");
      return;
    }
    window.speechSynthesis.cancel(); // Stop any ongoing speech
    const text = `New task assigned: ${taskTitle}. ${taskDescription}. Location: ${taskLocation}.`;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = language;
    utterance.rate = 0.9;
    window.speechSynthesis.speak(utterance);
  };

  return (
    <button
      onClick={speak}
      className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
    >
      🔊 Listen to Briefing
    </button>
  );
}
