-- Sprint 23 (S23-03, REC-06): registro das ações de gerenciamento da equipe. Responde "quem
-- aprovou esta conta?" (ameaça 13): cada aprovação, recusa, mudança de cargo, remoção e
-- reativação, com quem fez, sobre quem e quando. Só o desenvolvedor e os professores o leem.

-- Nomes e cargos são cópias do momento da ação: o histórico sobrevive à edição do perfil e ao
-- expurgo de contas (Q-19 d), que deixa os identificadores vazios.
CREATE TABLE app.management_log (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  at timestamptz NOT NULL,
  action text NOT NULL CHECK (
    action IN ('aprovar', 'recusar', 'alterar_cargo', 'remover', 'reativar')
  ),
  actor_id uuid NULL REFERENCES app.account (id) ON DELETE SET NULL,
  actor_name text NOT NULL,
  actor_role app.role NULL,
  target_id uuid NULL REFERENCES app.account (id) ON DELETE SET NULL,
  target_name text NOT NULL,
  from_status app.status NOT NULL,
  to_status app.status NOT NULL,
  from_role app.role NULL,
  to_role app.role NULL
);

CREATE INDEX management_log_at ON app.management_log (at DESC, id DESC);

-- 12 meses, como a telemetria (P-06). A função roda com os direitos de quem a criou: a API
-- expurga sem ter DELETE na tabela, e o prazo é contado a partir do relógio do banco, então
-- nenhuma chamada apaga um registro com menos de 12 meses.
CREATE FUNCTION app.purge_management_log(asked timestamptz) RETURNS integer
LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
  WITH removed AS (
    DELETE FROM app.management_log
    WHERE at < least(asked, now()) - interval '12 months'
    RETURNING 1
  )
  SELECT count(*)::integer FROM removed
$$;

REVOKE ALL ON FUNCTION app.purge_management_log(timestamptz) FROM PUBLIC;

-- Só acrescentar e ler: a API não altera nem apaga um registro.
GRANT SELECT, INSERT ON app.management_log TO ipc_app;
GRANT EXECUTE ON FUNCTION app.purge_management_log(timestamptz) TO ipc_app;
