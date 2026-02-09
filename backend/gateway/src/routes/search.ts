import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { MeiliSearch } from 'meilisearch';

export default async function searchRoutes(app: FastifyInstance) {
    const client = new MeiliSearch({
        host: process.env.MEILI_HOST || 'http://meilisearch:7700',
        apiKey: process.env.MEILI_MASTER_KEY || 'masterKey',
    });

    app.addHook('onRequest', async (request: FastifyRequest, reply: FastifyReply) => {
        try {
            await request.jwtVerify();
        } catch (err) {
            reply.status(401).send({ error: "Unauthorized" });
        }
    });

    app.get('/', async (request, reply) => {
        const { q } = request.query as { q: string };

        if (!q || q.length < 2) {
            return [];
        }

        try {
            const index = client.index('contents');
            const searchRes = await index.search(q, {
                attributesToHighlight: ['text'],
                limit: 20
            });
            return searchRes.hits;
        } catch (err) {
            app.log.error(err);
            // If index doesn't exist yet, return empty
            return [];
        }
    });
}
