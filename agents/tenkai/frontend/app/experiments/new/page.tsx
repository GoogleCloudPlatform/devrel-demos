import { getScenarios, getTemplates } from "@/app/api/api";
import ExperimentForm from "@/components/ExperimentForm";
import { PageHeader } from "@/components/ui/page-header";

export default async function NewExperimentPage() {
    const [templates, scenarios] = await Promise.all([
        getTemplates(),
        getScenarios()
    ]);

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader 
                title="Launch Experiment" 
                description="Initialize a new agent benchmarking session."
                backHref="/experiments"
            />

            <ExperimentForm templates={templates} scenarios={scenarios} />
        </div>
    );
}