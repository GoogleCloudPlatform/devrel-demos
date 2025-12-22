'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function DeleteAllButton() {
    const router = useRouter();
    const [deleting, setDeleting] = useState(false);

    const handleDeleteAll = async () => {
        if (!confirm("⚠️ WARNING: This will delete ALL experiments and their results permanently.\n\nThis action cannot be undone.")) return;
        if (!confirm("Are you really sure?")) return;

        setDeleting(true);
        try {
            const res = await fetch('/api/experiments', { method: 'DELETE' });
            if (res.ok) {
                router.refresh();
            } else {
                alert("Failed to delete all experiments");
            }
        } catch (e) {
            alert("Error deleting experiments");
        } finally {
            setDeleting(false);
        }
    };

    return (
        <button
            onClick={handleDeleteAll}
            disabled={deleting}
            className="text-red-500 hover:text-red-400 hover:bg-red-500/10 font-bold py-2 px-4 rounded-lg transition-all text-xs tracking-widest uppercase flex items-center gap-2 border border-transparent hover:border-red-500/20"
        >
            {deleting ? 'Deleting...' : 'Delete All'}
        </button>
    );
}
