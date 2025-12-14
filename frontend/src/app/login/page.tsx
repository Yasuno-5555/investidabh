'use client';

import { useState } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
    const [isRegister, setIsRegister] = useState(false);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const router = useRouter();
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login';
            const res = await axios.post(`${API_URL}${endpoint}`, { username, password });

            if (!isRegister) {
                // ログイン成功: トークン保存
                localStorage.setItem('token', res.data.token);
                router.push('/'); // ダッシュボードへ
            } else {
                // 登録成功: ログインモードへ
                alert('Registered! Please login.');
                setIsRegister(false);
            }
        } catch (err) {
            alert('Authentication failed');
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-100">
            <div className="w-full max-w-md p-8 bg-white rounded shadow-md">
                <h1 className="text-2xl font-bold mb-6 text-center">
                    {isRegister ? 'Register' : 'Login'} to Investidubh
                </h1>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Username</label>
                        <input
                            type="text"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            className="mt-1 block w-full p-2 border rounded"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            className="mt-1 block w-full p-2 border rounded"
                            required
                        />
                    </div>
                    <button type="submit" className="w-full py-2 px-4 bg-black text-white rounded hover:bg-gray-800">
                        {isRegister ? 'Register' : 'Login'}
                    </button>
                </form>
                <button
                    onClick={() => setIsRegister(!isRegister)}
                    className="w-full mt-4 text-sm text-blue-600 hover:underline"
                >
                    {isRegister ? 'Already have an account? Login' : 'Need an account? Register'}
                </button>
            </div>
        </div>
    );
}
