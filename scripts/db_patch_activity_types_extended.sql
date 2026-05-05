-- Extend activity_type_enum to support additional Strava activity types.
-- ALTER TYPE ... ADD VALUE cannot run inside a transaction block, so no BEGIN/COMMIT.

ALTER TYPE activity_type_enum ADD VALUE IF NOT EXISTS 'walk';
ALTER TYPE activity_type_enum ADD VALUE IF NOT EXISTS 'weights';
ALTER TYPE activity_type_enum ADD VALUE IF NOT EXISTS 'mobility';
