'use client';

import { useState, useEffect } from 'react';
import useSWR, { mutate } from 'swr';
import axios from 'axios';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import Navbar from '../components/Navbar';
import Spinner from '../components/Spinner';
import { Toaster, toast } from 'react-hot-toast';
import DOMPurify from 'dompurify';

const fetcher = (url: string) => {
    const token = localStorage.getItem('token');
    return axios.get(url, {
        headers: { Authorization: `Bearer ${token}` }
    }).then(res => res.data);
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

export default function Home() {
    const [url, setUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<any[]>([]);
    const [modules, setModules] = useState({
        dns: true,
        whois: true,
        threat: true,
        wayback: false,
        github: false
    });
    const router = useRouter();

    // Search Effect
    useEffect(() => {
        const delayDebounceFn = setTimeout(async () => {
            if (searchQuery.length > 2) {
                const token = localStorage.getItem('token');
                try {
                    const res = await axios.get(`${API_URL}/api/search?q=${encodeURIComponent(searchQuery)}`, {
                        headers: { Authorization: `Bearer ${token}` }
                    });
                    setSearchResults(res.data);
                } catch (err) {
                    console.error("Search failed", err);
                }
            } else {
                setSearchResults([]);
            }
        }, 500);

        return () => clearTimeout(delayDebounceFn);
    }, [searchQuery]);

    // Auth Check & SSE Setup
    useEffect(() => {
        const token = localStorage.getItem('token');
        if (!token) {
            router.push('/login');
            return;
        }

        // Real-time Feedback via SSE
        const eventSource = new EventSource(`${API_URL}/api/alerts/stream?token=${token}`);
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'info') toast(data.message, { icon: 'ℹ️' });
                else if (data.type === 'success') toast.success(data.message);
                else if (data.type === 'warning') toast(data.message, { icon: '⚠️' });
                else if (data.type === 'error') toast.error(data.message);
            } catch (e) {}
        };
        return () => eventSource.close();
    }, [router]);

    // Use SWR with auth fetcher
    const { data: investigations, error } = useSWR(
        `${API_URL}/api/investigations`,
        fetcher
    );

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        const token = localStorage.getItem('token');
        try {
            await axios.post(`${API_URL}/api/investigations`,
                { targetUrl: url, modules },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            toast.success(`Investigation started for ${url}`);
            setUrl('');
            mutate(`${API_URL}/api/investigations`);
        } catch (err) {
            if (axios.isAxiosError(err) && err.response?.status === 401) {
                router.push('/login');
            } else {
                toast.error('Error creating investigation');
            }
        } finally {
            setLoading(false);
        }
    };

    if (error) {
        if (axios.isAxiosError(error) && error?.response?.status === 401) {
            router.push('/login');
            return null;
        }
        return null;
    }

    return (
        <div className="min-h-screen bg-slate-50">
            <Toaster position="bottom-right" toastOptions={{ className: 'text-sm font-semibold border border-slate-100 shadow-xl' }} />
            <Navbar />

            <main className="max-w-7xl mx-auto p-8">
                {/* Case-Centric Hero Section */}
                <div className="flex justify-between items-end mb-12">
                    <div>
                        <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight mb-2">
                            Intelligence <span className="text-blue-600">Workspace</span>
                        </h1>
                        <p className="text-slate-500 font-medium">Manage investigations, evidence, and hypotheses in a centralized ledger.</p>
                    </div>
                    <button className="bg-blue-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-blue-700 shadow-lg shadow-blue-200 transition-all flex items-center gap-2">
                        <span>＋</span> New Investigation Case
                    </button>
                </div>

                {/* Case Selection Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
                    {[
                        { title: 'Op. Silver Bullet', subject: 'Phishing Group X', leads: 12, status: 'OPEN', color: 'blue' },
                        { title: 'Data Leak Analysis', subject: 'Internal Leak', leads: 4, status: 'OPEN', color: 'orange' },
                        { title: 'Brand Impersonation', subject: 'Logo Abuse', leads: 28, status: 'OPEN', color: 'purple' },
                    ].map((caseItem, idx) => (
                        <div key={idx} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 hover:shadow-xl hover:-translate-y-1 transition-all cursor-pointer group">
                            <div className="flex justify-between items-start mb-4">
                                <div className={`w-10 h-10 rounded-xl bg-${caseItem.color}-50 flex items-center justify-center text-xl`}>📁</div>
                                <span className="text-[10px] font-black bg-slate-100 px-2 py-0.5 rounded text-slate-500 uppercase tracking-widest">{caseItem.status}</span>
                            </div>
                            <h3 className="font-bold text-slate-800 text-lg group-hover:text-blue-600 transition-colors">{caseItem.title}</h3>
                            <p className="text-xs text-slate-500 mb-4">Target: {caseItem.subject}</p>
                            <div className="flex justify-between items-center pt-4 border-t border-slate-50">
                                <span className="text-xs font-bold text-slate-400">{caseItem.leads} Leads Collected</span>
                                <span className="text-blue-600 text-xs font-bold">Open Case →</span>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Quick Lead Acquisition (Wizard) */}
                <div className="bg-slate-900 rounded-3xl p-10 text-white shadow-2xl relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-8 opacity-10 text-8xl">🕵️</div>
                    <div className="relative z-10 max-w-2xl">
                        <h2 className="text-2xl font-bold mb-2">Acquire New Lead</h2>
                        <p className="text-slate-400 text-sm mb-8">Start a new evidence collection session. Data will be hashed and added to the Custody Ledger automatically.</p>

                        <form onSubmit={handleSubmit} className="bg-white/10 backdrop-blur-md p-2 rounded-2xl border border-white/10 flex gap-2">
                            <input
                                type="url"
                                value={url}
                                onChange={(e) => setUrl(e.target.value)}
                                placeholder="Enter Target URL (e.g. https://example.com)"
                                className="flex-grow bg-transparent border-none focus:ring-0 text-white placeholder-slate-500 font-medium px-4"
                                required
                            />
                            <button
                                type="submit"
                                disabled={loading}
                                className="bg-white text-slate-900 px-8 py-3 rounded-xl font-bold hover:bg-slate-100 transition-all flex items-center gap-2"
                            >
                                {loading ? <Spinner /> : 'Acquire Evidence'}
                            </button>
                        </form>
                        
                        <div className="mt-4 flex gap-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" checked={modules.dns} onChange={(e) => setModules({...modules, dns: e.target.checked})} className="rounded border-slate-700 bg-slate-800 text-blue-500" /> DNS RECON
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" checked={modules.threat} onChange={(e) => setModules({...modules, threat: e.target.checked})} className="rounded border-slate-700 bg-slate-800 text-blue-500" /> THREAT INTEL
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" checked={modules.wayback} onChange={(e) => setModules({...modules, wayback: e.target.checked})} className="rounded border-slate-700 bg-slate-800 text-blue-500" /> WAYBACK
                            </label>
                        </div>
                    </div>
                </div>

                {/* Search Bar (Overlay Style) */}
                <div className="mb-12 relative max-w-4xl mx-auto">
                    <div className="bg-white rounded-lg border shadow-sm p-4 flex gap-4 items-center">
                        <span className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Deep Search</span>
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search across all captured content..."
                            className="flex-grow bg-transparent outline-none text-slate-800 placeholder-slate-400"
                        />
                        {searchResults.length > 0 && (
                            <button onClick={() => setSearchResults([])} className="text-xs text-slate-400 hover:text-slate-600">Clear</button>
                        )}
                    </div>

                    {/* Search Results Dropdown */}
                    {searchResults.length > 0 && (
                        <div className="absolute z-20 w-full mt-2 bg-white/95 backdrop-blur border rounded-xl shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-2">
                            <div className="px-4 py-2 bg-slate-50 border-b text-xs font-bold text-slate-500">RESULTS</div>
                            <div className="max-h-96 overflow-y-auto">
                                {searchResults.map((hit: any) => (
                                    <Link key={hit.id} href={`/investigations/${hit.id}`} className="block p-4 hover:bg-blue-50 border-b last:border-0 transition-colors">
                                        <div className="font-semibold text-blue-600 mb-1">{hit.url}</div>
                                        <div className="text-sm text-slate-600 line-clamp-2"
                                            dangerouslySetInnerHTML={{
                                                __html: DOMPurify.sanitize(hit.snippet)
                                            }}
                                        />
                                    </Link>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Recent Investigations */}
                <h2 className="text-2xl font-bold text-slate-800 mb-6 flex items-center gap-2">
                    <span>Recent Investigations</span>
                    <span className="text-sm font-normal text-slate-500 bg-slate-200 px-2 py-1 rounded-full">{investigations?.length || 0}</span>
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {investigations?.map((inv: any) => (
                        <Link key={inv.id} href={`/investigations/${inv.id}`} className="group relative block h-full">
                            <div className="h-full bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:shadow-md hover:border-blue-300 transition-all cursor-pointer flex flex-col justify-between">
                                <div>
                                    <div className="flex justify-between items-start mb-4">
                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${inv.status === 'COMPLETED' ? 'bg-green-50 text-green-700 border-green-200' :
                                            inv.status === 'PENDING' ? 'bg-yellow-50 text-yellow-700 border-yellow-200' : 'bg-red-50 text-red-700 border-red-200'
                                            }`}>
                                            {inv.status}
                                        </span>
                                        <span className="text-xs text-slate-400">{new Date(inv.created_at).toLocaleDateString()}</span>
                                    </div>
                                    <h3 className="text-lg font-bold text-slate-900 group-hover:text-blue-600 truncate mb-2" title={inv.target_url}>
                                        {inv.target_url.replace(/^https?:\/\//, '')}
                                    </h3>
                                </div>
                                <div className="mt-4 pt-4 border-t border-slate-100 flex justify-between items-center text-sm text-slate-500">
                                    <span>View Details &rarr;</span>
                                </div>
                            </div>
                        </Link>
                    ))}
                    {!investigations && (
                        [1, 2, 3].map(i => (
                            <div key={i} className="h-32 bg-slate-100 rounded-xl animate-pulse" />
                        ))
                    )}
                </div>
            </main>
        </div>
    );
}
