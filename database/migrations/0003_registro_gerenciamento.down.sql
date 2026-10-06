-- Volta da 0003: apaga o registro das ações de gerenciamento e o expurgo dele.

DROP FUNCTION app.purge_management_log(timestamptz);
DROP TABLE app.management_log;
