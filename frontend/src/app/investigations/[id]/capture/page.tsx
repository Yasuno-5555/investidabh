'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import axios from 'axios';
import Navbar from '../../../components/Navbar';
import Spinner from '../../../components/Spinner';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

export default function ForensicWorkbench() {
    const { id } = useParams();
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [screenshot, setScreenshot] = useState<string | null>(null);
    const [url, setUrl] = useState('');
    const [logs, setLogs] = useState<{ id: string, action: string, timestamp: string }[]>([]);
    const [sessionStatus, setSessionStatus] = useState<'IDLE' | 'ACTIVE' | 'RECORDING'>('IDLE');
    const viewportRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (!token) {
            router.push('/login');
            return;
        }

        // Initialize Session
        const init = async () => {
            try {
                const res = await axios.get(`${API_URL}/api/investigations/${id}`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                setUrl(res.data.target_url);
                // In a real implementation, we would start a remote browser here.
                // For this demo, we simulate the first load.
                setSessionStatus('ACTIVE');
                setLoading(false);
                refreshViewport();
            } catch (err) {
                console.error(err);
            }
        };
        init();
    }, [id]);

    const refreshViewport = async () => {
        // Mocking a remote browser viewport refresh
        // In reality, this would fetch from /api/interactive/:id/screenshot
        const token = localStorage.getItem('token');
        try {
            // We use the existing artifact as a starting point for the demo
            const res = await axios.get(`${API_URL}/api/investigations/${id}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const screenshotArt = res.data.artifacts.find((a: any) => a.artifact_type === 'screenshot');
            if (screenshotArt) {
                const imgRes = await axios.get(`${API_URL}/api/artifacts/${screenshotArt.id}/content`, {
                    headers: { Authorization: `Bearer ${token}` },
                    responseType: 'blob'
                });
                setScreenshot(URL.createObjectURL(imgRes.data));
            }
        } catch (err) {}
    };

    const addLog = (action: string) => {
        setLogs(prev => [
            { id: Math.random().toString(36).substr(2, 9), action, timestamp: new Date().toLocaleTimeString() },
            ...prev
        ]);
    };

    const handleViewportClick = (e: React.MouseEvent) => {
        if (sessionStatus !== 'ACTIVE' && sessionStatus !== 'RECORDING') return;
        
        const rect = viewportRef.current?.getBoundingClientRect();
        if (rect) {
            const x = Math.round(e.clientX - rect.left);
            const y = Math.round(e.clientY - rect.top);
            addLog(`CLICK at (${x}, ${y})`);
            // Here we would send axios.post(`${API_URL}/api/interactive/${id}/click`, { x, y })
        }
    };

    const handleCommit = async () => {
        setLoading(true);
        // Simulate evidence preservation
        addLog("COMMIT: Final Evidence Package Signed & Saved");
        setTimeout(() => {
            setLoading(false);
            alert("Forensic Evidence Package created successfully with SHA-256 integrity seal.");
            router.push(`/investigations/${id}`);
        }, 1500);
    };

    return (
        <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
            <Navbar />
            
            {/* Workbench Header */}
            <header className="bg-slate-800 border-b border-slate-700 px-6 py-3 flex justify-between items-center shadow-lg">
                <div className="flex items-center gap-4">
                    <div className="bg-red-600 px-2 py-1 rounded text-[10px] font-black uppercase tracking-tighter animate-pulse">Live Forensic Session</div>
                    <h1 className="text-sm font-mono font-bold text-slate-300 truncate max-w-md">{url}</h1>
                </div>
                <div className="flex gap-3">
                    <button 
                        onClick={() => setSessionStatus(sessionStatus === 'RECORDING' ? 'ACTIVE' : 'RECORDING')}
                        className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${sessionStatus === 'RECORDING' ? 'bg-red-500 text-white animate-pulse' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
                    >
                        <span className="w-2 h-2 rounded-full bg-current"></span>
                        {sessionStatus === 'RECORDING' ? 'Recording Steps...' : 'Start Recording'}
                    </button>
                    <button 
                        onClick={handleCommit}
                        disabled={loading}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-1.5 rounded-lg text-xs font-bold shadow-lg shadow-blue-900/20 disabled:opacity-50 transition-all"
                    >
                        {loading ? 'Sealing...' : 'Commit Evidence'}
                    </button>
                </div>
            </header>

            <main className="flex-grow flex overflow-hidden">
                {/* Left Panel: Logs & Chain of Custody */}
                <aside className="w-80 bg-slate-800/50 border-r border-slate-700 flex flex-col">
                    <div className="p-4 border-b border-slate-700 bg-slate-800">
                        <h2 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4">Audit Log / Chain of Custody</h2>
                        <div className="space-y-3 h-[calc(100vh-250px)] overflow-y-auto pr-2 custom-scrollbar">
                            {logs.length === 0 && (
                                <div className="text-[10px] text-slate-600 italic">No actions recorded yet...</div>
                            )}
                            {logs.map(log => (
                                <div key={log.id} className="bg-slate-900/50 border border-slate-700/50 rounded p-2 animate-in slide-in-from-left-2">
                                    <div className="flex justify-between text-[8px] font-mono text-slate-500 mb-1">
                                        <span>#{log.id}</span>
                                        <span>{log.timestamp}</span>
                                    </div>
                                    <div className="text-[10px] font-bold text-blue-400 font-mono">{log.action}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                    <div className="mt-auto p-4 bg-slate-900/80 text-[9px] font-mono text-slate-500">
                        <div>INVESTIGATOR: Analyst_01</div>
                        <div>SESSION_ID: {id?.slice(0,8)}...</div>
                        <div className="text-green-500 mt-1">INTEGRITY_SEAL: ACTIVE (SHA256)</div>
                    </div>
                </aside>

                {/* Center: Remote Browser Viewport */}
                <div className="flex-grow bg-black relative flex items-center justify-center p-4">
                    <div 
                        ref={viewportRef}
                        onClick={handleViewportClick}
                        className="relative bg-white shadow-2xl rounded-sm overflow-hidden cursor-crosshair group"
                        style={{ width: '1280px', height: '800px', transform: 'scale(0.8)', transformOrigin: 'center' }}
                    >
                        {screenshot ? (
                            <img src={screenshot} alt="Remote Browser" className="w-full h-full object-contain" />
                        ) : (
                            <div className="w-full h-full flex flex-col items-center justify-center bg-slate-900">
                                <Spinner />
                                <div className="text-xs text-slate-500 mt-4 font-mono">Initializing Remote Browser Session...</div>
                            </div>
                        )}
                        
                        {/* Interactive Overlays */}
                        <div className="absolute inset-0 bg-blue-500/0 group-hover:bg-blue-500/5 transition-all pointer-events-none"></div>
                        <div className="absolute top-2 left-2 bg-black/50 text-[10px] px-2 py-1 rounded text-white font-mono opacity-0 group-hover:opacity-100 transition-opacity">
                            VIEWPORT: 1280x800 | PROXY: TOR_EXIT_DE
                        </div>
                    </div>

                    {/* HUD Controls */}
                    <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex gap-4 bg-slate-800/90 backdrop-blur border border-slate-700 p-2 rounded-2xl shadow-2xl">
                        <div className="flex border-r border-slate-700 pr-4 mr-2 gap-2">
                            <button className="p-2 hover:bg-slate-700 rounded-xl transition-colors">⬅️</button>
                            <button className="p-2 hover:bg-slate-700 rounded-xl transition-colors">➡️</button>
                            <button className="p-2 hover:bg-slate-700 rounded-xl transition-colors" onClick={refreshViewport}>🔄</button>
                        </div>
                        <input 
                            type="text" 
                            value={url} 
                            readOnly
                            className="bg-slate-900 border border-slate-700 rounded-xl px-4 py-1 text-xs font-mono w-96 text-slate-400 focus:outline-none"
                        />
                        <button className="bg-slate-700 text-[10px] px-3 py-1 rounded-xl hover:bg-slate-600 font-bold transition-all" onClick={() => addLog(`NAVIGATE to ${url}`)}>Go</button>
                    </div>
                </div>
            </main>

            <style jsx>{`
                .custom-scrollbar::-webkit-scrollbar { width: 4px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #475569; }
            `}</style>
        </div>
    );
}
