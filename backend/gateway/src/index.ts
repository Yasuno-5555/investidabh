import { buildApp } from './app.js';
import * as dotenv from 'dotenv';
import path, { dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables from root
dotenv.config({ path: path.resolve(__dirname, '../../../.env') });

const start = async () => {
    const { app, redis, pool } = buildApp();
    const PORT = parseInt(process.env.GATEWAY_PORT || '4000');

    try {
        // Wait for Redis and Postgres to be ready
        await redis.ping();
        await pool.query('SELECT 1');
        app.log.info('Redis and PostgreSQL are connected.');

        await app.listen({ port: PORT, host: '0.0.0.0' });
        console.log(`Gateway listening on port ${PORT}`);
    } catch (err) {
        app.log.error(err);
        process.exit(1);
    }
};

start();
