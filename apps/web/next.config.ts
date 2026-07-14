import type { NextConfig } from 'next';

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

export default nextConfig;
