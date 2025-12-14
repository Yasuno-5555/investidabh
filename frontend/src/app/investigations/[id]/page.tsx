'use client';

import { useEffect } from 'react';
import useSWR from 'swr';
import axios from 'axios';
import { useParams, useRouter } from 'next/navigation';

const fetcher = (url: string) => {
    const token = localStorage.getItem('token');
    return axios.get(url, {
        headers: { Authorization: `Bearer ${token}` }
    }).then(res => res.data);
};
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

export default function InvestigationDetail() {
    const { id } = useParams();
    const router = useRouter();

    // Auth Check
    useEffect(() => {
        if (!localStorage.getItem('token')) {
            router.push('/login');
        }
    }, [router]);

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
        </div>
            
            {/* Export & Status */ }
    <div className="flex gap-4 items-center">
        {investigation.status === 'COMPLETED' && (
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
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm flex items-center gap-2"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Export PDF
            </button>
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
                <h2 className="text-xl font-bold mb-4">Extracted Intelligence</h2>
                <div className="bg-white border rounded overflow-hidden">
                    <table className="w-full text-left">
                        <thead className="bg-gray-50 text-sm uppercase text-gray-500">
                            <tr>
                                <th className="px-6 py-3">Type</th>
                                <th className="px-6 py-3">Value</th>
                                <th className="px-6 py-3">Confidence</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y">
                            {investigation.intelligence.map((item: any) => (
                                <tr key={item.id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{item.type}</td>
                                    <td className="px-6 py-4 text-sm text-gray-500 font-mono select-all">{item.value}</td>
                                    <td className="px-6 py-4 text-sm text-gray-500">{item.confidence}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        )
    }
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
