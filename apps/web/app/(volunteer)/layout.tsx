export default function VolunteerLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col min-h-screen max-w-md mx-auto bg-slate-900 shadow-2xl overflow-hidden relative">
      <div className="flex-1 overflow-y-auto pb-16">
        {children}
      </div>
      
      {/* Mobile Bottom Nav */}
      <nav className="absolute bottom-0 w-full bg-slate-950 border-t border-slate-800 flex justify-around p-4 z-50">
        <a href="/feed" className="flex flex-col items-center text-slate-400 hover:text-cyan-400 transition-colors">
          <span className="text-xs mt-1 font-medium">Feed</span>
        </a>
        <a href="/profile" className="flex flex-col items-center text-slate-400 hover:text-cyan-400 transition-colors">
          <span className="text-xs mt-1 font-medium">Profile</span>
        </a>
      </nav>
    </div>
  );
}
