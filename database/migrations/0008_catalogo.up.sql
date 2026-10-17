-- Catálogo das listas do Dikastis e o token de importação (Sprint 50, S50-04 e S50-05; ADR-15 e
-- ADR-19). O catálogo guarda o que existe no Dikastis para cada período (turmas, listas e
-- questões, com o enunciado e só os casos de exemplo); nenhum dado de aluno. O token de
-- importação, pessoal, é guardado só como SHA-256.

CREATE TABLE app.catalog_period (
    period     text PRIMARY KEY CHECK (period ~ '^\d{4}\.[12]$'),
    first_seen timestamptz NOT NULL
);

CREATE TABLE app.catalog_class (
    id              uuid PRIMARY KEY,
    dikastis_org_id text NOT NULL UNIQUE CHECK (length(dikastis_org_id) BETWEEN 1 AND 64),
    period          text NOT NULL REFERENCES app.catalog_period (period),
    name            text NOT NULL CHECK (length(name) BETWEEN 1 AND 200),
    course          text NOT NULL CHECK (course IN ('SI', 'EC', 'CC/IA', 'CC', 'outro')),
    last_seen       timestamptz NOT NULL
);

CREATE TABLE app.catalog_list (
    id               uuid PRIMARY KEY,
    period           text NOT NULL REFERENCES app.catalog_period (period),
    kind             text NOT NULL CHECK (kind IN ('treino', 'lista', 'prova')),
    number           integer CHECK (number BETWEEN 1 AND 20),
    title            text NOT NULL CHECK (length(title) BETWEEN 1 AND 300),
    starts_at        timestamptz,
    ends_at          timestamptz,
    last_seen        timestamptz NOT NULL,
    missing_since    timestamptz,
    CHECK ((kind = 'treino') = (number IS NULL))
);
-- Uma lista (ou prova) por período e número; a de treino, uma por período.
CREATE UNIQUE INDEX catalog_list_identity ON app.catalog_list (period, kind, coalesce(number, 0));

-- A mesma lista aparece em várias turmas, cada uma com o próprio id de tarefa no Dikastis.
CREATE TABLE app.catalog_list_task (
    dikastis_task_id text PRIMARY KEY CHECK (length(dikastis_task_id) BETWEEN 1 AND 64),
    list_id          uuid NOT NULL REFERENCES app.catalog_list (id) ON DELETE CASCADE,
    class_id         uuid NOT NULL REFERENCES app.catalog_class (id) ON DELETE CASCADE
);

CREATE TABLE app.catalog_question (
    id                  uuid PRIMARY KEY,
    period              text NOT NULL REFERENCES app.catalog_period (period),
    question_id         text NOT NULL CHECK (question_id ~ '^[LP][1-9]\d?-Q[1-9]\d?$'),
    list_id             uuid NOT NULL REFERENCES app.catalog_list (id) ON DELETE CASCADE,
    dikastis_problem_id text NOT NULL CHECK (length(dikastis_problem_id) BETWEEN 1 AND 64),
    title               text NOT NULL CHECK (length(title) BETWEEN 1 AND 300),
    description         text NOT NULL CHECK (length(description) <= 20000),
    input_description   text NOT NULL CHECK (length(input_description) <= 20000),
    output_description  text NOT NULL CHECK (length(output_description) <= 20000),
    samples             jsonb NOT NULL,
    time_limit_ms       integer CHECK (time_limit_ms BETWEEN 0 AND 600000),
    content_hash        char(64) NOT NULL,
    version             integer NOT NULL CHECK (version >= 1),
    first_seen          timestamptz NOT NULL,
    updated_at          timestamptz NOT NULL,
    missing_since       timestamptz,
    UNIQUE (period, question_id)
);

-- As versões anteriores de um enunciado que mudou no Dikastis: as 5 mais recentes.
CREATE TABLE app.catalog_question_version (
    question_id        uuid NOT NULL REFERENCES app.catalog_question (id) ON DELETE CASCADE,
    version            integer NOT NULL,
    title              text NOT NULL,
    description        text NOT NULL,
    input_description  text NOT NULL,
    output_description text NOT NULL,
    samples            jsonb NOT NULL,
    content_hash       char(64) NOT NULL,
    replaced_at        timestamptz NOT NULL,
    PRIMARY KEY (question_id, version)
);

CREATE TABLE app.import_run (
    id          uuid PRIMARY KEY,
    account_id  uuid NOT NULL REFERENCES app.account (id) ON DELETE CASCADE,
    mode        text NOT NULL CHECK (mode IN ('manual', 'semi')),
    period      text NOT NULL REFERENCES app.catalog_period (period),
    started_at  timestamptz NOT NULL,
    finished_at timestamptz,
    counts      jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX import_run_started ON app.import_run (started_at DESC);

CREATE TABLE app.import_token (
    id           uuid PRIMARY KEY,
    account_id   uuid NOT NULL REFERENCES app.account (id) ON DELETE CASCADE,
    token_hash   char(64) NOT NULL UNIQUE,
    label        text NOT NULL CHECK (length(label) BETWEEN 1 AND 60),
    created_at   timestamptz NOT NULL,
    expires_at   timestamptz NOT NULL,
    revoked_at   timestamptz,
    last_used_at timestamptz
);
CREATE INDEX import_token_account ON app.import_token (account_id);

GRANT SELECT, INSERT, UPDATE ON
    app.catalog_period, app.catalog_class, app.catalog_list, app.catalog_list_task,
    app.catalog_question, app.import_run, app.import_token
TO ipc_app;
-- Só as versões antigas (a sexta sai) e as tarefas de uma lista são apagadas pelo código.
GRANT SELECT, INSERT, DELETE ON app.catalog_question_version TO ipc_app;
GRANT DELETE ON app.catalog_list_task TO ipc_app;
