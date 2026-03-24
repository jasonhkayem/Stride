-- Apply this patch to your existing PostgreSQL database.

BEGIN;

ALTER TABLE activity_comments
ADD COLUMN IF NOT EXISTS parent_comment_id UUID NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'activity_comments_parent_comment_id_fkey'
    ) THEN
        ALTER TABLE activity_comments
        ADD CONSTRAINT activity_comments_parent_comment_id_fkey
        FOREIGN KEY (parent_comment_id)
        REFERENCES activity_comments(comment_id);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS user_follows (
    follow_id UUID PRIMARY KEY,
    follower_id UUID NOT NULL REFERENCES users(user_id),
    following_id UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_follows_pair UNIQUE (follower_id, following_id),
    CONSTRAINT ck_user_follows_no_self_follow CHECK (follower_id <> following_id)
);

COMMIT;
