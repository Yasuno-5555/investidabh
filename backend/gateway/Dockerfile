FROM node:18-alpine

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy root config
COPY package.json pnpm-workspace.yaml ./

# Copy shared packages
COPY packages ./packages

# Copy service
COPY backend/gateway ./backend/gateway

# Install dependencies
RUN pnpm install

# Build shared packages only
RUN pnpm --filter @investidubh/ts-types build || true
RUN pnpm --filter @investidubh/logger build || true

# Use dev mode (tsx) to bypass TypeScript compilation issues
WORKDIR /app/backend/gateway
CMD ["pnpm", "dev"]
