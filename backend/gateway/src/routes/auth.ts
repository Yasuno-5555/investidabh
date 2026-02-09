import { FastifyInstance } from 'fastify';
import bcrypt from 'bcryptjs';
import { Pool } from 'pg';
import { z } from 'zod';

const CredentialsSchema = z.object({
    username: z.string().min(3).max(50),
    password: z.string().min(6).max(100)
});

export default async function authRoutes(app: FastifyInstance, options: { pool: Pool }) {
    const { pool } = options;

    app.post('/register', async (request, reply) => {
        const result = CredentialsSchema.safeParse(request.body);
        if (!result.success) {
            return reply.status(400).send(result.error);
        }

        const { username, password } = result.data;
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

    app.post('/login', async (request, reply) => {
        const result = CredentialsSchema.safeParse(request.body);
        if (!result.success) {
            return reply.status(400).send(result.error);
        }

        const { username, password } = result.data;
        const res = await pool.query("SELECT * FROM users WHERE username = $1", [username]);
        const user = res.rows[0];

        if (!user || !(await bcrypt.compare(password, user.password_hash))) {
            return reply.status(401).send({ message: "Invalid credentials" });
        }

        const token = app.jwt.sign({ id: user.id, username: user.username });
        return { token };
    });
}
