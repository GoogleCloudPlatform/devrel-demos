'use client';

import { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'dark' | 'light' | 'happy' | 'beach';

type ThemeProviderProps = {
    children: React.ReactNode;
    defaultTheme?: Theme;
    storageKey?: string;
};

type ThemeProviderState = {
    theme: Theme;
    setTheme: (theme: Theme) => void;
};

const initialState: ThemeProviderState = {
    theme: 'dark',
    setTheme: () => null,
};

const ThemeProviderContext = createContext<ThemeProviderState>(initialState);

export function ThemeProvider({
    children,
    defaultTheme = 'dark',
    storageKey = 'tenkai-ui-theme',
}: ThemeProviderProps) {
    const [theme, setTheme] = useState<Theme>(defaultTheme);

    useEffect(() => {
        const stored = localStorage.getItem(storageKey) as Theme;
        if (stored) {
            setTheme(stored);
        }
    }, [storageKey]);

    useEffect(() => {
        const root = window.document.documentElement;

        // Reset classes/attributes
        root.classList.remove('light', 'dark');
        root.removeAttribute('data-theme');

        if (theme === 'happy') {
            root.setAttribute('data-theme', 'happy');
            root.classList.add('dark');
        } else if (theme === 'beach') {
            root.setAttribute('data-theme', 'beach');
            root.classList.add('light'); // Beach is a light theme
        } else if (theme === 'light') {
            root.classList.add('light');
            root.setAttribute('data-theme', 'light');
        } else {
            root.classList.add('dark');
            root.setAttribute('data-theme', 'dark');
        }
    }, [theme]);

    const value = {
        theme,
        setTheme: (theme: Theme) => {
            localStorage.setItem(storageKey, theme);
            setTheme(theme);
        },
    };

    return (
        <ThemeProviderContext.Provider value={value}>
            {children}
        </ThemeProviderContext.Provider>
    );
}

export const useTheme = () => {
    const context = useContext(ThemeProviderContext);

    if (context === undefined)
        throw new Error('useTheme must be used within a ThemeProvider');

    return context;
};
