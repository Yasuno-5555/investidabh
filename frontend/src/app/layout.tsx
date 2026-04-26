import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'Investidubh',
    description: 'OSINT Investigation Platform',
};

import OpsecStatus from '../components/OpsecStatus';

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body className="pb-6">
                {children}
                <OpsecStatus />
            </body>
        </html>
    );
}
