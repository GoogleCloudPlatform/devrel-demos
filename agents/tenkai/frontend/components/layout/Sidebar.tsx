'use client';

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeSwitcher } from "../ThemeSwitcher";

export function Sidebar() {
    const pathname = usePathname();

    const navItems = [
        { icon: "📊", label: "Dashboard", href: "/" },
        { icon: "📈", label: "Experiments", href: "/experiments" },
        { icon: "📝", label: "Templates", href: "/templates" },
        { icon: "🧪", label: "Scenarios", href: "/scenarios" },
    ];

    return (
        <aside className="w-[240px] bg-background border-r border-border h-screen fixed left-0 top-0 flex flex-col z-50">
            {/* Header */}
            <div className="h-[56px] flex items-center px-4 border-b border-border">
                <div className="flex items-center gap-2">
                    <div className="w-5 h-5 bg-primary rounded-[2px] flex items-center justify-center">
                        <span className="text-primary-foreground text-body font-black italic">T</span>
                    </div>
                    <span className="text-header font-bold tracking-tight">Tenkai</span>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
                {navItems.map((item) => {
                    const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href));
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`flex items-center gap-3 px-3 py-2 rounded-[2px] transition-colors text-body font-medium ${isActive
                                ? "bg-muted text-foreground"
                                : "text-muted-foreground hover:bg-card hover:text-foreground"
                                }`}
                        >
                            <span className="opacity-80 flex items-center justify-center">{item.icon}</span>
                            <span>{item.label}</span>
                        </Link>
                    );
                })}
            </nav>

            {/* Footer */}
            <div className="p-4 border-t border-border space-y-4">
                <ThemeSwitcher />
                <div className="text-body font-mono font-bold uppercase opacity-20 tracking-widest text-xs">
                    v0.3.0
                </div>
            </div>
        </aside>
    );
}