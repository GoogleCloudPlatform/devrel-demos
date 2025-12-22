import Link from "next/link";

export default function ExperimentsPage() {
    return (
        <div className="p-10 space-y-8 animate-in fade-in duration-500">
            <header>
                <h2 className="text-sm font-semibold text-blue-500 uppercase tracking-widest mb-1">Laboratory</h2>
                <h1 className="text-4xl font-bold tracking-tight">Experiments</h1>
                <p className="text-zinc-500 mt-2">Manage and launch your Tenkai studies.</p>
            </header>

            <div className="glass rounded-2xl p-10 flex flex-col items-center justify-center text-center border border-white/5 shadow-2xl">
                <div className="text-6xl mb-6">🧪</div>
                <h2 className="text-2xl font-bold mb-2">Study Management</h2>
                <p className="text-zinc-400 max-w-md mx-auto mb-8">
                    This section will allow you to browse all available studies in the <code>studies/</code> directory,
                    configure parameters, and launch new runs directly from the UI.
                </p>
                <div className="flex gap-4">
                    <Link href="/" className="px-6 py-2 rounded-lg bg-white/5 hover:bg-white/10 transition-all text-sm font-bold border border-white/10">
                        Back to Dashboard
                    </Link>
                    <button className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 transition-all text-sm font-bold shadow-lg shadow-blue-500/20">
                        Coming Soon: Create Study
                    </button>
                </div>
            </div>
        </div>
    );
}
