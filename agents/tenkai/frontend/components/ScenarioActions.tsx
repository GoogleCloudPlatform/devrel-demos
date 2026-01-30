'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button } from './ui/button';

import { toast } from 'sonner';

export default function ScenarioActions({ id }: { id: string }) {
    const router = useRouter();
    const [deleting, setDeleting] = useState(false);

    const handleDelete = async () => {
        if (!confirm("Are you sure you want to delete this scenario? This cannot be undone.")) return;

        setDeleting(true);
        try {
            const res = await fetch(`/api/scenarios/${id}`, { method: 'DELETE' });
            if (res.ok) {
                toast.success("Scenario deleted successfully");
                router.push('/scenarios');
                router.refresh();
            } else {
                toast.error("Failed to delete scenario");
            }
        } catch (e) {
            toast.error("Error deleting scenario");
        } finally {
            setDeleting(false);
        }
    };

    return (
        <>
            <>
                <Link href={`/scenarios/edit?id=${id}`}>
                    <Button variant="outline" size="sm">
                        Edit
                    </Button>
                </Link>
                <Button variant="destructive" size="sm" onClick={handleDelete} disabled={deleting}>
                    Delete
                </Button>
            </>
        </>
    );
}
