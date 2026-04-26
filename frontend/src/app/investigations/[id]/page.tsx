import { useParams, useRouter } from 'next/navigation';
import Navbar from '../../../components/Navbar';
import Spinner from '../../../components/Spinner';
import Link from 'next/link';
import DecisionModal from '../../../components/DecisionModal';

const fetcher = (url: string) => {
    const token = localStorage.getItem('token');
    return axios.get(url, {
        headers: { Authorization: `Bearer ${token}` }
    }).then(res => res.data);
};
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

export default function InvestigationDetail() {
    const [selectedItem, setSelectedItem] = useState<any>(null);
    const [isDecisionOpen, setIsDecisionOpen] = useState(false);
    const [isVerifyOpen, setIsVerifyOpen] = useState(false);
    const [decisionAction, setDecisionAction] = useState('');
    const router = useRouter();

    // 1秒ごとにポーリングしてステータス更新
    const { data: investigation, error } = useSWR(
        id ? `${API_URL}/api/investigations/${id}` : null,
        fetcher,
        { refreshInterval: 1000 }
    );

    if (error) {
        if (axios.isAxiosError(error) && error?.response?.status === 401) {
            router.push('/login');
            return null;
        }
        return <div>Failed to load or access denied</div>;
    }
    if (!investigation) return <div>Loading...</div>;

    // Artifact Proxy URL also needs auth logic? 
    // No, the proxy endpoint is protected by JWT in the standard header if using fetch, 
    // but for <img> src, we can't easily add headers.
    // Standard approach: 
    // 1. Signed URLs (complex)
    // 2. Cookie based auth (we are using localStorage)
    // 3. Gateway accepts token in query param (less secure but works for MVP)
    // 4. Fetch blob in JS and create object URL

    // For MVP, we will use the fetch blob approach for Screenshots to keep it secure
    // For HTML iframe, it's tricker. We might need to expose a temporary token or use query param.
    // Let's implement a simple Image component that fetches with token.

    return (
        <div className="max-w-6xl mx-auto p-8">
            
            {/* Export & Status */ }
    <div className="flex gap-4 items-center">
        {investigation.status === 'COMPLETED' && (
            <div className="flex gap-2">
                <button
                    onClick={async () => {
                        const token = localStorage.getItem('token');
                        try {
                            const response = await axios.get(`${API_URL}/api/investigations/${id}/export`, {
                                headers: { Authorization: `Bearer ${token}` },
                                responseType: 'blob',
                            });

                            const url = window.URL.createObjectURL(new Blob([response.data]));
                            const link = document.createElement('a');
                            link.href = url;
                            link.setAttribute('download', `report-${id}.pdf`);
                            document.body.appendChild(link);
                            link.click();
                            link.remove();
                        } catch (err) {
                            alert("Failed to download report");
                        }
                    }}
                    className="bg-blue-600 text-white px-4 py-2 rounded-xl hover:bg-blue-700 text-sm font-bold flex items-center gap-2 shadow-md transition-all"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Export PDF
                </button>
                <Link
                    href={`/investigations/${id}/capture`}
                    className="bg-red-600 text-white px-4 py-2 rounded-xl hover:bg-red-700 text-sm font-bold flex items-center gap-2 shadow-md transition-all"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Interactive Workbench
                </Link>
            </div>
        )}
    </div>
      </div >

        <div className="mb-8 border-b pb-4">
            <h1 className="text-2xl font-bold mb-2">{investigation.target_url}</h1>
            <div className="flex gap-4 text-sm text-gray-600">
                <span>ID: {investigation.id}</span>
                <span>Status:
                    <span className={`ml-2 font-bold ${investigation.status === 'COMPLETED' ? 'text-green-600' : 'text-yellow-600'
                        }`}>
                        {investigation.status}
                    </span>
                </span>
            </div>
        </div>

    {
        investigation.status === 'PENDING' && (
            <div className="text-center py-20 bg-gray-50 rounded animate-pulse">
                Processing... Collector is working.
            </div>
        )
    }

    {/* Artifacts Gallery */ }
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {investigation.artifacts?.map((art: any) => (
            <div key={art.id} className="border rounded p-4">
                <h3 className="font-semibold mb-2 uppercase text-xs text-gray-500">{art.artifact_type}</h3>

                {art.artifact_type === 'screenshot' && (
                    <SecureImage
                        src={`${API_URL}/api/artifacts/${art.id}/content`}
                        alt="Screenshot"
                    />
                )}

                {art.artifact_type === 'html' && (
                    <div className="bg-gray-100 p-4 text-center text-gray-500 text-sm">
                        HTML Preview requires simpler authentication than JWT header.<br />
                        (Raw HTML not displayed in MVP Auth mode)
                    </div>
                )}
            </div>
        ))}
    </div>

    {/* Intelligence Data */ }
    {
        investigation.intelligence && investigation.intelligence.length > 0 && (
            <div className="mt-12 border-t pt-8">
                <h2 className="text-xl font-black text-slate-800 mb-6 flex items-center gap-3">
                    <span className="w-8 h-8 bg-slate-900 text-white rounded-lg flex items-center justify-center text-sm">⚖️</span>
                    Intelligence Quality Ledger
                </h2>

                {/* UNKNOWN / CONFLICT BANNERS */}
                <div className="space-y-4 mb-8">
                    {investigation.intelligence.some((i: any) => i.status === 'CONFLICT') && (
                        <div className="bg-red-600 text-white p-4 rounded-2xl flex items-center justify-between shadow-lg shadow-red-200">
                            <div className="flex items-center gap-4">
                                <span className="text-2xl animate-bounce">⚠️</span>
                                <div>
                                    <div className="font-black uppercase tracking-widest text-[10px]">Critical Timeline Conflict Detected</div>
                                    <div className="text-sm font-bold">Multiple data points show temporal impossibility. Manual review required.</div>
                                </div>
                            </div>
                            <button className="bg-white text-red-600 px-4 py-2 rounded-xl text-xs font-black hover:bg-slate-100 transition-all">Review Conflicts</button>
                        </div>
                    )}
                    {investigation.intelligence.some((i: any) => i.status === 'UNKNOWN') && (
                        <div className="bg-slate-900 text-white p-4 rounded-2xl flex items-center justify-between border border-slate-700">
                            <div className="flex items-center gap-4">
                                <span className="text-2xl opacity-50">❓</span>
                                <div>
                                    <div className="font-black uppercase tracking-widest text-[10px] text-slate-500">Unknown Intelligence State</div>
                                    <div className="text-sm font-bold">Insufficient evidence to confirm attribution. Data requires external validation.</div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
                <div className="bg-white border border-slate-100 rounded-3xl shadow-xl overflow-hidden">
                    <table className="w-full text-left border-collapse">
                        <thead className="bg-slate-50 text-[10px] uppercase text-slate-500 font-black tracking-widest border-b border-slate-100">
                            <tr>
                                <th className="px-6 py-4">Evidence & Source</th>
                                <th className="px-6 py-4">Observed Value</th>
                                <th className="px-6 py-4">Multi-Axis Confidence (IQ)</th>
                                <th className="px-6 py-4">Custody</th>
                                <th className="px-6 py-4 text-right">Provenance</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {investigation.intelligence.map((item: any) => (
                                <tr key={item.id} className={`hover:bg-slate-50/80 transition-colors ${item.status === 'CONFLICT' ? 'bg-red-50/50' : ''}`}>
                                    <td className="px-6 py-4">
                                        <div className="flex flex-col">
                                            <span className="text-sm font-bold text-slate-800">{item.type}</span>
                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">{item.source_type}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-mono text-slate-600 bg-slate-100 px-2 py-1 rounded select-all border border-slate-200/50">{item.value}</span>
                                            {item.status === 'CONFLICT' && <span className="bg-red-600 text-white text-[8px] font-black px-1 rounded">CONFLICT</span>}
                                            {item.status === 'UNKNOWN' && <span className="bg-slate-400 text-white text-[8px] font-black px-1 rounded">UNKNOWN</span>}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 w-48">
                                            {/* Multi-Axis bars */}
                                            {['Reliability', 'Freshness', 'Corroboration', 'Analyst'].map(axis => (
                                                <div key={axis} className="flex flex-col">
                                                    <div className="flex justify-between text-[7px] font-black text-slate-400 uppercase mb-0.5">
                                                        <span>{axis.slice(0,3)}</span>
                                                        <span>{((item.confidence_axes?.[axis.toLowerCase()] || 0.5) * 100).toFixed(0)}%</span>
                                                    </div>
                                                    <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
                                                        <div className={`h-full ${axis === 'Analyst' ? 'bg-green-500' : 'bg-blue-400'}`} style={{ width: `${(item.confidence_axes?.[axis.toLowerCase()] || 0.5) * 100}%` }}></div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <button 
                                            onClick={() => setIsVerifyOpen(true)}
                                            className="group flex items-center gap-2 hover:bg-slate-100 px-2 py-1 rounded-lg transition-all"
                                        >
                                            <span className="w-2 h-2 rounded-full bg-green-500 group-hover:animate-ping"></span>
                                            <span className="text-[9px] font-mono text-slate-400 uppercase group-hover:text-slate-800">Verifiable</span>
                                        </button>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex justify-end gap-1">
                                            <button 
                                                onClick={() => { setSelectedItem(item); setDecisionAction('Confirm'); setIsDecisionOpen(true); }}
                                                className="p-2 hover:bg-green-100 text-green-600 rounded-xl transition-all" 
                                                title="Sign-off & Confirm"
                                            >✓</button>
                                            <button 
                                                onClick={() => { setSelectedItem(item); setDecisionAction('Override'); setIsDecisionOpen(true); }}
                                                className="p-2 hover:bg-blue-100 text-blue-600 rounded-xl transition-all font-black text-[10px]" 
                                                title="Override with Rationale"
                                            >SCORE</button>
                                            <button 
                                                onClick={() => { setSelectedItem(item); setDecisionAction('Flag Conflict'); setIsDecisionOpen(true); }}
                                                className="p-2 hover:bg-red-100 text-red-600 rounded-xl transition-all" 
                                                title="Flag Timeline Conflict"
                                            >⚠️</button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        )
    }
            {/* TIER S+ MODALS */}
            <DecisionModal 
                isOpen={isDecisionOpen}
                onClose={() => setIsDecisionOpen(false)}
                title={`${decisionAction}: ${selectedItem?.value}`}
                action={decisionAction}
                onConfirm={(data) => {
                    console.log("TIER S+ DECISION SIGNED:", data);
                    setIsDecisionOpen(false);
                    // In real app: axios.post(`/api/intelligence/${selectedItem.id}/decide`, data)
                }}
            />

            {isVerifyOpen && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center bg-slate-900/80 backdrop-blur-md animate-in fade-in">
                    <div className="bg-white rounded-3xl p-10 max-w-2xl w-full border border-slate-200 shadow-2xl">
                        <div className="flex items-center gap-4 mb-6">
                            <span className="text-4xl">🔐</span>
                            <div>
                                <h3 className="text-2xl font-black text-slate-800">Verify Evidence Integrity</h3>
                                <p className="text-slate-500 text-sm font-bold uppercase tracking-widest">Local Verification Protocol</p>
                            </div>
                        </div>
                        <div className="bg-slate-900 text-blue-400 p-6 rounded-2xl font-mono text-sm mb-6 shadow-inner overflow-x-auto">
                            <div className="text-slate-500 mb-2"># 1. Download evidence file</div>
                            <div>curl -H "Authorization: Bearer $TOKEN" {API_URL}/api/artifacts/[ID]/content -o evidence.bin</div>
                            <div className="text-slate-500 my-2"># 2. Verify SHA-256 integrity seal</div>
                            <div>echo "[EXPECTED_HASH]  evidence.bin" | sha256sum -c</div>
                        </div>
                        <div className="flex justify-end">
                            <button onClick={() => setIsVerifyOpen(false)} className="bg-slate-900 text-white px-8 py-3 rounded-xl font-bold">Acknowledge</button>
                        </div>
                    </div>
                </div>
            )}
        </div >
    );
}

// Helper component to load image with Auth header
function SecureImage({ src, alt }: { src: string, alt: string }) {
    const [objectUrl, setObjectUrl] = useState<string | null>(null);

    useEffect(() => {
        const token = localStorage.getItem('token');
        axios.get(src, {
            responseType: 'blob',
            headers: { Authorization: `Bearer ${token}` }
        })
            .then(res => {
                setObjectUrl(URL.createObjectURL(res.data));
            })
            .catch(err => console.error("Failed to load image", err));

        return () => {
            if (objectUrl) URL.revokeObjectURL(objectUrl);
        }
    }, [src]);

    if (!objectUrl) return <div className="w-full h-48 bg-gray-200 animate-pulse"></div>;

    return <img src={objectUrl} alt={alt} className="w-full h-auto border" />;
}

import { useState } from 'react';
