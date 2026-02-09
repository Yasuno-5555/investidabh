'use client';

import { useState, useEffect } from 'react';
import useSWR, { mutate } from 'swr';
import axios from 'axios';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import Navbar from '../components/Navbar';
import Spinner from '../components/Spinner';

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

    // Auth Check
    useEffect(() => {
        if (!localStorage.getItem('token')) {
            router.push('/login');
        }
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
                { targetUrl: url },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            setUrl('');
            mutate(`${API_URL}/api/investigations`);
        } catch (err) {
            if (axios.isAxiosError(err) && err.response?.status === 401) {
                router.push('/login');
            } else {
                alert('Error creating investigation');
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
        return <div>Failed to load</div>;
    }

    return (
        <div className="min-h-screen bg-slate-50">
            <Navbar />

            <main className="max-w-7xl mx-auto p-8">
                {/* Hero Section */}
                <div className="text-center py-12 mb-8">
                    <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight sm:text-5xl mb-4">
                        Intelligence Analysis <span className="text-blue-600">Simplified</span>
                    </h1>
                    <p className="max-w-2xl mx-auto text-lg text-slate-600 mb-8">
                        Automated OSINT collection, analysis, and visualization platform.
                        Enter a URL to start your investigation.
                    </p>

                    {/* Input Form */}
                    <form onSubmit={handleSubmit} className="max-w-xl mx-auto flex gap-2 relative">
                        <div className="relative flex-grow">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <span className="text-gray-400">🔍</span>
                            </div>
                            <input
                                type="url"
                                value={url}
                                onChange={(e) => setUrl(e.target.value)}
                                placeholder="Target URL (e.g. https://example.com)"
                                className="w-full pl-10 pr-4 py-4 border border-gray-200 rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                                required
                            />
                        </div>
                        <button
                            type="submit"
                            disabled={loading}
                            className="bg-slate-900 text-white px-8 py-4 rounded-xl font-bold hover:bg-slate-800 disabled:opacity-70 transition-all flex items-center gap-2 shadow-lg"
                        >
                            {loading ? <Spinner /> : 'Investigate'}
                        </button>
                    </form>
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
import DOMPurify from 'dompurify';

                                // ... (inside the component)

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
                            <div key={i} className="h-32 bg-slate-100 rounded-xl animate-pulse"></div>
                        ))
                    )}
                </div>
            </main>
        </div>
    );
}
