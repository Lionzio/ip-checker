-- Volta da 0008: apaga o catálogo e os tokens de importação (dados do Dikastis e hashes; nenhum
-- dado de aluno). Uma nova sincronização refaz o catálogo.
DROP TABLE app.import_token;
DROP TABLE app.import_run;
DROP TABLE app.catalog_question_version;
DROP TABLE app.catalog_question;
DROP TABLE app.catalog_list_task;
DROP TABLE app.catalog_list;
DROP TABLE app.catalog_class;
DROP TABLE app.catalog_period;
