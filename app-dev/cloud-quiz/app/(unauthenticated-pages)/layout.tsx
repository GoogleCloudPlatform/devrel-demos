import Navbar from '@/app/components/navbar'
import '@/app/globals.css'

export const metadata = {
  title: 'About Cloud Quiz',
  description: 'An open-source party game to learn about Google Cloud.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <>
      <Navbar />
      <main className="mt-5 mx-auto max-w-2xl underline hover:decoration-[var(--google-cloud-blue)]">
        {children}
      </main>
    </>
  )
}
