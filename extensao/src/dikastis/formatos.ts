// Os formatos das respostas do Dikastis (S50-02; docs/api-dikastis.md). Um validador por
// endereço, sem biblioteca: cada campo usado é conferido; os demais são ignorados (e nunca
// guardados). Campo faltando ou de outro tipo lança FormatoDesconhecido.

import { FormatoDesconhecido } from "./erros";
import type { CasoDeExemplo, Problema, Tarefa, TarefaResumo, Turma } from "./tipos";

export type Validador<T> = (dado: unknown, endereco: string) => T;

type Objeto = Record<string, unknown>;

function objeto(valor: unknown, endereco: string, campo: string): Objeto {
  if (typeof valor !== "object" || valor === null || Array.isArray(valor)) {
    throw new FormatoDesconhecido(endereco, campo, "um objeto");
  }
  return valor as Objeto;
}

function texto(o: Objeto, campo: string, endereco: string, caminho = campo): string {
  const valor = o[campo];
  if (typeof valor !== "string") throw new FormatoDesconhecido(endereco, caminho, "um texto");
  return valor;
}

/** Texto, ou vazio quando o Dikastis manda null (descrições opcionais). */
function textoOuVazio(o: Objeto, campo: string, endereco: string, caminho = campo): string {
  const valor = o[campo];
  if (valor === null || valor === undefined) return "";
  if (typeof valor !== "string") throw new FormatoDesconhecido(endereco, caminho, "um texto");
  return valor;
}

function dataOuNulo(o: Objeto, campo: string, endereco: string): string | null {
  const valor = o[campo];
  if (valor === null || valor === undefined) return null;
  if (typeof valor !== "string" || Number.isNaN(Date.parse(valor))) {
    throw new FormatoDesconhecido(endereco, campo, "uma data");
  }
  return new Date(valor).toISOString();
}

function lista(o: Objeto, campo: string, endereco: string): unknown[] {
  const valor = o[campo];
  if (!Array.isArray(valor)) throw new FormatoDesconhecido(endereco, campo, "uma lista");
  return valor;
}

/** GET /api/organizations/<id>: as turmas (``teams``) da organização. */
export const validarOrganizacao: Validador<Turma[]> = (dado, endereco) => {
  const raiz = objeto(dado, endereco, "(resposta)");
  return lista(raiz, "teams", endereco).map((item, i) => {
    const turma = objeto(item, endereco, `teams[${i}]`);
    return {
      id: texto(turma, "id", endereco, `teams[${i}].id`),
      nome: texto(turma, "name", endereco, `teams[${i}].name`),
    };
  });
};

/** GET /api/teams/<id>: as tarefas (``tasks``). Os membros da turma vêm junto e são ignorados. */
export const validarTurma: Validador<TarefaResumo[]> = (dado, endereco) => {
  const raiz = objeto(dado, endereco, "(resposta)");
  return lista(raiz, "tasks", endereco).map((item, i) => {
    const tarefa = objeto(item, endereco, `tasks[${i}]`);
    return {
      id: texto(tarefa, "id", endereco, `tasks[${i}].id`),
      titulo: texto(tarefa, "title", endereco, `tasks[${i}].title`),
    };
  });
};

/** GET /api/tasks/<id>: título, datas e os problemas da tarefa. */
export const validarTarefa: Validador<Tarefa> = (dado, endereco) => {
  const raiz = objeto(dado, endereco, "(resposta)");
  return {
    titulo: texto(raiz, "title", endereco),
    inicio: dataOuNulo(raiz, "beginTime", endereco),
    fim: dataOuNulo(raiz, "endTime", endereco),
    problemas: lista(raiz, "problems", endereco).map((item, i) => {
      const entrada = objeto(item, endereco, `problems[${i}]`);
      const problema = objeto(entrada["problem"], endereco, `problems[${i}].problem`);
      return {
        id: texto(problema, "id", endereco, `problems[${i}].problem.id`),
        titulo: texto(problema, "title", endereco, `problems[${i}].problem.title`),
      };
    }),
  };
};

/** GET /api/problems/<id>: o enunciado e só os casos de exemplo (``isSample: true``). */
export const validarProblema: Validador<Problema> = (dado, endereco) => {
  const raiz = objeto(dado, endereco, "(resposta)");
  const limite = raiz["timeLimit"];
  if (limite !== null && limite !== undefined && typeof limite !== "number") {
    throw new FormatoDesconhecido(endereco, "timeLimit", "um número");
  }
  const exemplos: CasoDeExemplo[] = [];
  lista(raiz, "testCases", endereco).forEach((item, i) => {
    const caso = objeto(item, endereco, `testCases[${i}]`);
    if (typeof caso["isSample"] !== "boolean") {
      throw new FormatoDesconhecido(endereco, `testCases[${i}].isSample`, "verdadeiro ou falso");
    }
    // Os casos ocultos não são lidos além do isSample: nunca saem daqui.
    if (!caso["isSample"]) return;
    exemplos.push({
      entrada: texto(caso, "input", endereco, `testCases[${i}].input`),
      saida: texto(caso, "output", endereco, `testCases[${i}].output`),
    });
  });
  return {
    titulo: texto(raiz, "title", endereco),
    descricao: textoOuVazio(raiz, "description", endereco),
    descricaoEntrada: textoOuVazio(raiz, "inputDescription", endereco),
    descricaoSaida: textoOuVazio(raiz, "outputDescription", endereco),
    limiteTempo: typeof limite === "number" && Number.isFinite(limite) ? limite : null,
    exemplos,
  };
};
