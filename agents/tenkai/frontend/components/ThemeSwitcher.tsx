'use client';

import { useTheme } from "./ThemeProvider";
import { Button } from "./ui/button";
import { Sun, Moon, Smile, Palmtree } from "lucide-react";
import { cn } from "@/utils/cn";

import { useEffect, useState } from "react";

export function ThemeSwitcher() {
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted) {
        return (
            <div className="flex gap-1 p-1 bg-muted/20 rounded-lg border border-border/50 h-10 w-[148px]" />
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
                onClick={() => setTheme('dark')}
                className={cn("w-8 h-8 rounded-md transition-all", theme === 'dark' ? "bg-zinc-800 text-white shadow-sm" : "text-muted-foreground hover:text-foreground")}
                title="Dark Mode"
            >
                <Moon className="w-4 h-4" />
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
                onClick={() => setTheme('beach')}
                className={cn("w-8 h-8 rounded-md transition-all", theme === 'beach' ? "bg-cyan-500 text-white shadow-sm" : "text-muted-foreground hover:text-cyan-400")}
                title="Beach Mode"
            >
                <Palmtree className="w-4 h-4" />
            </Button>
        </div>
    );
}
