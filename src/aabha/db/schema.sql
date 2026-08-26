CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username       TEXT        NOT NULL CHECK (length(username) BETWEEN 3 AND 32),
    email          TEXT        NOT NULL,
    password_hash  TEXT        NOT NULL,
    dob            DATE        NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Case-folded, so "Aayush" and "aayush" cannot both be registered while the
-- column still keeps whatever casing the user chose for themselves.
CREATE UNIQUE INDEX IF NOT EXISTS users_username_key ON users (lower(username));
CREATE UNIQUE INDEX IF NOT EXISTS users_email_key ON users (lower(email));

-- Memories and conversations die with the user they belong to.

CREATE TABLE IF NOT EXISTS memory (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    key           TEXT        NOT NULL CHECK (length(key) BETWEEN 1 AND 64),
    kind          TEXT        NOT NULL DEFAULT 'fact'
                  CHECK (kind IN ('preference', 'habit', 'fact')),
    content       TEXT        NOT NULL CHECK (length(content) BETWEEN 1 AND 2000),
    source        TEXT        NOT NULL DEFAULT 'conversation'
                  CHECK (source IN ('user', 'agent', 'conversation', 'system')),
    importance    SMALLINT    NOT NULL DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at  TIMESTAMPTZ,

    -- The handle the assistant names a memory by. Saving under a key that is
    -- already taken overwrites it, which is what keeps one fact from being
    -- stored three ways.
    UNIQUE (user_id, key)
);

-- Recall reads a user's whole set, most important first, so the index carries
-- the ordering rather than leaving it to a sort.
CREATE INDEX IF NOT EXISTS memory_user_recall_idx
    ON memory (user_id, importance DESC, updated_at DESC);


CREATE TABLE IF NOT EXISTS conversation (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID        NOT NULL REFERENCES users (id) ON DELETE CASCADE,

    -- NULL until the call ends, which is what tells a conversation that was
    -- summarised apart from one that was cut off before it could be.
    summary        TEXT,

    message_count  INTEGER     NOT NULL DEFAULT 0 CHECK (message_count >= 0),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS conversation_user_recent_idx
    ON conversation (user_id, created_at DESC);
