'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function RelaunchButton({ id }: { id: number }) {
    const router = useRouter();
    const [loading, setLoading] = useState(false);

    const handleRelaunch = async () => {
        if (!confirm('Are you sure you want to relaunch this experiment? This will create a new run with the same parameters.')) {
            return;
        }

        setLoading(true);
        try {
            const res = await fetch(`/api/experiments/${id}/relaunch`, {
                method: 'POST'
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || 'Failed to relaunch');
            }

            // Redirect to dashboard with started toast
            router.push('/?started=true');
        } catch (error) {
            alert('Error relaunching experiment: ' + error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <button
            onClick={handleRelaunch}
            disabled={loading}
            className="px-4 py-1.5 rounded-lg bg-blue-600/10 text-blue-400 hover:bg-blue-600 hover:text-white border border-blue-500/20 transition-all text-xs font-bold uppercase tracking-widest flex items-center gap-2"
        >
            {loading ? 'Launching...' : 'Relaunch 🚀'}
        </button>
    );
}
