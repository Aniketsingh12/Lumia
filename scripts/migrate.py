"""Run Supabase schema migrations.

Execute this script to create the required tables in your Supabase project.
You can also run these SQL statements directly in the Supabase SQL Editor.
"""

SCHEMA_SQL = """
-- Organizations
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    plan TEXT DEFAULT 'free',
    owner_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    org_id UUID REFERENCES organizations(id),
    role TEXT DEFAULT 'owner',
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bots
CREATE TABLE IF NOT EXISTS bots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    tone TEXT DEFAULT 'friendly',
    greeting_message TEXT DEFAULT 'Hi! How can I help you today?',
    fallback_message TEXT DEFAULT 'I''m not sure about that. Let me connect you to a human.',
    custom_rules JSONB DEFAULT '[]',
    channels JSONB DEFAULT '{}',
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    message_count INTEGER DEFAULT 0,
    doc_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Knowledge Documents
CREATE TABLE IF NOT EXISTS knowledge_docs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_url TEXT,
    file_type TEXT NOT NULL,
    status TEXT DEFAULT 'processing',
    chunk_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    error_message TEXT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    channel TEXT DEFAULT 'website',
    customer_id TEXT,
    customer_name TEXT,
    customer_contact TEXT,
    status TEXT DEFAULT 'active',
    assigned_agent_id UUID,
    ai_resolution BOOLEAN DEFAULT TRUE,
    satisfaction_score INTEGER,
    tags JSONB DEFAULT '[]',
    last_message TEXT,
    message_count INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- Messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    attachments JSONB DEFAULT '[]',
    source_chunks JSONB DEFAULT '[]',
    confidence_score FLOAT,
    intent TEXT,
    feedback TEXT,
    feedback_comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analytics Events
CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Widget Configs
CREATE TABLE IF NOT EXISTS widget_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID UNIQUE REFERENCES bots(id) ON DELETE CASCADE,
    primary_color TEXT DEFAULT '#6366f1',
    text_color TEXT DEFAULT '#ffffff',
    position TEXT DEFAULT 'bottom-right',
    width INTEGER DEFAULT 380,
    height INTEGER DEFAULT 600,
    show_powered_by BOOLEAN DEFAULT TRUE,
    auto_open BOOLEAN DEFAULT FALSE,
    auto_open_delay INTEGER DEFAULT 5
);

-- Webhook Configs
CREATE TABLE IF NOT EXISTS webhook_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    events JSONB DEFAULT '["message.created"]',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- API Keys
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT DEFAULT 'Default',
    key_hash TEXT NOT NULL,
    prefix TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_bots_org_id ON bots(org_id);
CREATE INDEX IF NOT EXISTS idx_conversations_bot_id ON conversations(bot_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_bot_id ON knowledge_docs(bot_id);
"""


def run_migration():
    print("=" * 60)
    print("BotForge Database Migration")
    print("=" * 60)
    print()
    print("Run the following SQL in your Supabase SQL Editor:")
    print("(Dashboard > SQL Editor > New Query)")
    print()
    print(SCHEMA_SQL)
    print()
    print("=" * 60)
    print("Copy the SQL above and execute it in Supabase.")


if __name__ == "__main__":
    run_migration()
