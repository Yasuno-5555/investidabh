import fastify, { FastifyInstance } from 'fastify';
import cors from '@fastify/cors';
import jwt from '@fastify/jwt';
import { createLogger } from '@investidubh/logger';
import Redis from 'ioredis';
import { Pool } from 'pg';
import authRoutes from './routes/auth';
import investigationRoutes from './routes/investigations';
import searchRoutes from './routes/search';

export function buildApp(): FastifyInstance {
    const logger = createLogger('gateway');
    const pool = new Pool({ connectionString: process.env.DATABASE_URL });
    const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

    const app = fastify({
        logger: logger as any,
        disableRequestLogging: true
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

    return app;
}
