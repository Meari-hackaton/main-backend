-- user_streaks 테이블 생성
CREATE TABLE IF NOT EXISTS user_streaks (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    total_days_active INTEGER DEFAULT 0,
    total_rituals_completed INTEGER DEFAULT 0,
    total_rituals_created INTEGER DEFAULT 0,
    last_activity_date DATE,
    last_ritual_date DATE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- daily_rituals 테이블 생성
CREATE TABLE IF NOT EXISTS daily_rituals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ritual_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    emoji VARCHAR(10),
    frequency VARCHAR(20) DEFAULT 'daily',
    duration_minutes INTEGER,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP WITH TIME ZONE,
    reflection TEXT,
    mood VARCHAR(50),
    date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date, ritual_type)
);

-- ritual_templates 테이블 생성
CREATE TABLE IF NOT EXISTS ritual_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    emoji VARCHAR(10),
    duration_minutes INTEGER,
    difficulty_level VARCHAR(20),
    tags TEXT[],
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_daily_rituals_user_date ON daily_rituals(user_id, date);
CREATE INDEX IF NOT EXISTS idx_daily_rituals_completed ON daily_rituals(completed);
CREATE INDEX IF NOT EXISTS idx_user_streaks_user ON user_streaks(user_id);