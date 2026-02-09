import fastify, { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import cors from '@fastify/cors';
import { createLogger } from '@investidubh/logger';
import Redis from 'ioredis';
import { v4 as uuidv4 } from 'uuid';
import { Pool } from 'pg';
import * as Minio from 'minio';
import { CreateInvestigationSchema, CollectorTask } from '@investidubh/ts-types';
import jwt from '@fastify/jwt';
import bcrypt from 'bcryptjs';

// Move Meilisearch requirement to global scope but initialize lazily or check if needed
// For better practices, we should initialize it once if possible.
const { MeiliSearch } = require('meilisearch');

export function buildApp(): FastifyInstance {
    const logger = createLogger('gateway');
    const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
    const pool = new Pool({
        connectionString: process.env.DATABASE_URL
    });

    const minioClient = new Minio.Client({
        endPoint: process.env.MINIO_ENDPOINT_HOST || 'minio',
        port: parseInt(process.env.MINIO_ENDPOINT_PORT || '9000'),
        useSSL: false,
        accessKey: process.env.MINIO_ROOT_USER || 'admin',
        secretKey: process.env.MINIO_ROOT_PASSWORD || 'password'
    });

    // Initialize Meilisearch client once
    const meiliClient = new MeiliSearch({
        host: process.env.MEILI_HOST || 'http://meilisearch:7700',
        apiKey: process.env.MEILI_MASTER_KEY || 'masterKey',
    });

    const app = fastify({
        logger: logger as any,
        disableRequestLogging: true
    });

    // 1. CORS Production Config
    const allowedOrigins = process.env.ALLOWED_ORIGINS
        ? process.env.ALLOWED_ORIGINS.split(',')
        : ['http://localhost:3000'];

    app.register(cors, {
        origin: allowedOrigins,
        credentials: true
    });

    // 2. Rate Limiting (DOS Protection)
    // Dynamic import to avoid issues if not yet installed, 
    // though ideally it should be in package.json
    const rateLimit = require('@fastify/rate-limit');
    app.register(rateLimit, {
        max: 100,
        timeWindow: '1 minute',
        // Exclude health check from rate limit
        allowList: ['/health']
    });

    // --- [Security] JWT Setup ---
    if (!process.env.JWT_SECRET) {
        throw new Error('FATAL: JWT_SECRET environment variable is not set. Refusing to start for security reasons.');
    }

    app.register(jwt, {
        secret: process.env.JWT_SECRET
    });

    // Authentication Middleware
    app.decorate("authenticate", async function (request: FastifyRequest, reply: FastifyReply) {
        try {
            await request.jwtVerify();
        } catch (err) {
            reply.status(401).send({ error: "Unauthorized", code: "UNAUTHORIZED", details: err instanceof Error ? err.message : String(err) });
        }
    });

    app.get('/health', async () => {
        return { status: 'ok', timestamp: new Date().toISOString() };
    });

    // --- [Auth API] ---

    // User Register
    app.post('/api/auth/register', async (request, reply) => {
        const { username, password } = request.body as any;

        if (!username || !password) return reply.status(400).send("Missing credentials");

        const hashedPassword = await bcrypt.hash(password, 10);

        try {
            const res = await pool.query(
                "INSERT INTO users (username, password_hash) VALUES ($1, $2) RETURNING id, username",
                [username, hashedPassword]
            );
            return res.rows[0];
        } catch (err) {
            return reply.status(409).send("Username already exists");
        }
    });

    // Login
    app.post('/api/auth/login', async (request, reply) => {
        const { username, password } = request.body as any;
        app.log.info({ msg: 'Login attempt', username });

        const res = await pool.query("SELECT * FROM users WHERE username = $1", [username]);
        const user = res.rows[0];

        if (!user) {
            app.log.warn({ msg: 'Login failed: User not found', username });
            return reply.status(401).send({ message: "Invalid credentials" });
        }

        const isMatch = await bcrypt.compare(password, user.password_hash);
        app.log.info({
            msg: 'Password check',
            username,
            hashLength: user.password_hash?.length,
            isMatch
        });

        if (!isMatch) {
            app.log.warn({ msg: 'Login failed: Password mismatch', username });
            return reply.status(401).send({ message: "Invalid credentials" });
        }

        // Token Issuance
        const token = app.jwt.sign({ id: user.id, username: user.username });
        return { token };
    });

    // --- [Protected Routes] ---

    // Create Investigation
    app.post('/api/investigations', {
        onRequest: [app.authenticate]
    }, async (request, reply) => {
        const user = request.user as { id: string };

        // 1. Validation
        const result = CreateInvestigationSchema.safeParse(request.body);
        if (!result.success) {
            return reply.status(400).send(result.error);
        }
        const { targetUrl } = result.data;

        // 2. Task ID Generation
        const investigationId = uuidv4();

        try {
            // 3. Create DB Record (Linked to User)
            await pool.query(
                "INSERT INTO investigations (id, target_url, status, user_id) VALUES ($1, $2, 'PENDING', $3)",
                [investigationId, targetUrl, user.id]
            );

            // 4. Create Collector Task
            const task: CollectorTask = {
                id: investigationId,
                targetUrl: targetUrl,
                requestedAt: new Date().toISOString(),
            };

            // 5. Push to Redis Queue
            await redis.lpush('tasks:collector', JSON.stringify(task));
            app.log.info({ msg: 'Task queued', taskId: investigationId, target: targetUrl, userId: user.id });
        } catch (err) {
            app.log.error({ msg: 'Failed to create investigation', err: err instanceof Error ? err.message : err });
            return reply.status(500).send({ error: 'Internal Server Error' });
        }

        return { status: 'queued', id: investigationId };
    });

    // List Investigations
    app.get('/api/investigations', {
        onRequest: [app.authenticate]
    }, async (request, reply) => {
        const user = request.user as { id: string };
        try {
            const result = await pool.query(
                "SELECT * FROM investigations WHERE user_id = $1 ORDER BY created_at DESC LIMIT 20",
                [user.id]
            );
            return result.rows;
        } catch (err) {
            app.log.error({ msg: 'Failed to fetch investigations', err: err instanceof Error ? err.message : err });
            return reply.status(500).send({ error: 'Internal Server Error' });
        }
    });

    // Get Single Investigation
    app.get('/api/investigations/:id', {
        onRequest: [app.authenticate]
    }, async (request, reply) => {
        const { id } = request.params as { id: string };
        const user = request.user as { id: string };

        try {
            // Strict ownership check (Removed legacy OR user_id IS NULL)
            const invResult = await pool.query(
                "SELECT * FROM investigations WHERE id = $1 AND user_id = $2",
                [id, user.id]
            );

            if (invResult.rows.length === 0) {
                return reply.status(404).send({ error: "Not found or access denied" });
            }

            // Fetch Artifacts
            const artResult = await pool.query(
                "SELECT * FROM artifacts WHERE investigation_id = $1",
                [id]
            );

            // Fetch Intelligence
            const intelResult = await pool.query(
                "SELECT * FROM intelligence WHERE investigation_id = $1",
                [id]
            );

            return {
                ...invResult.rows[0],
                artifacts: artResult.rows,
                intelligence: intelResult.rows
            };
        } catch (err) {
            app.log.error({ msg: 'Failed to fetch investigation', err: err instanceof Error ? err.message : err });
            return reply.status(500).send({ error: 'Internal Server Error' });
        }
    });

    // Artifact Proxy API (2. Artifact Access Control Added)
    app.get('/api/artifacts/:id/content', {
        onRequest: [app.authenticate]
    }, async (request, reply) => {
        const { id } = request.params as { id: string };
        const user = request.user as { id: string };

        try {
            // Verify ownership via investigation join
            const artResult = await pool.query(
                `SELECT a.storage_path, a.artifact_type, i.user_id
                 FROM artifacts a
                 JOIN investigations i ON a.investigation_id = i.id
                 WHERE a.id = $1 AND i.user_id = $2`,
                [id, user.id]
            );

            if (artResult.rows.length === 0) {
                return reply.status(404).send({ error: "Artifact not found or access denied" });
            }

            const { storage_path, artifact_type } = artResult.rows[0];
            const bucketName = 'raw-data';

            let contentType = 'application/octet-stream';
            if (artifact_type === 'screenshot') contentType = 'image/png';
            if (artifact_type === 'html') contentType = 'text/html';

            reply.header('Content-Type', contentType);
            // 🛡️ Security Headers for Artifacts
            reply.header('X-Content-Type-Options', 'nosniff');
            reply.header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:;");

            if (artifact_type === 'html') {
                // Force download for HTML to prevent script execution in the same origin
                reply.header('Content-Disposition', `attachment; filename="artifact-${id}.html"`);
            }

            const dataStream = await minioClient.getObject(bucketName, storage_path);
            return reply.send(dataStream);

        } catch (err) {
            app.log.error({ msg: 'Storage error', err: err instanceof Error ? err.message : err });
            return reply.status(500).send({ error: "Storage error" });
        }
    });

    // Search API
    app.get('/api/search', {
        onRequest: [app.authenticate]
    }, async (request, reply) => {
        const { q } = request.query as { q: string };

        if (!q) return [];

        try {
            const index = meiliClient.index('contents');
            const user = request.user as { id: string };
            const searchRes = await index.search(q, {
                attributesToCrop: ['text'],
                cropLength: 50,
                limit: 10,
                filter: `user_id = '${user.id}'`
            });

            return searchRes.hits.map((hit: any) => ({
                id: hit.investigation_id,
                url: hit.url,
                snippet: hit._formatted?.text || hit.text?.substring(0, 100) + '...'
            }));
        } catch (err) {
            app.log.error({ msg: 'Search failed', err: err instanceof Error ? err.message : err });
            return reply.status(500).send({ error: "Search failed" });
        }
    });

    // PDF Export API (3. Streaming Screenshot)
    app.get('/api/investigations/:id/export', {
        onRequest: [app.authenticate]
    }, async (request, reply) => {
        const { id } = request.params as { id: string };
        const user = request.user as { id: string };

        try {
            // Strict ownership check
            const invResult = await pool.query(
                "SELECT * FROM investigations WHERE id = $1 AND user_id = $2",
                [id, user.id]
            );

            if (invResult.rows.length === 0) {
                return reply.status(404).send("Not found");
            }
            const investigation = invResult.rows[0];

            // Intelligence Fetch
            const intelResult = await pool.query(
                "SELECT * FROM intelligence WHERE investigation_id = $1 ORDER BY score DESC",
                [id]
            );

            // Screenshot Path Fetch
            const artResult = await pool.query(
                "SELECT storage_path FROM artifacts WHERE investigation_id = $1 AND artifact_type = 'screenshot'",
                [id]
            );

            const PDFDocument = require('pdfkit');
            const doc = new PDFDocument({ margin: 50 });

            reply.header('Content-Type', 'application/pdf');
            reply.header('Content-Disposition', `attachment; filename="report-${id}.pdf"`);

            // Stream directly to reply.raw
            doc.pipe(reply.raw);

            // --- Header ---
            doc.fontSize(24).text('Investidubh Intelligence Report', { align: 'center' });
            doc.moveDown();

            doc.fontSize(10).text(`Target: ${investigation.target_url}`);
            doc.text(`ID: ${investigation.id}`);
            doc.text(`Generated: ${new Date().toLocaleString()}`);
            doc.moveDown();

            // --- Screenshot (Efficiently Buffered for pdfkit) ---
            if (artResult.rows.length > 0) {
                try {
                    const bucketName = 'raw-data';
                    const stream = await minioClient.getObject(bucketName, artResult.rows[0].storage_path);

                    doc.text('Captured Screenshot', { underline: true });
                    doc.moveDown(0.5);

                    // pdfkit doc.image requires a Buffer or Path. 
                    // While we can't stream directly to doc.image in standard pdfkit, 
                    // we will consume the stream.
                    const chunks: any[] = [];
                    for await (const chunk of stream) chunks.push(chunk);
                    const buffer = Buffer.concat(chunks);
                    doc.image(buffer, { fit: [500, 300], align: 'center' });
                    doc.moveDown();
                } catch (e) {
                    doc.text('(Screenshot unavailable)');
                }
            }

            // --- Intelligence Table ---
            doc.addPage();
            doc.fontSize(16).text('PRIORITY INTELLIGENCE', { underline: true });
            doc.moveDown();

            let y = doc.y;
            doc.fontSize(10).font('Helvetica-Bold');
            doc.text('Entity', 50, y);
            doc.text('Type', 250, y);
            doc.text('Score', 350, y);
            doc.text('Notes', 450, y);

            doc.moveTo(50, y + 15).lineTo(550, y + 15).stroke();
            y += 20;
            doc.font('Helvetica');

            intelResult.rows.forEach((item: any) => {
                if (y > 700) {
                    doc.addPage();
                    y = 50;
                }

                const score = item.score || 0;
                const isHighPriority = score >= 50;

                if (isHighPriority) doc.fillColor('red');
                else doc.fillColor('black');

                doc.text(item.value.substring(0, 40), 50, y, { width: 190, lineBreak: false });
                doc.fillColor('black');
                doc.text(item.type, 250, y);
                doc.text(`${score.toFixed(0)}`, 350, y);
                doc.text(item.metadata?.notes || '', 450, y);

                y += 20;
            });

            doc.moveDown(2);
            doc.fontSize(8).text('Generated by Investidubh - Automated OSINT Platform', { align: 'center', color: 'grey' });

            doc.end();
            // reply.raw.end() is called by doc.pipe/doc.end
            return reply;

        } catch (err) {
            app.log.error({ msg: 'Export failed', err: err instanceof Error ? err.message : err });
            return reply.status(500).send({ error: "Export failed" });
        }
    });

    // --- [Phase 30] Intelligence Report Pro - PDF Generation ---
    app.post('/api/report/generate', {
        onRequest: [app.authenticate]
    }, async (request: FastifyRequest, reply: FastifyReply) => {
        const user = request.user as { id: string };
        const { investigation_id, graph_image } = request.body as {
            investigation_id: string;
            graph_image?: string; // Base64 PNG
        };

        try {
            // Fetch investigation
            const invResult = await pool.query(
                "SELECT * FROM investigations WHERE id = $1 AND user_id = $2",
                [investigation_id, user.id]
            );

            if (invResult.rowCount === 0) {
                return reply.status(404).send({ error: "Investigation not found" });
            }

            const investigation = invResult.rows[0];

            // Fetch graph data for insights
            const invIds = [investigation_id];
            const intelRows = await pool.query(
                "SELECT * FROM intelligence WHERE investigation_id = ANY($1::uuid[])",
                [invIds]
            );

            // Calculate basic stats
            const entitySet = new Set<string>();
            intelRows.rows.forEach((item: any) => {
                entitySet.add(`${item.entity_type}-${item.normalized_value}`);
            });

            // Since we don't have the analysis service running here, generate a simple PDF
            // In production, this would call the Python reporter service
            const PDFDocument = require('pdfkit');
            const doc = new PDFDocument({ margin: 50 });

            const chunks: Buffer[] = [];
            doc.on('data', (chunk: Buffer) => chunks.push(chunk));
            doc.on('end', () => {
                const pdfBuffer = Buffer.concat(chunks);
                reply.header('Content-Type', 'application/pdf');
                reply.header('Content-Disposition', `attachment; filename="report-${investigation_id}.pdf"`);
                reply.send(pdfBuffer);
            });

            // Cover Page
            doc.fontSize(32).fillColor('#2563eb').text('INVESTIDUBH', { align: 'center' });
            doc.fontSize(18).fillColor('#64748b').text('Intelligence Report', { align: 'center' });
            doc.moveDown(2);
            doc.fontSize(14).fillColor('#1e293b').text(investigation.target_url, { align: 'center' });
            doc.moveDown();
            doc.fontSize(10).fillColor('#94a3b8').text(`Generated: ${new Date().toISOString()}`, { align: 'center' });

            doc.addPage();

            // Executive Summary
            doc.fontSize(20).fillColor('#2563eb').text('📊 Executive Summary');
            doc.moveDown();
            doc.fontSize(12).fillColor('#1e293b');
            doc.text(`Total Entities: ${entitySet.size}`);
            doc.text(`Total Intelligence Records: ${intelRows.rowCount}`);
            doc.text(`Investigation Status: ${investigation.status}`);

            doc.moveDown(2);

            // Top Entities placeholder
            doc.fontSize(20).fillColor('#2563eb').text('🔑 Key Findings');
            doc.moveDown();
            doc.fontSize(12).fillColor('#64748b').text('See graph analysis for detailed entity priority scores and relationships.');

            doc.moveDown(2);

            // Graph Image (if provided)
            if (graph_image && graph_image.startsWith('data:image')) {
                doc.addPage();
                doc.fontSize(20).fillColor('#2563eb').text('🕸️ Relationship Map');
                doc.moveDown();

                try {
                    const base64Data = graph_image.split(',')[1];
                    const imgBuffer = Buffer.from(base64Data, 'base64');
                    doc.image(imgBuffer, { fit: [500, 400], align: 'center' });
                } catch (imgErr) {
                    doc.fontSize(10).fillColor('#ef4444').text('(Graph image could not be embedded)');
                }
            }

            // Footer
            doc.moveDown(3);
            doc.fontSize(8).fillColor('#94a3b8').text('Generated by Investidubh — Commercial-Grade OSINT Platform', { align: 'center' });

            doc.end();

        } catch (err) {
            app.log.error({ msg: 'Report generation failed', err: err instanceof Error ? err.message : err });
            return reply.status(500).send({ error: "Report generation failed" });
        }
    });

    // --- [Phase 28] Entity Metadata Update API (Analyst Notes, Tags, Pinning) ---
    app.patch('/api/entities/:entityType/:entityValue', {
        onRequest: [app.authenticate]
    }, async (request, reply) => {
        const user = request.user as { id: string };
        const { entityType, entityValue } = request.params as { entityType: string; entityValue: string };
        const { notes, tags, pinned, pinned_position } = request.body as {
            notes?: string;
            tags?: string[];
            pinned?: boolean;
            pinned_position?: { x: number; y: number };
        };

        try {
            // Build the metadata update object
            const metadataUpdate: Record<string, any> = {};
            if (notes !== undefined) metadataUpdate.notes = notes;
            if (tags !== undefined) metadataUpdate.tags = tags;
            if (pinned !== undefined) metadataUpdate.pinned = pinned;
            if (pinned_position !== undefined) metadataUpdate.pinned_position = pinned_position;

            if (Object.keys(metadataUpdate).length === 0) {
                return reply.status(400).send({ error: "No update fields provided" });
            }

            // Update metadata using jsonb_set or || operator
            // Security: Only update entities belonging to the user's investigations
            const result = await pool.query(`
                UPDATE intelligence 
                SET metadata = COALESCE(metadata, '{}'::jsonb) || $1::jsonb
                WHERE entity_type = $2 
                  AND normalized_value = $3
                  AND investigation_id IN (SELECT id FROM investigations WHERE user_id = $4)
                RETURNING id, metadata
            `, [JSON.stringify(metadataUpdate), entityType, entityValue, user.id]);

            if (result.rowCount === 0) {
                return reply.status(404).send({ error: "Entity not found or not owned by user" });
            }

            return {
                success: true,
                updated: result.rowCount,
                metadata: result.rows[0]?.metadata
            };

        } catch (err) {
            app.log.error({ msg: 'Entity update failed', err: err instanceof Error ? err.message : err });
            return reply.status(500).send({ error: "Entity update failed" });
        }
    });


    // --- [Phase 32] Real-time Alerts Stream (SSE) ---
    app.get('/api/alerts/stream', {
        onRequest: [app.authenticate]
    }, (request, reply) => {
        // Manual SSE Headers
        reply.raw.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*' // Adjust for prod
        });

        // Send initial heartbeat
        reply.raw.write(`event: ping\ndata: {}\n\n`);

        // Heartbeat Interval (30s)
        const heartbeat = setInterval(() => {
            reply.raw.write(`event: ping\ndata: {}\n\n`);
        }, 30000);

        const sub = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

        sub.subscribe('alerts', (err) => {
            if (err) {
                request.log.error(`Failed to subscribe: ${err.message}`);
                return;
            }
        });

        sub.on('message', (channel, message) => {
            if (channel === 'alerts') {
                // Forward to client with event: alert
                // We assume message is a JSON string
                reply.raw.write(`event: alert\ndata: ${message}\n\n`);
            }
        });

        // Cleanup on close
        request.raw.on('close', () => {
            clearInterval(heartbeat);
            sub.disconnect();
        });
    });

    // --- [Phase 33] Timeline Intelligence API ---
    app.get('/api/investigations/:id/timeline', {
        onRequest: [app.authenticate]
    }, async (request, reply) => {
        const { id } = request.params as { id: string };
        const user = request.user as { id: string };

        try {
            // Verify ownership
            const invResult = await pool.query(
                "SELECT created_at FROM investigations WHERE id = $1 AND user_id = $2",
                [id, user.id]
            );

            if (invResult.rowCount === 0) {
                return reply.status(404).send({ error: "Investigation not found" });
            }

            const investigationStart = new Date(invResult.rows[0].created_at);

            // Fetch Intelligence with Timestamps
            const intelResult = await pool.query(
                "SELECT type, value, created_at, metadata FROM intelligence WHERE investigation_id = $1 ORDER BY created_at ASC",
                [id]
            );

            // Transform to Timeline Events
            // Bucketize or Stream? Stream is better for frontend flexibility.
            const events = intelResult.rows.map((row: any) => {
                let eventType = 'ENTITY_FOUND';
                let severity = 'info';

                // Check for TTPs
                if (row.metadata?.ttps?.length > 0) {
                    eventType = 'TTP_DETECTED';
                    severity = 'critical';
                } else if (row.metadata?.is_watchlist) {
                    eventType = 'WATCHLIST_MATCH';
                    severity = 'high';
                }

                return {
                    time: row.created_at,
                    type: eventType,
                    label: `${row.type}: ${row.value}`,
                    severity: severity,
                    details: row.metadata
                };
            });

            // Add Investigation Start Event
            events.unshift({
                time: investigationStart.toISOString(),
                type: 'INVESTIGATION_START',
                label: 'Investigation Started',
                severity: 'info',
                details: {}
            });

            return {
                start_time: investigationStart.toISOString(),
                item_count: events.length,
                events: events
            };

        } catch (err) {
            app.log.error({ msg: 'Timeline fetch failed', err: err instanceof Error ? err.message : err });
            return reply.status(500).send({ error: "Timeline fetch failed" });
        }
    });







    return app;
}
