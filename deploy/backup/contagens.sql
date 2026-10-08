-- Linhas por tabela dos esquemas do backup (app e telemetry), em ordem de nome (S30-07).
--
-- Roda no "Backup do banco do piloto", logo depois do pg_dump, e na restauração de ensaio
-- (docs/runbook.md, "Restaurar um backup"): as duas listas precisam ser iguais. Só números e
-- nomes de tabela; nenhum dado.
SELECT format('%s.%s', table_schema, table_name) AS tabela,
       (xpath('/row/n/text()',
              query_to_xml(format('SELECT count(*) AS n FROM %I.%I', table_schema, table_name),
                           false, true, '')))[1]::text::bigint AS linhas
FROM information_schema.tables
WHERE table_schema IN ('app', 'telemetry') AND table_type = 'BASE TABLE'
ORDER BY 1;
