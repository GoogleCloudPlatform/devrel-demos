'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function RefreshOnInterval({ active }: { active: boolean }) {
    const router = useRouter();

    useEffect(() => {
        // If there are active experiments, refresh more frequently
        // Otherwise, refresh occasionally to detect new ones
        	const intervalTime = active ? 1000 : 5000;
        const interval = setInterval(() => {
            router.refresh();
        }, intervalTime);

        return () => clearInterval(interval);
    }, [active, router]);

    return null;
}
