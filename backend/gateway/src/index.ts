import { buildApp } from './app.js';
import * as dotenv from 'dotenv';
import path from 'path';

// Load environment variables from root
dotenv.config({ path: path.resolve(__dirname, '../../../.env') });

const start = async () => {
    const app = buildApp();
    const PORT = parseInt(process.env.GATEWAY_PORT || '4000');

    try {
        await app.listen({ port: PORT, host: '0.0.0.0' });
        console.log(`Gateway listening on port ${PORT}`);
    } catch (err) {
        app.log.error(err);
        process.exit(1);
    }
};

start();
