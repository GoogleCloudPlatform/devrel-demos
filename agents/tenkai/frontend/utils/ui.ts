

export function cn(...classes: (string | undefined | null | false)[]) {
    return classes.filter(Boolean).join(" ");
}

export function formatDuration(ns: number): string {
    const ms = ns / 1_000_000;
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    const s = ms / 1000;
    if (s < 60) return `${s.toFixed(2)}s`;
    const m = s / 60;
    return `${m.toFixed(1)}m`;
}

export function getStatusColor(status: string): string {
    switch (status?.toUpperCase()) {
        case "SUCCESS":
        case "COMPLETED":
            return "text-green-500";
        case "RUNNING":
            return "text-blue-500 animate-pulse";
        case "FAILED":
            return "text-red-500";
        case "ABORTED":
            return "text-yellow-500";
        default:
            return "text-gray-500";
    }
}

export function toSnakeCase(str: string): string {
    return str
        .toLowerCase()
        .replace(/\s+/g, '_')           // Replace spaces with _
        .replace(/[^\w-]+/g, '')       // Remove all non-word chars
        .replace(/--+/g, '_')          // Replace multiple - with single _
        .replace(/^-+/, '')             // Trim - from start of text
        .replace(/-+$/, '');            // Trim - from end of text
}
