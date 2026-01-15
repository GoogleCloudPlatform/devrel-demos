'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Lock, LockOpen } from 'lucide-react';
import { toast } from 'sonner';

interface LockToggleProps {
    locked: boolean;
    onToggle: (locked: boolean) => Promise<boolean>; // Returns success
    className?: string;
}

export default function LockToggle({ locked, onToggle, className }: LockToggleProps) {
    const [isLoading, setIsLoading] = useState(false);

    const handleToggle = async (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();

        setIsLoading(true);
        try {
            const success = await onToggle(!locked);
            if (success) {
                toast.success(locked ? "Unlocked" : "Locked");
            }
        } catch (err) {
            console.error(err);
            toast.error("Failed to toggle lock");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Button
            variant="ghost"
            size="sm"
            onClick={handleToggle}
            disabled={isLoading}
            className={className}
            title={locked ? "Unlock" : "Lock"}
        >
            {locked ? (
                <Lock className="w-4 h-4 text-amber-500" />
            ) : (
                <LockOpen className="w-4 h-4 text-muted-foreground opacity-50 hover:opacity-100" />
            )}
        </Button>
    );
}
