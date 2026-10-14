ALTER TABLE principals ADD COLUMN IF NOT EXISTS password_salt text;
ALTER TABLE principals ADD COLUMN IF NOT EXISTS password_hash text;
CREATE TABLE IF NOT EXISTS sessions (
 token_hash text PRIMARY KEY, principal_id text NOT NULL REFERENCES principals(id),
 expires_at timestamptz NOT NULL DEFAULT now()+interval '8 hours'
);
CREATE TABLE IF NOT EXISTS login_budgets (
 principal_id text PRIMARY KEY, attempts integer NOT NULL DEFAULT 0,
 window_start timestamptz NOT NULL DEFAULT now()
);
