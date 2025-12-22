import Link from 'next/link';

async function getTemplates() {
    try {
        const res = await fetch('http://localhost:3000/api/templates', { cache: 'no-store' });
        if (!res.ok) throw new Error('Failed to fetch templates');
        return await res.json();
    } catch (e) {
        console.error(e);
        return [];
    }
}

export default async function TemplatesPage() {
    const templates: { id: string, name: string }[] = await getTemplates();

    return (
        <div className="p-10 space-y-10 animate-in fade-in duration-500 max-w-7xl mx-auto">
            <header className="flex justify-between items-end border-b border-white/5 pb-8">
                <div>
                    <Link href="/" className="text-xs font-bold text-blue-500 uppercase tracking-widest hover:text-blue-400 transition-colors">← Dashboard</Link>
                    <h1 className="text-4xl font-bold tracking-tight mt-2">Templates</h1>
                    <p className="text-zinc-400 mt-2">Manage experiment blueprints and default configurations.</p>
                </div>
                <Link href="/templates/new">
                    <button className="bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-6 rounded-lg shadow-lg shadow-blue-500/20 transition-all border border-blue-400/20 flex items-center gap-2 uppercase text-sm tracking-widest">
                        <span>+</span> New Template
                    </button>
                </Link>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {templates.map((template) => (
                    <Link href={`/templates/${template.id}`} key={template.id}>
                        <div className="glass p-6 rounded-2xl border border-white/5 hover:bg-white/[0.02] hover:border-blue-500/30 transition-all cursor-pointer group">
                            <div className="flex justify-between items-start mb-4">
                                <span className="text-2xl">📝</span>
                                <span className="text-zinc-500 group-hover:text-blue-400 transition-colors">→</span>
                            </div>
                            <h3 className="font-bold text-lg text-gray-200 group-hover:text-white transition-colors capitalize">
                                {template.name}
                            </h3>
                            <p className="text-sm text-zinc-500 font-mono mt-1">{template.id}</p>
                        </div>
                    </Link>
                ))}
            </div>
        </div>
    );
}
