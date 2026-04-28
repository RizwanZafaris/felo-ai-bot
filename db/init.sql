CREATE TABLE IF NOT EXISTS quota_usage (
    user_id TEXT NOT NULL,
    year_month TEXT NOT NULL,
    calls_used INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, year_month)
);

CREATE TABLE IF NOT EXISTS user_profile (
    user_id TEXT PRIMARY KEY,
    tier TEXT NOT NULL DEFAULT 'free',
    monthly_income_pkr NUMERIC(12,2) DEFAULT 0,
    monthly_spend_pkr NUMERIC(12,2) DEFAULT 0,
    savings_pkr NUMERIC(12,2) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES user_profile(user_id) ON DELETE CASCADE,
    amount_pkr NUMERIC(12,2) NOT NULL,
    category TEXT NOT NULL,
    merchant TEXT,
    occurred_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tx_user_time ON transactions(user_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS goals (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES user_profile(user_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    target_pkr NUMERIC(12,2) NOT NULL,
    current_pkr NUMERIC(12,2) DEFAULT 0,
    deadline TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS bills (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES user_profile(user_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    amount_pkr NUMERIC(12,2) NOT NULL,
    due_day INTEGER NOT NULL,
    paid_this_month BOOLEAN DEFAULT FALSE
);
