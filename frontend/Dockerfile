# Multi-stage build: build React app with Node 22, serve with Nginx
# syntax=docker/dockerfile:1.4

# Build with BuildKit for faster rebuilds (caches npm downloads):
#   DOCKER_BUILDKIT=1 docker build -t frontend .
# Or enable globally in /etc/docker/daemon.json: {"features": {"buildkit": true}}

# ---- Stage 1: Build frontend ----
FROM node:22-alpine AS build
WORKDIR /app

# Install Python and build dependencies for node-gyp (required for native modules)
RUN apk add --no-cache python3 make g++

# Build arguments for Vite environment variables
ARG VITE_CONTRACT_ADDRESS
ARG VITE_CHAIN_ID
ARG VITE_WALLETCONNECT_PROJECT_ID
ARG VITE_ONCHAINKIT_API_KEY
ARG VITE_PINATA_GATEWAY
ARG VITE_PINATA_GATEWAY_TOKEN

# Convert ARGs to ENV so Vite can access them during build
ENV VITE_CONTRACT_ADDRESS=$VITE_CONTRACT_ADDRESS
ENV VITE_CHAIN_ID=$VITE_CHAIN_ID
ENV VITE_WALLETCONNECT_PROJECT_ID=$VITE_WALLETCONNECT_PROJECT_ID
ENV VITE_ONCHAINKIT_API_KEY=$VITE_ONCHAINKIT_API_KEY
ENV VITE_PINATA_GATEWAY=$VITE_PINATA_GATEWAY
ENV VITE_PINATA_GATEWAY_TOKEN=$VITE_PINATA_GATEWAY_TOKEN

# Install dependencies with BuildKit cache (dramatically speeds up rebuilds)
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci || npm install

# Copy sources and build
COPY . .
RUN npm run build

# ---- Stage 2: Serve with Nginx ----
FROM nginx:1.27-alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Custom Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Use default nginx start command
