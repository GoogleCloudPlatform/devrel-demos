'use client';

import { useEffect, useState } from 'react';

export default function Toast({ message, type = 'success', duration = 5000 }: { message: string, type?: 'success' | 'error', duration?: number }) {
    const [visible, setVisible] = useState(true);

    useEffect(() => {
        const timer = setTimeout(() => {
            setVisible(false);
        }, duration);
        return () => clearTimeout(timer);
    }, [duration]);

    if (!visible) return null;

    return (
        <div className="fixed bottom-8 right-8 z-[200] animate-in slide-in-from-right-8 duration-500 text-body">
            <div className={`flex items-center gap-4 px-6 py-4 rounded-md shadow-2xl border ${type === 'success' ? 'bg-card border-success/20 text-foreground' : 'bg-card border-destructive/20 text-foreground'
                }`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${type === 'success' ? 'bg-success/20 text-success' : 'bg-destructive/10 text-destructive'}`}>
                    {type === 'success' ? '✓' : '✕'}
                </div>
                <div>
                    <p className="font-bold">{message}</p>
                </div>
            </div>
        </div>
    );
}