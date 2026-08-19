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
        // Cible interne au réseau Docker (résolue côté serveur Next.js uniquement).
        // Ne pas confondre avec NEXT_PUBLIC_API_URL, qui doit être joignable depuis le navigateur.
        destination: `${process.env.API_URL || 'https://api:8000'}/api/:path*`,
      },
    ];
  },
  experimental: {
    serverComponentsExternalPackages: ['axios'],
  },
};

module.exports = nextConfig;