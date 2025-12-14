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

# Build shared packages
RUN pnpm --filter @investidubh/ts-types build
RUN pnpm --filter @investidubh/logger build

# Build Gateway
WORKDIR /app/backend/gateway
RUN pnpm build

CMD ["node", "dist/index.js"]
