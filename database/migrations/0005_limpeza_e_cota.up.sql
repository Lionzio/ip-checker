-- Sprint 25 (S25-03; Q-19 d, REC-06): limpeza diária do banco e expurgo de contas sem atividade.
-- S25-05: a cota diária de feedbacks passa a ficar no banco e não zera num deploy.
-- Uma função só, chamada pela API ao subir e uma vez por dia. Ela roda com os direitos de quem a
-- criou: a API continua sem DELETE nas contas, e os prazos são contados pelo relógio do banco, então
-- nenhuma chamada apaga antes da hora.

-- Atividade de uma conta: o cadastro, cada login, a confirmação do e-mail e cada mudança de status
-- ou de cargo. Uma conta removida conta os 365 dias a partir da remoção.
ALTER TABLE app.account ADD COLUMN last_activity_at timestamptz NOT NULL DEFAULT now();

-- Uma conta apagada leva os e-mails dela (o e-mail fica livre para um novo cadastro) e deixa vazio
-- o "quem decidiu" das contas que ela aprovou; o registro de gerenciamento guarda o nome (REC-06).
ALTER TABLE app.account_email DROP CONSTRAINT account_email_account_id_fkey;
ALTER TABLE app.account_email ADD CONSTRAINT account_email_account_id_fkey
  FOREIGN KEY (account_id) REFERENCES app.account (id) ON DELETE CASCADE;
ALTER TABLE app.account DROP CONSTRAINT account_decided_by_fkey;
ALTER TABLE app.account ADD CONSTRAINT account_decided_by_fkey
  FOREIGN KEY (decided_by) REFERENCES app.account (id) ON DELETE SET NULL;

-- Cota diária de feedbacks por conta (S25-05): o dia é o de UTC, e o teto do servidor é a soma
-- do dia. Some com a conta e, dois dias depois, na limpeza diária.
CREATE TABLE app.feedback_quota (
  day date NOT NULL,
  account_id uuid NOT NULL REFERENCES app.account (id) ON DELETE CASCADE,
  used integer NOT NULL CHECK (used > 0),
  PRIMARY KEY (day, account_id)
);
GRANT SELECT, INSERT, UPDATE ON app.feedback_quota TO ipc_app;

CREATE FUNCTION app.housekeeping(asked timestamptz)
RETURNS TABLE (sessions integer, tokens integer, unverified integer, inactive integer, log integer)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
DECLARE
  moment timestamptz := least(asked, now());
BEGIN
  -- Sessões vencidas: a API já as recusa; aqui só deixam de ocupar espaço.
  DELETE FROM app.session s WHERE s.expires_at <= moment;
  GET DIAGNOSTICS sessions = ROW_COUNT;

  -- Links de e-mail já usados ou vencidos (verificação e redefinição de senha).
  DELETE FROM app.email_token t WHERE t.used_at IS NOT NULL OR t.expires_at <= moment;
  GET DIAGNOSTICS tokens = ROW_COUNT;

  -- Cadastros que nunca confirmaram o e-mail: 48 horas desde o último pedido (o link vale 24; um
  -- novo cadastro com o mesmo e-mail recomeça o prazo). O nome e o e-mail ficam livres.
  DELETE FROM app.account a
  WHERE a.status = 'aguardando_verificacao'
    AND a.last_activity_at <= moment - interval '48 hours';
  GET DIAGNOSTICS unverified = ROW_COUNT;

  -- Q-19 d: contas fora do status ativo, com 365 dias sem atividade. A do desenvolvedor, nunca.
  DELETE FROM app.account a
  WHERE a.status IN ('aguardando_aprovacao', 'recusado', 'ex_monitor', 'conselheiro', 'inativo')
    AND a.last_activity_at <= moment - interval '365 days'
    AND a.signup_method <> 'seed'
    AND a.role IS DISTINCT FROM 'desenvolvedor';
  GET DIAGNOSTICS inactive = ROW_COUNT;

  -- REC-06: o registro de gerenciamento guarda 12 meses.
  DELETE FROM app.management_log m WHERE m.at < moment - interval '12 months';
  GET DIAGNOSTICS log = ROW_COUNT;

  -- S25-05: a cota de feedbacks só importa no dia; ontem fica, por causa do fuso.
  DELETE FROM app.feedback_quota q WHERE q.day < (moment AT TIME ZONE 'UTC')::date - 1;

  RETURN NEXT;
END
$$;

REVOKE ALL ON FUNCTION app.housekeeping(timestamptz) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.housekeeping(timestamptz) TO ipc_app;
