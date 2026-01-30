'use client';

import { useRouter } from 'next/navigation';
import { toggleLock } from '@/lib/api';
import LockToggle from '@/components/LockToggle';

interface ExperimentLockToggleProps {
    experimentId: number;
    initialLocked: boolean;
}

export default function ExperimentLockToggle({ experimentId, initialLocked }: ExperimentLockToggleProps) {
    const router = useRouter();

    const handleToggle = async (locked: boolean) => {
        const success = await toggleLock(experimentId, locked);
        if (success) {
            router.refresh(); // Refresh Server Component data
            return true;
        }
        return false;
    };

    return (
        <LockToggle
            locked={initialLocked}
            onToggle={handleToggle}
        />
    );
}
