// O mapeamento dos nomes do Dikastis para o catálogo (S50-03): o período e o curso de uma turma,
// o tipo de uma tarefa e o identificador de uma questão (26.2L1Q1 → L1-Q1).

export type Curso = "SI" | "EC" | "CC/IA" | "CC" | "outro";
export type TipoDeLista = "treino" | "lista" | "prova";

/** "IP SI UFPE 2026.2" → "2026.2"; sem período no fim, null. */
export function periodoDaTurma(nome: string): string | null {
  return /(\d{4}\.[12])\s*$/.exec(nome)?.[1] ?? null;
}

export function cursoDaTurma(nome: string): Curso {
  if (/\bCC\s*\/\s*IA\b/i.test(nome) || /\bIA\b/.test(nome)) return "CC/IA";
  if (/\bSI\b/.test(nome)) return "SI";
  if (/\bEC\b/.test(nome)) return "EC";
  if (/\bCC\b/.test(nome)) return "CC";
  return "outro";
}

/** Os períodos têm o formato AAAA.S, então a ordem do texto é a ordem do tempo. */
export function periodoAPartirDe(periodo: string, minimo: string): boolean {
  return periodo >= minimo;
}

export interface TipoDaTarefa {
  tipo: TipoDeLista;
  numero: number | null;
}

/** "Lista de Treinamento" → treino; "Lista 3" → lista 3; "Prova 1" → prova 1; outras, null. */
export function tipoDaTarefa(titulo: string): TipoDaTarefa | null {
  const limpo = titulo.trim();
  if (/^Lista\s+de\s+Treinamento\b/i.test(limpo)) return { tipo: "treino", numero: null };
  const lista = /^Lista\s+(\d+)\b/i.exec(limpo);
  if (lista?.[1]) return comNumero("lista", Number(lista[1]));
  const prova = /^Prova\s+(\d+)\b/i.exec(limpo);
  if (prova?.[1]) return comNumero("prova", Number(prova[1]));
  return null;
}

function comNumero(tipo: TipoDeLista, numero: number): TipoDaTarefa | null {
  return numero >= 1 && numero <= 20 ? { tipo, numero } : null;
}

export interface QuestaoDoTitulo {
  periodo: string;
  /** L1-Q1 ou P1-Q2, sem zero à esquerda. */
  id: string;
}

const PREFIXO = /^(\d{2})\.([12])\s*([LP])(\d+)\s*Q(\d+)/;

/** "26.2L1Q1 - Eco" → {periodo: "2026.2", id: "L1-Q1"}; "20.2L1Q01" → L1-Q1 de 2020.2. */
export function questaoDoTitulo(titulo: string): QuestaoDoTitulo | null {
  const partes = PREFIXO.exec(titulo.trim());
  if (!partes) return null;
  const [, ano, semestre, letra, lista, questao] = partes;
  const n = Number(lista);
  const q = Number(questao);
  if (n < 1 || n > 99 || q < 1 || q > 99) return null;
  return { periodo: `20${ano}.${semestre}`, id: `${letra}${n}-Q${q}` };
}

/** O título sem o prefixo: "26.2L1Q1 - Eco" → "Eco"; sem nada depois, o título inteiro. */
export function tituloSemPrefixo(titulo: string): string {
  const resto = titulo
    .trim()
    .replace(PREFIXO, "")
    .replace(/^[\s\-–—:]+/, "")
    .trim();
  return resto === "" ? titulo.trim() : resto;
}

/** O limite de tempo em milissegundos: até 60 é em segundos (ver docs/api-dikastis.md). */
export function limiteEmMs(valor: number | null): number | null {
  if (valor === null || valor < 0) return null;
  const ms = Math.round(valor <= 60 ? valor * 1000 : valor);
  return ms <= 600_000 ? ms : null;
}
