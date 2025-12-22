import Link from "next/link";
import { getExperiments } from "@/lib/api";
import ExperimentRow from "@/components/ExperimentRow";

import DeleteAllButton from "@/components/DeleteAllButton";

export default async function ReportsPage() {
    const experiments = await getExperiments();

    // Sort by timestamp descending
    const sortedExperiments = [...experiments].sort((a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );

    return (
        <div className="p-10 space-y-10 animate-in fade-in duration-500">
            <header>
                <div className="flex justify-between items-end">
                    <div>
                        <h2 className="text-base font-semibold text-blue-500 uppercase tracking-widest mb-1">Analytics</h2>
                        <h1 className="text-4xl font-bold tracking-tight">Reports</h1>
                        <p className="text-zinc-500 mt-2">Historical analysis and statistical comparisons.</p>
                    </div>
                    <DeleteAllButton />
                </div>
            </header>

            <section className="glass rounded-2xl overflow-hidden border border-white/5">
                <div className="p-6 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
                    <h3 className="text-lg font-bold">Experiment History</h3>
                    <span className="text-xs font-bold text-zinc-500 uppercase tracking-widest">
                        {sortedExperiments.length} Total Runs
                    </span>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="text-zinc-500 text-xs uppercase font-bold tracking-widest border-b border-white/5">
                                <th className="px-6 py-4 w-[200px]">Experiment</th>
                                <th className="px-6 py-4">Description</th>
                                <th className="px-6 py-4 w-[100px]">Execution</th>
                                <th className="px-6 py-4 w-[100px]">Success</th>
                                <th className="px-6 py-4 text-right w-[100px]">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {sortedExperiments.map((exp, idx) => (
                                <ExperimentRow key={idx} exp={exp} />
                            ))}
                            {sortedExperiments.length === 0 && (
                                <tr>
                                    <td colSpan={2} className="px-6 py-10 text-center text-zinc-600 text-base">No historical data available.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    );
}
