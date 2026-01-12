'use client';

import { useState } from "react";
import { Button } from "./ui/button";

export default function KillExperimentButton({ experimentId }: { experimentId: string | number }) {
    const [loading, setLoading] = useState(false);

    const handleKill = async () => {
        if (!confirm("Are you sure you want to kill this experiment? Running jobs will be stopped.")) return;

        setLoading(true);
        try {
            const res = await fetch(`/api/experiments/${experimentId}/control`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: 'stop' }) // API expects "command" not action
            });

            if (res.ok) {
                alert("Kill signal sent.");
            } else {
                alert("Failed to send kill signal");
            }
        } catch (e) {
            alert("Error sending kill signal");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Button
            variant="destructive"
            size="sm"
            onClick={handleKill}
            disabled={loading}
        >
            <span className="mr-2">🛑</span> Kill
        </Button>
    );
}
