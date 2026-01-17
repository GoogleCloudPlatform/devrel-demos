'use client';

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeSwitcher } from "../ThemeSwitcher";
import { useSidebar } from "./SidebarContext";
import { ChevronLeft, ChevronRight } from "lucide-react";

export function Sidebar() {
    const pathname = usePathname();
    const { isCollapsed, toggleSidebar } = useSidebar();

    const navItems = [
        { icon: "📊", label: "Dashboard", href: "/" },
        { icon: "📈", label: "Experiments", href: "/experiments" },
        { icon: "📝", label: "Templates", href: "/templates" },
        { icon: "🧪", label: "Scenarios", href: "/scenarios" },
    ];

    return (
        <aside className={`${isCollapsed ? 'w-[60px]' : 'w-[240px]'} bg-background border-r border-border h-screen fixed left-0 top-0 flex flex-col z-50 transition-all duration-300`}>
            {/* Header */}
            <div className={`h-[56px] flex items-center ${isCollapsed ? 'justify-center' : 'px-4'} border-b border-border relative group`}>
                <div className="flex items-center gap-2">
                    <div className="w-5 h-5 bg-primary rounded-[2px] flex items-center justify-center flex-shrink-0">
                        <span className="text-primary-foreground text-body font-black italic">T</span>
                    </div>
                    {!isCollapsed && <span className="text-header font-bold tracking-tight whitespace-nowrap overflow-hidden">Tenkai</span>}
                </div>

                {/* Toggle Button */}
                <button
                    onClick={toggleSidebar}
                    className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 bg-background border border-border rounded-full flex items-center justify-center text-muted-foreground hover:text-primary z-50 shadow-sm transition-colors"
                    title={isCollapsed ? "Expand" : "Collapse"}
                >
                    {isCollapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
                </button>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto overflow-x-hidden">
                {navItems.map((item) => {
                    const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href));
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`flex items-center gap-3 px-3 py-2 rounded-[2px] transition-colors text-body font-medium ${isActive
                                ? "bg-muted text-foreground"
                                : "text-muted-foreground hover:bg-card hover:text-foreground"
                                } ${isCollapsed ? 'justify-center' : ''}`}
                            title={isCollapsed ? item.label : undefined}
                        >
                            <span className="opacity-80 flex items-center justify-center text-lg">{item.icon}</span>
                            {!isCollapsed && <span className="whitespace-nowrap overflow-hidden">{item.label}</span>}
                        </Link>
                    );
                })}
            </nav>

            {/* Footer */}
            <div className={`p-4 border-t border-border space-y-4 ${isCollapsed ? 'flex flex-col items-center' : ''}`}>
                <ThemeSwitcher showLabel={!isCollapsed} />
                {!isCollapsed && (
                    <div className="text-body font-mono font-bold uppercase opacity-20 tracking-widest text-xs whitespace-nowrap overflow-hidden">
                        v0.3.0
                    </div>
                )}
            </div>
        </aside>
    );
}