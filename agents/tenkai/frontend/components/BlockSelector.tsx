'use client';

import { useState, useEffect } from 'react';
import { Select } from './ui/input'; // Using the Select from ui/input as before
import { ConfigBlock, ConfigBlockType } from '@/types/domain';

interface BlockSelectorProps {
    type: ConfigBlockType;
    label: string;
    onSelect: (block: ConfigBlock) => void;
    className?: string;
}

export function BlockSelector({ type, label, onSelect, className }: BlockSelectorProps) {
    const [blocks, setBlocks] = useState<ConfigBlock[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchBlocks = async () => {
            try {
                const res = await fetch(`/api/blocks?type=${type}`);
                if (res.ok) {
                    const data = await res.json();
                    setBlocks(data || []);
                }
            } catch (error) {
                console.error("Failed to fetch blocks", error);
            } finally {
                setLoading(false);
            }
        };
        fetchBlocks();
    }, [type]);

    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const id = parseInt(e.target.value);
        const block = blocks.find(b => b.id === id);
        if (block) {
            onSelect(block);
        }
    };

    if (loading) return <div className="text-xs text-muted-foreground">Loading blocks...</div>;

    return (
        <Select
            label={label}
            options={blocks.map(b => ({ value: String(b.id), label: b.name }))}
            onChange={handleChange}
            className={className}
        />
    );
}
