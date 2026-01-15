import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { cn } from "@/utils/cn";

export interface Scenario {
    id: string;
    name: string;
    description: string;
}

interface ScenarioSelectorProps {
    scenarios: Scenario[];
    selectedIds: string[];
    onToggle: (id: string) => void;
    className?: string;
}

export function ScenarioSelector({ scenarios, selectedIds, onToggle, className }: ScenarioSelectorProps) {
    if (!scenarios || scenarios.length === 0) {
        return (
            <Card className={cn("border-dashed", className)}>
                <CardContent className="flex flex-col items-center justify-center p-8 text-center text-muted-foreground">
                    <p>No scenarios found.</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className={className}>
            <CardHeader>
                <CardTitle>Scenarios</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-1 gap-3">
                    {scenarios.map(scen => {
                        // Ensure IDs are compared as strings to avoid type mismatches
                        const isSelected = selectedIds.includes(String(scen.id));
                        return (
                            <button
                                key={scen.id}
                                type="button"
                                onClick={() => onToggle(String(scen.id))}
                                className={cn(
                                    "text-left p-4 panel transition-all flex items-start gap-4 border rounded-md group",
                                    isSelected
                                        ? "border-primary bg-primary/5 shadow-[0_0_0_1px] shadow-primary/20"
                                        : "border-border hover:border-accent bg-muted/20"
                                )}
                            >
                                <div className={cn(
                                    "mt-1 w-5 h-5 flex-shrink-0 rounded border flex items-center justify-center transition-colors",
                                    isSelected
                                        ? "bg-primary border-primary"
                                        : "border-muted-foreground/30 group-hover:border-muted-foreground/60"
                                )}>
                                    {isSelected && <span className="text-primary-foreground text-xs font-bold">✓</span>}
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                        <span className={cn(
                                            "font-bold text-base",
                                            isSelected ? "text-primary" : "text-foreground"
                                        )}>
                                            {scen.name || `Scenario ${scen.id}`}
                                        </span>
                                        <span className="text-xs font-mono text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded border border-border">
                                            {scen.id}
                                        </span>
                                    </div>

                                    {scen.description ? (
                                        <p className="text-sm text-muted-foreground leading-relaxed max-w-3xl">
                                            {scen.description}
                                        </p>
                                    ) : (
                                        <p className="text-sm text-muted-foreground/50 italic">No description provided.</p>
                                    )}
                                </div>
                            </button>
                        );
                    })}
                </div>
            </CardContent>
        </Card>
    );
}
