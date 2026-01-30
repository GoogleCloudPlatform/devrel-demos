"use client";

import React, { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import ClientReportPage from "./ClientReportPage";
import { Loader2 } from "lucide-react";

function ExperimentViewContent() {
    const searchParams = useSearchParams();
    const id = searchParams.get("id");

    if (!id) return <div className="p-20 text-center text-red-500">Missing Experiment ID</div>;

    return <ClientReportPage id={id} />;
}

export default function Page() {
    return (
        <Suspense fallback={<div className="flex h-screen items-center justify-center"><Loader2 className="animate-spin" /></div>}>
            <ExperimentViewContent />
        </Suspense>
    );
}
