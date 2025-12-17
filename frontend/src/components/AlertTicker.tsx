'use client';

import { useEffect, useState } from 'react';

interface Alert {
    type: string;
    entity: string;
    entity_type: string;
    reason: string;
    details?: any;
    timestamp?: number;
}

export default function AlertTicker() {
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (!token) return;

        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';
        // Pass token in URL query param since EventSource doesn't support headers natively (or use fetch-based polyfill)
        // However, for security, using a library like `event-source-polyfill` is better to send Headers.
        // BUT, standard native EventSource does NOT support authorization headers.
        // For MVP, we'll try to append ?token=... or just handle it if Gateway accepts it (Gateway expects Header).
        // If Gateway expects Header, we MUST use a polyfill or fetch loop.
        // Let's implement a simple fetch-reader loop which acts like SSE but allows headers.

        // Actually, let's use the fetch API with ReadableStream for SSE consumption to support Auth Header.
        let active = true;

        const connect = async () => {
            try {
                const response = await fetch(`${API_URL}/api/alerts/stream`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (!response.ok) {
                    console.error("Alert stream failed", response.status);
                    return;
                }

                if (!response.body) return;
                setConnected(true);

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (active) {
                    const { value, done } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n\n');
                    buffer = lines.pop() || ''; // Keep incomplete part

                    for (const block of lines) {
                        const blockLines = block.split('\n');
                        let eventType = 'message';
                        let dataStr = '';

                        for (const line of blockLines) {
                            if (line.startsWith('event: ')) {
                                eventType = line.substring(7).trim();
                            } else if (line.startsWith('data: ')) {
                                dataStr = line.substring(6);
                            }
                        }

                        if (eventType === 'alert' && dataStr) {
                            try {
                                const data = JSON.parse(dataStr);
                                setAlerts(prev => [data, ...prev].slice(0, 5));
                            } catch (e) {
                                console.error("Alert parse error", e);
                            }
                        }
                    }
                }
            } catch (err) {
                console.error("SSE Error:", err);
                setConnected(false);
                // Retry?
                if (active) setTimeout(connect, 5000);
            }
        };

        connect();

        return () => { active = false; };
    }, []);

    if (alerts.length === 0) return null;

    return (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full">
            {alerts.map((alert, idx) => (
                <div key={idx} className="bg-red-900/90 text-white p-3 rounded-lg shadow-lg border-l-4 border-red-500 animate-in slide-in-from-right fade-in duration-300 backdrop-blur-sm">
                    <div className="flex justify-between items-start">
                        <strong className="text-sm font-bold uppercase tracking-wider text-red-200">
                            {alert.reason || 'Threat Detected'}
                        </strong>
                        <button
                            onClick={() => setAlerts(prev => prev.filter((_, i) => i !== idx))}
                            className="text-red-300 hover:text-white text-xs"
                        >✕</button>
                    </div>
                    <div className="mt-1 font-mono text-sm break-all">
                        {alert.entity}
                    </div>
                    {alert.details?.ttps && (
                        <div className="mt-2 flex flex-wrap gap-1">
                            {alert.details.ttps.map((t: string) => (
                                <span key={t} className="px-1.5 py-0.5 bg-red-700 rounded text-[10px] font-bold">
                                    {t}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}
