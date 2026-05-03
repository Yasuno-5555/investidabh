import fastify, { FastifyInstance } from 'fastify';
import cors from '@fastify/cors';
import jwt from '@fastify/jwt';
import { createLogger } from '@investidubh/logger';
import RedisModule from 'ioredis';
const Redis = (RedisModule as any).default || RedisModule;
import pg from 'pg';
const { Pool } = pg;
import authRoutes from './routes/auth.js';
import investigationRoutes from './routes/investigations.js';
import searchRoutes from './routes/search.js';

export function buildApp() {
    const logger = createLogger('gateway');
    const pool = new Pool({ connectionString: process.env.DATABASE_URL });
    const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

    const app = fastify({
        logger: logger as any,
        disableRequestLogging: false
    });

    app.register(cors, { origin: '*' });

    if (!process.env.JWT_SECRET) {
        throw new Error('JWT_SECRET is required');
    }

    app.register(jwt, { secret: process.env.JWT_SECRET });

    // API Routes
    app.register(authRoutes, { prefix: '/api/auth', pool });
    app.register(investigationRoutes, { prefix: '/api/investigations', pool, redis });
    app.register(searchRoutes, { prefix: '/api/search' });

    // Basic Health Check
    app.get('/health', async () => ({ status: 'ok', timestamp: new Date().toISOString() }));
    app.get('/api/health', async () => ({ status: 'ok', scope: 'api' }));

    return { app, redis, pool };
}
