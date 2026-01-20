'use client';

import React from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { useSidebar } from "./SidebarContext";

export function MainLayoutWrapper({ children }: { children: React.ReactNode }) {
    const { isCollapsed } = useSidebar();

    return (
        <>
            <Sidebar />
            <main className={`min-h-screen bg-background transition-all duration-300 ${isCollapsed ? 'ml-[60px]' : 'ml-[240px]'}`}>
                {children}
            </main>
        </>
    );
}
