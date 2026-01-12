import { cn } from "@/utils/cn";

interface ProgressBarProps {
    percentage: number;
    completed: number;
    total: number;
    status: string;
    className?: string;
    showLabel?: boolean;
}

export default function ProgressBar({ percentage, completed, total, status, className, showLabel = true }: ProgressBarProps) {
    const isCompleted = status?.toUpperCase() === 'COMPLETED';
    const isAborted = status?.toUpperCase() === 'ABORTED';
    const isRunning = status?.toUpperCase() === 'RUNNING';

    // Status Banner Style (Primary)
    // Running: Indigo (#6366f1)
    // Aborted: Zinc/Gray
    // Completed: Emerald/Green
    // Queued/Default: Blue/Indigo

    let barColor = "bg-indigo-500";
    if (isCompleted) barColor = "bg-emerald-500";
    if (isAborted) barColor = "bg-zinc-600";
    if (isRunning) barColor = "bg-indigo-500"; // StatusBanner uses #6366f1 which is indigo-500

    return (
        <div className={cn("flex flex-col gap-1", className)}>
            {showLabel && (
                <div className="flex justify-between text-xs font-mono">
                    <span className={cn(
                        "font-bold",
                        percentage === 100 ? "text-emerald-500" : "text-indigo-400"
                    )}>{percentage.toFixed(0)}%</span>
                    <span className="text-muted-foreground">{completed}/{total}</span>
                </div>
            )}
            <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                <div
                    className={cn(
                        "h-full transition-all duration-1000 ease-out",
                        barColor
                    )}
                    style={{ width: `${percentage}%` }}
                />
            </div>
        </div>
    );
}
