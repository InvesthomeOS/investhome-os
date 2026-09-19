import type { NextConfig } from 'next';
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

const nextConfig: NextConfig = {
  // Standalone file tracing uses symlinks; Windows without Developer Mode fails EPERM.
  ...(process.platform === 'win32' ? {} : { output: 'standalone' as const }),
  reactStrictMode: true,
  transpilePackages: [
    '@investhome/shared',
    '@investhome/ui',
    '@investhome/auth',
    '@investhome/permissions',
    '@investhome/events',
    '@investhome/ai-runtime',
  ],
  typedRoutes: false,
};

export default withNextIntl(nextConfig);
