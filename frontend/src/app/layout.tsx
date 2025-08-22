import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { ThemeProvider } from '@/components/providers/theme-provider';
import { I18nProvider } from '@/components/providers/i18n-provider';
import { QueryProvider } from '@/components/providers/query-provider';
import { ToastProvider } from '@/components/providers/toast-provider';
import { KeyboardShortcutsProvider } from '@/components/providers/keyboard-shortcuts-provider';
import { ErrorProvider } from '@/components/providers/error-provider';
import { SidebarNav } from '@/components/layout/sidebar-nav';
import { TopNav } from '@/components/layout/top-nav';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
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
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        <I18nProvider>
          <ThemeProvider
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
          >
            <ErrorProvider>
              <QueryProvider>
                <KeyboardShortcutsProvider>
                  <div className="min-h-screen bg-background">
                    {/* Main Layout */}
                    <div className="flex h-screen">
                      {/* Sidebar */}
                      <aside className="hidden w-64 border-r border-border bg-card lg:block">
                        <SidebarNav />
                      </aside>

                      {/* Main Content Area */}
                      <div className="flex flex-1 flex-col overflow-hidden">
                        {/* Top Navigation */}
                        <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
                          <TopNav />
                        </header>

                        {/* Page Content */}
                        <main className="flex-1 overflow-auto">
                          <div className="container mx-auto px-4 py-6">
                            {children}
                          </div>
                        </main>
                      </div>
                    </div>
                  </div>
                  <ToastProvider />
                </KeyboardShortcutsProvider>
              </QueryProvider>
            </ErrorProvider>
          </ThemeProvider>
        </I18nProvider>
      </body>
    </html>
  );
}