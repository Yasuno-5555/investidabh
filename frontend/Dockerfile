FROM node:18-alpine

WORKDIR /app

RUN npm install -g pnpm

# Copy root config
COPY package.json pnpm-workspace.yaml ./

# Copy shared packages
COPY packages ./packages

# Copy service
COPY frontend ./frontend

# Install
RUN pnpm install

# Frontend Dev Server
WORKDIR /app/frontend
# Bind to 0.0.0.0 is implicit in Next.js dev? usually defaults to localhost or 0.0.0.0
# Better to be explicit or ensure nextdev works in docker
CMD ["pnpm", "dev", "-p", "3000", "-H", "0.0.0.0"]
