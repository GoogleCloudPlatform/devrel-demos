import React from 'react';
import { cn } from '@/utils/cn';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
    helperText?: string;
}

export function Input({ label, error, helperText, className = '', ...props }: InputProps) {
    return (
        <div className="space-y-2 w-full">
            {label && <label className="block text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">{label}</label>}
            <input
                className={cn(
                    "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm text-foreground shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
                    error ? "border-destructive focus-visible:ring-destructive" : "",
                    className
                )}
                {...props}
            />
            {error && <p className="text-sm font-medium text-destructive">{error}</p>}
            {helperText && !error && <p className="text-sm text-muted-foreground">{helperText}</p>}
        </div>
    );
}

interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
    label?: string;
    error?: string;
    helperText?: string;
}

export function TextArea({ label, error, helperText, className = '', rows = 4, ...props }: TextAreaProps) {
    return (
        <div className="space-y-2 w-full">
            {label && <label className="block text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">{label}</label>}
            <textarea
                rows={rows}
                className={cn(
                    "flex min-h-[60px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
                    error ? "border-destructive focus-visible:ring-destructive" : "",
                    className
                )}
                {...props}
            />
            {error && <p className="text-sm font-medium text-destructive">{error}</p>}
            {helperText && !error && <p className="text-sm text-muted-foreground">{helperText}</p>}
        </div>
    );
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
    label?: string;
    error?: string;
    options: { value: string; label: string }[];
}

export function Select({ label, error, options, className = '', ...props }: SelectProps) {
    return (
        <div className="space-y-2 w-full">
            {label && <label className="block text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">{label}</label>}
            <div className="relative">
                <select
                    className={cn(
                        "flex h-9 w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50 appearance-none",
                        error ? "border-destructive focus:ring-destructive" : "",
                        className
                    )}
                    {...props}
                >
                    {options.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                            {opt.label}
                        </option>
                    ))}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground">
                    <svg className="h-4 w-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                </div>
            </div>
            {error && <p className="text-sm font-medium text-destructive">{error}</p>}
        </div>
    );
}
