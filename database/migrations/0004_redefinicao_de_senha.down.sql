-- Volta da 0004: apaga os tokens de redefinição de senha e restringe de novo a finalidade.

DELETE FROM app.email_token WHERE purpose = 'redefinicao';
ALTER TABLE app.email_token DROP CONSTRAINT email_token_purpose_check;
ALTER TABLE app.email_token ADD CONSTRAINT email_token_purpose_check
  CHECK (purpose IN ('verificacao'));
