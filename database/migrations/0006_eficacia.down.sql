-- Volta da 0006: tira a view de adoção, os registros de adoção e a marca da conta de verificação.

DROP VIEW telemetry.v_team_adoption_by_list;
DROP TABLE app.list_adoption;
ALTER TABLE app.account DROP COLUMN check_account;
