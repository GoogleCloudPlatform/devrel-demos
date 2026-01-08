import { useState, useEffect, useRef } from 'react';
import { Button } from "@/components/ui/button";
import { RefreshCw, FileText } from "lucide-react";

export function LogsViewer() {
    const [logs, setLogs] = useState<string>("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const endRef = useRef<HTMLDivElement>(null);

    const fetchLogs = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch('/api/logs');
            if (!res.ok) {
                throw new Error(`Failed to fetch logs: ${res.statusText}`);
            }
            const text = await res.text();
            setLogs(text);
            // Auto-scroll to bottom
            // setTimeout(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs();
        const interval = setInterval(fetchLogs, 1000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="flex flex-col h-full space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                    <FileText className="h-5 w-5" />
                    Server Logs (tenkai.log)
                </h2>
                <Button variant="outline" size="sm" onClick={fetchLogs} disabled={loading}>
                    <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                </Button>
            </div>

            <div className="flex-1 min-h-0 border rounded-md bg-zinc-950 text-zinc-50 p-4 font-mono text-xs overflow-auto h-[600px]">
                {error ? (
                    <div className="text-red-400">Error: {error}</div>
                ) : (
                    <div className="whitespace-pre-wrap font-mono">
                        {logs || "No logs available."}
                        <div ref={endRef} />
                    </div>
                )}
            </div>
        </div>
    );
}
