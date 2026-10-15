-- Painel por lista (S40-03, US-16): a API passa a ler as views anônimas da telemetria para mostrar,
-- no Gerenciar, as regras mais violadas de cada lista. O ipc_reader só lê as views v_* (contagens
-- por período, lista e questão, sem código, conta, nome nem IP); nenhuma tabela nova é exposta.
GRANT ipc_reader TO ipc_app;
