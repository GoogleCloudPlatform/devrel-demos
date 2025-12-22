'use client';

import Link from "next/link";
import { usePathname } from "next/navigation";

export function SidebarNav() {
    const pathname = usePathname();

    const navItems = [
        { icon: "📊", label: "Dashboard", href: "/" },
        { icon: "📈", label: "Reports", href: "/reports" },
        { icon: "📝", label: "Templates", href: "/templates" },
        { icon: "🧪", label: "Scenarios", href: "/scenarios" },
    ];

    return (
        <nav className="flex-1 space-y-2">
            {navItems.map((item) => {
                const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href));
                return (
                    <Link key={item.href} href={item.href}>
                        <SidebarItem icon={item.icon} label={item.label} active={isActive} />
                    </Link>
                );
            })}
        </nav>
    );
}

function SidebarItem({ icon, label, active = false }: { icon: string; label: string; active?: boolean }) {
    return (
        <div className={`flex items-center gap-3 px-4 py-2.5 rounded-lg cursor-pointer transition-all ${active ? "bg-white/10 text-white border border-white/10" : "text-zinc-400 hover:text-white hover:bg-white/5"
            }`}>
            <span className="text-lg">{icon}</span>
            <span className="text-sm font-medium">{label}</span>
        </div>
    );
}
