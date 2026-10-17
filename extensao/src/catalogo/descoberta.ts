// A descoberta (S50-03): lê no Dikastis as turmas do período, as tarefas e os problemas, e monta
// o catálogo. Roda no script da página. Só os casos de exemplo entram; os ocultos são descartados
// no adaptador (formatos.ts) e nunca chegam aqui.

import { ORGANIZACAO_IP, PERIODO_MINIMO } from "../config";
import type { ClienteDikastis } from "../dikastis/cliente";
import {
  validarOrganizacao,
  validarProblema,
  validarTarefa,
  validarTurma,
} from "../dikastis/formatos";
import { hashDoConteudo } from "./hash";
import {
  type Curso,
  type TipoDeLista,
  cursoDaTurma,
  limiteEmMs,
  periodoAPartirDe,
  periodoDaTurma,
  questaoDoTitulo,
  tipoDaTarefa,
  tituloSemPrefixo,
} from "./mapeamento";

export interface TurmaDoCatalogo {
  id: string;
  nome: string;
  curso: Curso;
}

export interface RefQuestao {
  problemaId: string;
  questaoId: string;
  hash: string;
}

export interface ListaDoCatalogo {
  tarefaId: string;
  turmaId: string;
  tipo: TipoDeLista;
  numero: number | null;
  titulo: string;
  inicio: string | null;
  fim: string | null;
  questoes: RefQuestao[];
}

export interface QuestaoDoCatalogo {
  questaoId: string;
  problemaId: string;
  tipoLista: TipoDeLista;
  numeroLista: number | null;
  titulo: string;
  descricao: string;
  descricaoEntrada: string;
  descricaoSaida: string;
  exemplos: { entrada: string; saida: string }[];
  limiteTempoMs: number | null;
  hash: string;
}

export interface Ignorados {
  turmas: number;
  tarefas: number;
  problemas: number;
}

export interface Catalogo {
  periodo: string;
  turmas: TurmaDoCatalogo[];
  listas: ListaDoCatalogo[];
  questoes: QuestaoDoCatalogo[];
  ignorados: Ignorados;
}

export class SemTurmas extends Error {
  constructor(minimo: string) {
    super(`O Dikastis não tem turmas de IP de ${minimo} em diante para esta conta.`);
    this.name = "SemTurmas";
  }
}

export interface OpcoesDescoberta {
  organizacao?: string;
  minimo?: string;
}

export async function lerCatalogo(
  cliente: ClienteDikastis,
  opcoes: OpcoesDescoberta = {},
): Promise<Catalogo> {
  const organizacao = opcoes.organizacao ?? ORGANIZACAO_IP;
  const minimo = opcoes.minimo ?? PERIODO_MINIMO;
  const ignorados: Ignorados = { turmas: 0, tarefas: 0, problemas: 0 };

  const todas = await cliente.get(`organizations/${organizacao}`, validarOrganizacao);
  const comPeriodo = todas.flatMap((turma) => {
    const periodo = periodoDaTurma(turma.nome);
    if (periodo === null || !periodoAPartirDe(periodo, minimo)) {
      ignorados.turmas++;
      return [];
    }
    return [{ ...turma, periodo }];
  });
  if (comPeriodo.length === 0) throw new SemTurmas(minimo);
  // O período mais recente; as turmas de outros períodos ficam para quando ele for o atual.
  const periodo = comPeriodo.map((t) => t.periodo).sort().at(-1) as string;
  const turmas: TurmaDoCatalogo[] = [];
  for (const turma of comPeriodo) {
    if (turma.periodo !== periodo) {
      ignorados.turmas++;
      continue;
    }
    turmas.push({ id: turma.id, nome: turma.nome.trim(), curso: cursoDaTurma(turma.nome) });
  }

  const listas: ListaDoCatalogo[] = [];
  const porQuestao = new Map<string, QuestaoDoCatalogo>();
  for (const turma of turmas) {
    const tarefas = await cliente.get(`teams/${turma.id}`, validarTurma);
    for (const resumo of tarefas) {
      const tipo = tipoDaTarefa(resumo.titulo);
      if (tipo === null) {
        ignorados.tarefas++;
        continue;
      }
      const tarefa = await cliente.get(`tasks/${resumo.id}`, validarTarefa);
      const refs: RefQuestao[] = [];
      for (const problema of tarefa.problemas) {
        const questao = questaoDoTitulo(problema.titulo);
        if (questao === null || questao.periodo !== periodo) {
          ignorados.problemas++;
          continue;
        }
        // A mesma questão em várias turmas é lida uma vez só (a primeira cópia vale).
        let lida = porQuestao.get(questao.id);
        if (lida === undefined) {
          lida = await lerQuestao(cliente, problema.id, questao.id, tipo.tipo, tipo.numero);
          porQuestao.set(questao.id, lida);
        }
        if (!refs.some((r) => r.questaoId === lida.questaoId)) {
          refs.push({ problemaId: lida.problemaId, questaoId: lida.questaoId, hash: lida.hash });
        }
      }
      listas.push({
        tarefaId: resumo.id,
        turmaId: turma.id,
        tipo: tipo.tipo,
        numero: tipo.numero,
        titulo: resumo.titulo.trim().slice(0, 300),
        inicio: tarefa.inicio,
        fim: tarefa.fim,
        questoes: refs,
      });
    }
  }
  return { periodo, turmas, listas, questoes: [...porQuestao.values()], ignorados };
}

async function lerQuestao(
  cliente: ClienteDikastis,
  problemaId: string,
  questaoId: string,
  tipoLista: TipoDeLista,
  numeroLista: number | null,
): Promise<QuestaoDoCatalogo> {
  const problema = await cliente.get(`problems/${problemaId}`, validarProblema);
  const titulo = tituloSemPrefixo(problema.titulo).slice(0, 300);
  // A API aceita até 10 casos de exemplo; as questões de IP têm 1 a 3.
  const exemplos = problema.exemplos
    .slice(0, 10)
    .map((e) => ({ entrada: e.entrada, saida: e.saida }));
  const hash = await hashDoConteudo({
    title: titulo,
    description: problema.descricao,
    input_description: problema.descricaoEntrada,
    output_description: problema.descricaoSaida,
    samples: exemplos.map((e) => ({ input: e.entrada, output: e.saida })),
  });
  return {
    questaoId,
    problemaId,
    tipoLista,
    numeroLista,
    titulo,
    descricao: problema.descricao,
    descricaoEntrada: problema.descricaoEntrada,
    descricaoSaida: problema.descricaoSaida,
    exemplos,
    limiteTempoMs: limiteEmMs(problema.limiteTempo),
    hash,
  };
}
