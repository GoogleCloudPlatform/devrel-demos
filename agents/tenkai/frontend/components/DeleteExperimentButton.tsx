'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button } from './ui/button';
import { Trash2 } from 'lucide-react';

import { toast } from 'sonner';

export default function DeleteExperimentButton({ id, name, compact = false }: { id: number, name: string, compact?: boolean }) {
    const router = useRouter();
    const [deleting, setDeleting] = useState(false);

    const handleDelete = async () => {
        if (!confirm(`Are you sure you want to delete experiment "${name}"?`)) return;

        setDeleting(true);
        try {
            const res = await fetch(`/api/experiments/${id}`, { method: 'DELETE' });
            if (res.ok) {
                toast.success("Experiment deleted successfully");
                if (!compact) {
                    router.push('/');
                } else {
                    router.refresh();
                }
            } else {
                toast.error("Failed to delete experiment");
            }
        } catch (e) {
            toast.error("Error deleting experiment");
        } finally {
            setDeleting(false);
        }
    };

    if (compact) {
        return (
            <Button
                variant="ghost"
                size="icon"
                onClick={handleDelete}
                disabled={deleting}
                className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                title="Delete Experiment"
            >
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">Delete</span>
            </Button>
        );
    }

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
