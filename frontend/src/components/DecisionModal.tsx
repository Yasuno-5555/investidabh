'use client';

import { useState } from 'react';

interface DecisionModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (data: { reason: string, referenceCase?: string }) => void;
    title: string;
    action: string;
}

export default function DecisionModal({ isOpen, onClose, onConfirm, title, action }: DecisionModalProps) {
    const [reason, setReason] = useState('');
    const [referenceCase, setReferenceCase] = useState('');

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden border border-slate-100 animate-in zoom-in-95 duration-200">
                <div className="bg-slate-50 px-8 py-6 border-b border-slate-100">
                    <h3 className="text-xl font-black text-slate-800 tracking-tight">{title}</h3>
                    <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mt-1">Decision Sign-off required</p>
                </div>
                
                <div className="p-8 space-y-6">
                    <div>
                        <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Rationale (Why?)</label>
                        <textarea 
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="e.g. Known C2 infrastructure observed in previous campaign #142..."
                            className="w-full bg-slate-50 border border-slate-200 rounded-xl p-4 text-sm text-slate-800 focus:ring-2 focus:ring-blue-500 outline-none min-h-[120px]"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Reference Case ID (Optional)</label>
                        <input 
                            type="text"
                            value={referenceCase}
                            onChange={(e) => setReferenceCase(e.target.value)}
                            placeholder="e.g. 550e8400-e29b..."
                            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-800 focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                    </div>

                    <div className="flex gap-3 pt-2">
                        <button 
                            onClick={onClose}
                            className="flex-grow px-6 py-3 rounded-xl font-bold text-slate-500 hover:bg-slate-50 transition-all"
                        >
                            Cancel
                        </button>
                        <button 
                            onClick={() => onConfirm({ reason, referenceCase })}
                            disabled={!reason}
                            className="flex-grow px-6 py-3 rounded-xl font-bold text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-30 transition-all shadow-lg"
                        >
                            Sign & {action}
                        </button>
                    </div>
                </div>
                
                <div className="bg-slate-900 px-8 py-3 text-[9px] font-mono text-slate-500 flex justify-between">
                    <span>OPERATOR: Yasuno S.</span>
                    <span>TIMESTAMP: {new Date().toISOString()}</span>
                </div>
            </div>
        </div>
    );
}
