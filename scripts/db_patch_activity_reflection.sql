-- Add related_activity_id to chatbot_sessions so a coaching session can be
-- linked to a specific activity for contextual reflection.

BEGIN;

ALTER TABLE chatbot_sessions
    ADD COLUMN IF NOT EXISTS related_activity_id UUID NULL
        REFERENCES activities(activity_id) ON DELETE SET NULL;

COMMIT;
