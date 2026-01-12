'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button } from './ui/button';

import { toast } from 'sonner';

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
                toast.success("All data deleted successfully");
                router.refresh();
            } else {
                toast.error("Failed to delete all experiments");
            }
        } catch (e) {
            toast.error("Error deleting experiments");
        } finally {
            setDeleting(false);
        }
    };

    return (
        <Button
            variant="destructive"
            size="sm"
            onClick={handleDeleteAll}
            disabled={deleting}
        >
            Delete All Data
        </Button>
    );
}
