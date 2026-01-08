'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';

interface ExperimentActionsProps {
    id: number;
    hasAnalysis: boolean;
    onGenerateAnalysis: () => Promise<void>;
    onRegenerateReport: () => Promise<void>;
    onExportMarkdown: () => void;
}

export function ExperimentActions({ id, hasAnalysis, onGenerateAnalysis, onRegenerateReport, onExportMarkdown }: ExperimentActionsProps) {
    const [analyzing, setAnalyzing] = useState(false);
    const [regenerating, setRegenerating] = useState(false);

    const handleAnalyze = async () => {
        setAnalyzing(true);
        await onGenerateAnalysis();
        setAnalyzing(false);
    };

    const handleRegenerate = async () => {
        setRegenerating(true);
        await onRegenerateReport();
        setRegenerating(false);
    };

    return (
        <div className="flex gap-2">
            <Button
                variant="secondary"
                size="sm"
                onClick={handleAnalyze}
                disabled={analyzing}
            >
                <span className="mr-2">✨</span>
                {hasAnalysis ? 'Update Analysis' : 'AI Analysis'}
            </Button>
            <Button
                variant="outline"
                size="sm"
                onClick={onExportMarkdown}
            >
                <span className="mr-2">📄</span>
                Export MD
            </Button>
            <Button
                variant="ghost"
                size="sm"
                onClick={handleRegenerate}
                isLoading={regenerating}
                title="Sync from Database"
            >
                ↻
            </Button>
        </div>
    );
}
