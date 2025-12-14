'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';

export default function Navbar() {
    const router = useRouter();
    const pathname = usePathname();

    const handleLogout = () => {
        localStorage.removeItem('token');
        router.push('/login');
    };

    const isActive = (path: string) => pathname === path ? 'text-blue-600 font-bold' : 'text-gray-600 hover:text-gray-900';

    return (
        <nav className="border-b bg-white/80 backdrop-blur sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16 items-center">
                    <div className="flex items-center gap-8">
                        {/* Logo */}
                        <Link href="/" className="text-xl font-bold tracking-tight text-gray-900">
                            investidubh
                            <span className="ml-1 text-[10px] align-top text-red-500 font-medium">BETA</span>
                        </Link>

                        {/* Valid Token Check - simple logic, if token exists show links */}
                        <div className="hidden md:flex gap-6 text-sm font-medium">
                            <Link href="/" className={isActive('/')}>
                                Dashboard
                            </Link>
                            <Link href="/graph" className={isActive('/graph')}>
                                Global Graph
                            </Link>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <button
                            onClick={handleLogout}
                            className="text-sm font-medium text-gray-500 hover:text-red-600 transition-colors"
                        >
                            Log out
                        </button>
                        <div className="h-8 w-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600">
                            U
                        </div>
                    </div>
                </div>
            </div>
        </nav>
    );
}
