-- Sprint 24 (S24-04, Q-19 b): "esqueci minha senha" por link de e-mail. O token é o mesmo mecanismo
-- da verificação (só o SHA-256 no banco, uso único), com outra finalidade e prazo de 1 hora.

ALTER TABLE app.email_token DROP CONSTRAINT email_token_purpose_check;
ALTER TABLE app.email_token ADD CONSTRAINT email_token_purpose_check
  CHECK (purpose IN ('verificacao', 'redefinicao'));
