# --- Build Stage ---
FROM node:18 AS builder

WORKDIR /app

# Install build tools for native modules
RUN apt-get update && apt-get install -y python-is-python3 make build-essential

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
FROM node:18 AS runner

WORKDIR /app

# Install build tools for native modules
RUN apt-get update && apt-get install -y python-is-python3 make build-essential

RUN npm install -g pnpm

# Copy helper scripts or config if needed
COPY package.json pnpm-workspace.yaml tsconfig.base.json ./

# Copy shared packages
COPY packages ./packages

# Copy service
COPY backend/gateway ./backend/gateway

# Install dependencies (production)
RUN pnpm install --prod

# Copy built artifacts from builder
COPY --from=builder /app/packages ./packages
COPY --from=builder /app/backend/gateway/dist ./backend/gateway/dist

WORKDIR /app/backend/gateway

ENV NODE_ENV=production
# Expose port (Fastify default 3000, or whatever config)
EXPOSE 4000

CMD ["node", "dist/index.js"]
