import Link from "next/link";
import { getExperiments, ExperimentRecord, getGlobalStats } from "@/lib/api";
import RefreshOnInterval from "@/components/RefreshOnInterval";
import ActiveExperimentCard from "@/components/ActiveExperimentCard";
import ExperimentRow from "@/components/ExperimentRow";
import Toast from "@/components/Toast";

export default async function Home() {
  const experiments = await getExperiments();
  const { totalRuns, avgSuccessRate } = await getGlobalStats();

  // Sort by timestamp descending
  const sortedExperiments = [...experiments].sort((a, b) =>
    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  const activeExperiments = sortedExperiments.filter(e => e.status === 'running' || e.status === 'paused');
  const completedExperiments = sortedExperiments.filter(e => e.status !== 'running' && e.status !== 'paused');

  return (
    <div className="p-10 space-y-10 animate-in fade-in duration-500">
      <RefreshOnInterval active={activeExperiments.length > 0} />
      {/* Header */}
      <header className="flex justify-between items-end">
        <div className="flex items-baseline gap-6">
          <div>
            <h2 className="text-base font-semibold text-blue-500 uppercase tracking-widest mb-1">Laboratory</h2>
            <h1 className="text-4xl font-bold tracking-tight">Experiment Dashboard</h1>
          </div>

        </div>
        <div className="flex gap-4">
          <Link href="/experiments/new">
            <button className="bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-6 rounded-lg shadow-lg shadow-blue-500/20 transition-all border border-blue-400/20 flex items-center gap-2 uppercase text-sm tracking-widest">
              <span>+</span> New Experiment
            </button>
          </Link>
        </div>
      </header>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard label="Total Jobs Executed" value={totalRuns.toString()} icon="📈" />
        <StatCard label="Avg Success Rate" value={avgSuccessRate} icon="✅" />
        <StatCard label="Active Runs" value={activeExperiments.length.toString()} status={activeExperiments.length > 0 ? "LIVE" : ""} icon="⚡" />
      </div>

      <div className="space-y-10">
        {/* Active Runs */}
        {activeExperiments.length > 0 && (
          <section className="space-y-4">
            <h3 className="text-lg font-bold flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
              Active Progress
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {activeExperiments.map((exp, idx) => (
                <ActiveExperimentCard key={idx} exp={exp} index={sortedExperiments.indexOf(exp)} />
              ))}
            </div>
          </section>
        )}

        {/* History Table */}
        <section className="glass rounded-2xl overflow-hidden border border-white/5">
          <div className="p-6 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
            <h3 className="text-lg font-bold">Recent History</h3>
            <span className="text-xs font-bold text-zinc-500 uppercase tracking-widest">
              Last {completedExperiments.length} experiments
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
                {completedExperiments.map((exp, idx) => (
                  <ExperimentRow key={idx} exp={exp} />
                ))}
                {completedExperiments.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-6 py-10 text-center text-zinc-600 text-base">No historical data available.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
      <Toast />
    </div>
  );
}

function StatCard({ label, value, status, icon }: any) {
  return (
    <div className="glass p-6 rounded-2xl border border-white/10 flex flex-col gap-1 relative overflow-hidden group">
      <div className="absolute -right-2 -top-2 text-4xl opacity-5 transition-transform group-hover:scale-125 duration-500">{icon}</div>
      <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest">{label}</p>
      <div className="flex items-baseline gap-2">
        <h3 className="text-3xl font-bold tracking-tight">{value}</h3>
        {status && <span className="px-1.5 py-0.5 rounded text-[10px] bg-blue-500/20 text-blue-400 font-black tracking-widest animate-pulse">{status}</span>}
      </div>
    </div>
  );
}
