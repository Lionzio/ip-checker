-- Volta da 0005: tira a limpeza diária, a cota de feedbacks, a coluna de atividade e as remoções
-- em cascata.

DROP FUNCTION app.housekeeping(timestamptz);
DROP TABLE app.feedback_quota;
ALTER TABLE app.account DROP CONSTRAINT account_decided_by_fkey;
ALTER TABLE app.account ADD CONSTRAINT account_decided_by_fkey
  FOREIGN KEY (decided_by) REFERENCES app.account (id);
ALTER TABLE app.account_email DROP CONSTRAINT account_email_account_id_fkey;
ALTER TABLE app.account_email ADD CONSTRAINT account_email_account_id_fkey
  FOREIGN KEY (account_id) REFERENCES app.account (id);
ALTER TABLE app.account DROP COLUMN last_activity_at;
