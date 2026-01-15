'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button } from './ui/button';
import { Trash2 } from 'lucide-react';

import { toast } from 'sonner';

export default function DeleteExperimentButton({ id, name, locked }: { id: number, name: string, locked?: boolean }) {
    const router = useRouter();
    const [deleting, setDeleting] = useState(false);

    const handleDelete = async () => {
        if (locked) {
            toast.error("Experiment is locked. Unlock it first.");
            return;
        }
        if (!confirm(`Are you sure you want to delete experiment "${name}"?`)) return;

        setDeleting(true);
        try {
            const res = await fetch(`/api/experiments/${id}`, { method: 'DELETE' });
            if (res.ok) {
                toast.success("Experiment deleted successfully");
                router.push('/');
            } else {
                const msg = await res.text(); // Backend might return error text like "experiment is locked"
                // Check if JSON
                try {
                    const json = JSON.parse(msg);
                    if (json.error) toast.error(`Failed to delete: ${json.error}`);
                    else toast.error("Failed to delete experiment");
                } catch {
                    toast.error(`Failed to delete: ${msg}` || "Unknown error");
                }
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
            disabled={deleting || locked}
            title={locked ? "Experiment is locked" : "Delete Experiment"}
            className={locked ? "opacity-50 cursor-not-allowed" : ""}
        >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
        </Button>
    );
}
