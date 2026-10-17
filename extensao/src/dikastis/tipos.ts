// Os tipos próprios da extensão (S50-02), desacoplados dos nomes do Dikastis: só o adaptador
// (formatos.ts) conhece os campos de lá.

export interface Turma {
  id: string;
  nome: string;
}

export interface TarefaResumo {
  id: string;
  titulo: string;
}

export interface ProblemaDaTarefa {
  id: string;
  titulo: string;
}

export interface Tarefa {
  titulo: string;
  inicio: string | null;
  fim: string | null;
  problemas: ProblemaDaTarefa[];
}

export interface CasoDeExemplo {
  entrada: string;
  saida: string;
}

export interface Problema {
  titulo: string;
  descricao: string;
  descricaoEntrada: string;
  descricaoSaida: string;
  /** O limite de tempo como o Dikastis manda (ver docs/api-dikastis.md). */
  limiteTempo: number | null;
  /** Só os casos de exemplo: os ocultos são descartados no adaptador e nunca saem dele. */
  exemplos: CasoDeExemplo[];
}
