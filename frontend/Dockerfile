# Lumio dashboard — build the Vite app, then serve the static output with Caddy.
#
# Two stages so the runtime image contains only the compiled assets and a web
# server: no Node, no node_modules, no source. Keeps the deployed image small.

# ---- build stage ---------------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /app

# IMPORTANT: Vite inlines VITE_* variables into the bundle at BUILD time, not
# at runtime. Setting VITE_API_URL only as a runtime variable would silently
# produce a bundle still pointing at the localhost fallback in src/lib/api.ts.
# Railway exposes service variables to the build, so it arrives as this ARG.
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Install dependencies first so this layer caches unless the lockfile changes.
# devDependencies are required — `npm run build` runs `tsc` before `vite build`.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- serve stage ---------------------------------------------------------
FROM caddy:2-alpine

COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv

EXPOSE 3000
