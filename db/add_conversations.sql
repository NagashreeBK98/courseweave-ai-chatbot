-- Persistent chat conversations per student
CREATE TABLE IF NOT EXISTS conversations (
    id           SERIAL PRIMARY KEY,
    student_id   INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    title        TEXT    NOT NULL DEFAULT 'New Chat',
    session_context JSONB,                          -- cached RAG context for follow-ups
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_student ON conversations(student_id);

-- Individual messages within a conversation
CREATE TABLE IF NOT EXISTS conversation_messages (
    id              SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(10) NOT NULL CHECK (role IN ('user', 'model')),
    text            TEXT   NOT NULL,
    courses         JSONB  DEFAULT '[]',            -- course cards attached to bot messages
    action          VARCHAR(20),                    -- recommend | followup | ask_path | complete
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_messages_conv ON conversation_messages(conversation_id);
