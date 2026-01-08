import Link from 'next/link';
import { Card } from '@/components/ui/card';

export default function SettingsPage() {
    return (
        <div className="p-8 max-w-4xl mx-auto space-y-8 animate-enter text-body">
            <div>
                <h1 className="text-title">Settings</h1>
                <p className="opacity-50 mt-2">Global framework preferences and runner configuration.</p>
            </div>

            <Card title="Framework Preferences">
                <div className="space-y-6">
                    <p className="opacity-50">Operational settings for the Tenkai orchestration engine.</p>
                    <Link href="/" className="inline-block px-6 py-2 rounded-md bg-white/5 hover:bg-white/10 transition-all font-bold border border-white/10">
                        Exit to Dashboard
                    </Link>
                </div>
            </Card>
        </div>
    );
}