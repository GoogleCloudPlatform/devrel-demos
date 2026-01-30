"use client";

import { useEffect, useState } from "react";
import { getExperiments } from "@/lib/api";
import ExperimentsHeader from "@/components/experiments/ExperimentsHeader";
import ExperimentsTable from "@/components/experiments/ExperimentsTable";
import { Loader2 } from "lucide-react";

export default function ExperimentsPage() {
    const [experiments, setExperiments] = useState<any[] | null>(null);

    useEffect(() => {
        getExperiments().then(data => {
            // Sort by timestamp descending
            const sorted = [...data].sort((a, b) =>
                new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
            );
            setExperiments(sorted);
        });
    }, []);


    if (!experiments) {
        return (
            <div className="p-6 space-y-6">
                <ExperimentsHeader />
                <div className="flex justify-center py-20 opacity-50">
                    <Loader2 className="animate-spin mr-2" /> Loading experiments...
                </div>
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            <ExperimentsHeader />
            <ExperimentsTable experiments={experiments} />
        </div>
    );
}
