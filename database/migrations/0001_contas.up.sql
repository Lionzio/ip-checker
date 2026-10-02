-- Sprint 13 (S13-01): contas, e-mails, sessões e tokens de e-mail (blueprint 5.2.5, ADR-04).
-- Aplicada por `python -m ipc_api.db.migrate up`, com a credencial de administrador do banco.
-- A API usa outro usuário, membro de ipc_app, que não altera o esquema nem apaga contas.

CREATE SCHEMA app;

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ipc_app') THEN
    CREATE ROLE ipc_app NOLOGIN;
  END IF;
END
$$;

CREATE TYPE app.role AS ENUM ('desenvolvedor', 'professor', 'monitor_chefe', 'monitor');
CREATE TYPE app.status AS ENUM (
  'aguardando_verificacao', 'aguardando_aprovacao', 'ativo',
  'recusado', 'ex_monitor', 'conselheiro', 'inativo'
);
CREATE TYPE app.treatment AS ENUM ('masculino', 'feminino', 'neutro');

CREATE TABLE app.account (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL CHECK (length(name) BETWEEN 2 AND 120 AND name = btrim(name)),
  course text NOT NULL CHECK (length(course) BETWEEN 2 AND 120 AND course = btrim(course)),
  -- Só o titular vê o tratamento; ele serve apenas ao feedback (FR-26).
  treatment app.treatment NOT NULL,
  -- Definido na aprovação (FR-27); vazio enquanto o cadastro espera.
  role app.role NULL,
  status app.status NOT NULL,
  ja_foi_monitor_chefe boolean NOT NULL DEFAULT false,
  -- Argon2id; vazio numa conta criada só pelo Google.
  password_hash text NULL,
  google_sub text NULL UNIQUE,
  signup_method text NOT NULL CHECK (signup_method IN ('senha', 'google', 'seed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  decided_by uuid NULL REFERENCES app.account (id),
  decided_at timestamptz NULL,
  CHECK (status <> 'ativo' OR role IS NOT NULL)
);

-- O nome também serve para entrar, então é único sem diferenciar maiúsculas (FR-23).
CREATE UNIQUE INDEX account_name_ci ON app.account (lower(name));

-- ja_foi_monitor_chefe vira verdadeiro na primeira vez que a pessoa recebe o cargo e nunca volta a
-- falso (FR-27): a regra fica no banco, e nenhuma atualização da API consegue desfazê-la.
CREATE FUNCTION app.keep_ja_foi_monitor_chefe() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.role = 'monitor_chefe' THEN
    NEW.ja_foi_monitor_chefe := true;
  END IF;
  IF TG_OP = 'UPDATE' THEN
    IF OLD.ja_foi_monitor_chefe THEN
      NEW.ja_foi_monitor_chefe := true;
    END IF;
  END IF;
  RETURN NEW;
END
$$;

CREATE TRIGGER account_keep_ja_foi_monitor_chefe
BEFORE INSERT OR UPDATE ON app.account
FOR EACH ROW EXECUTE FUNCTION app.keep_ja_foi_monitor_chefe();

-- Cada e-mail leva a uma única conta; o desenvolvedor tem dois (P-14). Só os domínios aceitos,
-- comparados exatamente depois do @ e já em minúsculas.
CREATE TABLE app.account_email (
  email text PRIMARY KEY CHECK (
    email = lower(email)
    AND length(email) <= 254
    AND email ~ '^[^@\s]+@[^@\s]+$'
    AND split_part(email, '@', 2) IN ('cin.ufpe.br', 'ufpe.br')
  ),
  account_id uuid NOT NULL REFERENCES app.account (id),
  is_primary boolean NOT NULL DEFAULT true,
  verified_at timestamptz NULL
);

CREATE INDEX account_email_account ON app.account_email (account_id);

-- Sessões no servidor (NFR-22): o banco guarda só o SHA-256 do identificador do cookie.
CREATE TABLE app.session (
  token_hash bytea PRIMARY KEY CHECK (length(token_hash) = 32),
  account_id uuid NOT NULL REFERENCES app.account (id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL
);

CREATE INDEX session_account ON app.session (account_id);

-- Tokens dos links de e-mail (verificação, Sprint 14): também só o hash, uso único, 24 h.
CREATE TABLE app.email_token (
  token_hash bytea PRIMARY KEY CHECK (length(token_hash) = 32),
  account_id uuid NOT NULL REFERENCES app.account (id) ON DELETE CASCADE,
  purpose text NOT NULL CHECK (purpose IN ('verificacao')),
  expires_at timestamptz NOT NULL,
  used_at timestamptz NULL
);

-- Privilégio mínimo: a API lê e escreve, mas nunca apaga uma conta (remover é mudar o status).
GRANT USAGE ON SCHEMA app TO ipc_app;
GRANT SELECT, INSERT, UPDATE ON app.account, app.account_email, app.email_token TO ipc_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON app.session TO ipc_app;
