-- 1. 調査案件（Case）
CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT,
    subject TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN', -- OPEN, CLOSED, ARCHIVED
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. 調査端緒（Leads）
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    target_value TEXT NOT NULL,
    lead_type TEXT NOT NULL DEFAULT 'URL',
    status TEXT NOT NULL DEFAULT 'PENDING',
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. 成果物テーブル (Evidence)
CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investigation_id UUID REFERENCES investigations(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    hash_sha256 TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. 証拠保全台帳 (Custody Ledger)
CREATE TABLE IF NOT EXISTS custody_ledger (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    artifact_id UUID REFERENCES artifacts(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    performed_by UUID REFERENCES users(id),
    ip_address TEXT,
    user_agent TEXT,
    proxy_used TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. 解析結果テーブル (Intelligence): Tier S+ 拡張
CREATE TABLE IF NOT EXISTS intelligence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investigation_id UUID REFERENCES investigations(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    value TEXT NOT NULL,
    normalized_value TEXT,
    
    -- AI Generated Multi-Axis Confidence (IQの高い信頼度)
    -- { "source": 0.9, "freshness": 0.6, "corroboration": 0.8, "contradiction": 0.1 }
    confidence_axes JSONB DEFAULT '{}',
    metadata JSONB,
    
    -- Analyst Status
    -- 'CONFIRMED', 'DISMISSED', 'UNKNOWN', 'CONFLICT', 'PENDING_REVIEW'
    status TEXT DEFAULT 'PENDING_REVIEW',
    is_contradiction BOOLEAN DEFAULT FALSE,
    tags TEXT[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. 意思決定来歴 (Decision Logs): 「誰が・なぜ」の署名
CREATE TABLE IF NOT EXISTS decision_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_id UUID NOT NULL, -- intelligence_id, case_id etc.
    target_type TEXT NOT NULL, -- 'INTELLIGENCE', 'CASE', 'ARTIFACT'
    action TEXT NOT NULL, -- 'OVERRIDE', 'CONFIRM', 'DISMISS', 'FLAG'
    
    performed_by UUID REFERENCES users(id),
    
    -- The "Why"
    reason TEXT,
    reference_case_id UUID REFERENCES cases(id),
    
    -- The "New State"
    old_value JSONB,
    new_value JSONB,
    
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. 時系列矛盾 (Timeline Conflicts): 自動検知された不整合
CREATE TABLE IF NOT EXISTS timeline_conflicts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    severity TEXT NOT NULL DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH, CRITICAL
    description TEXT NOT NULL,
    evidence_ids UUID[], -- 矛盾に関与している証拠群
    status TEXT DEFAULT 'OPEN', -- OPEN, RESOLVED, DISMISSED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. 仮説 & ノート
CREATE TABLE IF NOT EXISTS hypotheses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence_score FLOAT DEFAULT 0.5,
    evidence_ids UUID[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analyst_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    investigation_id UUID REFERENCES investigations(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_intelligence_norm ON intelligence(normalized_value);
CREATE INDEX IF NOT EXISTS idx_decision_logs_target ON decision_logs(target_id);
CREATE INDEX IF NOT EXISTS idx_timeline_conflicts_case ON timeline_conflicts(case_id);
