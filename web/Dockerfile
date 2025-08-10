# Dockerfile pour l'interface web SaveOS
FROM node:18-alpine AS builder

WORKDIR /app

# Copier les fichiers de package
COPY package.json ./

# Installer les dépendances
RUN npm install --only=production

# Copier le code source
COPY . .

# Variables d'environnement pour le build
ENV NEXT_PUBLIC_API_URL=https://localhost:8000

# Build de l'application
RUN npm run build

# Image de production
FROM node:18-alpine AS runner

WORKDIR /app

# Créer un utilisateur non-root
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copier les fichiers nécessaires depuis le builder
COPY --from=builder /app/public ./public
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