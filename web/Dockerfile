# Dockerfile pour l'interface web SaveOS
FROM node:20-alpine AS builder

WORKDIR /app

# Copier les fichiers de package
COPY package.json ./

# devDependencies comprises : le build type-check aussi les fichiers de test
# et vitest.config.ts (cf. Dockerfile.prod). Le stage runner ne copie que la
# sortie standalone, l'image finale n'est donc pas alourdie.
RUN npm install

# Copier le code source
COPY . .

# Créer le dossier public s'il n'existe pas
RUN mkdir -p public

# Variables d'environnement pour le build
ENV NEXT_PUBLIC_API_URL=https://localhost:8000

# Build de l'application
RUN npm run build

# Image de production
FROM node:20-alpine AS runner

WORKDIR /app

# Créer un utilisateur non-root
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Créer le dossier public vide (Next.js peut fonctionner sans)
RUN mkdir -p ./public

# Copier les fichiers de build Next.js
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Changer vers l'utilisateur non-root
USER nextjs

# Exposer le port
EXPOSE 3000

# Variables d'environnement
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Commande de démarrage
CMD ["node", "server.js"]