// Do catálogo lido no Dikastis para o contrato da API (S50-05): o manifesto, as questões e as
// partes de até 100 KB.

import { PARTE_MAX_BYTES, PARTE_MAX_QUESTOES } from "../config";
import type { Catalogo, QuestaoDoCatalogo } from "../catalogo/descoberta";
import type { ManifestoApi, QuestaoApi } from "../ipchecker/cliente";

export function montarManifesto(catalogo: Catalogo, modo: "manual" | "semi"): ManifestoApi {
  return {
    period: catalogo.periodo,
    mode: modo,
    classes: catalogo.turmas.map((t) => ({
      dikastis_org_id: t.id,
      name: t.nome,
      course: t.curso,
    })),
    lists: catalogo.listas.map((l) => ({
      dikastis_task_id: l.tarefaId,
      class_org_id: l.turmaId,
      kind: l.tipo,
      number: l.numero,
      title: l.titulo,
      starts_at: l.inicio,
      ends_at: l.fim,
      questions: l.questoes.map((q) => ({
        dikastis_problem_id: q.problemaId,
        question_id: q.questaoId,
        content_hash: q.hash,
      })),
    })),
  };
}

export function questaoParaApi(q: QuestaoDoCatalogo): QuestaoApi {
  return {
    question_id: q.questaoId,
    dikastis_problem_id: q.problemaId,
    list_kind: q.tipoLista,
    list_number: q.numeroLista,
    title: q.titulo,
    description: q.descricao,
    input_description: q.descricaoEntrada,
    output_description: q.descricaoSaida,
    samples: q.exemplos.map((e) => ({ input: e.entrada, output: e.saida })),
    time_limit_ms: q.limiteTempoMs,
    content_hash: q.hash,
  };
}

const bytes = (valor: unknown) => new TextEncoder().encode(JSON.stringify(valor)).length;

/**
 * As questões em partes de até ``maxBytes`` (o corpo inteiro, com folga para o run_id e o
 * período) e ``maxQuestoes``. Uma questão maior que o limite vai sozinha.
 */
export function dividirEmPartes(
  questoes: QuestaoApi[],
  maxBytes = PARTE_MAX_BYTES,
  maxQuestoes = PARTE_MAX_QUESTOES,
): QuestaoApi[][] {
  const folga = 200;
  const partes: QuestaoApi[][] = [];
  let atual: QuestaoApi[] = [];
  let tamanho = folga;
  for (const questao of questoes) {
    const peso = bytes(questao) + 1;
    if (atual.length > 0 && (tamanho + peso > maxBytes || atual.length >= maxQuestoes)) {
      partes.push(atual);
      atual = [];
      tamanho = folga;
    }
    atual.push(questao);
    tamanho += peso;
  }
  if (atual.length > 0) partes.push(atual);
  return partes;
}
