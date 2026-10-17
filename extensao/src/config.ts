// Constantes da extensão (S50-01). Nada aqui é segredo.

/** A organização da disciplina de IP no Dikastis (onde ficam as turmas de cada período). */
export const ORGANIZACAO_IP = "01F7ACA5J73D78D3ETM724AQ3M";
/** O endereço do Dikastis; a API fica em /api, na mesma origem da página. */
export const DIKASTIS = "https://dikastis.com.br";
/** O IP-Checker do piloto (a Vercel repassa /api/* à API). */
export const ENDERECO_PADRAO = "https://ip-checker-red-phi.vercel.app";
/** As turmas de períodos anteriores ficam de fora. */
export const PERIODO_MINIMO = "2026.2";
/** No máximo 2 pedidos por segundo ao Dikastis (S50-02). */
export const INTERVALO_DIKASTIS_MS = 500;
/** As esperas antes de repetir um 429 ou 5xx do Dikastis. */
export const ESPERAS_DIKASTIS_MS = [2_000, 4_000, 8_000] as const;
/** O modo semi-automático verifica no máximo uma vez a cada 30 minutos (S50-07). */
export const INTERVALO_SEMI_MS = 30 * 60 * 1000;
/** As questões vão ao IP-Checker em partes de até 100 KB e 60 questões (S50-03). */
export const PARTE_MAX_BYTES = 100_000;
export const PARTE_MAX_QUESTOES = 60;
