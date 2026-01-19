'use client';

import { useTheme } from "./ThemeProvider";
import { Button } from "./ui/button";
import { Sun, Moon, Smile, Palmtree, Skull, Ghost, Gamepad2 } from "lucide-react";
import { cn } from "@/lib/utils";

import { useEffect, useState } from "react";

export function ThemeSwitcher({ showLabel = true }: { showLabel?: boolean }) {
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted) {
        return (
            <div className={cn("flex gap-1 p-1 bg-muted/20 rounded-lg border border-border/50 transition-all", showLabel ? "h-10 w-[148px]" : "h-10 w-10")} />
        );
    }

    const cycleTheme = () => {
        // Light, Pacman, Tropical, Happy, Dracula, Dark
        const themes = [
            { name: 'light', icon: Sun },
            { name: 'pacman', icon: Gamepad2 },
            { name: 'tropical', icon: Palmtree },
            { name: 'happy', icon: Smile },
            { name: 'dracula', icon: Ghost },
            { name: 'dark', icon: Moon },
        ];
        const currentIdx = themes.findIndex(t => t.name === theme);
        const next = themes[(currentIdx + 1) % themes.length].name;
        setTheme(next as any);
    };

    if (!showLabel) {
        const themes = [
            { name: 'light', icon: Sun },
            { name: 'pacman', icon: Gamepad2 },
            { name: 'tropical', icon: Palmtree },
            { name: 'happy', icon: Smile },
            { name: 'dracula', icon: Ghost },
            { name: 'dark', icon: Moon },
        ];
        const currentThemeIcon = themes.find(t => t.name === theme)?.icon || Moon;
        const IconComponent = currentThemeIcon;

        return (
            <div className="flex justify-center w-full">
                <Button variant="ghost" size="icon" onClick={cycleTheme} className="w-10 h-10 rounded-md bg-muted/20 border border-border/50 text-foreground hover:bg-muted/40" title={`Current: ${theme} (Click to cycle)`}>
                    <IconComponent className="w-4 h-4" />
                </Button>
            </div>
        );
    }

    return (
        <div className="flex gap-1 p-1 bg-muted/20 rounded-lg border border-border/50">
            <Button
                variant="ghost"
                size="icon"
                onClick={() => setTheme('light')}
                className={cn("w-8 h-8 rounded-md transition-all", theme === 'light' ? "bg-white text-zinc-900 shadow-sm" : "text-muted-foreground hover:text-foreground")}
                title="Light Mode"
            >
                <Sun className="w-4 h-4" />
            </Button>
            <Button
                variant="ghost"
                size="icon"
                onClick={() => setTheme('pacman')}
                className={cn("w-8 h-8 rounded-md transition-all", theme === 'pacman' ? "bg-yellow-400 text-black shadow-sm" : "text-muted-foreground hover:text-yellow-400")}
                title="Pacman Mode"
            >
                <Gamepad2 className="w-4 h-4" />
            </Button>
            <Button
                variant="ghost"
                size="icon"
                onClick={() => setTheme('tropical')}
                className={cn("w-8 h-8 rounded-md transition-all", theme === 'tropical' ? "bg-emerald-500 text-white shadow-sm" : "text-muted-foreground hover:text-emerald-500")}
                title="Tropical Mode"
            >
                <Palmtree className="w-4 h-4" />
            </Button>
            <Button
                variant="ghost"
                size="icon"
                onClick={() => setTheme('happy')}
                className={cn("w-8 h-8 rounded-md transition-all", theme === 'happy' ? "bg-pink-500 text-white shadow-sm" : "text-muted-foreground hover:text-pink-400")}
                title="Happy Mode"
            >
                <Smile className="w-4 h-4" />
            </Button>
            <Button
                variant="ghost"
                size="icon"
                onClick={() => setTheme('dracula')}
                className={cn("w-8 h-8 rounded-md transition-all", theme === 'dracula' ? "bg-red-500 text-white shadow-sm" : "text-muted-foreground hover:text-red-500")}
                title="Dracula Mode"
            >
                <Ghost className="w-4 h-4" />
            </Button>
            <Button
                variant="ghost"
                size="icon"
                onClick={() => setTheme('dark')}
                className={cn("w-8 h-8 rounded-md transition-all", theme === 'dark' ? "bg-zinc-800 text-white shadow-sm" : "text-muted-foreground hover:text-foreground")}
                title="Dark Mode"
            >
                <Moon className="w-4 h-4" />
            </Button>
        </div>
    );
}
