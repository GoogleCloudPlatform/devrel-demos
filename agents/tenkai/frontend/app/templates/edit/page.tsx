"use client";

import React, { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import ClientTemplateEditor from "./ClientTemplateEditor";
import { Loader2 } from "lucide-react";

function TemplateEditContent() {
    const searchParams = useSearchParams();
    const name = searchParams.get("name");

    if (!name) return <div className="p-20 text-center text-red-500">Missing Template Name</div>;

    return <ClientTemplateEditor name={name} />;
}

export default function Page() {
    return (
        <Suspense fallback={<div className="flex h-screen items-center justify-center"><Loader2 className="animate-spin" /></div>}>
            <TemplateEditContent />
        </Suspense>
    );
}
