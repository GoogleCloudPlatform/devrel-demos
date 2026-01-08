import React from 'react';
import Link from 'next/link';
import { Button } from './button';

interface PageHeaderProps {
    title: string;
    description?: string;
    backHref?: string;
    backLabel?: string;
    action?: {
        label: string;
        href?: string;
        onClick?: () => void;
        icon?: React.ReactNode;
        variant?: React.ComponentProps<typeof Button>['variant'];
    };
    actions?: React.ReactNode;
    children?: React.ReactNode;
}

export function PageHeader({ title, description, backHref, backLabel = "Back", action, actions, children }: PageHeaderProps) {
    return (
        <div className="mb-12 animate-enter">
            {backHref && (
                <Link href={backHref} className="inline-flex items-center text-body text-[#a1a1aa] hover:text-white mb-6 transition-colors font-bold uppercase tracking-wider">
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path></svg>
                    {backLabel}
                </Link>
            )}

            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-8">
                <div className="space-y-2">
                    <h1 className="text-title">{title}</h1>
                    {description && <p className="text-body max-w-3xl opacity-80">{description}</p>}
                </div>

                {action && (
                    <div className="flex-shrink-0">
                        {action.href ? (
                            <Link href={action.href}>
                                <Button variant={action.variant || 'default'}>
                                    {action.icon && <span className="mr-2 flex items-center">{action.icon}</span>}
                                    {action.label}
                                </Button>
                            </Link>
                        ) : (
                            <Button
                                variant={action.variant || 'default'}
                                onClick={action.onClick}
                            >
                                {action.icon && <span className="mr-2 flex items-center">{action.icon}</span>}
                                {action.label}
                            </Button>
                        )}
                    </div>
                )}
                {actions && (
                    <div className="flex-shrink-0 flex gap-2 items-center">
                        {actions}
                    </div>
                )}
            </div>
            {children && <div className="mt-10">{children}</div>}
        </div>
    );
}
