# ── Stage 1: Build ──────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

# Install dependencies first (layer cache)
COPY services/dashboard/package.json services/dashboard/package-lock.json* ./
RUN npm ci --ignore-scripts

# Copy source and build
COPY services/dashboard/ .
RUN npm run build

# ── Stage 2: Serve ──────────────────────────────────────────────
FROM nginx:1.27-alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY services/dashboard/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
