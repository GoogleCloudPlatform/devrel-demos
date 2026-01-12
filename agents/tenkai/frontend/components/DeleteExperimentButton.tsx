'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button } from './ui/button';
import { Trash2 } from 'lucide-react';

import { toast } from 'sonner';

export default function DeleteExperimentButton({ id, name }: { id: number, name: string }) {
    const router = useRouter();
    const [deleting, setDeleting] = useState(false);

    const handleDelete = async () => {
        if (!confirm(`Are you sure you want to delete experiment "${name}"?`)) return;

        setDeleting(true);
        try {
            const res = await fetch(`/api/experiments/${id}`, { method: 'DELETE' });
            if (res.ok) {
                toast.success("Experiment deleted successfully");
                router.push('/');
            } else {
                toast.error("Failed to delete experiment");
            }
        } catch (e) {
            toast.error("Error deleting experiment");
        } finally {
            setDeleting(false);
        }
    };

    return (
        <Button
            variant="destructive"
            size="sm"
            onClick={handleDelete}
            disabled={deleting}
        >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
        </Button>
    );
}
