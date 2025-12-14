CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 調査案件テーブル
CREATE TABLE IF NOT EXISTS investigations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, PROCESSING, COMPLETED, FAILED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 成果物テーブル (HTML, Screenshotなど)
CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investigation_id UUID REFERENCES investigations(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL, -- 'html', 'screenshot', 'json'
    storage_path TEXT NOT NULL,  -- MinIO内のパス
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 解析結果テーブル (メール、重要語句など)
CREATE TABLE IF NOT EXISTS intelligence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investigation_id UUID REFERENCES investigations(id) ON DELETE CASCADE,
    type TEXT NOT NULL,         -- 'email', 'phone', 'ip', etc.
    value TEXT NOT NULL,        -- Original extracted text
    normalized_value TEXT,      -- [NEW] Normalized for linking (lowercase etc)
    confidence FLOAT DEFAULT 0.5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster graph queries
CREATE INDEX IF NOT EXISTS idx_intelligence_norm ON intelligence(normalized_value);
CREATE INDEX IF NOT EXISTS idx_intelligence_investigation_id ON intelligence(investigation_id);

-- ユーザーテーブル
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 既存テーブルの所有者カラム (以前のデータとの互換性のためNULL許容)
ALTER TABLE investigations ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
