import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'MFI Platform — Pan-African Microfinance SaaS',
  description: 'Institutional-grade microfinance management for Africa',
  manifest: '/manifest.json',
  themeColor: '#060a14',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
