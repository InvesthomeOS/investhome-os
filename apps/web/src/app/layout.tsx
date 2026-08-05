import type { Metadata } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getMessages } from 'next-intl/server';

import { brandFontStack } from '@/lib/fonts';

import './globals.css';
import './premium-shell.css';
import './shell-v2.css';
import './executive-home.css';
import './screenshot-dashboard.css';

export const metadata: Metadata = {
  title: 'Investhome OS',
  description: 'Enterprise real-estate investment operating system',
  icons: {
    icon: [
      { url: '/brand/favicons/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/brand/favicons/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon.ico' },
    ],
    apple: [{ url: '/brand/favicons/apple-touch-icon.png', sizes: '180x180' }],
  },
  manifest: '/site.webmanifest',
};

const themeInitScript = `(function(){try{var m=localStorage.getItem('investhome-theme');var t='light';if(m==='dark'){t='dark';}else if(m==='system'&&window.matchMedia('(prefers-color-scheme: dark)').matches){t='dark';}document.documentElement.setAttribute('data-theme',t);}catch(e){document.documentElement.setAttribute('data-theme','light');}})();`;

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale} data-theme="light" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
        <style
          dangerouslySetInnerHTML={{
            __html: `html,body{font-family:${brandFontStack};}`,
          }}
        />
      </head>
      <body>
        <NextIntlClientProvider locale={locale} messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
