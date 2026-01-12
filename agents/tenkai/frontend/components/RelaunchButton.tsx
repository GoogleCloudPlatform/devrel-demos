'use client';

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "./ui/button";

import { toast } from "sonner";

export default function RelaunchButton({ experimentId, disabled }: { experimentId: string | number, disabled?: boolean }) {
    const router = useRouter();
    const [loading, setLoading] = useState(false);

    const handleRelaunch = async () => {
        toast("Relaunch this experiment?", {
            action: {
                label: "Confirm Relaunch",
                onClick: async () => {
                    setLoading(true);
                    try {
                        const res = await fetch(`/api/experiments/${experimentId}/relaunch`, { method: 'POST' });
                        if (res.ok) {
                            toast.success("Experiment relaunched successfully!");
                            router.push('/experiments');
                        } else {
                            toast.error("Failed to relaunch experiment");
                        }
                    } catch (e) {
                        toast.error("Error relaunching experiment");
                    } finally {
                        setLoading(false);
                    }
                }
            }
        });
    };

    return (
        <Button
            variant="outline"
            size="sm"
            onClick={handleRelaunch}
            disabled={loading || disabled}
        >
            <span className="mr-2">🚀</span> Relaunch
        </Button>
    );
}