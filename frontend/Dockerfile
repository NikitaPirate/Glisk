# Multi-stage build: build Next.js app with Node 22, run with standalone server
# syntax=docker/dockerfile:1.4

# Build with BuildKit for faster rebuilds (caches npm downloads):
#   DOCKER_BUILDKIT=1 docker build -t frontend .
# Or enable globally in /etc/docker/daemon.json: {"features": {"buildkit": true}}

# ---- Stage 1: Dependencies ----
FROM node:22-alpine AS deps
WORKDIR /app

# Install Python and build dependencies for node-gyp (required for native modules)
RUN apk add --no-cache python3 make g++

# Install dependencies with BuildKit cache
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci || npm install

# ---- Stage 2: Build ----
FROM node:22-alpine AS build
WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy sources
COPY . .

# Build arguments for Next.js environment variables
ARG NEXT_PUBLIC_NETWORK
ARG NEXT_PUBLIC_CONTRACT_ADDRESS
ARG NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID
ARG NEXT_PUBLIC_ONCHAINKIT_API_KEY
ARG NEXT_PUBLIC_PINATA_GATEWAY
ARG NEXT_PUBLIC_PINATA_GATEWAY_TOKEN
ARG BACKEND_URL

# Convert ARGs to ENV so Next.js can access them during build
ENV NEXT_PUBLIC_NETWORK=$NEXT_PUBLIC_NETWORK
ENV NEXT_PUBLIC_CONTRACT_ADDRESS=$NEXT_PUBLIC_CONTRACT_ADDRESS
ENV NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=$NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID
ENV NEXT_PUBLIC_ONCHAINKIT_API_KEY=$NEXT_PUBLIC_ONCHAINKIT_API_KEY
ENV NEXT_PUBLIC_PINATA_GATEWAY=$NEXT_PUBLIC_PINATA_GATEWAY
ENV NEXT_PUBLIC_PINATA_GATEWAY_TOKEN=$NEXT_PUBLIC_PINATA_GATEWAY_TOKEN
ENV BACKEND_URL=$BACKEND_URL

# Disable telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1

# Build Next.js app
RUN npm run build

# ---- Stage 3: Production ----
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built assets and standalone server
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=build --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
