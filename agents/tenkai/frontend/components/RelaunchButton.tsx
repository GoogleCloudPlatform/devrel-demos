'use client';

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "./ui/button";

export default function RelaunchButton({ experimentId }: { experimentId: string | number }) {
    const router = useRouter();
    const [loading, setLoading] = useState(false);

    const handleRelaunch = async () => {
        if (!confirm("Relaunch this experiment? It will start a new run with the same configuration.")) return;

        setLoading(true);
        try {
            const res = await fetch(`/api/experiments/${experimentId}/relaunch`, { method: 'POST' });
            if (res.ok) {
                router.push('/experiments');
            } else {
                alert("Failed to relaunch experiment");
            }
        } catch (e) {
            alert("Error relaunching experiment");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Button
            variant="outline"
            size="sm"
            onClick={handleRelaunch}
            disabled={loading}
        >
            <span className="mr-2">🚀</span> Relaunch
        </Button>
    );
}