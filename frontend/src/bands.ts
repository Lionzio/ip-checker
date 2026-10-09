import type { SimilarityBand } from "./types/api";

/**
 * Cores das faixas de similaridade do FR-29, sempre com o nome da faixa escrito junto (NFR-19):
 * no painel de plágio (S17-03) e na comparação com o gabarito (S32-06).
 */
export const BAND_STYLES: Record<SimilarityBand["id"], string> = {
  plagio: "border-red-400 bg-red-100 text-red-900 dark:border-red-500 dark:bg-red-950 dark:text-red-100",
  altas_chances:
    "border-orange-400 bg-orange-100 text-orange-900 dark:border-orange-500 dark:bg-orange-950 dark:text-orange-100",
  requer_atencao:
    "border-amber-400 bg-amber-100 text-amber-900 dark:border-amber-500 dark:bg-amber-950 dark:text-amber-100",
  ligeiramente_suspeito:
    "border-sky-400 bg-sky-100 text-sky-900 dark:border-sky-500 dark:bg-sky-950 dark:text-sky-100",
  sem_suspeitas:
    "border-green-400 bg-green-100 text-green-900 dark:border-green-500 dark:bg-green-950 dark:text-green-100",
};

export const PERCENT = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
