'use client';

import { useEffect, useState } from 'react';
import ReactFlow, {
    useNodesState,
    useEdgesState,
    Background,
    Controls,
    MiniMap,
    Panel
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import axios from 'axios';
import Navbar from '../../components/Navbar';
import Spinner from '../../components/Spinner';
import AlertTicker from '../../components/AlertTicker';
import TimelineView from '../../components/TimelineView';

// Graph Layout Helper
const getLayoutedElements = (nodes: any[], edges: any[]) => {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    const nodeWidth = 180;
    const nodeHeight = 50;

    dagreGraph.setGraph({ rankdir: 'LR' });

    nodes.forEach((node) => {
        // dagre needs simple string IDs
        dagreGraph.setNode(node.id, { width: node.style?.width || nodeWidth, height: node.style?.height || nodeHeight });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    nodes.forEach((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        if (nodeWithPosition) {
            node.position = {
                x: nodeWithPosition.x - (node.style?.width || nodeWidth) / 2,
                y: nodeWithPosition.y - (node.style?.height || nodeHeight) / 2,
            };
        } else {
            node.position = { x: 0, y: 0 };
        }
    });

    return { nodes, edges };
};

export default function GraphPage() {
    // Raw Data (all nodes/edges from API)
    const [initialNodes, setInitialNodes] = useState<any[]>([]);
    const [initialEdges, setInitialEdges] = useState<any[]>([]);

    // React Flow State (currently viewed nodes/edges)
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    // UI State
    const [selectedNode, setSelectedNode] = useState<any>(null);
    const [loading, setLoading] = useState(false);


    // Timeline State
    const [minTime, setMinTime] = useState(0);
    const [maxTime, setMaxTime] = useState(100);
    const [currentTime, setCurrentTime] = useState(100);

    // Phase 33.2: Hypothesis State
    const [isHypothesisMode, setIsHypothesisMode] = useState(false);
    const [hypothesisNodes, setHypothesisNodes] = useState<any[]>([]);
    const [hypothesisEdges, setHypothesisEdges] = useState<any[]>([]);

    const addShadowNode = () => {
        const id = `shadow-${Date.now()}`;
        const newNode = {
            id,
            type: 'default', // or special 'hypothesis' type if we register it
            position: { x: Math.random() * 500, y: Math.random() * 500 },
            data: { label: 'New Hypothesis', type: 'shadow' },
            style: {
                border: '2px dashed #a855f7', // Purple dashed
                backgroundColor: '#faf5ff',
                color: '#6b21a8',
                width: 180,
                borderRadius: 8,
                padding: 10
            },
            draggable: true,
        };
        setHypothesisNodes((prev) => [...prev, newNode]);
        setNodes((prev) => [...prev, newNode]); // Add to ReactFlow nodes immediately? Or merge?
        // ReactFlow manages 'nodes' state passed to <ReactFlow nodes={nodes}>.
        // We should allow basic dragging.
    };

    // When toggling mode, we might want to filter view or just overlay.
    // For now, simple overlay.

    // Merge Hypothesis Data into Main Flow
    // We update 'nodes' state when hypothesis changes? 
    // Or we keep separate and merge on render? 
    // ReactFlow takes 'nodes' prop. 'nodes' state is managed by 'useNodesState'.
    // To mix them, we should append hypothesisNodes to 'nodes' when created.
    // But 'useNodesState' handles internal updates.
    // Better: Update 'nodes' directly when adding shadow node.

    // Connection handling for shadow edges
    const onConnect = (params: any) => {
        if (!isHypothesisMode) return; // Only allow manual connecting in hypothesis mode for now?
        // Or allowing connecting real nodes too? 
        // Let's assume user connects shadow-shadow or real-shadow.
        const newEdge = {
            ...params,
            id: `e-${params.source}-${params.target}-${Date.now()}`,
            animated: true,
            style: { stroke: '#a855f7', strokeDasharray: '5,5' }
        };
        setEdges((eds) => [...eds, newEdge]);
        setHypothesisEdges((eds) => [...eds, newEdge]);
    };

    const fetchData = async () => {
        setLoading(true);
        const token = localStorage.getItem('token');
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';
        if (!token) {
            setLoading(false);
            return;
        }

        try {
            const res = await axios.get(`${API_URL}/api/graph`, {
                headers: { Authorization: `Bearer ${token}` }
            });

            // レイアウト計算
            const layouted = getLayoutedElements(res.data.nodes, res.data.edges);

            setInitialNodes(layouted.nodes);
            setInitialEdges(layouted.edges);

            // 時間範囲の計算
            const timestamps = [...layouted.nodes, ...layouted.edges]
                .map(item => item.data?.timestamp)
                .filter(t => t); // undefined除外

            if (timestamps.length > 0) {
                const min = Math.min(...timestamps);
                const max = Math.max(...timestamps);
                // UI用に少し余裕を持たせる
                setMinTime(min);
                setMaxTime(max + 1000);
                setCurrentTime(max + 1000); // 最初は全部表示
            } else {
                // Default time if no data
                const now = Date.now();
                setMinTime(now);
                setMaxTime(now);
                setCurrentTime(now);
            }
        } catch (err) {
            console.error("Graph fetch failed", err);
        } finally {
            setLoading(false);
        }
    };

    // 1. Fetch & Setup
    useEffect(() => {
        fetchData();
    }, []);

    // Node Click Handler
    const onNodeClick = (_: React.MouseEvent, node: any) => {
        setSelectedNode(node);
    };

    // Close Details
    const closeDetails = () => setSelectedNode(null);


    // 2. Filter logic (Timeline Effect)
    useEffect(() => {
        if (initialNodes.length === 0) return;

        // 現在時刻より「前」に作られたノードのみ表示
        const filteredNodes = initialNodes.filter(n => n.data.timestamp <= currentTime);

        // エッジは「両端のノードが存在する」かつ「エッジ自体の作成時間が現在時刻以下」
        // (今回はエッジデータにもtimestamp入れたので単純比較でも可)
        const activeNodeIds = new Set(filteredNodes.map(n => n.id));
        const filteredEdges = initialEdges.filter(e =>
            e.data.timestamp <= currentTime &&
            activeNodeIds.has(e.source) &&
            activeNodeIds.has(e.target)
        );

        setNodes(filteredNodes);
        setEdges(filteredEdges);
    }, [currentTime, initialNodes, initialEdges, setNodes, setEdges]);

    // 日付フォーマット用
    const formatDate = (ts: number) => {
        if (!ts) return '';
        return new Date(ts).toLocaleString();
    };

    return (
        <div className="w-full h-screen bg-slate-50 flex flex-col">
            <Navbar />
            <div className="flex-grow relative">
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    onNodeClick={(e, node) => setSelectedNode(node)}
                    fitView
                    attributionPosition="bottom-right"
                    minZoom={0.1}
                >
                    <Background color="#cbd5e1" gap={20} />
                    <Controls />
                    <MiniMap className="border rounded shadow-lg" />

                    {/* Top Right Controls */}
                    <Panel position="top-right" className="flex flex-col gap-2 max-w-xs">
                        <div className="flex gap-2">
                            <button
                                onClick={() => fetchData()}
                                className="bg-white/90 backdrop-blur border text-slate-700 px-4 py-2 rounded-lg shadow-sm hover:bg-white hover:text-blue-600 transition-all font-semibold text-sm flex items-center gap-2"
                            >
                                {loading && <Spinner className="w-4 h-4" />}
                                {loading ? 'Refreshing...' : 'Refresh'}
                            </button>
                            <button
                                disabled={loading}
                                onClick={async () => {
                                    // Phase 34: Export PDF
                                    try {
                                        // Find an investigation ID (MVP: First one found)
                                        const invIds = Array.from(new Set(nodes.map((n: any) => n.id.startsWith('inv-') ? n.id.replace('inv-', '') : null).filter(Boolean)));
                                        const targetInvId = invIds.length > 0 ? invIds[0] : null;

                                        if (!targetInvId) {
                                            alert("No investigation data found to export.");
                                            return;
                                        }

                                        const token = localStorage.getItem('token');
                                        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

                                        // Simple UI Feedback
                                        const btn = document.getElementById('export-pdf-btn');
                                        if (btn) btn.innerText = "Generating...";

                                        const response = await axios.get(
                                            `${API_URL}/api/investigations/${targetInvId}/report`,
                                            {
                                                headers: { Authorization: `Bearer ${token}` },
                                                responseType: 'blob'
                                            }
                                        );

                                        const url = window.URL.createObjectURL(new Blob([response.data]));
                                        const link = document.createElement('a');
                                        link.href = url;
                                        // Get filename from header or generate
                                        link.setAttribute('download', `investidubh-report-${targetInvId}-${new Date().toISOString().split('T')[0]}.pdf`);
                                        document.body.appendChild(link);
                                        link.click();
                                        link.remove();

                                        if (btn) btn.innerText = "📄 Export PDF";

                                    } catch (err: any) {
                                        console.error(err);
                                        alert(`PDF export failed: ${err.response?.statusText || err.message}`);
                                        const btn = document.getElementById('export-pdf-btn');
                                        if (btn) btn.innerText = "📄 Export PDF";
                                    }
                                }}
                                id="export-pdf-btn"
                                className={`bg-blue-600 text-white px-4 py-2 rounded-lg shadow-sm hover:bg-blue-700 transition-all font-semibold text-sm flex items-center gap-2 ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                            >
                                📄 Export PDF
                            </button>
                        </div>

                        {/* Phase 29: Insights Panel */}
                        {(initialNodes as any)?.insights && (
                            <div className="bg-white/90 backdrop-blur rounded-xl shadow-lg border border-white/50 p-3 text-xs">
                                {/* ... existing insights ... */}
                                {/* Top Entities */}
                                {(initialNodes as any).insights.top_entities?.length > 0 && (
                                    <div className="mb-3">
                                        <span className="font-bold text-slate-500 uppercase tracking-wide block mb-2">🔑 Key Entities</span>
                                        {(initialNodes as any).insights.top_entities.slice(0, 3).map((e: any, i: number) => (
                                            <div key={i} className="flex justify-between items-center py-1 border-b border-slate-100 last:border-0">
                                                <span className="font-medium text-slate-700 truncate max-w-[140px]">{e.label}</span>
                                                <span className="text-yellow-600 font-bold">{e.priority}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                                {/* ... */}
                            </div>
                        )}

                        {/* Phase 36: Integrity Check (Admin) */}
                        <div className="mt-2 text-right">
                            <button
                                onClick={async () => {
                                    if (!confirm("Run full integrity verification? This may take time.")) return;
                                    try {
                                        const token = localStorage.getItem('token');
                                        alert("Running verification... Please wait.");
                                        const res = await axios.post(
                                            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000'}/api/admin/verify-integrity`,
                                            {},
                                            { headers: { Authorization: `Bearer ${token}` } }
                                        );
                                        const r = res.data;
                                        alert(`Verification Complete.\nScanned: ${r.scanned}\nPassed: ${r.passed}\nFailed: ${r.failed}\nErrors: ${r.errors.length}`);
                                        if (r.failed > 0) {
                                            console.error("Corrupted Artifacts:", r.corrupted_artifacts);
                                            alert("CRITICAL WARNING: Integrity failures detected! Check console for details.");
                                        }
                                    } catch (e: any) {
                                        alert("Verification failed: " + e.message);
                                        console.error(e);
                                    }
                                }}
                                className="text-[10px] text-slate-400 hover:text-slate-600 underline"
                            >
                                Run System Integrity Check 🛡️
                            </button>
                        </div>
                    </Panel>

                    {/* Detail Panel */}
                    {selectedNode && (
                        <Panel position="top-left" className="m-4">
                            <div className="w-96 bg-white/90 backdrop-blur rounded-2xl shadow-2xl border border-white/50 p-6 animate-in slide-in-from-left-4 fade-in duration-200">
                                <div className="flex justify-between items-start mb-4">
                                    <h3 className="font-bold text-xl text-slate-900 break-words leading-tight">
                                        {selectedNode.data.value || selectedNode.data.label}
                                    </h3>
                                    <button onClick={closeDetails} className="text-slate-400 hover:text-slate-600 p-1 bg-slate-100 rounded-full">✕</button>
                                </div>

                                <div className="space-y-4">
                                    <div className="flex items-center gap-4 border-b border-slate-100 pb-4">
                                        <div className="flex-1">
                                            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Type</span>
                                            <span className={`inline-block px-2 py-1 rounded text-xs font-bold capitalize bg-slate-100 text-slate-600`}>
                                                {selectedNode.data.type || 'Unknown'}
                                            </span>
                                        </div>
                                        <div className="flex-1 text-right">
                                            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Priority</span>
                                            <span className={`text-2xl font-black ${selectedNode.data.priority?.score >= 75 ? 'text-red-500' :
                                                selectedNode.data.priority?.score >= 50 ? 'text-orange-500' : 'text-slate-700'
                                                }`}>
                                                {selectedNode.data.priority?.score || selectedNode.data.score || 0}
                                            </span>
                                            <span className="text-xs text-slate-400">/100</span>
                                        </div>
                                    </div>

                                    {/* Priority Score Breakdown */}
                                    {selectedNode.data.priority?.breakdown && (
                                        <div className="mt-4 pt-4 border-t border-slate-100">
                                            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-3">Score Breakdown</span>
                                            <div className="space-y-2">
                                                {[
                                                    { key: 'degree', label: 'Degree', color: 'bg-blue-500' },
                                                    { key: 'frequency', label: 'Frequency', color: 'bg-green-500' },
                                                    { key: 'cross_investigation', label: 'Cross-Inv', color: 'bg-purple-500' },
                                                    { key: 'sentiment', label: 'Sentiment', color: 'bg-red-500' },
                                                    { key: 'freshness', label: 'Freshness', color: 'bg-cyan-500' }
                                                ].map(item => (
                                                    <div key={item.key} className="flex items-center gap-2 text-xs">
                                                        <span className="w-20 text-slate-500">{item.label}</span>
                                                        <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                                                            <div
                                                                className={`h-full ${item.color}`}
                                                                style={{ width: `${selectedNode.data.priority.breakdown[item.key]}%` }}
                                                            />
                                                        </div>
                                                        <span className="w-8 text-right font-mono text-slate-600">
                                                            {selectedNode.data.priority.breakdown[item.key]}
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div>
                                            <span className="text-xs text-slate-400 block mb-1">CONFIDENCE</span>
                                            <span className="font-mono font-medium text-slate-700">
                                                {selectedNode.data.confidence ? (selectedNode.data.confidence * 100).toFixed(0) + '%' : 'N/A'}
                                            </span>
                                        </div>
                                        <div>
                                            <span className="text-xs text-slate-400 block mb-1">CONNECTIONS</span>
                                            <span className="font-mono font-medium text-slate-700">{selectedNode.data.degree || selectedNode.data.stats?.frequency}</span>
                                        </div>

                                        {/* Phase 26: Temporal Intelligence */}
                                        {selectedNode.data.stats && (
                                            <>
                                                <div className="col-span-2 pt-2 border-t border-slate-100">
                                                    <span className="text-xs text-slate-400 block mb-1">LIFESPAN</span>
                                                    <span className="text-slate-700 text-sm">
                                                        {new Date(selectedNode.data.stats.first_seen).toLocaleDateString()}
                                                        {' ~ '}
                                                        {new Date(selectedNode.data.stats.last_seen).toLocaleDateString()}
                                                    </span>
                                                </div>
                                                <div>
                                                    <span className="text-xs text-slate-400 block mb-1">SIGHTINGS</span>
                                                    <span className="text-xl font-black text-slate-700">{selectedNode.data.stats.frequency}</span>
                                                </div>
                                                <div>
                                                    <span className="text-xs text-slate-400 block mb-1">FRESHNESS</span>
                                                    <span className={`inline-block px-2 py-1 rounded text-xs font-bold 
                                                        ${selectedNode.data.stats.aging_category === 'FRESH' ? 'bg-green-100 text-green-700' :
                                                            selectedNode.data.stats.aging_category === 'RECENT' ? 'bg-blue-100 text-blue-700' :
                                                                selectedNode.data.stats.aging_category === 'STALE' ? 'bg-yellow-100 text-yellow-700' :
                                                                    'bg-slate-200 text-slate-500'}`}>
                                                        {selectedNode.data.stats.aging_category}
                                                    </span>
                                                </div>
                                            </>
                                        )}

                                        <div className="col-span-2">
                                            <span className="text-xs text-slate-400 block mb-1">FIRST SEEN</span>
                                            <span className="text-slate-700">{formatDate(selectedNode.data.timestamp)}</span>
                                        </div>
                                    </div>

                                    {/* Ghost Entity based on ANCIENT */}
                                    {selectedNode.data.stats?.aging_category === 'ANCIENT' && (
                                        <div className="mt-4 bg-orange-50 border border-orange-100 rounded-lg p-3 flex gap-3 text-sm text-orange-800">
                                            <span className="text-lg">👻</span>
                                            <div>
                                                <strong className="block font-bold">Ghost Entity</strong>
                                                Detected in historical records but not in current fetch.
                                            </div>
                                        </div>
                                    )}

                                    {selectedNode.data.isHighPriority && (
                                        <div className="mt-2 bg-red-50 border border-red-100 rounded-lg p-3 text-sm text-red-800 font-medium text-center">
                                            ⚠️ High Priority Target
                                        </div>
                                    )}

                                    {/* Advanced NLP: Relations */}
                                    {(selectedNode.data.relations?.length > 0 || selectedNode.data.metadata?.relations?.length > 0) && (
                                        <div className="mt-4">
                                            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">Relations</span>
                                            <div className="space-y-2">
                                                {(selectedNode.data.relations || selectedNode.data.metadata?.relations || []).map((rel: any, idx: number) => (
                                                    <div key={idx} className="flex items-center gap-2 text-sm bg-slate-50 p-2 rounded border border-slate-100">
                                                        <span className="font-bold text-blue-600">{rel.label}</span>
                                                        <span className="text-slate-400">&rarr;</span>
                                                        <span className="font-medium text-slate-700">{rel.target}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Sentiment Indicator */}
                                    <div className="mt-4 pt-4 border-t border-slate-100">
                                        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">Sentiment Analysis</span>
                                        <div className="flex items-center gap-3">
                                            <div className={`h-2 flex-grow rounded-full bg-slate-100 overflow-hidden`}>
                                                <div
                                                    className={`h-full ${selectedNode.data.sentiment > 0.1 ? 'bg-green-500' : selectedNode.data.sentiment < -0.1 ? 'bg-red-500' : 'bg-slate-400'}`}
                                                    style={{ width: `${Math.min(100, Math.abs(selectedNode.data.sentiment || 0) * 100)}%` }}
                                                ></div>
                                            </div>
                                            <span className="text-xs font-mono font-bold text-slate-600">
                                                {(selectedNode.data.sentiment || 0).toFixed(2)}
                                            </span>
                                        </div>
                                    </div>

                                    {/* --- Phase 32: TTP & Intelligence --- */}
                                    {(selectedNode.data.metadata?.ttps?.length > 0) && (
                                        <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3">
                                            <span className="text-xs font-bold text-red-600 uppercase tracking-wider block mb-2">Threat Indicators (TTPs)</span>
                                            <div className="flex flex-wrap gap-1">
                                                {selectedNode.data.metadata.ttps.map((ttp: string) => {
                                                    // Simple mapping for display
                                                    const ttpNames: Record<string, string> = {
                                                        'T1566': 'Phishing', 'T1566.002': 'Spearphishing Link',
                                                        'T1190': 'Exploit Public-Facing App', 'T1110': 'Brute Force',
                                                        'T1588': 'Malware'
                                                    };
                                                    const name = ttpNames[ttp] || ttp;
                                                    return (
                                                        <span key={ttp} title={name !== ttp ? `${ttp}: ${name}` : ttp} className="px-2 py-1 bg-red-100 text-red-800 text-xs font-bold rounded border border-red-200 cursor-help">
                                                            {name !== ttp ? `[${ttp}] ${name}` : ttp}
                                                        </span>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}

                                    {/* Intelligence Tab (Enrichment) */}
                                    {(selectedNode.data.metadata?.whois || selectedNode.data.metadata?.dns_records) && (
                                        <div className="mt-4 pt-4 border-t border-slate-100">
                                            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-3">Enrichment Data</span>

                                            {/* WHOIS */}
                                            {selectedNode.data.metadata?.whois && (
                                                <div className="mb-3">
                                                    <span className="text-[10px] text-slate-500 font-bold block bg-slate-100 px-2 py-1 rounded-t">WHOIS</span>
                                                    <div className="bg-slate-50 border border-t-0 border-slate-100 p-2 rounded-b text-xs space-y-1">
                                                        <div className="flex justify-between">
                                                            <span className="text-slate-400">Registrar</span>
                                                            <span className="text-slate-700 font-medium truncate max-w-[150px]">{selectedNode.data.metadata.whois.registrar}</span>
                                                        </div>
                                                        <div className="flex justify-between">
                                                            <span className="text-slate-400">Org</span>
                                                            <span className="text-slate-700 font-medium truncate max-w-[150px]">{selectedNode.data.metadata.whois.org}</span>
                                                        </div>
                                                        <div className="flex justify-between">
                                                            <span className="text-slate-400">Created</span>
                                                            <span className="text-slate-700">{selectedNode.data.metadata.whois.creation_date?.split(' ')[0]}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            )}

                                            {/* DNS */}
                                            {selectedNode.data.metadata?.dns_records && (
                                                <div className="mb-3">
                                                    <span className="text-[10px] text-slate-500 font-bold block bg-slate-100 px-2 py-1 rounded-t">DNS RECORDS</span>
                                                    <div className="bg-slate-50 border border-t-0 border-slate-100 p-2 rounded-b text-xs space-y-1">
                                                        {Object.keys(selectedNode.data.metadata.dns_records).map((rtype) => (
                                                            <div key={rtype} className="flex justify-between">
                                                                <span className="text-slate-400 font-mono">{rtype}</span>
                                                                <span className="text-slate-700 font-mono truncate max-w-[150px]">
                                                                    {selectedNode.data.metadata.dns_records[rtype][0]}
                                                                    {selectedNode.data.metadata.dns_records[rtype].length > 1 && <span className="text-xs text-slate-400 ml-1">(+{selectedNode.data.metadata.dns_records[rtype].length - 1})</span>}
                                                                </span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* --- Phase 28: Analyst Tools --- */}
                                    <div className="mt-4 pt-4 border-t border-slate-100">
                                        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-3">Analyst Tools</span>

                                        {/* Pin Toggle */}
                                        <div className="flex items-center justify-between mb-3">
                                            <span className="text-sm text-slate-600">Pin Node</span>
                                            <button
                                                onClick={() => {
                                                    const isPinned = !selectedNode.data.metadata?.pinned;
                                                    // API call would go here
                                                    alert(`Node ${isPinned ? 'pinned' : 'unpinned'}. (API connection pending)`);
                                                }}
                                                className={`px-3 py-1 rounded text-xs font-bold transition-all ${selectedNode.data.metadata?.pinned
                                                    ? 'bg-yellow-100 text-yellow-700 border border-yellow-300'
                                                    : 'bg-slate-100 text-slate-500'
                                                    }`}
                                            >
                                                {selectedNode.data.metadata?.pinned ? '📌 Pinned' : 'Pin'}
                                            </button>
                                        </div>

                                        {/* Tags */}
                                        <div className="mb-3">
                                            <span className="text-xs text-slate-400 block mb-2">Tags</span>
                                            <div className="flex flex-wrap gap-1 mb-2">
                                                {(selectedNode.data.metadata?.tags || []).map((tag: string, idx: number) => (
                                                    <span key={idx} className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                                                        {tag}
                                                        <button className="ml-1 text-blue-400 hover:text-blue-600">&times;</button>
                                                    </span>
                                                ))}
                                            </div>
                                            <div className="flex gap-1">
                                                <select className="flex-1 text-xs border rounded px-2 py-1 bg-white">
                                                    <option value="">Add tag...</option>
                                                    <option value="watchlist">Watchlist</option>
                                                    <option value="confirmed">Confirmed</option>
                                                    <option value="ignore">Ignore</option>
                                                    <option value="reviewed">Reviewed</option>
                                                </select>
                                                <button className="px-2 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600">+</button>
                                            </div>
                                        </div>

                                        {/* Notes */}
                                        <div>
                                            <span className="text-xs text-slate-400 block mb-2">Notes</span>
                                            <textarea
                                                className="w-full text-sm border rounded p-2 h-20 resize-none"
                                                placeholder="Add analyst notes..."
                                                defaultValue={selectedNode.data.metadata?.notes || ''}
                                            />
                                            <button className="mt-2 w-full px-3 py-1.5 bg-slate-700 text-white text-xs rounded hover:bg-slate-800 font-medium">
                                                Save Notes
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </Panel>
                    )}

                    {/* Timeline Control Panel */}
                    <Panel position="bottom-center" className="w-full max-w-xl mb-8 p-0">
                        <div className="bg-white/80 backdrop-blur rounded-2xl shadow-xl border border-white/50 p-4">
                            <div className="flex justify-between text-xs font-bold text-slate-500 mb-2 uppercase tracking-wide">
                                <span>Timeline</span>
                                <span>{formatDate(currentTime)}</span>
                            </div>

                            <input
                                type="range"
                                min={minTime}
                                max={maxTime}
                                value={currentTime}
                                onChange={(e) => setCurrentTime(Number(e.target.value))}
                                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600 hover:accent-blue-700"
                            />

                            <div className="flex justify-between text-[10px] text-slate-400 mt-2 font-mono">
                                <span>{formatDate(minTime)}</span>
                                <span>{formatDate(maxTime)}</span>
                            </div>
                        </div>
                    </Panel>

                    {/* --- Phase 33.2: Hypothesis Toolbar --- */}
                    {isHypothesisMode && (
                        <Panel position="top-center" className="mt-4">
                            <div className="bg-purple-900/90 backdrop-blur text-white px-6 py-3 rounded-full shadow-2xl border border-purple-500 flex items-center gap-4 animate-in fade-in slide-in-from-top-4">
                                <span className="font-bold tracking-wider text-purple-200 text-xs uppercase">Hypothesis Mode</span>
                                <div className="h-4 w-px bg-purple-700"></div>
                                <button
                                    onClick={addShadowNode}
                                    className="flex items-center gap-2 hover:text-purple-200 transition-colors text-sm font-medium"
                                >
                                    <span className="text-lg">⊕</span> Add Shadow Entity
                                </button>
                                <button
                                    onClick={() => setHypothesisEdges([])}
                                    className="text-xs text-purple-400 hover:text-white transition-colors"
                                >
                                    Clear Edges
                                </button>
                                <button
                                    onClick={() => {
                                        setHypothesisNodes([]);
                                        setHypothesisEdges([]);
                                    }}
                                    className="text-xs text-red-400 hover:text-red-300 transition-colors"
                                >
                                    Reset All
                                </button>
                            </div>
                        </Panel>
                    )}

                    <Panel position="top-right" className="mr-4 mt-4">
                        <button
                            onClick={() => setIsHypothesisMode(!isHypothesisMode)}
                            className={`px-4 py-2 rounded-lg font-bold shadow-lg transition-all ${isHypothesisMode
                                ? 'bg-purple-600 text-white ring-2 ring-purple-400 ring-offset-2'
                                : 'bg-white text-slate-600 hover:bg-slate-50'
                                }`}
                        >
                            {isHypothesisMode ? '🔮 Exit Hypothesis' : '🔮 Hypothesis Mode'}
                        </button>
                    </Panel>

                    {/* Phase 32: Alert Ticker */}
                    <AlertTicker />
                </ReactFlow>
            </div>
        </div>
    );
}
