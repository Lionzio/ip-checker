-- Volta da 0002: apaga o esquema telemetry inteiro (eventos, views e o expurgo).
-- Os papéis ipc_writer e ipc_reader ficam: podem ter membros criados fora das migrações.

REVOKE ipc_writer FROM ipc_app;
DROP SCHEMA telemetry CASCADE;
