import type { Metadata } from 'next';
import { IBM_Plex_Mono } from 'next/font/google';
import './globals.css';
import { DomainProvider } from '@/lib/DomainContext';

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Synapse - Knowledge Intelligence',
  description:
    'Graph-augmented retrieval over your second brain and exam prep corpora. What you know, and what you still need to learn.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={ibmPlexMono.variable}>
      <body>
        <DomainProvider>{children}</DomainProvider>
      </body>
    </html>
  );
}