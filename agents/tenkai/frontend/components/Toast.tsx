'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function Toast() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const [show, setShow] = useState(false);

    // Timer Effect
    useEffect(() => {
        if (show) {
            const timer = setTimeout(() => {
                setShow(false);
            }, 3000);
            return () => clearTimeout(timer);
        }
    }, [show]);

    // URL Check Effect
    useEffect(() => {
        if (searchParams.get('started') === 'true') {
            setShow(true);
            // Clear URL immediately so refresh doesn't trigger it again
            router.replace('/');
        }
    }, [searchParams, router]);

    if (!show) return null;

    return (
        <div className="fixed bottom-10 right-10 z-50 animate-in slide-in-from-right-10 duration-500 fade-in">
            <div className="bg-blue-600 text-white px-6 py-4 rounded-xl shadow-[0_20px_50px_rgba(37,99,235,0.3)] border border-blue-400/20 flex items-center gap-4">
                <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center shrink-0">
                    <span className="text-lg">🚀</span>
                </div>
                <div>
                    <h4 className="font-bold text-base tracking-tight">Experiment Launched</h4>
                    <p className="text-xs text-blue-100 font-medium opacity-90 mt-0.5">Your evaluation has started successfully.</p>
                </div>
                <button
                    onClick={() => setShow(false)}
                    className="ml-4 text-blue-200 hover:text-white transition-colors"
                >
                    ✕
                </button>
            </div>
        </div>
    );
}
