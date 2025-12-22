import Link from "next/link";

export default function SettingsPage() {
    return (
        <div className="p-10 space-y-8 animate-in fade-in duration-500">
            <header>
                <h2 className="text-sm font-semibold text-blue-500 uppercase tracking-widest mb-1">Configuration</h2>
                <h1 className="text-4xl font-bold tracking-tight">Settings</h1>
                <p className="text-zinc-500 mt-2">Personalize your Tenkai environment.</p>
            </header>

            <div className="glass rounded-2xl p-10 flex flex-col items-center justify-center text-center border border-white/5 shadow-2xl">
                <div className="text-6xl mb-6">⚙️</div>
                <h2 className="text-2xl font-bold mb-2">Framework Preferences</h2>
                <p className="text-zinc-400 max-w-md mx-auto mb-8">
                    Configure default models, concurrency limits, API keys, and UI theme preferences.
                </p>
                <div className="flex gap-4">
                    <Link href="/" className="px-6 py-2 rounded-lg bg-white/5 hover:bg-white/10 transition-all text-sm font-bold border border-white/10">
                        Back to Dashboard
                    </Link>
                </div>
            </div>
        </div>
    );
}
