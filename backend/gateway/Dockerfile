# --- Build Stage ---
FROM node:18-alpine AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy root config
COPY package.json pnpm-workspace.yaml tsconfig.base.json ./

# Copy shared packages
COPY packages ./packages

# Copy service
COPY backend/gateway ./backend/gateway

# Install dependencies
RUN pnpm install

# Build shared packages
RUN pnpm --filter @investidubh/ts-types build
RUN pnpm --filter @investidubh/logger build

# Build Gateway
RUN pnpm --filter @investidubh/gateway build

# --- Production Stage ---
FROM node:18-alpine AS runner

WORKDIR /app

RUN npm install -g pnpm

# Copy helper scripts or config if needed
COPY package.json pnpm-workspace.yaml ./

# Copy built artifacts from builder
COPY --from=builder /app/packages ./packages
COPY --from=builder /app/backend/gateway/dist ./backend/gateway/dist
COPY --from=builder /app/backend/gateway/package.json ./backend/gateway/package.json
COPY --from=builder /app/node_modules ./node_modules

WORKDIR /app/backend/gateway

ENV NODE_ENV=production
# Expose port (Fastify default 3000, or whatever config)
EXPOSE 4000

CMD ["node", "dist/app.js"]
