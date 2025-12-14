import { z } from 'zod';

export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: {
        code: string;
        message: string;
    };
    timestamp: string;
}

export interface User {
    id: number;
    username: string;
    createdAt: string;
}

export type UserRole = 'admin' | 'investigator' | 'viewer';

// 調査対象の入力スキーマ
export const CreateInvestigationSchema = z.object({
    targetUrl: z.string().url(),
    notes: z.string().optional(),
    ttlDays: z.number().min(1).max(30).default(7), // データ保存期間
});

export type CreateInvestigationInput = z.infer<typeof CreateInvestigationSchema>;

// タスクキューに投げるメッセージの型
export interface CollectorTask {
    id: string; // UUID
    targetUrl: string;
    requestedAt: string;
}
