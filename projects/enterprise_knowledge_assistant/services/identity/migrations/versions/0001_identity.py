"""Create Identity-owned schema, forced tenant policies and narrow authentication functions.

All identifiers are UUIDs; timestamps are UTC.
Text lengths count Unicode code points, not bytes, unless explicitly stated.
"""

from alembic import op

revision = "0001_identity"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply immutable schema and scoped grants; no cross-service database is accessed."""
    op.execute("""
    CREATE TABLE companies (
      id uuid PRIMARY KEY, name text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 100 AND name = btrim(name) AND name !~ '[[:cntrl:]]'),
      created_at timestamptz NOT NULL
    );
    CREATE TABLE accounts (
      id uuid PRIMARY KEY, company_id uuid NOT NULL REFERENCES companies(id),
      email text NOT NULL CHECK (char_length(email) BETWEEN 3 AND 254),
      normalized_email text NOT NULL UNIQUE CHECK (char_length(normalized_email) BETWEEN 3 AND 254),
      display_name text NOT NULL CHECK (char_length(display_name) BETWEEN 1 AND 100 AND display_name = btrim(display_name) AND display_name !~ '[[:cntrl:]]'),
      role text NOT NULL CHECK (role IN ('admin','user')),
      password_hash text NOT NULL CHECK (password_hash LIKE '$argon2id$%'),
      credential_version integer NOT NULL CHECK (credential_version >= 1),
      must_change_password boolean NOT NULL DEFAULT true,
      created_at timestamptz NOT NULL, password_changed_at timestamptz,
      UNIQUE (id, company_id)
    );
    CREATE INDEX accounts_company ON accounts(company_id);
    CREATE TABLE login_sessions (
      id uuid PRIMARY KEY, account_id uuid NOT NULL REFERENCES accounts(id),
      token_digest text NOT NULL UNIQUE CHECK (token_digest ~ '^[0-9a-f]{64}$'),
      credential_version integer NOT NULL CHECK (credential_version >= 1),
      csrf_secret text NOT NULL CHECK (char_length(csrf_secret) >= 32),
      created_at timestamptz NOT NULL, last_activity_at timestamptz NOT NULL,
      revoked_at timestamptz,
      CHECK (last_activity_at >= created_at)
    );
    CREATE INDEX login_sessions_account ON login_sessions(account_id);
    CREATE TABLE login_attempt_windows (
      email_key text PRIMARY KEY CHECK (email_key ~ '^[0-9a-f]{64}$'),
      window_started_at timestamptz NOT NULL,
      failure_count integer NOT NULL CHECK (failure_count BETWEEN 0 AND 5),
      blocked_until timestamptz
    );

    ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
    ALTER TABLE companies FORCE ROW LEVEL SECURITY;
    ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
    ALTER TABLE accounts FORCE ROW LEVEL SECURITY;
    ALTER TABLE login_sessions ENABLE ROW LEVEL SECURITY;
    ALTER TABLE login_sessions FORCE ROW LEVEL SECURITY;
    -- Migration authority is available only inside explicitly granted definer routines.
    -- Runtime identities cannot SET ROLE to the owner; normal DML requires trusted context.
    CREATE POLICY company_scope ON companies USING (current_user = 'identity_migration' OR id::text = current_setting('taskify.company_id', true));
    CREATE POLICY account_scope ON accounts USING (current_user = 'identity_migration' OR company_id::text = current_setting('taskify.company_id', true));
    CREATE POLICY session_scope ON login_sessions USING (current_user = 'identity_migration' OR account_id IN (SELECT id FROM accounts WHERE company_id::text = current_setting('taskify.company_id', true)));

    CREATE FUNCTION taskify_create_company(p_id uuid, p_name text, p_created timestamptz) RETURNS void
      LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      INSERT INTO public.companies VALUES (p_id, p_name, p_created);
    $$;
    CREATE FUNCTION taskify_company_exists(p_id uuid) RETURNS boolean
      LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      SELECT EXISTS (SELECT 1 FROM public.companies WHERE id = p_id);
    $$;
    CREATE FUNCTION taskify_account_by_email(p_email text) RETURNS SETOF accounts
      LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      SELECT * FROM public.accounts WHERE normalized_email = p_email FOR UPDATE;
    $$;
    CREATE FUNCTION taskify_account_by_id(p_id uuid) RETURNS SETOF accounts
      LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      SELECT * FROM public.accounts WHERE id = p_id FOR UPDATE;
    $$;
    CREATE FUNCTION taskify_session(p_digest text, p_id uuid) RETURNS SETOF login_sessions
      LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      SELECT * FROM public.login_sessions WHERE (p_digest IS NULL) <> (p_id IS NULL)
        AND (token_digest = p_digest OR id = p_id);
    $$;
    CREATE FUNCTION taskify_revoke_sessions(p_account uuid, p_now timestamptz) RETURNS void
      LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      UPDATE public.login_sessions SET revoked_at = p_now WHERE account_id = p_account AND revoked_at IS NULL;
    $$;
    CREATE FUNCTION taskify_immutable_account_company() RETURNS trigger
      LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
      BEGIN
        IF NEW.company_id <> OLD.company_id THEN RAISE EXCEPTION 'Account ownership is immutable'; END IF;
        RETURN NEW;
      END;
    $$;
    CREATE TRIGGER immutable_account_company BEFORE UPDATE ON accounts FOR EACH ROW EXECUTE FUNCTION taskify_immutable_account_company();
    GRANT EXECUTE ON FUNCTION taskify_create_company(uuid,text,timestamptz), taskify_company_exists(uuid), taskify_account_by_email(text), taskify_account_by_id(uuid), taskify_session(text,uuid), taskify_revoke_sessions(uuid,timestamptz) TO identity_runtime;
    """)


def downgrade() -> None:
    """Remove only this owned schema; no other service's storage or grants are modified."""
    op.execute("""
    DROP FUNCTION taskify_create_company(uuid,text,timestamptz), taskify_company_exists(uuid), taskify_account_by_email(text), taskify_account_by_id(uuid), taskify_session(text,uuid), taskify_revoke_sessions(uuid,timestamptz);
    DROP TABLE login_sessions, login_attempt_windows, accounts, companies;
    DROP FUNCTION taskify_immutable_account_company();
    """)
