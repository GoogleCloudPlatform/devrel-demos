import { getBlocks } from "@/app/api/api";
import TemplateForm from "@/components/TemplateForm";
import { PageHeader } from "@/components/ui/page-header";

export default async function NewTemplatePage() {
    const blocks = await getBlocks();

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader
                title="Design Template"
                description="Configure a new benchmarking template."
                backHref="/templates"
                backLabel="Templates"
            />

            <TemplateForm blocks={blocks} />
        </div>
    );
}