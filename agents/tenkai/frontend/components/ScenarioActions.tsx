'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button } from './ui/button';

export default function ScenarioActions({ id }: { id: string }) {
    const router = useRouter();
    const [deleting, setDeleting] = useState(false);

    const handleDelete = async () => {
        if (!confirm("Are you sure you want to delete this scenario? This cannot be undone.")) return;

        setDeleting(true);
        try {
            const res = await fetch(`/api/scenarios/${id}`, { method: 'DELETE' });
            if (res.ok) {
                router.push('/scenarios');
                router.refresh();
            } else {
                alert("Failed to delete scenario");
            }
        } catch (e) {
            alert("Error deleting scenario");
        } finally {
            setDeleting(false);
        }
    };

    return (
        <>
            <>
                <Link href={`/scenarios/${id}/edit`}>
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
