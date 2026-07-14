import type { NextConfig } from 'next';
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

const nextConfig: NextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  transpilePackages: [
    '@investhome/shared',
    '@investhome/ui',
    '@investhome/auth',
    '@investhome/permissions',
    '@investhome/events',
    '@investhome/ai-runtime',
  ],
  typedRoutes: true,
};

export default withNextIntl(nextConfig);
