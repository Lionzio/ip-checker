-- Sprint 21 (S21-01): telemetria anônima das verificações (blueprint 5.2.4, FR-16, FR-17, NFR-12).
-- Aplicada por `python -m ipc_api.db.migrate up`, com a credencial de administrador do banco.
--
-- Nada aqui identifica uma pessoa: não há código, IP, conta nem identificador de cliente.
-- ipc_writer só insere eventos e chama o expurgo; ipc_reader só lê as views v_*. A API entra
-- no banco como membro de ipc_app, que passa a ser membro de ipc_writer.

CREATE SCHEMA telemetry;

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ipc_writer') THEN
    CREATE ROLE ipc_writer NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ipc_reader') THEN
    CREATE ROLE ipc_reader NOLOGIN;
  END IF;
END
$$;

CREATE TYPE telemetry.outcome AS ENUM
  ('valid', 'invalid', 'syntax_error', 'rejected', 'analysis_limit');

CREATE TABLE telemetry.validation_event (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  semester text NOT NULL CHECK (semester ~ '^[0-9]{4}[.][12]$'),
  list_number smallint NOT NULL CHECK (list_number BETWEEN 1 AND 6),
  question_id text NULL CHECK (question_id ~ '^L[1-6]-Q[0-9]{1,3}$'),
  ruleset_version text NOT NULL CHECK (ruleset_version ~ '^[0-9]{4}[.][12][.][0-9]+$'),
  outcome telemetry.outcome NOT NULL,
  violation_count smallint NOT NULL DEFAULT 0 CHECK (violation_count BETWEEN 0 AND 200),
  analysis_ms integer NOT NULL CHECK (analysis_ms >= 0)
);

CREATE INDEX validation_event_created_at ON telemetry.validation_event (created_at);

CREATE TABLE telemetry.validation_event_rule (
  event_id uuid NOT NULL REFERENCES telemetry.validation_event (id) ON DELETE CASCADE,
  rule_id text NOT NULL CHECK (rule_id ~ '^R-[0-9]{2}$'),
  occurrences smallint NOT NULL CHECK (occurrences BETWEEN 1 AND 200),
  PRIMARY KEY (event_id, rule_id)
);

-- FR-17: consultas agregadas para professores, por período, lista e questão.
CREATE VIEW telemetry.v_top_rules_by_list AS
SELECT e.semester, e.list_number, e.question_id, r.rule_id,
       count(*) AS events,
       sum(r.occurrences) AS occurrences
FROM telemetry.validation_event e
JOIN telemetry.validation_event_rule r ON r.event_id = e.id
GROUP BY e.semester, e.list_number, e.question_id, r.rule_id;

CREATE VIEW telemetry.v_syntax_error_rate AS
SELECT semester, list_number, question_id,
       count(*) AS events,
       count(*) FILTER (WHERE outcome = 'syntax_error') AS syntax_errors,
       round(100.0 * count(*) FILTER (WHERE outcome = 'syntax_error') / count(*), 1)
         AS syntax_error_pct
FROM telemetry.validation_event
GROUP BY semester, list_number, question_id;

CREATE VIEW telemetry.v_weekly_volume AS
SELECT semester, list_number,
       date_trunc('week', created_at)::date AS week,
       count(*) AS events,
       count(*) FILTER (WHERE outcome = 'valid') AS valid,
       count(*) FILTER (WHERE outcome = 'invalid') AS invalid,
       count(*) FILTER (WHERE outcome = 'syntax_error') AS syntax_error,
       count(*) FILTER (WHERE outcome IN ('rejected', 'analysis_limit')) AS refused
FROM telemetry.validation_event
GROUP BY semester, list_number, date_trunc('week', created_at)::date;

-- P-06: nada fica mais de 12 meses. A função roda com os direitos de quem a criou, então o
-- ipc_writer consegue expurgar sem ter DELETE nem SELECT nas tabelas. A API a chama ao subir e
-- uma vez por dia; o pg_cron não é necessário (ele não existe no PostgreSQL das Fases 0 e 2).
CREATE FUNCTION telemetry.purge_expired() RETURNS integer
LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
  WITH removed AS (
    DELETE FROM telemetry.validation_event
    WHERE created_at < now() - interval '12 months'
    RETURNING 1
  )
  SELECT count(*)::integer FROM removed
$$;

REVOKE ALL ON FUNCTION telemetry.purge_expired() FROM PUBLIC;

GRANT USAGE ON SCHEMA telemetry TO ipc_writer, ipc_reader;
GRANT INSERT ON telemetry.validation_event, telemetry.validation_event_rule TO ipc_writer;
GRANT EXECUTE ON FUNCTION telemetry.purge_expired() TO ipc_writer;
GRANT SELECT ON telemetry.v_top_rules_by_list, telemetry.v_syntax_error_rate,
  telemetry.v_weekly_volume TO ipc_reader;
GRANT ipc_writer TO ipc_app;
