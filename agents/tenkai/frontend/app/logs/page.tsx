'use client';

import { PageHeader } from "@/components/ui/page-header";
import { LogsViewer } from "@/components/LogsViewer";

export default function LogsPage() {
    return (
        <div className="container py-8 max-w-7xl mx-auto space-y-6">
            <PageHeader
                title="Server Logs"
                description="Debug logs from the Tenkai server process."
            />
            <div className="bg-card border rounded-lg p-6 shadow-sm">
                <LogsViewer />
            </div>
        </div>
    );
}
