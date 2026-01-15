import { getExperiments } from "@/app/api/api";
import ExperimentsHeader from "@/components/experiments/ExperimentsHeader";
import ExperimentsTable from "@/components/experiments/ExperimentsTable";

export default async function ExperimentsPage() {
    const experiments = await getExperiments();

    // Sort by timestamp descending
    const sortedExperiments = [...experiments].sort((a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );

    return (
        <div className="p-6 space-y-6">
            <ExperimentsHeader />
            <ExperimentsTable experiments={sortedExperiments} />
        </div>
    );
}

