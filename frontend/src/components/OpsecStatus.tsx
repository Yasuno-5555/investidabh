'use client';

export default function OpsecStatus() {
    return (
        <div className="fixed bottom-0 left-0 right-0 bg-slate-900 text-[10px] text-slate-400 px-4 py-1 flex justify-between items-center z-[100] border-t border-slate-800 uppercase tracking-widest font-bold">
            <div className="flex gap-4">
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                    Gateway: Connected
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                    Network: Tor (Exit: DE)
                </span>
            </div>
            <div className="flex gap-4">
                <span>API Version: v0.1.0-alpha</span>
                <span className="text-slate-500">Workspace: Local-Dev</span>
            </div>
        </div>
    );
}
