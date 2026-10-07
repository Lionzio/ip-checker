-- Sprint 28 (S28-02; P-09, Q-15): relatório de eficácia do piloto.
--
-- Critério 2 (uso pela equipe): em cada lista, pelo menos 70% dos membros ativos usam a ferramenta.
-- A telemetria é anônima (NFR-12) e não diz quem usou; por isso a adoção fica aqui, no esquema
-- app, ligada à conta: um registro por (conta, período, lista), gravado na primeira verificação,
-- sem data, sem código e sem resultado, e apagado junto com a conta. Quem consulta (ipc_reader) só
-- vê a porcentagem por período e lista, nunca quem usou.
--
-- A conta de verificação do deploy (S16-02) é marcada pelo pipeline, com a credencial de
-- administrador: as verificações dela não entram na telemetria nem na adoção, e ela não conta
-- como membro da equipe.

ALTER TABLE app.account ADD COLUMN check_account boolean NOT NULL DEFAULT false;

CREATE TABLE app.list_adoption (
  account_id uuid NOT NULL REFERENCES app.account (id) ON DELETE CASCADE,
  semester text NOT NULL CHECK (semester ~ '^[0-9]{4}[.][12]$'),
  list_number smallint NOT NULL CHECK (list_number BETWEEN 1 AND 6),
  PRIMARY KEY (account_id, semester, list_number)
);

-- A API só acrescenta (INSERT ... ON CONFLICT DO NOTHING); não lê nem apaga.
GRANT INSERT ON app.list_adoption TO ipc_app;

-- Membros ativos: contas ativas da equipe, sem a do desenvolvedor e sem a conta de verificação
-- [PREMISSA: o desenvolvedor mantém a ferramenta e não corrige listas]. A porcentagem usa os
-- membros ativos no momento da consulta: quem saiu da equipe deixa de contar nos dois lados.
-- Cada período que já teve alguma verificação aparece com as 6 listas, mesmo as sem uso (0%).
-- A view roda com os direitos de quem a criou: o ipc_reader a lê sem ter acesso ao esquema app.
CREATE VIEW telemetry.v_team_adoption_by_list AS
WITH members AS (
  SELECT a.id
  FROM app.account a
  WHERE a.status = 'ativo' AND a.role <> 'desenvolvedor' AND NOT a.check_account
),
periods AS (
  SELECT DISTINCT semester FROM app.list_adoption
)
SELECT p.semester, l.list_number::smallint AS list_number,
       CASE WHEN (SELECT count(*) FROM members) = 0 THEN NULL
            ELSE round(100.0 * count(m.id) / (SELECT count(*) FROM members), 1)
       END AS adoption_pct
FROM periods p
CROSS JOIN generate_series(1, 6) AS l (list_number)
LEFT JOIN app.list_adoption u ON u.semester = p.semester AND u.list_number = l.list_number
LEFT JOIN members m ON m.id = u.account_id
GROUP BY p.semester, l.list_number;

GRANT SELECT ON telemetry.v_team_adoption_by_list TO ipc_reader;
