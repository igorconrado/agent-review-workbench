CREATE TABLE IF NOT EXISTS principals (
 id text PRIMARY KEY, organization text NOT NULL,
 role text NOT NULL CHECK (role IN ('reviewer','viewer')), active boolean NOT NULL DEFAULT true
);
CREATE TABLE IF NOT EXISTS cases (
 id uuid PRIMARY KEY, organization text NOT NULL, context_version integer NOT NULL DEFAULT 1,
 evidence jsonb NOT NULL, status text NOT NULL DEFAULT 'open'
 CHECK (status IN ('open','review','approved','rejected','cancelled','executed','uncertain')),
 action jsonb, action_hash text, decision_by text REFERENCES principals(id),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS tool_calls (
 action_hash text PRIMARY KEY, case_id uuid NOT NULL REFERENCES cases(id),
 state text NOT NULL CHECK (state IN ('unknown','settled')), result jsonb,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS audit (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, case_id uuid NOT NULL REFERENCES cases(id),
 actor text NOT NULL, event text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE SCHEMA IF NOT EXISTS sandbox;
CREATE TABLE IF NOT EXISTS sandbox.effects (
 action_hash text PRIMARY KEY, action jsonb NOT NULL, result jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
