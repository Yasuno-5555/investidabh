import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { Pool } from 'pg';
import Redis from 'ioredis';
import { v4 as uuidv4 } from 'uuid';
import { CreateInvestigationSchema, CollectorTask } from '@investidubh/ts-types';

export default async function investigationRoutes(app: FastifyInstance, options: { pool: Pool, redis: Redis }) {
    const { pool, redis } = options;

    app.addHook('onRequest', async (request: FastifyRequest, reply: FastifyReply) => {
        try {
            await request.jwtVerify();
        } catch (err) {
            reply.status(401).send({ error: "Unauthorized" });
        }
    });

    app.post('/', async (request, reply) => {
        const user = request.user as { id: string };
        const result = CreateInvestigationSchema.safeParse(request.body);
        if (!result.success) return reply.status(400).send(result.error);

        const { targetUrl } = result.data;
        const investigationId = uuidv4();

        try {
            await pool.query(
                "INSERT INTO investigations (id, target_url, status, user_id) VALUES ($1, $2, 'PENDING', $3)",
                [investigationId, targetUrl, user.id]
            );

            const task: CollectorTask = {
                id: investigationId,
                targetUrl: targetUrl,
                requestedAt: new Date().toISOString(),
            };

            await redis.lpush('tasks:collector', JSON.stringify(task));
            return { status: 'queued', id: investigationId };
        } catch (err) {
            app.log.error(err);
            return reply.status(500).send({ error: 'Internal Server Error' });
        }
    });

    app.get('/', async (request) => {
        const user = request.user as { id: string };
        const result = await pool.query(
            "SELECT * FROM investigations WHERE user_id = $1 ORDER BY created_at DESC LIMIT 20",
            [user.id]
        );
        return result.rows;
    });

    app.get('/:id', async (request, reply) => {
        const { id } = request.params as { id: string };
        const user = request.user as { id: string };
        const invResult = await pool.query(
            "SELECT * FROM investigations WHERE id = $1 AND user_id = $2",
            [id, user.id]
        );

        if (invResult.rows.length === 0) return reply.status(404).send({ error: "Not found" });

        const artResult = await pool.query("SELECT * FROM artifacts WHERE investigation_id = $1", [id]);
        const intelResult = await pool.query("SELECT * FROM intelligence WHERE investigation_id = $1", [id]);

        return { ...invResult.rows[0], artifacts: artResult.rows, intelligence: intelResult.rows };
    });
}
