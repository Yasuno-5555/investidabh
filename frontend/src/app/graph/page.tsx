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
                    onNodeClick={onNodeClick}
                    onPaneClick={closeDetails}
                    fitView
                >
                    <Background color="#cbd5e1" gap={20} />
                    <Controls />
                    <MiniMap className="border rounded shadow-lg" />

                    {/* Top Right Controls */}
                    <Panel position="top-right" className="flex gap-2">
                        <button
                            onClick={() => fetchData()}
                            className="bg-white/90 backdrop-blur border text-slate-700 px-4 py-2 rounded-lg shadow-sm hover:bg-white hover:text-blue-600 transition-all font-semibold text-sm flex items-center gap-2"
                        >
                            {loading && <Spinner className="w-4 h-4" />}
                            {loading ? 'Refreshing...' : 'Refresh Graph'}
                        </button>
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
                                            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Score</span>
                                            <span className={`text-xl font-black ${selectedNode.data.score > 50 ? 'text-red-500' : 'text-slate-700'}`}>
                                                {selectedNode.data.score ? selectedNode.data.score.toFixed(0) : 0}
                                            </span>
                                            <span className="text-xs text-slate-400">/100</span>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div>
                                            <span className="text-xs text-slate-400 block mb-1">CONFIDENCE</span>
                                            <span className="font-mono font-medium text-slate-700">
                                                {selectedNode.data.confidence ? (selectedNode.data.confidence * 100).toFixed(0) + '%' : 'N/A'}
                                            </span>
                                        </div>
                                        <div>
                                            <span className="text-xs text-slate-400 block mb-1">CONNECTIONS</span>
                                            <span className="font-mono font-medium text-slate-700">{selectedNode.data.degree}</span>
                                        </div>
                                        <div className="col-span-2">
                                            <span className="text-xs text-slate-400 block mb-1">FIRST SEEN</span>
                                            <span className="text-slate-700">{formatDate(selectedNode.data.timestamp)}</span>
                                        </div>
                                    </div>

                                    {selectedNode.data.isGhost && (
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
                                    {selectedNode.data.relations && selectedNode.data.relations.length > 0 && (
                                        <div className="mt-4">
                                            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">Parameters & Relations</span>
                                            <div className="space-y-2">
                                                {selectedNode.data.relations.map((rel: any, idx: number) => (
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
                </ReactFlow>
            </div>
        </div>
    );
}
