/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://localhost:8000',
  },
  async rewrites() {
    // fallback (et non un tableau nu) : ce rewrite ne doit s'appliquer que
    // si aucune route filesystem (statique OU dynamique) ne correspond.
    // Un tableau nu s'applique avant les routes dynamiques et avalerait
    // silencieusement web/app/api/**/[..]/route.ts (ex. .../snapshots/[id]/browse) —
    // ces proxys portent le token dashboard et gèrent le certificat TLS
    // self-signed, contrairement à ce rewrite brut.
    return {
      fallback: [
        {
          source: '/api/:path*',
          // Cible interne au réseau Docker (résolue côté serveur Next.js uniquement).
          // Ne pas confondre avec NEXT_PUBLIC_API_URL, qui doit être joignable depuis le navigateur.
          destination: `${process.env.API_URL || 'https://api:8000'}/api/:path*`,
        },
      ],
    };
  },
  experimental: {
    serverComponentsExternalPackages: ['axios'],
  },
};

module.exports = nextConfig;