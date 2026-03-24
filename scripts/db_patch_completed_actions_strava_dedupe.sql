-- De-duplicate Strava imports and enforce uniqueness for future imports.
-- Run in pgAdmin on your project database.

BEGIN;

-- Keep the newest row per (user_id, strava_activity_id), delete older duplicates.
WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY user_id, strava_activity_id
            ORDER BY created_at DESC, id DESC
        ) AS rn
    FROM completed_actions
    WHERE strava_activity_id IS NOT NULL
)
DELETE FROM completed_actions ca
USING ranked r
WHERE ca.id = r.id
  AND r.rn > 1;

-- Enforce one Strava activity import per user.
CREATE UNIQUE INDEX IF NOT EXISTS uq_completed_actions_user_strava_activity
ON completed_actions(user_id, strava_activity_id)
WHERE strava_activity_id IS NOT NULL;

COMMIT;
