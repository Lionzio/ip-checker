-- Volta da 0001: apaga o esquema app inteiro (contas, e-mails, sessões e tokens).
-- O papel ipc_app fica: ele pode ter membros criados fora das migrações (o usuário da API).

DROP SCHEMA app CASCADE;
