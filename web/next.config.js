/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://localhost:8000',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'https://localhost:8000'}/api/:path*`,
      },
    ];
  },
  experimental: {
    serverComponentsExternalPackages: ['axios'],
  },
};

module.exports = nextConfig;