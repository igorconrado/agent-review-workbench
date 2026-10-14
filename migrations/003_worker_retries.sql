ALTER TABLE cases ADD COLUMN IF NOT EXISTS worker_attempts integer NOT NULL DEFAULT 0 CHECK (worker_attempts >= 0);
ALTER TABLE cases ADD COLUMN IF NOT EXISTS worker_available_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE cases ADD COLUMN IF NOT EXISTS worker_last_error text;
CREATE INDEX IF NOT EXISTS cases_worker_due ON cases(worker_available_at, created_at, id)
WHERE status IN ('approved', 'uncertain') AND worker_attempts < 5;
