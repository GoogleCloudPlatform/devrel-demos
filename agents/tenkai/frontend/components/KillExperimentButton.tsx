'use client';

import { useState } from "react";
import { Button } from "./ui/button";

import { toast } from "sonner";

export default function KillExperimentButton({ experimentId, disabled }: { experimentId: string | number, disabled?: boolean }) {
    const [loading, setLoading] = useState(false);

    const handleKill = async () => {
        toast("Are you sure you want to kill this experiment?", {
            action: {
                label: "Confirm Kill",
                onClick: async () => {
                    setLoading(true);
                    try {
                        const res = await fetch(`/api/experiments/${experimentId}/control`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ command: 'stop' }) // API expects "command" not action
                        });

                        if (res.ok) {
                            toast.success("Kill signal sent.");
                        } else {
                            toast.error("Failed to send kill signal");
                        }
                    } catch (e) {
                        toast.error("Error sending kill signal");
                    } finally {
                        setLoading(false);
                    }
                }
            }
        });
    };

    return (
        <Button
            variant="destructive"
            size="sm"
            onClick={handleKill}
            disabled={loading || disabled}
        >
            <span className="mr-2">🛑</span> Kill
        </Button>
    );
}
