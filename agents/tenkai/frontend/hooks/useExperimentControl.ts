import { useState, useCallback } from 'react';

export type ExperimentStatus = 'running' | 'ABORTED' | 'completed';

export interface UseExperimentControlOptions {
    onStatusChange?: (status: ExperimentStatus) => void;
    onAnalysisUpdate?: (analysis: string) => void;
}

export function useExperimentControl(experimentId: number | string, initialStatus: ExperimentStatus, options?: UseExperimentControlOptions) {
    const [status, setStatus] = useState<ExperimentStatus>(initialStatus);
    const [loadingAction, setLoadingAction] = useState<string | null>(null);
    const handleControl = useCallback(async (action: 'stop') => {
        setLoadingAction(action);
        try {
            const res = await fetch('/api/experiments/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: experimentId, action }),
            });
            if (res.ok) {
                let newStatus: ExperimentStatus = status;
                if (action === 'stop') newStatus = 'ABORTED';

                setStatus(newStatus);
                options?.onStatusChange?.(newStatus);
                return true;

            } else {
                const data = await res.json().catch(() => ({}));
                alert(`Failed to ${action} experiment: ${data.error || 'Unknown error'}`);
                return false;
            }
        } catch (e) {
            console.error(e);
            alert(`Error sending ${action} command`);
            return false;
        } finally {
            setLoadingAction(null);
        }
    }, [experimentId, status, options]);

    const handleExplain = useCallback(async () => {
        setLoadingAction('explain');
        try {
            const res = await fetch(`/api/experiments/${experimentId}/explain`, { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                options?.onAnalysisUpdate?.(data.analysis);
                return data.analysis;
            } else {
                const data = await res.json().catch(() => ({}));
                alert(`Failed to generate AI insights: ${data.error || 'Unknown server error'}`);
            }
        } catch (e) {
            console.error(e);
            alert('Error generating AI insights. Check console.');
        } finally {
            setLoadingAction(null);
        }
    }, [experimentId, options]);

    const handleRegenerate = useCallback(async () => {
        setLoadingAction('regenerate');
        try {
            const res = await fetch(`/api/experiments/${experimentId}/regenerate`, { method: 'POST' });
            if (res.ok) {
                window.location.reload();
            } else {
                alert('Failed to regenerate report');
            }
        } catch (e) {
            console.error(e);
            alert('Error regenerating report');
        } finally {
            setLoadingAction(null);
        }
    }, [experimentId]);

    return {
        status,
        setStatus,
        loadingAction,
        handleControl,
        handleExplain,
        handleRegenerate
    };
}
