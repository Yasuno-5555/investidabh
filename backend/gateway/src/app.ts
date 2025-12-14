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

    const app = fastify({
        logger: logger as any,
        disableRequestLogging: true
    });

    app.register(cors, {
        origin: true, // Dev only
    });

    // --- [Security] JWT Setup ---
    app.register(jwt, {
        secret: process.env.JWT_SECRET || 'dev-secret-do-not-use-in-prod'
    });

    // 認証デコレータ (ミドルウェア)
    app.decorate("authenticate", async function (request: FastifyRequest, reply: FastifyReply) {
        try {
            await request.jwtVerify();
        } catch (err) {
            reply.send(err);
        }
    });

    app.get('/health', async () => {
        return { status: 'ok', timestamp: new Date().toISOString() };
    });

    // --- [Auth API] ---

    // ユーザー登録
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

    // ログイン
    app.post('/api/auth/login', async (request, reply) => {
        const { username, password } = request.body as any;

        const res = await pool.query("SELECT * FROM users WHERE username = $1", [username]);
        const user = res.rows[0];

        if (!user || !(await bcrypt.compare(password, user.password_hash))) {
            return reply.status(401).send({ message: "Invalid credentials" });
        }

        // トークン発行
        const token = app.jwt.sign({ id: user.id, username: user.username });
        return { token };
    });

    // --- [Protected Routes] ---

    // 調査作成エンドポイント (認証必須)
    app.post('/api/investigations', {
        onRequest: [app.authenticate]
    }, async (request, reply) => {
        // ユーザーIDを取得して調査に紐付け
        const user = request.user as { id: string };

        // 1. バリデーション
        const result = CreateInvestigationSchema.safeParse(request.body);
        if (!result.success) {
            return reply.status(400).send(result.error);
        }
        const { targetUrl } = result.data;

        // 2. タスクID生成
        const investigationId = uuidv4();

        try {
            // 3. DBにレコード作成 (ユーザーID紐付け)
            await pool.query(
                "INSERT INTO investigations (id, target_url, status, user_id) VALUES ($1, $2, 'PENDING', $3)",
                [investigationId, targetUrl, user.id]
            );

            // 4. Collectorへのメッセージ作成
            const task: CollectorTask = {
                id: investigationId,
                targetUrl: targetUrl,
                requestedAt: new Date().toISOString(),
            };

            // 5. Redisのキュー(List)にPush
            await redis.lpush('tasks:collector', JSON.stringify(task));
            app.log.info({ msg: 'Task queued', taskId: investigationId, target: targetUrl, userId: user.id });
        } catch (err) {
            app.log.error({ msg: 'Failed to create investigation', err });
            return reply.status(500).send({ error: 'Internal Server Error' });
        }

        return { status: 'queued', id: investigationId };
    });

    // 調査一覧取得 API (認証必須 & 自分のデータのみ)
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
            app.log.error({ msg: 'Failed to fetch investigations', err });
            return reply.status(500).send({ error: 'Internal Server Error' });
        }
    });

    // 調査取得エンドポイント (認証必須)
    app.get('/api/investigations/:id', {
        onRequest: [app.authenticate]
    }, async (request, reply) => {
        const { id } = request.params as { id: string };
        const user = request.user as { id: string };

        try {
            // 調査情報の取得 (自分のものか確認)
            const invResult = await pool.query(
                "SELECT * FROM investigations WHERE id = $1 AND (user_id = $2 OR user_id IS NULL)",
                [id, user.id]
                // 移行期間中なのでNULLも許容するが、基本は自分のID
            );

            if (invResult.rows.length === 0) {
                return reply.status(404).send({ error: "Not found" });
            }

            // 成果物の取得
            const artResult = await pool.query(
                "SELECT * FROM artifacts WHERE investigation_id = $1",
                [id]
            );

            // Intelligenceの取得
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
            app.log.error({ msg: 'Failed to fetch investigation', err });
            return reply.status(500).send({ error: 'Internal Server Error' });
        }
    });

    // 成果物プロキシ API (MinIO -> Gateway -> Browser) (認証必須)
    app.get('/api/artifacts/:id/content', {
        onRequest: [app.authenticate]
    }, async (request, reply) => {
        const { id } = request.params as { id: string };

        try {
            // DBからパスを取得
            const artResult = await pool.query(
                "SELECT storage_path, artifact_type FROM artifacts WHERE id = $1",
                [id]
            );

            if (artResult.rows.length === 0) {
                return reply.status(404).send({ error: "Artifact not found" });
            }

            const { storage_path, artifact_type } = artResult.rows[0];
            const bucketName = 'raw-data';

            // Content-Typeの決定
            let contentType = 'application/octet-stream';
            if (artifact_type === 'screenshot') contentType = 'image/png';
            if (artifact_type === 'html') contentType = 'text/html';

            reply.header('Content-Type', contentType);

            // MinIOからストリームを取得してレスポンスに流す
            const dataStream = await minioClient.getObject(bucketName, storage_path);
            return reply.send(dataStream);

        } catch (err) {
            app.log.error({ msg: 'Storage error', err });
            return reply.status(500).send({ error: "Storage error" });
        }
    });

    // 検索 API (認証必須)
    app.get('/api/search', {
        onRequest: [app.authenticate]
    }, async (request, reply) => {
        const { q } = request.query as { q: string };

        if (!q) return [];

        try {
            // Meilisearchクライアント初期化 (本番では外に出して再利用推奨)
            const { MeiliSearch } = require('meilisearch');
            const meiliClient = new MeiliSearch({
                host: process.env.MEILI_HOST || 'http://meilisearch:7700',
                apiKey: process.env.MEILI_MASTER_KEY || 'masterKey',
            });

            const index = meiliClient.index('contents');
            const searchRes = await index.search(q, {
                attributesToCrop: ['text'], // ハイライト用にテキストを切り抜き
                cropLength: 50,
                limit: 10,
                // filter: `user_id = '${request.user.id}'` // 将来的にはここで所有者フィルタリングを入れる
            });

            return searchRes.hits.map((hit: any) => ({
                id: hit.investigation_id,
                url: hit.url,
                snippet: hit._formatted?.text || hit.text?.substring(0, 100) + '...'
            }));
        } catch (err) {
            app.log.error({ msg: 'Search failed', err });
            return reply.status(500).send({ error: "Search failed" });
        }
    });

    // PDF Export API (認証必須)
    app.get('/api/investigations/:id/export', {
        onRequest: [app.authenticate]
    }, async (request, reply) => {
        const { id } = request.params as { id: string };
        const user = request.user as { id: string };

        try {
            // 1. データ取得 (セキュリティチェック: user_id)
            const invResult = await pool.query(
                "SELECT * FROM investigations WHERE id = $1 AND (user_id = $2 OR user_id IS NULL)",
                [id, user.id]
            );

            if (invResult.rows.length === 0) {
                return reply.status(404).send("Not found");
            }
            const investigation = invResult.rows[0];

            // Intelligence取得
            const intelResult = await pool.query(
                "SELECT * FROM intelligence WHERE investigation_id = $1 ORDER BY score DESC",
                [id]
            );

            // スクリーンショットのパス取得
            const artResult = await pool.query(
                "SELECT storage_path FROM artifacts WHERE investigation_id = $1 AND artifact_type = 'screenshot'",
                [id]
            );

            // 2. PDF生成準備
            const PDFDocument = require('pdfkit');
            const doc = new PDFDocument({ margin: 50 });

            reply.header('Content-Type', 'application/pdf');
            reply.header('Content-Disposition', `attachment; filename="report-${id}.pdf"`);

            doc.pipe(reply.raw);

            // --- Header ---
            doc.fontSize(24).text('Investidubh Intelligence Report', { align: 'center' });
            doc.moveDown();

            doc.fontSize(10).text(`Target: ${investigation.target_url}`);
            doc.text(`ID: ${investigation.id}`);
            doc.text(`Generated: ${new Date().toLocaleString()}`);
            doc.moveDown();

            // --- Screenshot ---
            if (artResult.rows.length > 0) {
                try {
                    const bucketName = 'raw-data';
                    const stream = await minioClient.getObject(bucketName, artResult.rows[0].storage_path);
                    const chunks: any[] = [];
                    for await (const chunk of stream) chunks.push(chunk);
                    const buffer = Buffer.concat(chunks);

                    doc.text('Captured Screenshot', { underline: true });
                    doc.moveDown(0.5);
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

            const tableTop = 100;
            const itemHeight = 20;

            // Table Header
            let y = doc.y;
            doc.fontSize(10).font('Helvetica-Bold');
            doc.text('Entity', 50, y);
            doc.text('Type', 250, y);
            doc.text('Score', 350, y);
            doc.text('Notes', 450, y);

            doc.moveTo(50, y + 15).lineTo(550, y + 15).stroke();
            y += 20;
            doc.font('Helvetica');

            // Table Rows
            const sortedIntelligence = intelResult.rows.sort((a: any, b: any) => (b.score || 0) - (a.score || 0));

            sortedIntelligence.forEach((item: any) => {
                if (y > 700) { // New Page
                    doc.addPage();
                    y = 50;
                }

                const score = item.score || 0;
                const isHighPriority = score >= 50;
                const entityDate = new Date(item.created_at || Date.now());
                const now = new Date();
                const isGhost = (now.getTime() - entityDate.getTime()) > (365 * 24 * 60 * 60 * 1000);

                // Highlight High Priority
                if (isHighPriority) doc.fillColor('red');
                else doc.fillColor('black');

                // Entity Value (Truncate if long)
                doc.text(item.value.substring(0, 40), 50, y, { width: 190, lineBreak: false });

                doc.fillColor('black');
                doc.text(item.type, 250, y);

                // Score
                if (isHighPriority) doc.font('Helvetica-Bold').fillColor('red');
                doc.text(`${score.toFixed(0)}`, 350, y);
                doc.font('Helvetica').fillColor('black');

                // Notes
                let notes = '';
                if (isGhost) notes += '(Historical) ';
                if (item.confidence) notes += `${(item.confidence * 100).toFixed(0)}% Conf.`;
                doc.text(notes, 450, y);

                y += itemHeight;
                doc.fillColor('black'); // Reset
            });

            // --- Footer ---
            doc.moveDown(2);
            doc.fontSize(8).text('Generated by Investidubh - Automated OSINT Platform', { align: 'center', color: 'grey' });

            doc.end();

            return reply;

        } catch (err) {
            app.log.error({ msg: 'Export failed', err });
            return reply.status(500).send({ error: "Export failed" });
        }
    });

    // Graph Analysis API (認証必須)
    app.get('/api/graph', {
        onRequest: [app.authenticate]
    }, async (request, reply) => {
        const user = request.user as { id: string };

        try {
            // 1. Fetch all investigations (Nodes A)
            const invRows = await pool.query(
                "SELECT id, target_url FROM investigations WHERE user_id = $1",
                [user.id]
            );

            // 2. Fetch all intelligence (Nodes B & Edges) - ONLY linked entities
            const intelRows = await pool.query(`
                SELECT i.id, i.investigation_id, i.type, i.value, i.normalized_value, i.created_at, i.confidence, i.score, i.sentiment_score, i.metadata
                FROM intelligence i
                JOIN investigations inv ON i.investigation_id = inv.id
                WHERE inv.user_id = $1 AND i.normalized_value IS NOT NULL
            `, [user.id]);

            const nodes: any[] = [];
            const edges: any[] = [];

            // 2.5 Calculate Degrees (Hubs)
            const degreeMap = new Map<string, number>();
            intelRows.rows.forEach((item: any) => {
                const entId = `ent-${item.type}-${item.normalized_value}`;
                degreeMap.set(entId, (degreeMap.get(entId) || 0) + 1);
            });

            // Create Investigation Nodes
            invRows.rows.forEach((inv: any) => {
                nodes.push({
                    id: `inv-${inv.id}`,
                    type: 'input',
                    data: { label: inv.target_url },
                    position: { x: 0, y: 0 },
                    style: { background: '#2563eb', color: 'white', border: 'none', width: 180, padding: 10, borderRadius: 5 }
                });
            });

            const addedEntities = new Set<string>();

            // Create Entity Nodes & Edges
            intelRows.rows.forEach((item: any) => {
                // Unique Entity ID based on Type + Normalized Value
                const entityId = `ent-${item.type}-${item.normalized_value}`;
                const degree = degreeMap.get(entityId) || 1;
                const isHub = degree > 1;

                // Entity Node (重複排除)
                if (!addedEntities.has(entityId)) {
                    let bgColor = '#10b981'; // Default Green (Email/Phone)
                    if (item.type === 'ip') bgColor = '#8b5cf6'; // Purple
                    if (item.type === 'domain') bgColor = '#6366f1'; // Indigo
                    if (item.type === 'subdomain') bgColor = '#a5b4fc'; // Light Indigo
                    if (item.type === 'organization') bgColor = '#f97316'; // Orange
                    if (item.type === 'person') bgColor = '#14b8a6'; // Teal
                    if (item.type === 'location') bgColor = '#ec4899'; // Pink

                    if (isHub && !['ip', 'domain', 'subdomain', 'organization', 'person', 'location'].includes(item.type)) {
                        bgColor = '#ef4444'; // Red for Hubs (Email/Phone only)
                    }

                    // Ghost Node Detection
                    const entityDate = new Date(item.created_at || Date.now());
                    const now = new Date();
                    const isGhost = (now.getTime() - entityDate.getTime()) > (365 * 24 * 60 * 60 * 1000);

                    const baseSize = item.type === 'subdomain' ? 30 : 50;
                    const size = Math.min(baseSize + (degree * 10), 150);

                    nodes.push({
                        id: entityId,
                        type: 'default',
                        data: {
                            label: item.value,
                            type: item.type,
                            value: item.value,
                            // Visualization properties
                            degree: degree, // Corrected from item.degree to local 'degree' variable
                            score: item.score || 0,
                            sentiment: item.sentiment_score || 0,
                            relations: item.metadata?.relations || [],
                            confidence: item.confidence,
                            timestamp: item.created_at,

                            // Flags
                            isHighPriority: (item.score || 0) >= 50,
                            isGhost: isGhost
                        },
                        position: { x: 0, y: 0 },
                        style: {
                            background: bgColor,
                            color: isGhost ? '#cbd5e1' : 'white',
                            border: isGhost ? '2px dashed #94a3b8' : 'none',
                            opacity: isGhost ? 0.7 : 1,
                            borderRadius: (item.type === 'ip' || item.type === 'organization') ? '4px' : '50%',
                            width: size,
                            height: size,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: item.type === 'subdomain' ? '8px' : '10px',
                            textAlign: 'center',
                            zIndex: isHub ? 10 : 1
                        }
                    });
                    addedEntities.add(entityId);
                }

                // Edge: Investigation -> Entity
                edges.push({
                    id: `edge-${item.id}`,
                    source: `inv-${item.investigation_id}`,
                    target: entityId,
                    animated: true,
                    style: { stroke: '#94a3b8' }
                });
            });

            return { nodes, edges };

        } catch (err) {
            app.log.error({ msg: 'Graph fetch failed', err });
            return reply.status(500).send({ error: "Graph fetch failed" });
        }
    });

    return app;
}
