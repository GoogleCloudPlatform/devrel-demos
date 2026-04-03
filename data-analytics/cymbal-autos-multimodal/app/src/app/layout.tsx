import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Cymbal Autos | Premium Deal Finder',
  description: 'Powered by Google Cloud and BigQuery Machine Learning',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header style={{
          backgroundColor: 'rgba(255, 255, 255, 0.8)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          borderBottom: '1px solid var(--border-light)',
          position: 'sticky',
          top: 0,
          zIndex: 100,
          boxShadow: '0 2px 4px rgba(0,0,0,0.02)'
        }}>
          <div className="container" style={{
            height: '80px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              {/* Logo mimicking the classic 4-color G but refined */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '2px',
                width: '32px',
                height: '32px',
                transform: 'rotate(45deg)',
                borderRadius: '4px',
                overflow: 'hidden'
              }}>
                <div style={{ background: 'var(--accent-red)' }}></div>
                <div style={{ background: 'var(--accent-blue)' }}></div>
                <div style={{ background: 'var(--accent-yellow)' }}></div>
                <div style={{ background: 'var(--accent-green)' }}></div>
              </div>
              <h1 style={{
                fontFamily: 'var(--font-serif)',
                fontSize: '1.5rem',
                fontWeight: 600,
                color: 'var(--text-primary)',
                letterSpacing: '-0.02em'
              }}>
                Cymbal Autos
              </h1>
            </div>

            <nav style={{
              display: 'flex',
              gap: '2rem',
              fontWeight: 500,
              color: 'var(--text-secondary)'
            }}>
              <a href="#" style={{ color: 'var(--accent-blue)' }}>Inventory</a>
              <a href="#">Financing</a>
              <a href="#">How our AI works</a>
            </nav>
          </div>
        </header>

        <main style={{ minHeight: 'calc(100vh - 80px - 100px)' }}>
          {children}
        </main>

        <footer style={{
          backgroundColor: 'var(--bg-tertiary)',
          padding: '3rem 0',
          borderTop: '1px solid var(--border-light)',
          marginTop: '4rem'
        }}>
          <div className="container" style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            color: 'var(--text-secondary)',
            fontSize: '0.875rem'
          }}>
            <div>
              <p>© 2026 Cymbal Autos.</p>
              <p style={{ marginTop: '0.5rem', opacity: 0.8 }}>
                Source: Based on GSA Auctions API (CC0 1.0). Data has been modified for this demo.
              </p>
            </div>
            <p>Powered by BigQuery, Vertex AI, and Gemini.</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
