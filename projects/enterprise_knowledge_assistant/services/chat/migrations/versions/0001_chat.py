"""Create account-private conversations, immutable accepted turns and narrowly fenced worker claims."""

from alembic import op

revision = "0001_chat"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply explicit composite ownership, terminal/idempotency uniqueness and forced private RLS."""
    op.execute("""
    CREATE TABLE conversations (
      id uuid PRIMARY KEY, company_id uuid NOT NULL, account_id uuid NOT NULL UNIQUE,
      last_sequence bigint NOT NULL CHECK(last_sequence>=0), created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL,
      UNIQUE(company_id,account_id), UNIQUE(id,company_id,account_id)
    );
    CREATE TABLE chat_turns (
      id uuid PRIMARY KEY, company_id uuid NOT NULL, account_id uuid NOT NULL, conversation_id uuid NOT NULL,
      client_message_id uuid NOT NULL, user_message_id uuid NOT NULL, assistant_message_id uuid,
      accepted_login_session_id uuid NOT NULL, state text NOT NULL CHECK(state IN ('queued','running','completed','failed')),
      attempt_count integer NOT NULL CHECK(attempt_count BETWEEN 0 AND 3), lease_owner uuid, lease_until timestamptz,
      lease_version bigint NOT NULL CHECK(lease_version>=0), created_at timestamptz NOT NULL, completed_at timestamptz,
      error_code text, ai_mode text NOT NULL CHECK(ai_mode IN ('stub','openai')), model text NOT NULL,
      graph_version text NOT NULL, prompt_version text NOT NULL, model_config_version text NOT NULL, retrieval_config_version text,
      UNIQUE(conversation_id,client_message_id), UNIQUE(id,conversation_id,company_id,account_id),
      UNIQUE(id,company_id,account_id), UNIQUE(user_message_id), UNIQUE(assistant_message_id),
      FOREIGN KEY(conversation_id,company_id,account_id) REFERENCES conversations(id,company_id,account_id) DEFERRABLE INITIALLY DEFERRED,
      CHECK((state IN ('completed','failed')) = (completed_at IS NOT NULL AND assistant_message_id IS NOT NULL)),
      CHECK(state NOT IN ('queued','running') OR retrieval_config_version IS NULL),
      CHECK((state='running') = (lease_owner IS NOT NULL AND lease_until IS NOT NULL))
    );
    CREATE UNIQUE INDEX one_active_turn ON chat_turns(conversation_id) WHERE state IN ('queued','running');
    CREATE INDEX claimable_turns ON chat_turns(state,created_at);
    CREATE TABLE chat_messages (
      id uuid PRIMARY KEY, company_id uuid NOT NULL, account_id uuid NOT NULL, conversation_id uuid NOT NULL,
      turn_id uuid NOT NULL, sequence bigint NOT NULL CHECK(sequence>0), sender text NOT NULL CHECK(sender IN ('user','assistant')),
      content text NOT NULL, outcome text, refusal_text text, created_at timestamptz NOT NULL,
      UNIQUE(conversation_id,sequence), UNIQUE(turn_id,sender), UNIQUE(id,company_id,account_id),
      UNIQUE(id,turn_id,conversation_id,company_id,account_id),
      FOREIGN KEY(conversation_id,company_id,account_id) REFERENCES conversations(id,company_id,account_id) DEFERRABLE INITIALLY DEFERRED,
      FOREIGN KEY(turn_id,conversation_id,company_id,account_id) REFERENCES chat_turns(id,conversation_id,company_id,account_id) DEFERRABLE INITIALLY DEFERRED,
      CHECK((sender='user' AND outcome IS NULL AND refusal_text IS NULL AND char_length(content) BETWEEN 1 AND 4000 AND btrim(content)=content)
        OR (sender='assistant' AND outcome IN ('answer','refusal','insufficient_information','clarification','failure') AND char_length(content) BETWEEN 1 AND 16000))
    );
    ALTER TABLE chat_turns ADD FOREIGN KEY(user_message_id,id,conversation_id,company_id,account_id)
      REFERENCES chat_messages(id,turn_id,conversation_id,company_id,account_id) DEFERRABLE INITIALLY DEFERRED;
    ALTER TABLE chat_turns ADD FOREIGN KEY(assistant_message_id,id,conversation_id,company_id,account_id)
      REFERENCES chat_messages(id,turn_id,conversation_id,company_id,account_id) DEFERRABLE INITIALLY DEFERRED;
    CREATE TABLE citations (
      id uuid PRIMARY KEY, company_id uuid NOT NULL, account_id uuid NOT NULL, assistant_message_id uuid NOT NULL,
      item_id uuid NOT NULL, revision_id uuid NOT NULL, chunk_id uuid NOT NULL, locator jsonb NOT NULL,
      title_at_answer text NOT NULL CHECK(char_length(title_at_answer) BETWEEN 1 AND 200), validated_at timestamptz NOT NULL,
      FOREIGN KEY(assistant_message_id,company_id,account_id) REFERENCES chat_messages(id,company_id,account_id) DEFERRABLE INITIALLY DEFERRED,
      UNIQUE(assistant_message_id,item_id,revision_id,chunk_id)
    );
    CREATE FUNCTION taskify_chat_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.company_id<>OLD.company_id OR NEW.account_id<>OLD.account_id OR NEW.id<>OLD.id THEN
        RAISE EXCEPTION 'Immutable chat ownership';
      END IF;
      IF TG_TABLE_NAME='chat_turns' AND
        (to_jsonb(NEW) - ARRAY['state','attempt_count','lease_owner','lease_until','lease_version','completed_at','assistant_message_id','error_code','retrieval_config_version']) <>
        (to_jsonb(OLD) - ARRAY['state','attempt_count','lease_owner','lease_until','lease_version','completed_at','assistant_message_id','error_code','retrieval_config_version']) THEN
        RAISE EXCEPTION 'Immutable accepted turn configuration';
      END IF;
      RETURN NEW;
    END $$;
    """)
    for table in ("conversations", "chat_turns", "chat_messages", "citations"):
        op.execute(f"""
        ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
        ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
        CREATE POLICY private_owner ON {table} USING (
          current_user='chat_migration' OR
          (company_id=nullif(current_setting('taskify.company_id',true),'')::uuid AND
           account_id=nullif(current_setting('taskify.account_id',true),'')::uuid)
        ) WITH CHECK (current_user='chat_migration' OR
          (company_id=nullif(current_setting('taskify.company_id',true),'')::uuid AND
           account_id=nullif(current_setting('taskify.account_id',true),'')::uuid));
        CREATE TRIGGER immutable_owner BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION taskify_chat_immutable();
        """)
    op.execute("""
    CREATE FUNCTION taskify_claim_turn(worker uuid, instant timestamptz) RETURNS SETOF chat_turns
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
    DECLARE exhausted chat_turns; assistant uuid; next_sequence bigint;
    BEGIN
      FOR exhausted IN SELECT * FROM chat_turns WHERE state='running' AND lease_until<=instant AND attempt_count>=3
        ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 20 LOOP
        assistant:=gen_random_uuid();
        UPDATE conversations SET last_sequence=last_sequence+1,updated_at=instant WHERE id=exhausted.conversation_id RETURNING last_sequence INTO next_sequence;
        INSERT INTO chat_messages(id,company_id,account_id,conversation_id,turn_id,sequence,sender,content,outcome,created_at)
          VALUES(assistant,exhausted.company_id,exhausted.account_id,exhausted.conversation_id,exhausted.id,next_sequence,'assistant','Processing was interrupted. Please retry.','failure',instant);
        UPDATE chat_turns SET state='failed',assistant_message_id=assistant,completed_at=instant,error_code='worker_interrupted',
          lease_owner=NULL,lease_until=NULL,retrieval_config_version=NULL WHERE id=exhausted.id;
      END LOOP;
      RETURN QUERY UPDATE chat_turns SET state='running',attempt_count=attempt_count+1,lease_owner=worker,
        lease_until=instant+interval '30 seconds',lease_version=lease_version+1,retrieval_config_version=NULL
        WHERE id=(SELECT id FROM chat_turns WHERE (state='queued' OR (state='running' AND lease_until<=instant))
          AND attempt_count<3 ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *;
    END $$;
    CREATE FUNCTION taskify_heartbeat_turn(turn_id uuid, worker uuid, version bigint, instant timestamptz) RETURNS boolean
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
    BEGIN
      UPDATE chat_turns SET lease_until=instant+interval '30 seconds'
        WHERE id=turn_id AND state='running' AND lease_owner=worker AND lease_version=version AND lease_until>instant;
      RETURN FOUND;
    END $$;
    REVOKE ALL ON FUNCTION taskify_claim_turn(uuid,timestamptz), taskify_heartbeat_turn(uuid,uuid,bigint,timestamptz) FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION taskify_claim_turn(uuid,timestamptz), taskify_heartbeat_turn(uuid,uuid,bigint,timestamptz) TO chat_runtime;
    """)


def downgrade() -> None:
    """Reject implicit destruction of saved company-private conversation history."""
    raise RuntimeError(
        "Use an explicitly reviewed forward migration; saved history must be preserved."
    )
