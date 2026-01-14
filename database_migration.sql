-- Database Migration Script
-- Adds new columns and tables for Messenger functionality

-- Add avito_user_id to profiles table
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS avito_user_id TEXT;

-- Add autoresponder_enabled to features (will be stored in JSON)
-- No schema change needed, handled in code

-- Update messages table to include more metadata
-- SQLite doesn't support ALTER COLUMN, so we create a new table

-- Create new messages table with additional fields
CREATE TABLE IF NOT EXISTS messages_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    avito_message_id TEXT,
    chat_id TEXT,
    direction TEXT NOT NULL CHECK(direction IN ('in', 'out')),
    content TEXT,
    author_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

-- Copy existing data
INSERT INTO messages_new (id, profile_id, avito_message_id, direction, content, created_at)
SELECT id, profile_id, avito_message_id, direction, content, created_at
FROM messages;

-- Drop old table and rename new one
DROP TABLE messages;
ALTER TABLE messages_new RENAME TO messages;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_messages_profile_chat ON messages(profile_id, chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_avito_id ON messages(avito_message_id);
CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_profiles_avito_user_id ON profiles(avito_user_id);

-- Create chats table for tracking chat metadata
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    avito_chat_id TEXT NOT NULL,
    item_id TEXT,
    last_message_at TIMESTAMP,
    last_checked_at TIMESTAMP,
    unread_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
    UNIQUE(profile_id, avito_chat_id)
);

CREATE INDEX IF NOT EXISTS idx_chats_profile ON chats(profile_id);
CREATE INDEX IF NOT EXISTS idx_chats_last_message ON chats(profile_id, last_message_at DESC);
