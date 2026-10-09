# Gabaritos sintéticos (e2e e ambiente local)

Gabaritos **inventados** para o e2e e para o ambiente local testarem a comparação com o gabarito
(ADR-11, Sprint 32). Nenhum é gabarito oficial: os oficiais ficam no repositório privado
`Lionzio/ip-checker-gabaritos` e nunca entram neste repositório (NFR-27). O compose monta esta pasta
na API (`IPC_GABARITOS_DIR`); para usar o clone dos gabaritos oficiais na sua máquina, defina
`IPC_GABARITOS_HOST_DIR` no `deploy/.env` (`deploy/compose.md`).
