import type { Metadata } from 'next';
import { Inter, Poppins, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { ThemeProvider } from '@/components/providers/theme-provider';
import { I18nProvider } from '@/components/providers/i18n-provider';
import { QueryProvider } from '@/components/providers/query-provider';
import { ToastProvider } from '@/components/providers/toast-provider';
import { KeyboardShortcutsProvider } from '@/components/providers/keyboard-shortcuts-provider';
import { ErrorProvider } from '@/components/providers/error-boundary';
import { LoadingProvider } from '@/components/providers/loading-provider';
import { AuthBootstrap } from '@/components/providers/auth-bootstrap';
import { AppShell } from '@/components/layout/app-shell';
import { GdprBanner } from '@/components/GdprBanner';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const poppins = Poppins({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-heading',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: 'OSINT Lead Generator',
    template: '%s | OSINT Lead Generator',
  },
  description: 'Profesjonell B2B lead-generering med OSINT-teknikker',
  keywords: ['OSINT', 'B2B', 'Lead Generation', 'Intelligence', 'Norge'],
  authors: [{ name: 'OSINT Team' }],
  creator: 'OSINT Lead Generator',
  metadataBase: new URL('http://localhost:3000'),
  openGraph: {
    type: 'website',
    locale: 'nb_NO',
    url: 'http://localhost:3000',
    title: 'OSINT Lead Generator',
    description: 'Profesjonell B2B lead-generering med OSINT-teknikker',
    siteName: 'OSINT Lead Generator',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'OSINT Lead Generator',
    description: 'Profesjonell B2B lead-generering med OSINT-teknikker',
  },
  robots: {
    index: false,
    follow: false,
    googleBot: {
      index: false,
      follow: false,
    },
  },
};

interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="nb" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${poppins.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        <I18nProvider>
          <ThemeProvider
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
          >
            <ErrorProvider>
              <LoadingProvider>
                <QueryProvider>
                  <AuthBootstrap />
                  <KeyboardShortcutsProvider>
                    <AppShell>{children}</AppShell>
                    <ToastProvider />
                    <GdprBanner />
                  </KeyboardShortcutsProvider>
                </QueryProvider>
              </LoadingProvider>
            </ErrorProvider>
          </ThemeProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
