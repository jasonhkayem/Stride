-- Break circular creation dependency between user_training_plans and training_plan_versions.

BEGIN;

ALTER TABLE user_training_plans
    ALTER COLUMN current_version_id DROP NOT NULL;

COMMIT;
