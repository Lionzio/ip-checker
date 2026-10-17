// O popup (S50-03, S50-07): "Verificar agora" mostra as novidades sem enviar; "Enviar" envia;
// "Ajustes" guarda o endereço do IP-Checker, o token (mostrado só mascarado) e o modo
// semi-automático. Sem framework: o popup é pequeno e abre a cada clique no ícone.

import { ENDERECO_PADRAO } from "../config";
import type { Estado, Pedido, Resposta } from "../mensagens";
import type { Resumo, ResultadoEnvio } from "../sincronizacao/sincronizar";

export interface ApiDoPopup {
  pedir(pedido: Pedido): Promise<Resposta>;
  gravar(dados: { endereco?: string; token?: string; semiAutomatico?: boolean }): Promise<void>;
  /** Pede ao Chrome o acesso a um endereço local (optional_host_permissions). */
  permitir(origem: string): Promise<boolean>;
}

const LOCAL = /^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/;

/** O endereço sem barra no fim, ou o motivo de recusa. */
export function conferirEndereco(valor: string): { ok: true; endereco: string; local: boolean } | {
  ok: false;
  motivo: string;
} {
  let url: URL;
  try {
    url = new URL(valor.trim());
  } catch {
    return { ok: false, motivo: "Endereço inválido." };
  }
  const origem = url.origin;
  if (origem === ENDERECO_PADRAO) return { ok: true, endereco: origem, local: false };
  if (LOCAL.test(origem)) return { ok: true, endereco: origem, local: true };
  return {
    ok: false,
    motivo: `Use o endereço do piloto (${ENDERECO_PADRAO}) ou um local (http://127.0.0.1:porta).`,
  };
}

export function textoDoResumo(resumo: Resumo | null): string {
  if (resumo === null) return "Ainda sem verificação.";
  const quando = new Date(resumo.em).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
  const novidades =
    resumo.novasOuAlteradas === 0 && resumo.sumidas === 0
      ? "nada novo"
      : `${plural(resumo.novasOuAlteradas, "questão nova ou alterada", "questões novas ou alteradas")}, ` +
        `${plural(resumo.sumidas, "sumida", "sumidas")}`;
  return (
    `${resumo.periodo}: ${plural(resumo.listas, "lista", "listas")}, ` +
    `${plural(resumo.questoes, "questão", "questões")}; ${novidades}. Verificado em ${quando}.`
  );
}

export function textoDoEnvio(envio: ResultadoEnvio): string {
  return (
    `Enviado: ${plural(envio.criadas, "questão nova", "questões novas")}, ` +
    `${plural(envio.atualizadas, "alterada", "alteradas")}.`
  );
}

function plural(n: number, um: string, varios: string): string {
  return `${n} ${n === 1 ? um : varios}`;
}

export function iniciarPopup(doc: Document, api: ApiDoPopup): Promise<void> {
  const el = <T extends HTMLElement>(id: string) => doc.getElementById(id) as T;
  const resumo = el<HTMLParagraphElement>("resumo");
  const situacao = el<HTMLParagraphElement>("situacao");
  const verificar = el<HTMLButtonElement>("verificar");
  const enviar = el<HTMLButtonElement>("enviar");
  const endereco = el<HTMLInputElement>("endereco");
  const token = el<HTMLInputElement>("token");
  const tokenAtual = el<HTMLElement>("token-atual");
  const semi = el<HTMLInputElement>("semi");
  const ajustes = el<HTMLDetailsElement>("ajustes");
  const formulario = el<HTMLFormElement>("formulario");

  const avisar = (texto: string, erro = false) => {
    situacao.textContent = texto;
    situacao.classList.toggle("erro", erro);
  };

  const mostrar = (estado: Estado) => {
    resumo.textContent = textoDoResumo(estado.resumo);
    endereco.value = estado.endereco;
    semi.checked = estado.semiAutomatico;
    tokenAtual.textContent = estado.token
      ? `Token salvo: ${estado.token}. Cole outro para trocar.`
      : "Crie o token no Perfil do IP-Checker e cole aqui.";
    enviar.disabled = !(estado.pendentes > 0 || (estado.resumo?.novasOuAlteradas ?? 0) > 0);
    if (!estado.token) ajustes.open = true;
  };

  const executar = async (pedido: Pedido, ocupado: string) => {
    verificar.disabled = true;
    enviar.disabled = true;
    avisar(ocupado);
    try {
      const resposta = await api.pedir(pedido);
      if (resposta.estado) mostrar(resposta.estado);
      if (!resposta.ok) {
        avisar(resposta.erro.mensagem, true);
      } else if (resposta.envio) {
        avisar(textoDoEnvio(resposta.envio));
      } else {
        avisar("");
      }
    } catch {
      avisar("A extensão não respondeu; feche e abra o popup de novo.", true);
    } finally {
      verificar.disabled = false;
    }
  };

  verificar.addEventListener("click", () => {
    void executar({ tipo: "verificar" }, "Lendo o Dikastis (leva alguns segundos)…");
  });
  enviar.addEventListener("click", () => {
    void executar({ tipo: "enviar" }, "Enviando ao IP-Checker…");
  });
  formulario.addEventListener("submit", (evento) => {
    evento.preventDefault();
    void salvar();
  });

  const salvar = async () => {
    const conferido = conferirEndereco(endereco.value);
    if (!conferido.ok) {
      avisar(conferido.motivo, true);
      return;
    }
    const novo = token.value.trim();
    if (novo !== "" && !/^ipc_imp_[\w-]{20,}$/.test(novo)) {
      avisar("Esse não parece um token de importação (começa com ipc_imp_).", true);
      return;
    }
    if (conferido.local && !(await api.permitir(`${conferido.endereco}/*`))) {
      avisar("Sem a permissão do Chrome para esse endereço local.", true);
      return;
    }
    await api.gravar({
      endereco: conferido.endereco,
      semiAutomatico: semi.checked,
      ...(novo !== "" ? { token: novo } : {}),
    });
    token.value = "";
    avisar("Ajustes salvos.");
    const resposta = await api.pedir({ tipo: "estado" });
    if (resposta.estado) mostrar(resposta.estado);
  };

  return (async () => {
    const resposta = await api.pedir({ tipo: "estado" });
    if (resposta.estado) mostrar(resposta.estado);
  })();
}

/* v8 ignore start -- a ligação com o Chrome; o resto é testado com uma API falsa */
if (typeof chrome !== "undefined" && chrome.runtime?.id) {
  void iniciarPopup(document, {
    pedir: (pedido) => chrome.runtime.sendMessage<Pedido, Resposta>(pedido),
    gravar: (dados) => chrome.storage.local.set(dados),
    permitir: (origem) => chrome.permissions.request({ origins: [origem] }),
  });
}
/* v8 ignore stop */
