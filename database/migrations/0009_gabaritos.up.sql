-- Gabaritos no banco, até dois por questão, cadastrados pelo painel (Sprint 51, S51-01; ADR-17).
-- O banco passa a ser a fonte da verdade: a chefia cola o gabarito "Notion" e o "IP CC" de cada
-- questão, o analisador o confere ao salvar e as violações ficam registradas. O código do gabarito
-- é confidencial (NFR-27): só a API (ipc_app) o lê; a view de leitura (ipc_reader) nunca o vê, e a
-- auditoria guarda só o SHA-256 do que foi salvo.

CREATE TABLE app.gabarito (
    id          uuid PRIMARY KEY,
    period      text NOT NULL REFERENCES app.catalog_period (period),
    question_id text NOT NULL CHECK (question_id ~ '^L[1-6]-Q[1-9]\d?$'),
    kind        text NOT NULL CHECK (kind IN ('notion', 'ip_cc')),
    source      text NOT NULL CHECK (source IN ('painel', 'dikastis', 'importado')),
    code        text NOT NULL CHECK (octet_length(code) BETWEEN 1 AND 51200),
    -- As regras acionadas ao salvar: [{"rule_id": "R-37", "line": 3}]. Nunca um trecho do código.
    violations  jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_by  uuid REFERENCES app.account (id) ON DELETE SET NULL,
    created_at  timestamptz NOT NULL,
    updated_by  uuid REFERENCES app.account (id) ON DELETE SET NULL,
    updated_at  timestamptz NOT NULL,
    UNIQUE (period, question_id, kind)
);

-- Quem criou, alterou ou apagou cada gabarito, e quando (ADR-17, item 1). Sem chave estrangeira
-- para o gabarito: o registro do que foi apagado continua.
CREATE TABLE app.gabarito_audit (
    id          bigserial PRIMARY KEY,
    period      text NOT NULL,
    question_id text NOT NULL,
    kind        text NOT NULL,
    action      text NOT NULL CHECK (action IN ('criar', 'alterar', 'apagar')),
    account_id  uuid REFERENCES app.account (id) ON DELETE SET NULL,
    at          timestamptz NOT NULL,
    code_sha256 char(64) NOT NULL
);
CREATE INDEX gabarito_audit_question ON app.gabarito_audit (period, question_id, kind, at DESC);

GRANT SELECT, INSERT, UPDATE, DELETE ON app.gabarito TO ipc_app;
GRANT SELECT, INSERT ON app.gabarito_audit TO ipc_app;
GRANT USAGE ON SEQUENCE app.gabarito_audit_id_seq TO ipc_app;
